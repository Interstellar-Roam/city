"""Unit tests for place sharing and road-validated route planning."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.geo.intent import IntentParser
from app.geo.schemas import (
    GeoPoint,
    PlaceCreate,
    PlaceResponse,
    RoutePlanCreate,
    RouteRecommendationRequest,
)
from app.geo.services import (
    DuplicatePlaceError,
    PlaceService,
    RoutePlanningService,
)
from app.geo.user_repositories import (
    MongoPlaceContributionRepository,
    MongoRoutePlanRepository,
)
from app.routing.base import RouteLeg, RoutingProvider, UnreachableRouteError
from app.routing.deterministic import DeterministicRoutingProvider


def make_place(
    name: str,
    longitude: float,
    latitude: float,
    *,
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    distance_m: float | None = None,
) -> PlaceResponse:
    now = datetime.now(timezone.utc)
    return PlaceResponse(
        id=uuid4(),
        name=name,
        location=GeoPoint(longitude=longitude, latitude=latitude),
        categories=categories or [],
        tags=tags or [],
        city="上海",
        district="徐汇区",
        source_type="platform",
        moderation_status="published",
        quality_score=0.8,
        created_at=now,
        updated_at=now,
        distance_m=distance_m,
    )


class FakePlaceRepository:
    def __init__(self, places: list[PlaceResponse], duplicate: PlaceResponse | None = None):
        self.places = places
        self.duplicate = duplicate
        self.created: list[PlaceResponse] = []

    async def find_duplicate(self, data: PlaceCreate, radius_m: float) -> PlaceResponse | None:
        return self.duplicate

    async def create_place(
        self,
        data: PlaceCreate,
        *,
        source_type: str,
        place_id: UUID | None = None,
        external_refs: dict[str, Any] | None = None,
        quality_score: float = 0,
    ) -> PlaceResponse:
        now = datetime.now(timezone.utc)
        result = PlaceResponse(
            id=place_id or uuid4(),
            **data.model_dump(),
            source_type=source_type,
            external_refs=external_refs or {},
            moderation_status="published",
            quality_score=quality_score,
            created_at=now,
            updated_at=now,
        )
        self.created.append(result)
        return result

    async def get_place(self, place_id: UUID) -> PlaceResponse | None:
        return next((place for place in self.places if place.id == place_id), None)

    async def get_places(self, place_ids: list[UUID]) -> list[PlaceResponse]:
        by_id = {place.id: place for place in self.places}
        return [by_id[place_id] for place_id in place_ids if place_id in by_id]

    async def search_places(self, **kwargs: Any) -> list[PlaceResponse]:
        categories = set(kwargs.get("categories") or [])
        tags = set(kwargs.get("tags") or [])
        filtered = [
            place
            for place in self.places
            if (not categories or categories.intersection(place.categories))
            and (not tags or tags.intersection(place.tags))
        ]
        return filtered or list(self.places)


class FakeContributionRepository:
    def __init__(self):
        self.records: dict[UUID, dict[str, Any]] = {}

    async def start_create(self, user_id: str, place_id: UUID, data: PlaceCreate) -> None:
        self.records[place_id] = {
            "user_id": user_id,
            "payload": data.model_dump(mode="json"),
            "status": "pending",
        }

    async def mark_published(self, user_id: str, place_id: UUID) -> None:
        assert self.records[place_id]["user_id"] == user_id
        self.records[place_id]["status"] = "published"

    async def mark_failed(self, user_id: str, place_id: UUID, reason: str) -> None:
        assert self.records[place_id]["user_id"] == user_id
        self.records[place_id].update(status="failed", reason=reason)


class FakePlanRepository:
    def __init__(self):
        self.saved: dict[UUID, dict[str, Any]] = {}

    async def save_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            **plan,
            "origin": plan["origin"].model_dump() if plan.get("origin") else None,
            "geometry": {
                "type": "LineString",
                "coordinates": plan["geometry"],
                "coordinate_system": "WGS84",
            },
            "stops": [
                {
                    **stop,
                    "place": stop["place"].model_dump(mode="json"),
                }
                for stop in plan["stops"]
            ],
            "legs": [
                {
                    **leg,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": leg["geometry"],
                        "coordinate_system": "WGS84",
                    },
                }
                for leg in plan["legs"]
            ],
            "travel_mode": "walking",
            "created_at": datetime.now(timezone.utc),
        }
        self.saved[plan["id"]] = normalized
        return normalized

    async def get_plan(self, route_plan_id: UUID) -> dict[str, Any] | None:
        return self.saved.get(route_plan_id)


class SelectivelyUnreachableProvider(RoutingProvider):
    name = "selective"
    version = "test"

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteLeg:
        if destination.longitude > 122:
            raise UnreachableRouteError("不可达")
        return RouteLeg(
            geometry=[
                (origin.longitude, origin.latitude),
                (destination.longitude, destination.latitude),
            ],
            distance_m=500,
            duration_s=400,
        )


def test_route_plan_rejects_duplicate_place_ids() -> None:
    place_id = uuid4()
    with pytest.raises(ValidationError):
        RoutePlanCreate(place_ids=[place_id, place_id])


@pytest.mark.asyncio
async def test_intent_parser_extracts_categories_tags_and_budgets() -> None:
    intent = await IntentParser().parse("想走一条安静有树荫的咖啡路线，控制在3公里和90分钟")
    assert "咖啡" in intent.categories
    assert {"安静", "树荫"}.issubset(intent.tags)
    assert intent.max_distance_m == 3000
    assert intent.max_duration_s == 5400


def test_recommendation_budget_priority() -> None:
    from_query = RoutePlanningService.resolve_recommendation_budgets(
        RouteRecommendationRequest(
            query="控制在3公里",
            origin=GeoPoint(longitude=121.44, latitude=31.20),
        ),
        query_max_distance_m=3000,
    )
    explicit = RoutePlanningService.resolve_recommendation_budgets(
        RouteRecommendationRequest(
            query="控制在3公里",
            origin=GeoPoint(longitude=121.44, latitude=31.20),
            max_distance_m=5000,
        ),
        query_max_distance_m=3000,
    )
    default = RoutePlanningService.resolve_recommendation_budgets(
        RouteRecommendationRequest(
            query="随便走走",
            origin=GeoPoint(longitude=121.44, latitude=31.20),
        )
    )

    assert from_query == (3000, None)
    assert explicit == (5000, None)
    assert default == (12_000, None)


@pytest.mark.asyncio
async def test_place_service_rejects_nearby_duplicate() -> None:
    duplicate = make_place("测试咖啡馆", 121.4, 31.2)
    repository = FakePlaceRepository([], duplicate=duplicate)
    service = PlaceService(repository, FakeContributionRepository())
    request = PlaceCreate(
        name="测试咖啡馆",
        location=GeoPoint(longitude=121.40001, latitude=31.20001),
    )
    with pytest.raises(DuplicatePlaceError) as exc:
        await service.share_place(request, "user-1")
    assert exc.value.duplicate.id == duplicate.id


@pytest.mark.asyncio
async def test_user_share_publishes_public_place_and_keeps_attribution_private() -> None:
    repository = FakePlaceRepository([])
    contributions = FakeContributionRepository()
    service = PlaceService(repository, contributions)
    request = PlaceCreate(
        name="公域咖啡馆",
        location=GeoPoint(longitude=121.45, latitude=31.21),
        categories=["咖啡"],
    )

    place = await service.share_place(request, "user-1")

    assert "created_by" not in place.model_dump()
    assert contributions.records[place.id]["user_id"] == "user-1"
    assert contributions.records[place.id]["status"] == "published"


@pytest.mark.asyncio
async def test_mongo_repositories_store_private_attribution_and_route_owner() -> None:
    contribution_collection = MagicMock()
    contribution_collection.update_one = AsyncMock()
    route_collection = MagicMock()
    route_collection.replace_one = AsyncMock()
    database = SimpleNamespace(
        user_place_contributions=contribution_collection,
        user_route_plans=route_collection,
    )
    place_id = uuid4()
    request = PlaceCreate(
        name="公共地点",
        location=GeoPoint(longitude=121.45, latitude=31.21),
    )

    contributions = MongoPlaceContributionRepository(database)
    await contributions.start_create("user-1", place_id, request)
    await contributions.mark_published("user-1", place_id)

    pending_document = contribution_collection.update_one.await_args_list[0].args[1]
    assert pending_document["$setOnInsert"]["user_id"] == "user-1"
    assert pending_document["$setOnInsert"]["place_id"] == str(place_id)
    assert contribution_collection.update_one.await_count == 2

    route_id = uuid4()
    routes = MongoRoutePlanRepository(database)
    stored = await routes.save_plan(
        {
            "id": route_id,
            "user_id": "user-2",
            "plan_kind": "explicit",
            "query": None,
            "origin": GeoPoint(longitude=121.44, latitude=31.20),
            "geometry": [(121.44, 31.20), (121.45, 31.21)],
            "total_distance_m": 1000,
            "total_duration_s": 600,
            "routing_provider": "test",
            "routing_version": "1",
            "is_simulated": True,
            "constraints": {},
            "score_breakdown": {},
            "stops": [],
            "legs": [],
            "expires_at": datetime.now(timezone.utc),
        }
    )
    route_document = route_collection.replace_one.await_args.args[1]
    assert route_document["_id"] == str(route_id)
    assert route_document["user_id"] == "user-2"
    assert stored["id"] == str(route_id)


@pytest.mark.asyncio
async def test_deterministic_provider_is_explicitly_simulated() -> None:
    provider = DeterministicRoutingProvider()
    leg = await provider.route(
        GeoPoint(longitude=121.43, latitude=31.20),
        GeoPoint(longitude=121.44, latitude=31.21),
    )
    assert provider.is_simulated is True
    assert leg.provider_metadata["simulated"] is True
    assert len(leg.geometry) >= 2
    assert leg.distance_m > 0
    assert leg.duration_s > 0


@pytest.mark.asyncio
async def test_explicit_plan_connects_four_places_and_returns_to_start() -> None:
    places = [
        make_place("A", 121.430, 31.200),
        make_place("B", 121.435, 31.203),
        make_place("C", 121.440, 31.205),
        make_place("D", 121.445, 31.208),
    ]
    plan_repository = FakePlanRepository()
    service = RoutePlanningService(
        places=FakePlaceRepository(places),
        plans=plan_repository,
        routing=DeterministicRoutingProvider(),
    )
    result = await service.create_explicit_plan(
        RoutePlanCreate(
            place_ids=[place.id for place in places],
            optimize_order=True,
            return_to_origin=True,
            max_distance_m=20_000,
        ),
        "user-1",
    )
    assert len(result.stops) == 4
    assert len(result.legs) == 4
    assert result.is_simulated is True
    assert result.geometry.coordinates[0] == result.geometry.coordinates[-1]
    assert result.total_distance_m == pytest.approx(sum(leg.distance_m for leg in result.legs))
    assert result.id in plan_repository.saved


@pytest.mark.asyncio
async def test_recommendation_skips_unreachable_place_and_uses_preferences() -> None:
    places = [
        make_place("安静公园", 121.430, 31.200, categories=["公园"], tags=["安静"], distance_m=200),
        make_place("偏好咖啡", 121.435, 31.202, categories=["咖啡"], tags=["安静"], distance_m=500),
        make_place("普通建筑", 121.440, 31.205, categories=["建筑"], tags=["历史"], distance_m=800),
        make_place("不可达地点", 123.000, 31.210, categories=["公园"], tags=["安静"], distance_m=900),
    ]
    service = RoutePlanningService(
        places=FakePlaceRepository(places),
        plans=FakePlanRepository(),
        routing=SelectivelyUnreachableProvider(),
    )
    result = await service.create_recommendation(
        RouteRecommendationRequest(
            query="推荐安静的咖啡和公园",
            origin=GeoPoint(longitude=121.429, latitude=31.199),
            radius_m=5000,
            max_stops=3,
            max_distance_m=10_000,
        ),
        "user-1",
        preferences={"preferred_tags": ["安静"]},
    )
    names = {stop.place.name for stop in result.stops}
    assert "不可达地点" not in names
    assert {"安静公园", "偏好咖啡"}.issubset(names)
    assert all(leg.reachable for leg in result.legs)
