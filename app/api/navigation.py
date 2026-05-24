"""导航API路由"""

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.config import get_settings
from app.database import Database
from app.middleware.auth import get_current_user
from app.schemas.route import NavigationData
from app.services.route_service import RouteService

router = APIRouter(prefix="/navigation", tags=["导航"])


def get_route_service() -> RouteService:
    """获取路线服务实例"""
    return RouteService(Database.get_db())


@router.get("/{route_id}", response_model=NavigationData, summary="获取导航数据")
async def get_navigation_data(
    route_id: str,
    service: RouteService = Depends(get_route_service)
) -> NavigationData:
    """
    获取路线的导航数据

    包括：
    - 路线点信息
    - POI兴趣点
    - 海拔剖面
    - 总距离和爬升
    """
    route = await service.get_route_by_id(route_id, increment_view=False)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    # 构建海拔剖面
    elevation_profile = []
    accumulated_distance = 0.0
    points = route.get("points", [])

    for i, point in enumerate(points):
        if i > 0 and "location" in points[i - 1] and "location" in point:
            # 计算累计距离
            prev_coords = points[i - 1]["location"]["coordinates"]
            curr_coords = point["location"]["coordinates"]
            # 简化距离计算（实际应使用Haversine公式）
            import math
            lon_diff = curr_coords[0] - prev_coords[0]
            lat_diff = curr_coords[1] - prev_coords[1]
            accumulated_distance += math.sqrt(lon_diff**2 + lat_diff**2) * 111000  # 粗略转换

        elevation_profile.append({
            "distance": accumulated_distance,
            "elevation": point.get("elevation", 0)
        })

    return NavigationData(
        route_id=route_id,
        points=points,
        pois=route.get("pois", []),
        elevation_profile=elevation_profile,
        total_distance=route.get("distance", 0),
        total_elevation_gain=route.get("elevation_gain", 0),
        estimated_time=route.get("estimated_duration", 0)
    )


@router.get("/amap/{route_id}", summary="获取高德地图导航数据")
async def get_amap_navigation(
    route_id: str,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """获取路线在高德地图上的导航数据"""
    settings = get_settings()
    if not settings.amap_api_key:
        raise HTTPException(status_code=501, detail="未配置高德地图API")

    route = await service.get_route_by_id(route_id, increment_view=False)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    # 获取路线点坐标
    points = route.get("points", [])
    if not points:
        raise HTTPException(status_code=400, detail="路线没有点数据")

    # 转换为高德地图格式
    locations = []
    for point in points:
        if "location" in point:
            coords = point["location"]["coordinates"]
            locations.append(f"{coords[0]},{coords[1]}")

    # 调用高德地图路径规划API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://restapi.amap.com/v3/direction/walking",
                params={
                    "key": settings.amap_api_key,
                    "origin": locations[0],
                    "destination": locations[-1],
                    "waypoints": "|".join(locations[1:-1]) if len(locations) > 2 else None
                }
            )
            data = response.json()
            
            if data.get("status") != "1":
                logger.error(f"高德地图API错误: {data}")
                raise HTTPException(status_code=500, detail="高德地图API调用失败")

            return {
                "success": True,
                "route_id": route_id,
                "amap_data": data
            }
        except httpx.HTTPError as e:
            logger.error(f"高德地图API请求失败: {e}")
            raise HTTPException(status_code=500, detail="高德地图API请求失败")


@router.get("/poi/{route_id}", summary="获取路线POI信息")
async def get_route_pois(
    route_id: str,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """获取路线上的所有POI兴趣点"""
    route = await service.get_route_by_id(route_id, increment_view=False)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    pois = route.get("pois", [])
    
    return {
        "success": True,
        "route_id": route_id,
        "total": len(pois),
        "pois": pois
    }


@router.post("/track/{route_id}", summary="记录用户导航轨迹")
async def record_navigation_track(
    route_id: str,
    user_id: str = Depends(get_current_user),
    longitude: float = Query(..., description="当前经度"),
    latitude: float = Query(..., description="当前纬度"),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """
    记录用户在导航过程中的位置

    用于实时跟踪用户位置，计算进度和爬升数据
    """
    current_location = {"longitude": longitude, "latitude": latitude}
    
    route = await service.get_route_by_id(route_id, increment_view=False)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    # TODO: 实现实时位置跟踪和进度计算
    # 这里可以集成WebSocket实现实时更新

    return {
        "success": True,
        "message": "位置已记录",
        "route_id": route_id,
        "current_location": current_location
    }
