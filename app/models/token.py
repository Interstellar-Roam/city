"""Token 认证数据模型"""

from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class RefreshToken(BaseModel):
    """Refresh Token 文档模型"""

    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    token: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    revoked: bool = False

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class VerificationCode(BaseModel):
    """短信验证码文档模型"""

    phone: str = Field(..., alias="_id")  # 手机号作为主键
    code: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    used: bool = False

    class Config:
        populate_by_name = True
