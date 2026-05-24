"""路线业务服务"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.route import Route
from app.schemas.route import PaginatedRoutes, RouteCreate, RouteListItem, RouteUpdate, RouteDetail
from app.utils.photo import prepare_photo_for_storage, config as photo_config


class RouteService:
    """路线服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.routes

    async def create_route(self, route_data: RouteCreate, user_id: str | None = None) -> dict[str, Any]:
        """创建新路线"""
        route_dict = route_data.model_dump()

        # 转换location格式
        start_loc = route_dict.pop("start_location")
        route_dict["start_location"] = {
            "type": "Point",
            "coordinates": [start_loc["longitude"], start_loc["latitude"]]
        }

        if end_loc := route_dict.pop("end_location"):
            route_dict["end_location"] = {
                "type": "Point",
                "coordinates": [end_loc["longitude"], end_loc["latitude"]]
            }

        route_dict["_id"] = str(ObjectId())
        route_dict["created_by"] = user_id
        route_dict["created_at"] = datetime.now()
        route_dict["updated_at"] = datetime.now()
        route_dict["favorites_count"] = 0
        route_dict["views_count"] = 0
        route_dict["completions_count"] = 0

        await self.collection.insert_one(route_dict)
        logger.info(f"创建路线: {route_dict['_id']}")

        return route_dict

    async def get_route_by_id(self, route_id: str, increment_view: bool = True) -> dict[str, Any] | None:
        """获取路线详情"""
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.collection.find_one({"_id": route_id})
        if not route:
            return None

        # 增加浏览次数
        if increment_view:
            await self.collection.update_one(
                {"_id": route_id},
                {"$inc": {"views_count": 1}}
            )

        return route

    async def list_routes(
        self,
        page: int = 1,
        page_size: int = 20,
        city: str | None = None,
        difficulty: str | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
        sort_by: str = "created_at",
        sort_order: int = -1,
        near_location: tuple[float, float] | None = None,  # (lon, lat)
        max_distance: float = 5000,  # 米
        exclude_unpublished: bool = True,
    ) -> PaginatedRoutes:
        """分页获取路线列表"""
        skip = (page - 1) * page_size
        query: dict[str, Any] = {}
        if exclude_unpublished:
            query["is_published"] = True

        # 过滤条件
        if city:
            query["city"] = city
        if difficulty:
            query["difficulty"] = difficulty
        if tags:
            query["tags"] = {"$in": tags}
        if created_by:
            query["created_by"] = created_by

        # 位置过滤
        if near_location:
            query["start_location"] = {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": list(near_location)
                    },
                    "$maxDistance": max_distance
                }
            }

        # 排序
        sort_field = sort_by
        if near_location and sort_by == "created_at":
            sort_field = None  # near查询自带排序

        # 查询总数
        total = await self.collection.count_documents(query)

        # 查询数据
        cursor = self.collection.find(query)
        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)
        cursor = cursor.skip(skip).limit(page_size)

        items = await cursor.to_list(length=page_size)

        return PaginatedRoutes(
            items=[RouteListItem(**item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            has_more=skip + len(items) < total
        )

    async def get_featured_routes(self, limit: int = 5) -> list[dict[str, Any]]:
        """获取精选路线列表"""
        cursor = self.collection.find(
            {"is_featured": True, "is_published": True}
        ).sort("favorites_count", -1).limit(limit)
        routes = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            routes.append(RouteListItem(**doc).model_dump())
        return routes

    async def update_route(self, route_id: str, route_data: RouteUpdate) -> dict[str, Any] | None:
        """更新路线"""
        if not ObjectId.is_valid(route_id):
            return None

        update_dict = route_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_route_by_id(route_id, increment_view=False)

        update_dict["updated_at"] = datetime.now()

        result = await self.collection.find_one_and_update(
            {"_id": route_id},
            {"$set": update_dict},
            return_document=True
        )

        return result

    async def delete_route(self, route_id: str) -> bool:
        """删除路线"""
        if not ObjectId.is_valid(route_id):
            return False

        result = await self.collection.delete_one({"_id": route_id})
        return result.deleted_count > 0

    async def toggle_favorite(self, route_id: str, user_id: str) -> bool:
        """切换收藏状态"""
        if not ObjectId.is_valid(route_id):
            return False

        # 检查是否已收藏
        user_col = self.db.users
        user = await user_col.find_one({"_id": user_id})

        if not user:
            return False

        is_favorited = route_id in user.get("favorite_routes", [])

        if is_favorited:
            # 取消收藏
            await user_col.update_one(
                {"_id": user_id},
                {"$pull": {"favorite_routes": route_id}}
            )
            await self.collection.update_one(
                {"_id": route_id},
                {"$inc": {"favorites_count": -1}}
            )
        else:
            # 添加收藏
            await user_col.update_one(
                {"_id": user_id},
                {"$push": {"favorite_routes": route_id}}
            )
            await self.collection.update_one(
                {"_id": route_id},
                {"$inc": {"favorites_count": 1}}
            )

        return not is_favorited

    async def search_by_keyword(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        """多字段关键词搜索，支持 $text 优先 + $regex 降级

        搜索范围: name, description, tags, city, district, pois.name, pois.tags
        """
        import re

        keyword = keyword.strip()[:200]  # 截断超长输入

        if not keyword:
            return []

        # 策略1: 使用 $text 索引搜索
        cursor = self.collection.find(
            {"$text": {"$search": keyword}, "is_published": True},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = await cursor.to_list(length=limit)

        # 策略2: $text 无结果时降级为 $regex 模糊匹配
        if not results:
            pattern = re.escape(keyword)
            cursor = self.collection.find(
                {
                    "is_published": True,
                    "$or": [
                        {"name": {"$regex": pattern, "$options": "i"}},
                        {"description": {"$regex": pattern, "$options": "i"}},
                        {"tags": {"$regex": pattern, "$options": "i"}},
                        {"city": {"$regex": pattern, "$options": "i"}},
                        {"district": {"$regex": pattern, "$options": "i"}},
                        {"pois.name": {"$regex": pattern, "$options": "i"}},
                        {"pois.tags": {"$regex": pattern, "$options": "i"}},
                    ]
                }
            ).limit(limit)
            results = await cursor.to_list(length=limit)

        return results

    # === 轨迹点编辑相关方法 ===

    async def add_point(
        self,
        route_id: str,
        index: int,
        point_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        在指定位置添加轨迹点

        Args:
            route_id: 路线ID
            index: 插入位置（0表示起点）
            point_data: 点数据 {longitude, latitude, elevation, name, description, is_waypoint}

        Returns:
            更新后的路线
        """
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])
        
        # 边界检查
        if index < 0 or index > len(points):
            return None

        # 构建新点
        new_point = {
            "location": {
                "type": "Point",
                "coordinates": [point_data["longitude"], point_data["latitude"]]
            },
            "elevation": point_data.get("elevation"),
            "name": point_data.get("name"),
            "description": point_data.get("description"),
            "is_waypoint": point_data.get("is_waypoint", False),
            "photos": [],
            "is_edited": True,
        }

        # 插入点
        points.insert(index, new_point)

        # 更新路线
        return await self._update_points_and_stats(route_id, points)

    async def update_point(
        self,
        route_id: str,
        index: int,
        updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        更新指定轨迹点

        Args:
            route_id: 路线ID
            index: 点索引
            updates: 更新数据 {longitude, latitude, name, description, is_waypoint}

        Returns:
            更新后的路线
        """
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])

        if index < 0 or index >= len(points):
            return None

        point = points[index]

        # 保存原始位置
        if ("longitude" in updates or "latitude" in updates) and not point.get("original_location"):
            point["original_location"] = point["location"]

        # 更新坐标
        if "longitude" in updates or "latitude" in updates:
            lon = updates.get("longitude", point["location"]["coordinates"][0])
            lat = updates.get("latitude", point["location"]["coordinates"][1])
            point["location"]["coordinates"] = [lon, lat]

        # 更新其他字段
        if "name" in updates:
            point["name"] = updates["name"]
        if "description" in updates:
            point["description"] = updates["description"]
        if "is_waypoint" in updates:
            point["is_waypoint"] = updates["is_waypoint"]

        point["is_edited"] = True
        points[index] = point

        return await self._update_points_and_stats(route_id, points)

    async def delete_point(self, route_id: str, index: int) -> dict[str, Any] | None:
        """
        删除指定轨迹点

        Args:
            route_id: 路线ID
            index: 点索引

        Returns:
            更新后的路线
        """
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])

        if index < 0 or index >= len(points):
            return None

        # 至少保留2个点
        if len(points) <= 2:
            return None

        del points[index]

        return await self._update_points_and_stats(route_id, points)

    async def batch_update_points(
        self,
        route_id: str,
        batch_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        批量更新轨迹点

        Args:
            route_id: 路线ID
            batch_data: {add_points, update_points, delete_indices}

        Returns:
            更新后的路线
        """
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])

        # 先删除（从后往前，避免索引变化）
        delete_indices = sorted(batch_data.get("delete_indices", []), reverse=True)
        for idx in delete_indices:
            if 0 <= idx < len(points):
                del points[idx]

        # 再更新
        for item in batch_data.get("update_points", []):
            idx = item.get("index")
            updates = item.get("updates", {})
            if idx is not None and 0 <= idx < len(points):
                if "longitude" in updates or "latitude" in updates:
                    lon = updates.get("longitude", points[idx]["location"]["coordinates"][0])
                    lat = updates.get("latitude", points[idx]["location"]["coordinates"][1])
                    points[idx]["location"]["coordinates"] = [lon, lat]
                for key in ["name", "description", "is_waypoint"]:
                    if key in updates:
                        points[idx][key] = updates[key]
                points[idx]["is_edited"] = True

        # 最后添加（按索引排序）
        add_points = sorted(batch_data.get("add_points", []), key=lambda x: x.get("index", 0))
        for item in add_points:
            idx = item.get("index", len(points))
            pt = item.get("point", {})
            new_point = {
                "location": {
                    "type": "Point",
                    "coordinates": [pt.get("longitude", 0), pt.get("latitude", 0)]
                },
                "name": pt.get("name"),
                "description": pt.get("description"),
                "is_waypoint": pt.get("is_waypoint", False),
                "photos": [],
                "is_edited": True,
            }
            points.insert(min(idx, len(points)), new_point)

        return await self._update_points_and_stats(route_id, points)

    async def add_photo_to_point(
        self,
        route_id: str,
        point_index: int,
        photo_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        为轨迹点添加照片

        Args:
            route_id: 路线ID
            point_index: 点索引
            photo_data: {data, content_type, caption}

        Returns:
            更新后的路线
        """
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])

        if point_index < 0 or point_index >= len(points):
            return None

        point = points[point_index]
        photos = point.get("photos", [])

        # 检查照片数量限制
        if len(photos) >= photo_config.max_photos_per_point:
            return None

        # 准备照片数据
        try:
            photo = prepare_photo_for_storage(
                data=photo_data["data"],
                content_type=photo_data.get("content_type"),
                caption=photo_data.get("caption"),
            )
        except ValueError as e:
            logger.error(f"照片处理失败: {e}")
            return None

        photos.append(photo)
        point["photos"] = photos
        point["is_edited"] = True

        # 更新数据库
        await self.collection.update_one(
            {"_id": route_id},
            {
                "$set": {
                    f"points.{point_index}": point,
                    "updated_at": datetime.now()
                }
            }
        )

        return await self.get_route_by_id(route_id, increment_view=False)

    async def delete_photo_from_point(
        self,
        route_id: str,
        point_index: int,
        photo_id: str
    ) -> dict[str, Any] | None:
        """删除轨迹点的照片"""
        if not ObjectId.is_valid(route_id):
            return None

        route = await self.get_route_by_id(route_id, increment_view=False)
        if not route:
            return None

        points = route.get("points", [])

        if point_index < 0 or point_index >= len(points):
            return None

        point = points[point_index]
        photos = point.get("photos", [])

        # 过滤掉指定照片
        point["photos"] = [p for p in photos if p.get("id") != photo_id]
        point["is_edited"] = True

        await self.collection.update_one(
            {"_id": route_id},
            {
                "$set": {
                    f"points.{point_index}": point,
                    "updated_at": datetime.now()
                }
            }
        )

        return await self.get_route_by_id(route_id, increment_view=False)

    async def _update_points_and_stats(
        self,
        route_id: str,
        points: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """更新轨迹点并重新计算统计信息"""
        # 计算距离和爬升
        distance = 0.0
        elevation_gain = 0.0

        for i in range(1, len(points)):
            prev = points[i - 1]["location"]["coordinates"]
            curr = points[i]["location"]["coordinates"]
            distance += _haversine(prev[1], prev[0], curr[1], curr[0])

            prev_ele = points[i - 1].get("elevation")
            curr_ele = points[i].get("elevation")
            if prev_ele is not None and curr_ele is not None:
                diff = curr_ele - prev_ele
                if diff > 0:
                    elevation_gain += diff

        # 更新起点终点
        start_location = points[0]["location"] if points else None
        end_location = points[-1]["location"] if points else None

        await self.collection.update_one(
            {"_id": route_id},
            {
                "$set": {
                    "points": points,
                    "distance": distance,
                    "elevation_gain": elevation_gain,
                    "start_location": start_location,
                    "end_location": end_location,
                    "updated_at": datetime.now()
                }
            }
        )

        return await self.get_route_by_id(route_id, increment_view=False)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离（米）"""
    import math
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
