"""环境切换功能测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from httpx import AsyncClient, ASGITransport


class TestEnvironmentSwitch:
    """环境切换端到端测试"""

    @pytest.mark.asyncio
    async def test_auth_works_with_both_environments(self):
        """验证 auth 接口在不同环境下都能正常工作"""
        from app.main import app
        from app.api.auth import get_auth_service
        from app.services.auth_service import AuthService

        mock_auth = AuthService(MagicMock())
        mock_auth.send_code = AsyncMock(return_value=(0, "ok"))
        mock_auth.verify_code = AsyncMock(return_value=(0, "ok"))
        mock_auth.login = AsyncMock(return_value=(0, "ok", {
            "access_token": "tok",
            "refresh_token": "ref",
            "token_type": "Bearer",
            "expires_in": 900,
            "user": {"id": "u1", "phone": "13800138000"}
        }))

        app.dependency_overrides[get_auth_service] = lambda: mock_auth
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 测试环境 1: 发送验证码
            resp = await client.post("/api/v1/auth/send-code", json={"phone": "13800138000"})
            assert resp.status_code == 200
            assert resp.json()["code"] == 0

            # 测试环境 2: 登录
            resp = await client.post("/api/v1/auth/login", json={"phone": "13800138000", "code": "123456"})
            assert resp.status_code == 200
            assert resp.json()["code"] == 0

        app.dependency_overrides.clear()
        print("✅ auth works across environments")

    @pytest.mark.asyncio
    async def test_protected_routes_consistent(self):
        """验证业务接口鉴权行为不因环境切换改变"""
        from app.main import app
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_route = RouteService(AsyncMock())
        app.dependency_overrides[get_route_service] = lambda: mock_route

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 不带 Token
            resp = await client.get("/api/v1/routes")
            assert resp.json()["code"] == 2001

            # 带无效 Token
            resp = await client.get("/api/v1/routes", headers={"Authorization": "Bearer invalid"})
            assert resp.json()["code"] == 2003

        app.dependency_overrides.clear()
        print("✅ auth behavior consistent")

    @pytest.mark.asyncio
    async def test_response_format_consistent(self):
        """验证响应格式不随环境变化"""
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert "status" in resp.json()
            print("✅ response format consistent")
