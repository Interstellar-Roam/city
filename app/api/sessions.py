"""会话相关API路由"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.database import Database
from app.schemas.session import SessionCreate, SessionDetail, SessionUpdate
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["会话管理"])


def get_session_service() -> SessionService:
    """获取会话服务实例"""
    return SessionService(Database.get_db())


@router.post("", response_model=dict[str, Any], summary="创建会话")
async def create_session(
    session_data: SessionCreate,
    service: SessionService = Depends(get_session_service)
) -> dict[str, Any]:
    """
    创建新的聊天会话

    - **user_id**: 用户ID
    - **title**: 会话标题（可选）
    - **context**: 会话上下文（可选）
    """
    session_id = await service.create_session(
        user_id=session_data.user_id,
        title=session_data.title,
        context=session_data.context
    )
    return {"success": True, "session_id": session_id}


@router.get("/user/{user_id}", summary="获取用户会话列表")
async def get_user_sessions(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: SessionService = Depends(get_session_service)
) -> dict[str, Any]:
    """获取指定用户的所有会话"""
    sessions = await service.get_user_sessions(user_id, limit, offset)
    return {
        "success": True,
        "total": len(sessions),
        "sessions": [s.model_dump() for s in sessions]
    }


@router.get("/{session_id}", response_model=SessionDetail, summary="获取会话详情")
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> SessionDetail:
    """获取指定会话的详细信息，包括所有消息"""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.put("/{session_id}", summary="更新会话")
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    service: SessionService = Depends(get_session_service)
) -> dict[str, Any]:
    """更新会话信息"""
    success = await service.update_session(
        session_id,
        title=session_data.title,
        context=session_data.context
    )
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已更新"}


@router.delete("/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> dict[str, Any]:
    """删除指定会话"""
    success = await service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}


@router.get("/preference/{user_id}", summary="获取用户偏好")
async def get_user_preference(
    user_id: str,
    service: SessionService = Depends(get_session_service)
) -> dict[str, Any]:
    """获取用户的路线偏好"""
    preference = await service.get_user_preference(user_id)
    analysis = await service.analyze_user_preference_from_history(user_id)

    return {
        "success": True,
        "preference": preference.model_dump() if preference else None,
        "history_analysis": analysis
    }
