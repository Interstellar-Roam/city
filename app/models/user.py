"""用户数据模型"""

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class User(BaseModel):
    """用户模型"""

    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    username: str
    email: str | None = None
    avatar: str | None = None
    bio: str | None = None

    # 用户统计
    total_distance: float = 0.0  # 总步行距离
    total_routes: int = 0  # 完成的路线数
    total_time: int = 0  # 总步行时间(分钟)

    # 收藏和创建的路线
    favorite_routes: list[str] = Field(default_factory=list)
    created_routes: list[str] = Field(default_factory=list)

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
