"""用户相关 schemas"""

from pydantic import BaseModel, Field


class UserStats(BaseModel):
    """用户统计数据"""
    total_distance_km: float = Field(0.0, description="总里程(km)")
    route_count: int = Field(0, description="路线数")
    favorite_count: int = Field(0, description="收藏数")


class UserProfile(BaseModel):
    """用户信息"""
    phone: str
    nickname: str | None = None
    avatar: str | None = None
    stats: UserStats = Field(default_factory=UserStats)


class UserUpdate(BaseModel):
    """更新用户信息"""
    nickname: str | None = Field(None, max_length=20)
    avatar: str | None = None
