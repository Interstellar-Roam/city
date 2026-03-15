"""GPS轨迹API路由"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import Database
from app.schemas.route import GPSTrackCreate, GPSTrackUpdate, GPSTrackResponse
from app.services.gps_service import GPSService

router = APIRouter(prefix="/gps", tags=["GPS轨迹"])


def get_gps_service() -> GPSService:
    """获取GPS服务实例"""
    return GPSService(Database.get_db())


@router.post("", response_model=dict[str, Any], summary="创建GPS轨迹")
async def create_track(
    track_data: GPSTrackCreate,
    service: GPSService = Depends(get_gps_service)
) -> dict[str, Any]:
    """
    创建新的GPS轨迹记录

    - **points**: GPS点数据列表，每个点包含location、elevation、timestamp等
    - **route_id**: 关联的路线ID（可选）
    - **user_id**: 用户ID（可选）
    """
    track = await service.create_track(track_data)
    return {"success": True, "data": track}


@router.get("/{track_id}", response_model=GPSTrackResponse, summary="获取轨迹详情")
async def get_track(
    track_id: str,
    service: GPSService = Depends(get_gps_service)
) -> GPSTrackResponse:
    """获取指定GPS轨迹的详细信息"""
    track = await service.get_track_by_id(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="轨迹不存在")
    return GPSTrackResponse(**track)


@router.get("/user/{user_id}", summary="获取用户轨迹列表")
async def list_user_tracks(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: GPSService = Depends(get_gps_service)
) -> dict[str, Any]:
    """获取用户的所有GPS轨迹记录"""
    result = await service.list_user_tracks(user_id, page, page_size)
    return {"success": True, **result}


@router.put("/{track_id}", response_model=dict[str, Any], summary="更新轨迹")
async def update_track(
    track_id: str,
    track_data: GPSTrackUpdate,
    service: GPSService = Depends(get_gps_service)
) -> dict[str, Any]:
    """更新GPS轨迹信息"""
    track = await service.update_track(track_id, track_data)
    if not track:
        raise HTTPException(status_code=404, detail="轨迹不存在")
    return {"success": True, "data": track}


@router.delete("/{track_id}", summary="删除轨迹")
async def delete_track(
    track_id: str,
    service: GPSService = Depends(get_gps_service)
) -> dict[str, Any]:
    """删除GPS轨迹"""
    success = await service.delete_track(track_id)
    if not success:
        raise HTTPException(status_code=404, detail="轨迹不存在")
    return {"success": True, "message": "轨迹已删除"}
