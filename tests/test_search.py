"""文本搜索功能测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchByKeyword:
    """RouteService.search_by_keyword 测试"""

    @pytest.mark.asyncio
    async def test_search_uses_text_index(self):
        """验证使用 $text 索引进行搜索"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        coll = MagicMock()
        service.collection = coll

        mock_route = {"_id": "r1", "name": "西湖漫步", "city": "杭州", "tags": ["徒步"]}
        cursor_mock = MagicMock()
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock
        cursor_mock.to_list = AsyncMock(return_value=[mock_route])
        coll.find.return_value = cursor_mock

        results = await service.search_by_keyword("杭州")

        assert len(results) == 1
        assert results[0]["city"] == "杭州"
        call_args = coll.find.call_args[0][0]
        assert "$text" in call_args

    @pytest.mark.asyncio
    async def test_search_matches_tag_field(self):
        """搜索 '咖啡' 应能匹配 tags 字段"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        coll = MagicMock()
        service.collection = coll

        mock_route = {"_id": "r2", "name": "上海咖啡之旅", "city": "上海", "tags": ["咖啡", "文艺"]}
        cursor_mock = MagicMock()
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock
        cursor_mock.to_list = AsyncMock(return_value=[mock_route])
        coll.find.return_value = cursor_mock

        results = await service.search_by_keyword("咖啡")

        assert len(results) == 1
        assert "咖啡" in results[0]["tags"]

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_match(self):
        """无匹配时返回空列表（非错误）"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        coll = MagicMock()
        service.collection = coll
        cursor_mock = MagicMock()
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock
        cursor_mock.to_list = AsyncMock(return_value=[])
        coll.find.return_value = cursor_mock

        results = await service.search_by_keyword("不存在的关键词xyz")

        # $text 无结果 → 降级 regex 也无结果 → 返回 []
        assert results == []

    @pytest.mark.asyncio
    async def test_search_truncates_long_keyword(self):
        """超长关键词自动截断到200字符"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        coll = MagicMock()
        service.collection = coll
        cursor_mock = MagicMock()
        cursor_mock.sort.return_value = cursor_mock
        cursor_mock.limit.return_value = cursor_mock
        cursor_mock.to_list = AsyncMock(return_value=[])
        coll.find.return_value = cursor_mock

        long_keyword = "x" * 300
        await service.search_by_keyword(long_keyword)

        search_term = coll.find.call_args_list[0][0][0]["$text"]["$search"]
        assert len(search_term) <= 200

    @pytest.mark.asyncio
    async def test_search_empty_keyword_returns_empty(self):
        """空关键词返回空列表"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        service.collection = MagicMock()

        results = await service.search_by_keyword("")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_falls_back_to_regex(self):
        """$text 无结果时降级为 $regex"""
        from app.services.route_service import RouteService
        service = RouteService(MagicMock())
        coll = MagicMock()
        service.collection = coll

        # $text 返回空 → 降级到 regex
        text_cursor = MagicMock()
        text_cursor.sort.return_value = text_cursor
        text_cursor.limit.return_value = text_cursor
        text_cursor.to_list = AsyncMock(return_value=[])  # 第一次$text无结果
        coll.find.return_value = text_cursor

        results = await service.search_by_keyword("罕见关键词")

        # 应触发两次 find 调用：$text + $regex
        assert coll.find.call_count == 2
        # 第二次应使用 $or + $regex
        second_call = coll.find.call_args[0][0]
        assert "$or" in second_call
        assert results == []


class TestSearchAPI:
    """搜索 API 端点测试"""

    @pytest.mark.asyncio
    async def test_search_endpoint_rejects_empty_keyword(self):
        """空关键词应返回 code=3001（需带有效 Token）"""
        from unittest.mock import MagicMock, patch
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.api.routes import get_route_service
        from app.services.route_service import RouteService

        mock_service = RouteService(MagicMock())
        app.dependency_overrides[get_route_service] = lambda: mock_service

        # Mock JWT 验证使其返回有效 payload
        with patch("app.middleware.auth.AuthService.verify_access_token") as mock_verify:
            mock_verify.return_value = (0, "ok", {"sub": "user1", "phone": "13800138000"})

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/routes/search",
                    params={"keyword": ""},
                    headers={"Authorization": "Bearer valid-token"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 3001, f"Expected 3001, got {data}"
                assert "keyword 不能为空" in data["message"]

        app.dependency_overrides.clear()
