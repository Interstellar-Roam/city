"""图片存储 API"""

from io import BytesIO

from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import Response
from PIL import Image as PILImage

from app.database import Database
from app.middleware.auth import get_current_user
from app.models.image import Image
from app.schemas.common import APIResponse

router = APIRouter(prefix="/images", tags=["图片存储"])


async def get_image_service():
    """获取图片服务（直接操作 images 集合）"""
    db = Database.get_db()
    return db.images


@router.post("/upload", summary="上传图片")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    route_id: str | None = None,
    user_id: str = Depends(get_current_user),
    collection=Depends(get_image_service)
):
    """上传图片到 MongoDB BLOB 存储，返回图片 URL"""
    if not file.content_type or not file.content_type.startswith("image/"):
        return APIResponse(code=3001, message="仅支持图片文件").model_dump()

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:  # 5MB 上限
        return APIResponse(code=3001, message="图片大小不能超过 5MB").model_dump()

    # 压缩优化到 ~200KB
    try:
        img = PILImage.open(BytesIO(data))
        img = img.convert("RGB")
        # 缩放到 1200px
        max_dim = 1200
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), PILImage.LANCZOS)
        # 二分搜索 JPEG 质量
        out = BytesIO()
        quality = 85
        img.save(out, "JPEG", quality=quality, optimize=True)
        while out.tell() > 200 * 1024 and quality > 20:
            quality -= 10
            out = BytesIO()
            img.save(out, "JPEG", quality=quality, optimize=True)
        data = out.getvalue()
    except Exception:
        pass  # 非图片或转换失败，使用原始数据

    img = Image(
        data=data,
        content_type=file.content_type,
        filename=file.filename or "untitled",
        size=len(data),
        route_id=route_id,
    )

    doc = img.model_dump(by_alias=True)
    await collection.insert_one(doc)

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpeg"
    # 检测是否通过 HTTPS 代理（nginx X-Forwarded-Proto），生产环境强制 HTTPS
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    scheme = "https" if forwarded_proto == "https" else request.url.scheme
    base = f"{scheme}://{request.base_url.hostname}"
    if request.base_url.port and request.base_url.port not in (80, 443):
        base += f":{request.base_url.port}"
    url = f"{base}/api/v1/images/{img.id}.{ext}"

    return APIResponse(data={"id": img.id, "url": url, "size": img.size}).model_dump()


@router.get("/{image_id}.{ext}", summary="获取图片")
async def get_image(
    image_id: str,
    ext: str,
    collection=Depends(get_image_service)
):
    """返回图片二进制内容（浏览器可直接显示）"""
    doc = await collection.find_one({"_id": image_id})
    if not doc:
        return Response(status_code=404)

    return Response(
        content=doc["data"],
        media_type=doc.get("content_type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"}
    )
