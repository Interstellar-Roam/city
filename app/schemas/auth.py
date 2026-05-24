"""认证相关 API Schema"""

from pydantic import BaseModel, Field


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., examples=["13800138000"], description="11位手机号")


class LoginRequest(BaseModel):
    """登录请求"""
    phone: str = Field(..., description="手机号")
    code: str = Field(..., min_length=6, max_length=6, description="6位验证码")


class RefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(..., description="Refresh Token")
