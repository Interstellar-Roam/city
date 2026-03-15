"""路线业务服务"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.route import Route
from app.schemas.route import PaginatedRoutes, RouteCreate, RouteListItem, RouteUpdate, RouteDetail


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
        route_dict["is_published"] = True

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
        sort_by: str = "created_at",
        sort_order: int = -1,
        near_location: tuple[float, float] | None = None,  # (lon, lat)
        max_distance: float = 5000,  # 米
    ) -> PaginatedRoutes:
        """分页获取路线列表"""
        skip = (page - 1) * page_size
        query: dict[str, Any] = {"is_published": True}

        # 过滤条件
        if city:
            query["city"] = city
        if difficulty:
            query["difficulty"] = difficulty
        if tags:
            query["tags"] = {"$in": tags}

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
        """关键词搜索"""
        cursor = self.collection.find(
            {"$text": {"$search": keyword}, "is_published": True},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        return await cursor.to_list(length=limit)
