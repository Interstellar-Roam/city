"""Tests for the bounded tool-calling route recommendation agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agent.route_recommendation import RouteRecommendationAgent
from app.geo.schemas import (
    GeoLineString,
    GeoPoint,
    PlaceResponse,
    RoutePlanResponse,
    RouteRecommendationRequest,
)
from app.geo.services import RoutePlanningService


def _place(name: str, longitude: float) -> PlaceResponse:
    now = datetime.now(timezone.utc)
    return PlaceResponse(
        id=uuid4(),
        name=name,
        location=GeoPoint(longitude=longitude, latitude=31.21),
        categories=["咖啡"],
        tags=["安静"],
        city="上海",
        source_type="platform",
        moderation_status="published",
        quality_score=0.8,
        created_at=now,
        updated_at=now,
        distance_m=500,
    )


def _plan(user_id: str, query: str) -> RoutePlanResponse:
    now = datetime.now(timezone.utc)
    return RoutePlanResponse(
        id=uuid4(),
        user_id=user_id,
        plan_kind="recommendation",
        query=query,
        origin=GeoPoint(longitude=121.44, latitude=31.20),
        geometry=GeoLineString(coordinates=[(121.44, 31.20), (121.45, 31.21)]),
        total_distance_m=1200,
        total_duration_s=900,
        routing_provider="test",
        is_simulated=True,
        constraints={},
        score_breakdown={"planner_mode": "agent"},
        stops=[],
        legs=[],
        created_at=now,
    )


def _tool_call(name: str, arguments: dict[str, object], call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments, ensure_ascii=False),
        ),
    )


def _response(*tool_calls: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=list(tool_calls)))
        ]
    )


def _client(*responses: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=list(responses)))
        )
    )


@pytest.mark.asyncio
async def test_agent_searches_public_places_then_builds_allowlisted_route() -> None:
    first = _place("安静咖啡馆", 121.45)
    second = _place("社区公园", 121.46)
    places = SimpleNamespace(search_places=AsyncMock(return_value=[first, second]))
    expected = _plan("user-secret", "想走安静的咖啡公园路线，控制在2公里")
    planner = SimpleNamespace(
        create_agent_plan=AsyncMock(return_value=expected),
        create_recommendation=AsyncMock(),
        resolve_recommendation_budgets=RoutePlanningService.resolve_recommendation_budgets,
    )
    client = _client(
        _response(
            _tool_call(
                "search_public_places",
                {"categories": ["咖啡", "公园"], "tags": ["安静"], "limit": 8},
                "search-1",
            )
        ),
        _response(
            _tool_call(
                "build_route_plan",
                {
                    "place_ids": [str(first.id), str(second.id)],
                    "selection_reason": "匹配安静咖啡与公园",
                },
                "build-1",
            )
        ),
    )
    agent = RouteRecommendationAgent(places, planner, client=client, enabled=True)
    request = RouteRecommendationRequest(
        query="想走安静的咖啡公园路线，控制在2公里",
        origin=GeoPoint(longitude=121.44123456, latitude=31.20123456),
        max_stops=4,
        categories=["文化"],
        tags=["拍照"],
    )

    result = await agent.recommend(
        request,
        "user-secret",
        preferences={"preferred_tags": ["安静"]},
    )

    assert result.id == expected.id
    planner.create_agent_plan.assert_awaited_once()
    call = planner.create_agent_plan.await_args
    assert call.args[0].max_distance_m == 2000
    assert call.args[2] == [first.id, second.id]
    assert call.kwargs["requested_categories"] == ["文化", "咖啡", "公园"]
    assert call.kwargs["requested_tags"] == ["拍照", "安静"]
    planner.create_recommendation.assert_not_awaited()

    places.search_places.assert_awaited_once()
    search_call = places.search_places.await_args.kwargs
    assert search_call["categories"] == ["文化", "咖啡", "公园"]
    assert search_call["tags"] == ["拍照", "安静"]

    first_messages = client.chat.completions.create.await_args_list[0].kwargs["messages"]
    serialized_prompt = json.dumps(first_messages, ensure_ascii=False)
    assert "user-secret" not in serialized_prompt
    assert "121.44123456" not in serialized_prompt
    assert "31.20123456" not in serialized_prompt


@pytest.mark.asyncio
async def test_agent_rejects_invented_place_id_and_falls_back() -> None:
    first = _place("已搜索地点A", 121.45)
    second = _place("已搜索地点B", 121.46)
    places = SimpleNamespace(search_places=AsyncMock(return_value=[first, second]))
    fallback = _plan("user-1", "推荐路线")
    planner = SimpleNamespace(
        create_agent_plan=AsyncMock(),
        create_recommendation=AsyncMock(return_value=fallback),
        resolve_recommendation_budgets=RoutePlanningService.resolve_recommendation_budgets,
    )
    client = _client(
        _response(_tool_call("search_public_places", {"limit": 5}, "search-1")),
        _response(
            _tool_call(
                "build_route_plan",
                {"place_ids": [str(first.id), str(uuid4())]},
                "build-1",
            )
        ),
        _response(),
    )
    agent = RouteRecommendationAgent(places, planner, client=client, enabled=True)
    request = RouteRecommendationRequest(
        query="推荐路线",
        origin=GeoPoint(longitude=121.44, latitude=31.20),
    )

    result = await agent.recommend(request, "user-1")

    assert result.id == fallback.id
    planner.create_agent_plan.assert_not_awaited()
    planner.create_recommendation.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_enforces_exact_stop_count_from_query() -> None:
    first = _place("地点A", 121.45)
    second = _place("地点B", 121.46)
    third = _place("地点C", 121.47)
    places = SimpleNamespace(search_places=AsyncMock(return_value=[first, second, third]))
    expected = _plan("user-1", "安排3个点")
    planner = SimpleNamespace(
        create_agent_plan=AsyncMock(return_value=expected),
        create_recommendation=AsyncMock(),
        resolve_recommendation_budgets=RoutePlanningService.resolve_recommendation_budgets,
    )
    client = _client(
        _response(_tool_call("search_public_places", {"limit": 5}, "search-1")),
        _response(
            _tool_call(
                "build_route_plan",
                {"place_ids": [str(first.id), str(second.id)]},
                "build-too-few",
            )
        ),
        _response(
            _tool_call(
                "build_route_plan",
                {"place_ids": [str(first.id), str(second.id), str(third.id)]},
                "build-exact",
            )
        ),
    )
    agent = RouteRecommendationAgent(places, planner, client=client, enabled=True)
    request = RouteRecommendationRequest(
        query="安排3个点",
        origin=GeoPoint(longitude=121.44, latitude=31.20),
        max_stops=4,
    )

    result = await agent.recommend(request, "user-1")

    assert result.id == expected.id
    assert client.chat.completions.create.await_count == 3
    planner.create_agent_plan.assert_awaited_once()
    call = planner.create_agent_plan.await_args
    assert call.args[2] == [first.id, second.id, third.id]
    assert call.kwargs["agent_metadata"]["target_stops"] == 3
    planner.create_recommendation.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_relaxes_overly_narrow_text_search_for_requested_stops() -> None:
    first = _place("展览馆A", 121.45)
    second = _place("艺术中心B", 121.46)
    third = _place("博物馆C", 121.47)
    places = SimpleNamespace(search_places=AsyncMock(side_effect=[[first], [first, second, third]]))
    expected = _plan("user-1", "想看展，安排三个点")
    planner = SimpleNamespace(
        create_agent_plan=AsyncMock(return_value=expected),
        create_recommendation=AsyncMock(),
        resolve_recommendation_budgets=RoutePlanningService.resolve_recommendation_budgets,
    )
    client = _client(
        _response(
            _tool_call(
                "search_public_places",
                {"query": "展览", "categories": ["文化"], "limit": 6},
                "search-1",
            )
        ),
        _response(
            _tool_call(
                "build_route_plan",
                {"place_ids": [str(first.id), str(second.id), str(third.id)]},
                "build-1",
            )
        ),
    )
    agent = RouteRecommendationAgent(places, planner, client=client, enabled=True)
    request = RouteRecommendationRequest(
        query="想看展，安排三个点",
        origin=GeoPoint(longitude=121.44, latitude=31.20),
        max_stops=4,
    )

    result = await agent.recommend(request, "user-1")

    assert result.id == expected.id
    assert places.search_places.await_count == 2
    strict_call, relaxed_call = places.search_places.await_args_list
    assert strict_call.kwargs["query"] == "展览"
    assert "query" not in relaxed_call.kwargs
    metadata = planner.create_agent_plan.await_args.kwargs["agent_metadata"]
    assert metadata["target_stops"] == 3
    assert metadata["search_trace"][0]["attempts"][1]["mode"] == ("without_text_query")


def test_stop_count_parser_does_not_treat_upper_bound_as_exact() -> None:
    assert RouteRecommendationAgent._requested_stop_count("安排3个点", 4) == 3
    assert RouteRecommendationAgent._requested_stop_count("安排三个点", 4) == 3
    assert RouteRecommendationAgent._requested_stop_count("不超过4个点", 4) is None
    assert RouteRecommendationAgent._requested_stop_count("最多四个地点", 4) is None


@pytest.mark.asyncio
async def test_agent_without_llm_uses_deterministic_fallback() -> None:
    fallback = _plan("user-1", "推荐路线")
    planner = SimpleNamespace(
        create_agent_plan=AsyncMock(),
        create_recommendation=AsyncMock(return_value=fallback),
    )
    agent = RouteRecommendationAgent(
        SimpleNamespace(),
        planner,
        enabled=False,
    )
    request = RouteRecommendationRequest(
        query="推荐路线",
        origin=GeoPoint(longitude=121.44, latitude=31.20),
    )

    result = await agent.recommend(request, "user-1")

    assert result.id == fallback.id
    planner.create_recommendation.assert_awaited_once()
