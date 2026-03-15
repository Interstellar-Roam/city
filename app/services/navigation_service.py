"""导航业务服务"""

from typing import Any

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.route import NavigationData


class NavigationService:
    """导航服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.routes_col = db.routes

    async def get_navigation_data(self, route_id: str) -> NavigationData | None:
        """获取路线导航数据"""
        route = await self.routes_col.find_one({"_id": route_id})
        if not route:
            return None

        # 构建海拔剖面
        elevation_profile = self._build_elevation_profile(route.get("points", []))

        return NavigationData(
            route_id=route_id,
            points=route.get("points", []),
            pois=route.get("pois", []),
            elevation_profile=elevation_profile,
            total_distance=route.get("distance", 0),
            total_elevation_gain=route.get("elevation_gain", 0),
            estimated_time=route.get("estimated_duration", 0)
        )

    def _build_elevation_profile(self, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """构建海拔剖面数据"""
        profile = []
        accumulated_distance = 0.0

        for i, point in enumerate(points):
            if i > 0 and "location" in points[i - 1] and "location" in point:
                # 计算距离增量
                import math
                prev = points[i - 1]["location"]["coordinates"]
                curr = point["location"]["coordinates"]
                lon_diff = curr[0] - prev[0]
                lat_diff = curr[1] - prev[1]
                # 粗略计算（实际应使用Haversine）
                accumulated_distance += math.sqrt(lon_diff**2 + lat_diff**2) * 111000

            profile.append({
                "distance": accumulated_distance,
                "elevation": point.get("elevation", 0)
            })

        return profile

    async def calculate_user_progress(
        self,
        route_id: str,
        user_location: tuple[float, float]
    ) -> dict[str, Any]:
        """计算用户在路线上的进度"""
        route = await self.routes_col.find_one({"_id": route_id})
        if not route:
            return {"error": "路线不存在"}

        points = route.get("points", [])
        if not points:
            return {"error": "路线没有点数据"}

        # 找到最近的路线点
        min_distance = float('inf')
        nearest_idx = 0

        for i, point in enumerate(points):
            if "location" not in point:
                continue
            coords = point["location"]["coordinates"]
            import math
            dist = math.sqrt(
                (coords[0] - user_location[0])**2 +
                (coords[1] - user_location[1])**2
            )
            if dist < min_distance:
                min_distance = dist
                nearest_idx = i

        # 计算进度
        progress = (nearest_idx + 1) / len(points) * 100

        return {
            "route_id": route_id,
            "progress": progress,
            "current_point_idx": nearest_idx,
            "total_points": len(points),
            "distance_to_nearest": min_distance * 111000  # 粗略转换
        }
