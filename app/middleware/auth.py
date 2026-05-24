"""JWT 鉴权中间件"""

from fastapi import Request, HTTPException
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
    for prefix in PUBLIC_PATHS:
        if path.startswith(prefix):
            return True
    return False


class AuthError(Exception):
    """认证错误，包含业务 code 和 message"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


async def get_current_user(request: Request) -> str:
    """从请求头提取并验证 JWT。鉴权失败抛出 AuthError"""
    path = request.url.path

    if is_public_path(path):
        return ""

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise AuthError(2001, "未登录")

    token = authorization[7:]
    code, message, payload = AuthService.verify_access_token(token)

    if code != 0:
        raise AuthError(code, message)

    return payload["sub"]


async def get_optional_user(request: Request) -> str | None:
    """尝试从请求头提取用户 ID，不抛异常。用于公开接口的可选鉴权"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    code, _, payload = AuthService.verify_access_token(token)
    if code != 0:
        return None

    return payload.get("sub")
