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
    RoutePointCreate,
    RoutePointUpdate,
    RoutePointsBatchUpdate,
    RoutePointPhotoUpload,
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


@router.get("/search", summary="关键词搜索路线")
async def search_routes(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """根据关键词搜索路线（支持路线名、城市、标签等）"""
    if not keyword.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "keyword 不能为空"}
        )
    results = await service.search_by_keyword(keyword.strip(), limit)
    return {"success": True, "total": len(results), "data": results}


@router.get("/{route_id}", response_model=RouteDetail, summary="获取路线详情")
async def get_route(
    route_id: str,
    lightweight: bool = Query(True, description="返回精简版轨迹点数据"),
    service: RouteService = Depends(get_route_service)
) -> RouteDetail:
    """获取指定路线的详细信息
    
    Args:
        lightweight: 是否返回精简版轨迹点（只包含location、elevation、timestamp）
    """
    route = await service.get_route_by_id(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")
    
    # 精简轨迹点数据
    if lightweight and "points" in route:
        route["points"] = [
            {
                "location": p.get("location"),
                "elevation": p.get("elevation"),
                "timestamp": p.get("timestamp")
            }
            for p in route["points"]
        ]
    
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


# === 轨迹点编辑API ===

@router.post("/{route_id}/points", summary="添加轨迹点")
async def add_route_point(
    route_id: str,
    index: int = Query(..., ge=0, description="插入位置"),
    point_data: RoutePointCreate = ...,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """
    在指定位置添加轨迹点

    - **index**: 插入位置（0表示起点，len表示终点）
    - **point_data**: 轨迹点数据
    """
    route = await service.add_point(route_id, index, point_data.model_dump())
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在或索引越界")
    return {"success": True, "data": route}


@router.put("/{route_id}/points/{index}", summary="更新轨迹点")
async def update_route_point(
    route_id: str,
    index: int,
    updates: RoutePointUpdate,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """更新指定轨迹点的信息"""
    route = await service.update_point(route_id, index, updates.model_dump(exclude_unset=True))
    if not route:
        raise HTTPException(status_code=404, detail="路线或轨迹点不存在")
    return {"success": True, "data": route}


@router.delete("/{route_id}/points/{index}", summary="删除轨迹点")
async def delete_route_point(
    route_id: str,
    index: int,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """删除指定轨迹点（路线至少保留2个点）"""
    route = await service.delete_point(route_id, index)
    if not route:
        raise HTTPException(status_code=400, detail="路线不存在、索引越界或点数过少")
    return {"success": True, "data": route}


@router.patch("/{route_id}/points", summary="批量更新轨迹点")
async def batch_update_points(
    route_id: str,
    batch_data: RoutePointsBatchUpdate,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """
    批量更新轨迹点

    操作顺序：先删除 → 再更新 → 最后添加
    """
    route = await service.batch_update_points(route_id, batch_data.model_dump())
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在或操作失败")
    return {"success": True, "data": route}


@router.post("/{route_id}/points/{index}/photos", summary="为轨迹点添加照片")
async def add_point_photo(
    route_id: str,
    index: int,
    photo_data: RoutePointPhotoUpload,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """
    为轨迹点添加照片（Base64内嵌）

    - 单张照片最大500KB
    - 每个点最多5张照片
    """
    route = await service.add_photo_to_point(route_id, index, photo_data.model_dump())
    if not route:
        raise HTTPException(status_code=400, detail="添加失败（路线不存在、索引越界或照片数量超限）")
    return {"success": True, "data": route}


@router.delete("/{route_id}/points/{index}/photos/{photo_id}", summary="删除轨迹点照片")
async def delete_point_photo(
    route_id: str,
    index: int,
    photo_id: str,
    service: RouteService = Depends(get_route_service)
) -> dict[str, Any]:
    """删除轨迹点的指定照片"""
    route = await service.delete_photo_from_point(route_id, index, photo_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线或照片不存在")
    return {"success": True, "data": route}
