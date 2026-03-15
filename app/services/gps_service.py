"""GPS轨迹业务服务"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.route import GPSTrackCreate, GPSTrackUpdate, GPSTrackResponse
from app.utils.helpers import calculate_distance, calculate_elevation_gain


class GPSService:
    """GPS轨迹服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.gps_tracks

    async def create_track(self, track_data: GPSTrackCreate) -> dict[str, Any]:
        """创建GPS轨迹"""
        track_dict = track_data.model_dump()

        track_dict["_id"] = str(ObjectId())
        track_dict["created_at"] = datetime.now()

        # 计算统计数据
        points = track_dict["points"]
        if points:
            stats = self._calculate_track_stats(points)
            track_dict.update(stats)

        # 如果有结束时间，计算持续时间
        if track_dict.get("ended_at"):
            duration = (track_dict["ended_at"] - track_dict["started_at"]).total_seconds()
            track_dict["duration"] = int(duration)

        await self.collection.insert_one(track_dict)
        logger.info(f"创建GPS轨迹: {track_dict['_id']}")

        # 更新用户统计
        if track_dict.get("user_id"):
            await self._update_user_stats(track_dict)

        # 更新路线完成次数
        if track_dict.get("route_id"):
            await self.db.routes.update_one(
                {"_id": track_dict["route_id"]},
                {"$inc": {"completions_count": 1}}
            )

        return track_dict

    async def get_track_by_id(self, track_id: str) -> dict[str, Any] | None:
        """获取轨迹详情"""
        if not ObjectId.is_valid(track_id):
            return None

        return await self.collection.find_one({"_id": track_id})

    async def list_user_tracks(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> dict[str, Any]:
        """获取用户的轨迹列表"""
        skip = (page - 1) * page_size

        total = await self.collection.count_documents({"user_id": user_id})

        cursor = self.collection.find({"user_id": user_id}) \
            .sort("created_at", -1) \
            .skip(skip) \
            .limit(page_size)

        items = await cursor.to_list(length=page_size)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": skip + len(items) < total
        }

    async def update_track(self, track_id: str, track_data: GPSTrackUpdate) -> dict[str, Any] | None:
        """更新轨迹"""
        if not ObjectId.is_valid(track_id):
            return None

        update_dict = track_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_track_by_id(track_id)

        # 如果更新了点数据，重新计算统计
        if "points" in update_dict:
            stats = self._calculate_track_stats(update_dict["points"])
            update_dict.update(stats)

        result = await self.collection.find_one_and_update(
            {"_id": track_id},
            {"$set": update_dict},
            return_document=True
        )

        return result

    async def delete_track(self, track_id: str) -> bool:
        """删除轨迹"""
        if not ObjectId.is_valid(track_id):
            return False

        result = await self.collection.delete_one({"_id": track_id})
        return result.deleted_count > 0

    def _calculate_track_stats(self, points: list[dict[str, Any]]) -> dict[str, Any]:
        """计算轨迹统计信息"""
        if len(points) < 2:
            return {"distance": 0.0, "elevation_gain": 0.0, "average_speed": 0.0}

        total_distance = 0.0
        elevations = []

        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]

            # 计算距离
            if "location" in prev and "location" in curr:
                coords1 = prev["location"]["coordinates"]
                coords2 = curr["location"]["coordinates"]
                total_distance += calculate_distance(
                    coords1[1], coords1[0],  # lat, lon
                    coords2[1], coords2[0]
                )

            # 收集海拔数据
            if "elevation" in prev:
                elevations.append(prev["elevation"])

        if points and "elevation" in points[-1]:
            elevations.append(points[-1]["elevation"])

        elevation_gain = calculate_elevation_gain(elevations)

        # 计算平均速度
        time_diffs = []
        for i in range(1, len(points)):
            if "timestamp" in points[i] and "timestamp" in points[i - 1]:
                t1 = datetime.fromisoformat(points[i - 1]["timestamp"])
                t2 = datetime.fromisoformat(points[i]["timestamp"])
                time_diffs.append((t2 - t1).total_seconds())

        total_time = sum(time_diffs) if time_diffs else 0
        average_speed = total_distance / total_time if total_time > 0 else 0

        return {
            "distance": total_distance,
            "elevation_gain": elevation_gain,
            "average_speed": average_speed
        }

    async def _update_user_stats(self, track: dict[str, Any]) -> None:
        """更新用户统计数据"""
        user_col = self.db.users
        await user_col.update_one(
            {"_id": track["user_id"]},
            {
                "$inc": {
                    "total_distance": track["distance"],
                    "total_routes": 1 if track.get("route_id") else 0,
                    "total_time": track.get("duration", 0) // 60  # 转换为分钟
                }
            }
        )
