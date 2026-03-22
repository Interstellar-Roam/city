"""照片处理工具模块 - Base64验证、压缩、大小限制"""

import base64
import hashlib
from io import BytesIO
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field

from app.config import get_settings


class PhotoConfig(BaseModel):
    """照片配置"""

    max_size_bytes: int = 500 * 1024  # 单张最大500KB
    max_photos_per_point: int = 5  # 每个点最多5张
    allowed_types: list[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    max_dimension: int = 1920  # 最大宽高


config = PhotoConfig()


def validate_base64_image(data: str) -> tuple[bool, str | None]:
    """
    验证Base64图片数据

    Returns:
        (is_valid, error_message)
    """
    try:
        # 尝试解码
        image_data = base64.b64decode(data)

        # 检查大小
        if len(image_data) > config.max_size_bytes:
            return False, f"图片大小超过限制({config.max_size_bytes // 1024}KB)"

        # 验证图片格式
        try:
            img = Image.open(BytesIO(image_data))
            img.verify()
        except Exception:
            return False, "无效的图片格式"

        return True, None

    except Exception as e:
        return False, f"Base64解码失败: {str(e)}"


def compress_image(
    data: str,
    max_size_bytes: int | None = None,
    max_dimension: int | None = None,
    quality: int = 85
) -> str:
    """
    压缩Base64图片

    Args:
        data: Base64编码的图片
        max_size_bytes: 最大字节数（可选，默认使用配置）
        max_dimension: 最大宽高（可选，默认使用配置）
        quality: JPEG质量(1-100)

    Returns:
        压缩后的Base64字符串
    """
    max_size = max_size_bytes or config.max_size_bytes
    max_dim = max_dimension or config.max_dimension

    image_data = base64.b64decode(data)
    img = Image.open(BytesIO(image_data))

    # 转换为RGB（处理PNG透明通道）
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 缩放尺寸
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # 压缩
    output = BytesIO()
    current_quality = quality

    while current_quality >= 20:
        output.seek(0)
        output.truncate()
        img.save(output, format="JPEG", quality=current_quality, optimize=True)

        if output.tell() <= max_size:
            break

        current_quality -= 10

    return base64.b64encode(output.getvalue()).decode("utf-8")


def get_image_info(data: str) -> dict[str, Any]:
    """
    获取Base64图片信息

    Returns:
        {width, height, format, size_bytes, content_type}
    """
    image_data = base64.b64decode(data)
    img = Image.open(BytesIO(image_data))

    format_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }

    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "size_bytes": len(image_data),
        "content_type": format_map.get(img.format, "image/jpeg"),
    }


def compute_photo_hash(data: str) -> str:
    """计算照片哈希值（用于去重）"""
    return hashlib.md5(data.encode()).hexdigest()[:16]


def prepare_photo_for_storage(
    data: str,
    content_type: str | None = None,
    caption: str | None = None,
    auto_compress: bool = True
) -> dict[str, Any]:
    """
    准备照片用于存储

    Args:
        data: 原始Base64数据（可含data:xxx;base64,前缀）
        content_type: MIME类型
        caption: 照片说明
        auto_compress: 是否自动压缩

    Returns:
        符合RoutePointPhoto格式的字典
    """
    from bson import ObjectId
    from datetime import datetime

    # 处理data URL前缀
    if data.startswith("data:"):
        # 解析 data:image/jpeg;base64,xxx 格式
        header, data = data.split(",", 1)
        if not content_type and ";base64" in header:
            content_type = header.split(":")[1].split(";")[0]

    data = data.strip()
    content_type = content_type or "image/jpeg"

    # 验证
    is_valid, error = validate_base64_image(data)
    if not is_valid:
        raise ValueError(error)

    # 压缩
    original_size = len(base64.b64decode(data))
    if auto_compress:
        data = compress_image(data)

    return {
        "id": str(ObjectId()),
        "data": data,
        "content_type": content_type,
        "caption": caption,
        "size": original_size,
        "created_at": datetime.now(),
    }
