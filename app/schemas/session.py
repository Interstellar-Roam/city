"""会话相关数据模型"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: user/assistant/tool")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据（如工具调用信息）")


class SessionCreate(BaseModel):
    """创建会话"""
    user_id: str = Field(..., description="用户ID")
    title: str | None = Field(None, description="会话标题")
    context: dict[str, Any] | None = Field(None, description="会话上下文")


class SessionUpdate(BaseModel):
    """更新会话"""
    title: str | None = None
    context: dict[str, Any] | None = None


class SessionDetail(BaseModel):
    """会话详情"""
    id: str = Field(..., alias="_id")
    user_id: str
    title: str | None
    messages: list[ChatMessage]
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        populate_by_name = True


class SessionSummary(BaseModel):
    """会话摘要（列表项）"""
    id: str = Field(..., alias="_id")
    user_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: str | None = None

    class Config:
        populate_by_name = True


class UserPreference(BaseModel):
    """用户偏好"""
    user_id: str
    preferred_cities: list[str] = Field(default_factory=list)
    preferred_difficulty: str | None = None
    preferred_distance_range: tuple[float, float] | None = None
    preferred_tags: list[str] = Field(default_factory=list)
    search_count: int = 0
    last_active: datetime | None = None
