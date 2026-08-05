"""Place sharing and road-validated multi-place route planning."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from loguru import logger

from app.config import get_settings
from app.geo.intent import IntentParser
from app.geo.repositories import PlaceRepositoryProtocol
from app.geo.schemas import (
    GeoPoint,
    PlaceCreate,
    PlaceResponse,
    RoutePlanCreate,
    RoutePlanResponse,
    RouteRecommendationRequest,
)
from app.geo.user_repositories import (
    PlaceContributionRepositoryProtocol,
    RoutePlanRepositoryProtocol,
)
from app.routing.base import (
    RouteLeg,
    RoutingProvider,
    UnreachableRouteError,
    haversine_m,
    merge_leg_geometries,
)


class DuplicatePlaceError(ValueError):
    def __init__(self, duplicate: PlaceResponse):
        self.duplicate = duplicate
        super().__init__(f"附近已存在同名地点: {duplicate.name}")


class PlaceNotFoundError(ValueError):
    pass


class RoutePlanningError(ValueError):
    pass


class RouteConstraintError(RoutePlanningError):
    pass


class PlaceService:
    def __init__(
        self,
        repository: PlaceRepositoryProtocol,
        contributions: PlaceContributionRepositoryProtocol,
    ):
        self.repository = repository
        self.contributions = contributions
        self.settings = get_settings()

    async def share_place(self, data: PlaceCreate, user_id: str) -> PlaceResponse:
        duplicate = await self.repository.find_duplicate(
            data,
            self.settings.place_duplicate_radius_m,
        )
        if duplicate:
            raise DuplicatePlaceError(duplicate)

        place_id = uuid4()
        await self.contributions.start_create(user_id, place_id, data)
        try:
            place = await self.repository.create_place(
                data,
                source_type="user",
                place_id=place_id,
                quality_score=0.5,
            )
        except Exception as exc:
            try:
                await self.contributions.mark_failed(user_id, place_id, str(exc))
            except Exception as tracking_error:  # pragma: no cover - preserves original failure
                logger.error(f"记录地点贡献失败状态时异常: {tracking_error}")
            raise
        await self.contributions.mark_published(user_id, place_id)
        return place


class RoutePlanningService:
    def __init__(
        self,
        places: PlaceRepositoryProtocol,
        plans: RoutePlanRepositoryProtocol,
        routing: RoutingProvider,
        intent_parser: IntentParser | None = None,
    ):
        self.places = places
        self.plans = plans
        self.routing = routing
        self.intent_parser = intent_parser or IntentParser()

    async def create_explicit_plan(
        self,
        request: RoutePlanCreate,
        user_id: str,
    ) -> RoutePlanResponse:
        places = await self.places.get_places(request.place_ids)
        missing = set(request.place_ids) - {place.id for place in places}
        if missing:
            raise PlaceNotFoundError(
                f"地点不存在: {', '.join(str(value) for value in sorted(missing, key=str))}"
            )

        ordered = self._order_places(places, request.origin, request.optimize_order)
        plan = await self._assemble_plan(
            places=ordered,
            user_id=user_id,
            plan_kind="explicit",
            query=None,
            origin=request.origin,
            return_to_origin=request.return_to_origin,
            max_distance_m=request.max_distance_m,
            max_duration_s=request.max_duration_s,
            planned_stay_seconds=request.planned_stay_seconds,
            score_breakdown={},
            skip_unreachable=False,
        )
        stored = await self.plans.save_plan(plan)
        return RoutePlanResponse(**stored)

    async def create_recommendation(
        self,
        request: RouteRecommendationRequest,
        user_id: str,
        preferences: dict[str, Any] | None = None,
    ) -> RoutePlanResponse:
        intent = await self.intent_parser.parse(request.query)
        requested_categories = _merge(request.categories, intent.categories)
        requested_tags = _merge(request.tags, intent.tags)
        preferred_tags = list((preferences or {}).get("preferred_tags") or [])
        preferred_cities = list((preferences or {}).get("preferred_cities") or [])
        city = intent.city or (preferred_cities[-1] if preferred_cities else None)

        candidates = await self.places.search_places(
            longitude=request.origin.longitude,
            latitude=request.origin.latitude,
            radius_m=request.radius_m,
            categories=requested_categories or None,
            tags=requested_tags or None,
            city=city,
            limit=30,
        )
        if len(candidates) < 2:
            candidates = await self.places.search_places(
                longitude=request.origin.longitude,
                latitude=request.origin.latitude,
                radius_m=request.radius_m,
                city=city,
                limit=30,
            )
        if len(candidates) < 2:
            raise RoutePlanningError("附近没有足够的已发布地点来生成路线")

        scored = sorted(
            candidates,
            key=lambda place: self._candidate_score(
                place,
                requested_categories=requested_categories,
                requested_tags=requested_tags,
                preferred_tags=preferred_tags,
            ),
            reverse=True,
        )
        selected = scored[: max(request.max_stops * 2, request.max_stops)]
        selected = self._order_places(selected, request.origin, optimize=True)

        max_distance, max_duration = self.resolve_recommendation_budgets(
            request,
            intent.max_distance_m,
            intent.max_duration_s,
        )
        last_error: Exception | None = None
        for stop_count in range(min(request.max_stops, len(selected)), 1, -1):
            try:
                plan = await self._assemble_plan(
                    places=selected[:stop_count],
                    user_id=user_id,
                    plan_kind="recommendation",
                    query=request.query,
                    origin=request.origin,
                    return_to_origin=request.return_to_origin,
                    max_distance_m=max_distance,
                    max_duration_s=max_duration,
                    planned_stay_seconds=request.planned_stay_seconds,
                    score_breakdown={
                        "planner_mode": "heuristic",
                        "requested_categories": requested_categories,
                        "requested_tags": requested_tags,
                        "preferred_tags": preferred_tags,
                    },
                    skip_unreachable=True,
                )
                if len(plan["stops"]) >= 2:
                    stored = await self.plans.save_plan(plan)
                    return RoutePlanResponse(**stored)
            except (RoutePlanningError, UnreachableRouteError) as exc:
                last_error = exc

        raise RoutePlanningError(str(last_error or "候选地点无法组成满足约束的可达路线"))

    @staticmethod
    def resolve_recommendation_budgets(
        request: RouteRecommendationRequest,
        query_max_distance_m: float | None = None,
        query_max_duration_s: int | None = None,
    ) -> tuple[float | None, int | None]:
        """Apply explicit request values before query values, then a safe default."""

        max_distance = request.max_distance_m or query_max_distance_m
        max_duration = request.max_duration_s or query_max_duration_s
        if max_distance is None and max_duration is None:
            max_distance = 12_000
        return max_distance, max_duration

    async def create_agent_plan(
        self,
        request: RouteRecommendationRequest,
        user_id: str,
        place_ids: list[UUID],
        *,
        requested_categories: list[str],
        requested_tags: list[str],
        preferred_tags: list[str],
        agent_metadata: dict[str, Any],
    ) -> RoutePlanResponse:
        """Build and persist a plan selected by the recommendation agent."""

        places = await self.places.get_places(place_ids)
        missing = set(place_ids) - {place.id for place in places}
        if missing:
            raise PlaceNotFoundError(
                f"地点不存在: {', '.join(str(value) for value in sorted(missing, key=str))}"
            )
        ordered = self._order_places(places, request.origin, optimize=True)
        plan = await self._assemble_plan(
            places=ordered,
            user_id=user_id,
            plan_kind="recommendation",
            query=request.query,
            origin=request.origin,
            return_to_origin=request.return_to_origin,
            max_distance_m=request.max_distance_m,
            max_duration_s=request.max_duration_s,
            planned_stay_seconds=request.planned_stay_seconds,
            score_breakdown={
                "planner_mode": "agent",
                "requested_categories": requested_categories,
                "requested_tags": requested_tags,
                "preferred_tags": preferred_tags,
                "agent": agent_metadata,
            },
            skip_unreachable=False,
        )
        stored = await self.plans.save_plan(plan)
        return RoutePlanResponse(**stored)

    @staticmethod
    def _candidate_score(
        place: PlaceResponse,
        *,
        requested_categories: list[str],
        requested_tags: list[str],
        preferred_tags: list[str],
    ) -> float:
        category_match = len(set(place.categories) & set(requested_categories))
        tag_match = len(set(place.tags) & set(requested_tags))
        preference_match = len(set(place.tags + place.categories) & set(preferred_tags))
        distance_penalty = (place.distance_m or 0) / 10_000
        return (
            category_match * 4
            + tag_match * 3
            + preference_match * 1.5
            + place.quality_score
            - distance_penalty
        )

    @staticmethod
    def _order_places(
        places: list[PlaceResponse],
        origin: GeoPoint | None,
        optimize: bool,
    ) -> list[PlaceResponse]:
        if not optimize or len(places) < 2:
            return list(places)

        remaining = list(places)
        if origin is None:
            ordered = [remaining.pop(0)]
            current = ordered[0].location
        else:
            ordered = []
            current = origin

        while remaining:
            nearest = min(remaining, key=lambda place: haversine_m(current, place.location))
            ordered.append(nearest)
            remaining.remove(nearest)
            current = nearest.location
        return ordered

    async def _assemble_plan(
        self,
        *,
        places: list[PlaceResponse],
        user_id: str,
        plan_kind: str,
        query: str | None,
        origin: GeoPoint | None,
        return_to_origin: bool,
        max_distance_m: float | None,
        max_duration_s: int | None,
        planned_stay_seconds: int,
        score_breakdown: dict[str, Any],
        skip_unreachable: bool,
    ) -> dict[str, Any]:
        if len(places) < 2:
            raise RoutePlanningError("至少需要两个地点")

        accepted_places: list[PlaceResponse] = []
        legs: list[RouteLeg] = []
        leg_records: list[dict[str, Any]] = []
        current = origin or places[0].location
        current_label = "当前位置" if origin else places[0].name
        start_index = 0 if origin else 1
        if origin is None:
            accepted_places.append(places[0])

        total_distance = 0.0
        walking_duration = 0
        for place in places[start_index:]:
            try:
                leg = await self.routing.route(current, place.location)
            except UnreachableRouteError:
                if skip_unreachable:
                    continue
                raise

            projected_distance = total_distance + leg.distance_m
            projected_duration = (
                walking_duration
                + leg.duration_s
                + (len(accepted_places) + 1) * planned_stay_seconds
            )
            if max_distance_m is not None and projected_distance > max_distance_m:
                if skip_unreachable:
                    continue
                raise RouteConstraintError("路线超过最大距离限制")
            if max_duration_s is not None and projected_duration > max_duration_s:
                if skip_unreachable:
                    continue
                raise RouteConstraintError("路线超过最大时长限制")

            legs.append(leg)
            leg_records.append(
                {
                    "order": len(leg_records),
                    "from_label": current_label,
                    "to_label": place.name,
                    "geometry": leg.geometry,
                    "distance_m": leg.distance_m,
                    "duration_s": leg.duration_s,
                    "instructions": leg.instructions,
                    "provider_metadata": leg.provider_metadata,
                    "reachable": leg.reachable,
                }
            )
            accepted_places.append(place)
            total_distance += leg.distance_m
            walking_duration += leg.duration_s
            current = place.location
            current_label = place.name

        if len(accepted_places) < 2:
            raise RoutePlanningError("可达且满足预算的地点不足两个")

        if return_to_origin:
            destination = origin or accepted_places[0].location
            destination_label = "当前位置" if origin else accepted_places[0].name
            return_leg = await self.routing.route(current, destination)
            projected_distance = total_distance + return_leg.distance_m
            projected_duration = (
                walking_duration
                + return_leg.duration_s
                + len(accepted_places) * planned_stay_seconds
            )
            if max_distance_m is not None and projected_distance > max_distance_m:
                raise RouteConstraintError("返程后路线超过最大距离限制")
            if max_duration_s is not None and projected_duration > max_duration_s:
                raise RouteConstraintError("返程后路线超过最大时长限制")
            legs.append(return_leg)
            leg_records.append(
                {
                    "order": len(leg_records),
                    "from_label": current_label,
                    "to_label": destination_label,
                    "geometry": return_leg.geometry,
                    "distance_m": return_leg.distance_m,
                    "duration_s": return_leg.duration_s,
                    "instructions": return_leg.instructions,
                    "provider_metadata": return_leg.provider_metadata,
                    "reachable": return_leg.reachable,
                }
            )
            total_distance = projected_distance
            walking_duration += return_leg.duration_s

        constraints = {
            "return_to_origin": return_to_origin,
            "max_distance_m": max_distance_m,
            "max_duration_s": max_duration_s,
            "planned_stay_seconds": planned_stay_seconds,
        }
        return {
            "id": uuid4(),
            "user_id": user_id,
            "plan_kind": plan_kind,
            "query": query,
            "origin": origin,
            "geometry": merge_leg_geometries(legs),
            "total_distance_m": round(total_distance, 2),
            "total_duration_s": walking_duration + len(accepted_places) * planned_stay_seconds,
            "routing_provider": self.routing.name,
            "routing_version": self.routing.version,
            "is_simulated": self.routing.is_simulated,
            "constraints": constraints,
            "score_breakdown": score_breakdown,
            "stops": [
                {
                    "order": order,
                    "place": place,
                    "planned_stay_seconds": planned_stay_seconds,
                }
                for order, place in enumerate(accepted_places)
            ],
            "legs": leg_records,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        }


def _merge(first: list[str], second: list[str]) -> list[str]:
    return list(dict.fromkeys([*first, *second]))
