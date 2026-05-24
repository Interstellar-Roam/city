"""路线 API 端点测试 — 重点验证 /routes/mine 和鉴权"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


def _make_paginated(items=None, total=0, page=1, page_size=20, has_more=False):
    """构造 PaginatedRoutes 字典"""
    return {
        "items": items or [],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    }


def _make_route_item(oid="abc123", name="测试路线", created_by=None):
    """构造单个路线项（包含 RouteDetail 所需的所有必填字段）"""
    item = {
        "_id": oid,
        "name": name,
        "description": None,
        "preview_image": None,
        "distance": 1000.0,
        "elevation_gain": 50.0,
        "estimated_duration": 3600,
        "city": "深圳",
        "favorites_count": 0,
        "views_count": 0,
        "completions_count": 0,
        "difficulty": "medium",
        "tags": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "start_location": {"type": "Point", "coordinates": [113.9, 22.5]},
    }
    if created_by is not None:
        item["created_by"] = created_by
    return item


class TestRoutesMineEndpoint:
    """验证 GET /routes/mine 端点"""

    @pytest.mark.asyncio
    async def test_mine_returns_only_my_routes(self):
        """/routes/mine 只返回当前用户的路线"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_svc = RouteService(mock_db)

        my_item = _make_route_item(oid="r1", name="我的路线", created_by="user_123")

        # Mock list_routes: created_by 过滤应该只返回匹配的
        async def fake_list_routes(**kwargs):
            created_by = kwargs.get("created_by")
            if created_by == "user_123":
                return _make_paginated(items=[my_item], total=1, has_more=False)
            return _make_paginated(items=[], total=0, has_more=False)

        mock_svc.list_routes = fake_list_routes

        app.dependency_overrides[get_current_user] = lambda: "user_123"
        app.dependency_overrides[get_route_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/routes/mine")
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["total"] == 1
            assert data["data"]["items"][0]["name"] == "我的路线"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mine_empty_when_no_routes(self):
        """/routes/mine 没有自己的路线时返回空列表"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_svc = RouteService(mock_db)
        mock_svc.list_routes = AsyncMock(return_value=_make_paginated(items=[], total=0))

        app.dependency_overrides[get_current_user] = lambda: "user_no_routes"
        app.dependency_overrides[get_route_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/routes/mine")
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["total"] == 0
            assert data["data"]["items"] == []

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mine_requires_auth(self):
        """/routes/mine 未登录返回 code=2001"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/routes/mine")
            data = resp.json()
            assert data["code"] == 2001


class TestRoutesListEndpoint:
    """验证 GET /routes 端点"""

    @pytest.mark.asyncio
    async def test_no_created_by_returns_all(self):
        """不传 created_by 返回所有已发布路线"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_svc = RouteService(mock_db)

        items = [
            _make_route_item(oid="r1", name="路线1"),
            _make_route_item(oid="r2", name="路线2"),
        ]
        mock_svc.list_routes = AsyncMock(return_value=_make_paginated(items=items, total=2))

        app.dependency_overrides[get_current_user] = lambda: "user_123"
        app.dependency_overrides[get_route_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/routes")
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["total"] == 2

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_created_by_with_user_id(self):
        """created_by 传用户ID只返回该用户的路线"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_svc = RouteService(mock_db)

        user_route = _make_route_item(oid="r1", name="用户路线", created_by="user_abc")

        async def fake_list_routes(**kwargs):
            created_by = kwargs.get("created_by")
            if created_by == "user_abc":
                return _make_paginated(items=[user_route], total=1)
            return _make_paginated(items=[], total=0)

        mock_svc.list_routes = fake_list_routes

        app.dependency_overrides[get_current_user] = lambda: "user_123"
        app.dependency_overrides[get_route_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/routes?created_by=user_abc")
            data = resp.json()
            assert data["code"] == 0
            assert data["data"]["total"] == 1
            assert data["data"]["items"][0]["name"] == "用户路线"

        app.dependency_overrides.clear()


class TestRouteCreation:
    """验证路线创建的鉴权"""

    @pytest.mark.asyncio
    async def test_create_route_sets_created_by(self):
        """创建路线时设置 created_by 为当前用户"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_svc = RouteService(mock_db)

        created_route = _make_route_item(oid="new1", name="新路线", created_by="user_123")
        mock_svc.create_route = AsyncMock(return_value=created_route)

        app.dependency_overrides[get_current_user] = lambda: "user_123"
        app.dependency_overrides[get_route_service] = lambda: mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/routes", json={
                "name": "新路线",
                "start_location": {"longitude": 113.9, "latitude": 22.5},
                "points": [],
                "distance": 0,
            })
            data = resp.json()
            assert data["code"] == 0
            mock_svc.create_route.assert_called_once()
            call_kwargs = mock_svc.create_route.call_args
            assert call_kwargs[1].get("user_id") == "user_123" or call_kwargs[0][1] == "user_123"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_route_requires_auth(self):
        """未登录创建路线返回 code=2001"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/routes", json={
                "name": "测试",
                "start_location": {"longitude": 113.9, "latitude": 22.5},
            })
            data = resp.json()
            assert data["code"] == 2001


class TestRouteServiceCreatedBy:
    """验证 RouteService 层的 created_by 过滤"""

    @pytest.mark.asyncio
    async def test_list_routes_with_created_by(self):
        """list_routes 传入 created_by 应在查询中加入该条件"""
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.routes = mock_collection

        mock_collection.count_documents = AsyncMock(return_value=1)
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[{
            "_id": "r1",
            "name": "我的路线",
            "description": None,
            "preview_image": None,
            "distance": 1000.0,
            "elevation_gain": 50.0,
            "estimated_duration": 3600,
            "city": "深圳",
            "favorites_count": 0,
            "difficulty": "medium",
            "tags": [],
            "created_at": datetime.utcnow(),
            "created_by": "user_123",
        }])
        mock_collection.find = MagicMock(return_value=mock_cursor)

        svc = RouteService(mock_db)
        result = await svc.list_routes(created_by="user_123")

        find_call_args = mock_collection.find.call_args[0][0]
        assert "created_by" in find_call_args
        assert find_call_args["created_by"] == "user_123"
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_routes_without_created_by(self):
        """list_routes 不传 created_by 时查询不含该字段"""
        from app.services.route_service import RouteService

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.routes = mock_collection

        mock_collection.count_documents = AsyncMock(return_value=0)
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find = MagicMock(return_value=mock_cursor)

        svc = RouteService(mock_db)
        await svc.list_routes()

        find_call_args = mock_collection.find.call_args[0][0]
        assert "created_by" not in find_call_args
