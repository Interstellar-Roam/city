"""路线相关API路由"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.database import Database
from app.schemas.route import (
    PaginatedRoutes,
    RouteCreate,
    RouteDetail,
    RouteUpdate,
)
from app.services.route_service import RouteService

router = APIRouter(prefix="/routes", tags=["路线管理"])


def get_route_service() -> RouteService:
    """获取路线服务实例"""
    return RouteService(Database.get_db())


@router.post("", response_model=dict[str, Any], summary="创建路线")
async def create_route(
    route_data: RouteCreate,
    user_id: str | None = Query(None, description="用户ID"),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """
    创建新的徒步路线

    - **name**: 路线名称
    - **description**: 路线描述
    - **points**: 路线点数据
    - **start_location**: 起点坐标
    """
    route = await service.create_route(route_data, user_id)
    return {"success": True, "data": route}


@router.get("", response_model=PaginatedRoutes, summary="获取路线列表")
async def list_routes(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    city: str | None = Query(None, description="城市"),
    difficulty: str | None = Query(None, description="难度"),
    tags: str | None = Query(None, description="标签（逗号分隔）"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: int = Query(-1, ge=-1, le=1, description="排序方向"),
    longitude: float | None = Query(None, description="经度（用于附近搜索）"),
    latitude: float | None = Query(None, description="纬度（用于附近搜索）"),
    max_distance: float = Query(5000, description="最大距离（米）"),
    service: RouteService = Depends(get_route_service)
) -> PaginatedRoutes:
    """
    分页获取路线列表

    支持按城市、难度、标签筛选，支持按距离排序
    """
    tags_list = tags.split(",") if tags else None
    near_location = (longitude, latitude) if longitude and latitude else None

    return await service.list_routes(
        page=page,
        page_size=page_size,
        city=city,
        difficulty=difficulty,
        tags=tags_list,
        sort_by=sort_by,
        sort_order=sort_order,
        near_location=near_location,
        max_distance=max_distance
    )


@router.get("/{route_id}", response_model=RouteDetail, summary="获取路线详情")
async def get_route(
    route_id: str,
    service: RouteService = Depends(get_route_service)
) -> RouteDetail:
    """获取指定路线的详细信息"""
    route = await service.get_route_by_id(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")
    return RouteDetail(**route)


@router.put("/{route_id}", response_model=dict[str, Any], summary="更新路线")
async def update_route(
    route_id: str,
    route_data: RouteUpdate,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """更新路线信息"""
    route = await service.update_route(route_id, route_data)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")
    return {"success": True, "data": route}


@router.delete("/{route_id}", summary="删除路线")
async def delete_route(
    route_id: str,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """删除路线"""
    success = await service.delete_route(route_id)
    if not success:
        raise HTTPException(status_code=404, detail="路线不存在")
    return {"success": True, "message": "路线已删除"}


@router.post("/{route_id}/favorite", summary="收藏/取消收藏路线")
async def toggle_favorite(
    route_id: str,
    user_id: str = Query(..., description="用户ID"),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """切换路线的收藏状态"""
    is_favorited = await service.toggle_favorite(route_id, user_id)
    action = "已收藏" if is_favorited else "已取消收藏"
    return {"success": True, "message": action}


@router.get("/search/{keyword}", summary="关键词搜索路线")
async def search_routes(
    keyword: str,
    limit: int = Query(20, ge=1, le=100),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """根据关键词搜索路线"""
    results = await service.search_by_keyword(keyword, limit)
    return {"success": True, "total": len(results), "data": results}
