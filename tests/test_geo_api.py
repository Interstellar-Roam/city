"""In-process API contract tests for the new geographic endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.places import get_place_service
from app.api.route_plans import get_route_recommendation_agent, get_session_service
from app.geo.schemas import GeoLineString, GeoPoint, PlaceResponse, RoutePlanResponse
from app.main import app


@pytest.mark.asyncio
async def test_share_place_api_returns_created_place() -> None:
    now = datetime.now(timezone.utc)
    place = PlaceResponse(
        id=uuid4(),
        name="用户分享地点",
        location=GeoPoint(longitude=121.45, latitude=31.21),
        categories=["咖啡"],
        tags=["安静"],
        source_type="user",
        moderation_status="published",
        quality_score=0.5,
        created_at=now,
        updated_at=now,
    )
    service = AsyncMock()
    service.share_place.return_value = place
    app.dependency_overrides[get_place_service] = lambda: service

    try:
        with patch("app.middleware.auth.AuthService.verify_access_token") as verify:
            verify.return_value = (0, "ok", {"sub": "user-1", "phone": "13800138000"})
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/places",
                    headers={"Authorization": "Bearer valid-token"},
                    json={
                        "name": "用户分享地点",
                        "location": {"longitude": 121.45, "latitude": 31.21},
                        "categories": ["咖啡"],
                        "tags": ["安静"],
                    },
                )
        assert response.status_code == 201
        payload = response.json()
        assert payload["code"] == 0
        assert payload["data"]["source_type"] == "user"
        assert "created_by" not in payload["data"]
        service.share_place.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_recommend_api_uses_authenticated_user_and_agent() -> None:
    now = datetime.now(timezone.utc)
    plan = RoutePlanResponse(
        id=uuid4(),
        user_id="user-1",
        plan_kind="recommendation",
        query="安静的公园路线",
        origin=GeoPoint(longitude=121.44, latitude=31.20),
        geometry=GeoLineString(
            coordinates=[(121.44, 31.20), (121.45, 31.21)]
        ),
        total_distance_m=1200,
        total_duration_s=900,
        routing_provider="test",
        is_simulated=True,
        score_breakdown={"planner_mode": "agent", "requested_tags": ["安静"]},
        stops=[],
        legs=[],
        created_at=now,
    )
    agent = MagicMock()
    agent.recommend = AsyncMock(return_value=plan)
    session_service = MagicMock()
    session_service.get_user_preference = AsyncMock(return_value=None)
    session_service.update_user_preference = AsyncMock()
    app.dependency_overrides[get_route_recommendation_agent] = lambda: agent
    app.dependency_overrides[get_session_service] = lambda: session_service

    try:
        with patch("app.middleware.auth.AuthService.verify_access_token") as verify:
            verify.return_value = (0, "ok", {"sub": "user-1", "phone": "13800138000"})
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/route-plans/recommend",
                    headers={"Authorization": "Bearer valid-token"},
                    json={
                        "query": "安静的公园路线",
                        "origin": {"longitude": 121.44, "latitude": 31.20},
                    },
                )

        assert response.status_code == 200
        assert response.json()["data"]["score_breakdown"]["planner_mode"] == "agent"
        call = agent.recommend.await_args
        assert call.args[1] == "user-1"
        assert call.kwargs["preferences"] is None
        session_service.update_user_preference.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()
