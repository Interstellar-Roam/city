"""统一 API 响应格式"""

from typing import Any

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """统一响应格式：{code, message, data}"""
    code: int = Field(0, description="0=成功, 1xxx=认证错误, 2xxx=鉴权错误")
    message: str = Field("ok")
    data: Any = None
