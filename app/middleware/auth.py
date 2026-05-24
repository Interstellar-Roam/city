"""JWT 鉴权中间件"""

from fastapi import Request
from fastapi.responses import JSONResponse
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

# 不需要鉴权的路径前缀
PUBLIC_PATHS = [
    "/api/v1/auth/",
    "/health",
    "/api/v1/config/",
    "/docs",
    "/openapi.json",
    "/redoc",
]


def is_public_path(path: str) -> bool:
    """检查路径是否公开（无需鉴权）"""
    for prefix in PUBLIC_PATHS:
        if path.startswith(prefix):
            return True
    return False


async def get_current_user(request: Request):
    """从请求头提取并验证 JWT，返回 user_id。鉴权失败返回 JSONResponse"""
    path = request.url.path

    if is_public_path(path):
        return ""  # 公开路径无需鉴权

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return JSONResponse(
            status_code=200,
            content=APIResponse(code=2001, message="未登录").model_dump()
        )

    token = authorization[7:]  # 去掉 "Bearer " 前缀
    code, message, payload = AuthService.verify_access_token(token)

    if code != 0:
        return JSONResponse(
            status_code=200,
            content=APIResponse(code=code, message=message).model_dump()
        )

    return payload["sub"]  # user_id
