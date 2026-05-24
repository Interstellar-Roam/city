"""认证相关 API 路由"""

from fastapi import APIRouter, Depends, Request

from app.database import Database
from app.schemas.auth import SendCodeRequest, LoginRequest, RefreshRequest
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


def get_auth_service() -> AuthService:
    return AuthService(Database.get_db())


@router.post("/send-code", summary="发送短信验证码")
async def send_code(req: SendCodeRequest, service: AuthService = Depends(get_auth_service)):
    """向指定手机号发送 6 位验证码（Mock 模式固定 123456）"""
    code, message = await service.send_code(req.phone)
    return APIResponse(code=code, message=message, data={"expires_in": 300})


@router.post("/login", summary="验证码登录")
async def login(req: LoginRequest, service: AuthService = Depends(get_auth_service)):
    """手机号 + 验证码登录，首次自动注册，返回双 Token"""
    # 先校验验证码
    code, message = await service.verify_code(req.phone, req.code)
    if code != 0:
        return APIResponse(code=code, message=message)

    # 登录
    code, message, data = await service.login(req.phone)
    return APIResponse(code=code, message=message, data=data)


@router.post("/refresh", summary="刷新 Token")
async def refresh(req: RefreshRequest, service: AuthService = Depends(get_auth_service)):
    """用 Refresh Token 轮换新的 Access Token + Refresh Token"""
    code, message, data = await service.refresh_tokens(req.refresh_token)
    return APIResponse(code=code, message=message, data=data)


@router.post("/logout", summary="登出")
async def logout(request: Request, service: AuthService = Depends(get_auth_service)):
    """登出并失效所有 Refresh Token"""
    from app.services.auth_service import AuthService as AS

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return APIResponse(code=2001, message="未登录")

    code, msg, payload = AS.verify_access_token(authorization[7:])
    if code != 0:
        return APIResponse(code=code, message=msg)

    await service.logout(payload["sub"])
    return APIResponse(message="已登出")
