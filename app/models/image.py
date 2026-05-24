"""图片存储模型 — MongoDB BLOB 存储"""

from datetime import datetime

import shortuuid
from pydantic import BaseModel, Field


class Image(BaseModel):
    """图片文档（images 集合）"""

    id: str = Field(default_factory=lambda: shortuuid.uuid()[:12], alias="_id")
    data: bytes = Field(..., description="二进制图片数据")
    content_type: str = Field(default="image/jpeg", description="MIME 类型")
    size: int = Field(default=0, description="文件大小（字节）")
    route_id: str | None = Field(None, description="关联路线 ID")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        json_encoders = {bytes: lambda v: f"<{len(v)} bytes>"}
