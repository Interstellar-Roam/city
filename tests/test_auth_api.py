"""认证 API 端点测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthAPI:
    """认证端点测试"""

    @pytest.mark.asyncio
    async def test_send_code_ok(self):
        """正常发送验证码返回 code=0"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.api.auth import get_auth_service
        from app.services.auth_service import AuthService

        mock_svc = AuthService(MagicMock())
        mock_svc.send_code = AsyncMock(return_value=(0, "ok"))

        app.dependency_overrides[get_auth_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/send-code", json={"phone": "13800138000"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 0

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_code_invalid_phone(self):
        """非法手机号返回 code=1001"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.api.auth import get_auth_service
        from app.services.auth_service import AuthService

        mock_svc = AuthService(MagicMock())
        mock_svc.send_code = AsyncMock(return_value=(1001, "手机号格式不正确"))

        app.dependency_overrides[get_auth_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/send-code", json={"phone": "123"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 1001

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_success(self):
        """正确验证码登录返回 token"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.api.auth import get_auth_service
        from app.services.auth_service import AuthService

        mock_svc = AuthService(MagicMock())
        mock_svc.verify_code = AsyncMock(return_value=(0, "ok"))
        mock_svc.login = AsyncMock(return_value=(0, "ok", {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {"id": "u1", "phone": "13800138000"}
        }))

        app.dependency_overrides[get_auth_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/login", json={"phone": "13800138000", "code": "123456"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["access_token"] == "test-access-token"
            assert data["data"]["user"]["phone"] == "13800138000"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_wrong_code(self):
        """错误验证码返回 code=1003"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.api.auth import get_auth_service
        from app.services.auth_service import AuthService

        mock_svc = AuthService(MagicMock())
        mock_svc.verify_code = AsyncMock(return_value=(1003, "验证码错误"))

        app.dependency_overrides[get_auth_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/login", json={"phone": "13800138000", "code": "000000"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == 1003

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_routes_require_auth(self):
        """未登录访问业务接口返回 code=2001"""
        import pytest
        from unittest.mock import MagicMock
        from fastapi import Request
        from app.middleware.auth import get_current_user, AuthError

        # 模拟非公开路径请求（无 Authorization header）
        scope = {"type": "http", "path": "/api/v1/routes", "headers": []}
        request = Request(scope)

        with pytest.raises(AuthError) as exc_info:
            await get_current_user(request)

        assert exc_info.value.code == 2001
        assert "未登录" in exc_info.value.message
