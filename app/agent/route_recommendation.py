"""Tool-calling agent for query-driven, road-validated route recommendations."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings
from app.geo.intent import IntentParser
from app.geo.repositories import PlaceRepositoryProtocol
from app.geo.schemas import RoutePlanResponse, RouteRecommendationRequest
from app.geo.services import RoutePlanningService
from app.routing.base import RoutingError

SEARCH_PUBLIC_PLACES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_public_places",
        "description": (
            "Search verified public places near the user's origin. Use this before selecting stops. "
            "The server applies the private origin and radius; never invent place IDs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Short public-place keyword"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 10,
                },
                "city": {"type": "string"},
                "limit": {"type": "integer", "minimum": 2, "maximum": 20},
            },
            "additionalProperties": False,
        },
    },
}

BUILD_ROUTE_PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "build_route_plan",
        "description": (
            "Build the final walking route from place IDs returned by search_public_places. "
            "The server validates every road leg and enforces all budgets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "place_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                    "minItems": 2,
                    "maxItems": 8,
                },
                "selection_reason": {
                    "type": "string",
                    "description": "Concise factual reason for the selected public places",
                    "maxLength": 300,
                },
            },
            "required": ["place_ids"],
            "additionalProperties": False,
        },
    },
}


class RouteRecommendationAgent:
    """Bounded agent whose only side effect is a validated final route plan."""

    SYSTEM_PROMPT = """You are a CityWalk route-selection agent.

You must use tools and follow this sequence:
1. Search public places. You may refine the search when results are insufficient.
2. Select 2 to max_stops place IDs only from tool results.
3. Call build_route_plan. If road validation rejects a combination, adjust once using observed data.

Rules:
- The current query outranks historical preferences.
- Never invent place IDs, coordinates, road distances, durations, or reachability.
- Do not request or infer a user ID or exact origin; the server applies private data.
- Keep selection_reason short and factual. Do not output chain-of-thought.
- A route exists only after build_route_plan succeeds.
"""

    def __init__(
        self,
        places: PlaceRepositoryProtocol,
        planner: RoutePlanningService,
        *,
        client: Any | None = None,
        enabled: bool | None = None,
    ):
        self.settings = get_settings()
        self.places = places
        self.planner = planner
        self.enabled = (
            self.settings.recommendation_agent_enabled if enabled is None else enabled
        )
        if client is not None:
            self.client = client
        elif self.enabled and self.settings.llm_api_key:
            self.client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
            )
        else:
            self.client = None

    async def recommend(
        self,
        request: RouteRecommendationRequest,
        user_id: str,
        preferences: dict[str, Any] | None = None,
    ) -> RoutePlanResponse:
        if not self.enabled or self.client is None:
            return await self._fallback(request, user_id, preferences)

        try:
            async with asyncio.timeout(
                self.settings.recommendation_agent_timeout_seconds
            ):
                plan = await self._run_agent(request, user_id, preferences or {})
            if plan is not None:
                return plan
        except Exception as exc:
            logger.warning(f"路线推荐 Agent 失败，回退确定性推荐: {exc}")
        return await self._fallback(request, user_id, preferences)

    async def _run_agent(
        self,
        request: RouteRecommendationRequest,
        user_id: str,
        preferences: dict[str, Any],
    ) -> RoutePlanResponse | None:
        request = self._apply_query_budgets(request)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": request.query,
                        "radius_m": request.radius_m,
                        "max_stops": request.max_stops,
                        "required_categories": request.categories,
                        "required_tags": request.tags,
                        "return_to_origin": request.return_to_origin,
                        "max_distance_m": request.max_distance_m,
                        "max_duration_s": request.max_duration_s,
                        "preferences": self._preference_summary(preferences),
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        discovered: dict[UUID, Any] = {}
        requested_categories = self._string_list(request.categories, 20)
        requested_tags = self._string_list(request.tags, 30)
        search_count = 0

        for iteration in range(1, self.settings.recommendation_agent_max_iterations + 1):
            response = await self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                tools=[SEARCH_PUBLIC_PLACES_TOOL, BUILD_ROUTE_PLAN_TOOL],
                tool_choice="auto",
                temperature=0,
            )
            message = response.choices[0].message
            tool_calls = list(message.tool_calls or [])
            if not tool_calls:
                return None

            assistant_tool_calls: list[dict[str, Any]] = []
            for index, tool_call in enumerate(tool_calls):
                call_id = tool_call.id or f"route-agent-{iteration}-{index}"
                assistant_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or "{}",
                        },
                    }
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": assistant_tool_calls,
                }
            )

            for index, tool_call in enumerate(tool_calls):
                call_id = assistant_tool_calls[index]["id"]
                name = tool_call.function.name
                arguments = self._parse_arguments(tool_call.function.arguments)

                if name == "search_public_places":
                    if search_count >= self.settings.recommendation_agent_max_searches:
                        result = {"success": False, "error": "search budget exhausted"}
                    else:
                        search_count += 1
                        categories = self._merge(
                            self._string_list(request.categories, 20),
                            self._string_list(arguments.get("categories"), 8),
                        )
                        tags = self._merge(
                            self._string_list(request.tags, 30),
                            self._string_list(arguments.get("tags"), 10),
                        )
                        requested_categories = self._merge(requested_categories, categories)
                        requested_tags = self._merge(requested_tags, tags)
                        candidates = await self.places.search_places(
                            longitude=request.origin.longitude,
                            latitude=request.origin.latitude,
                            radius_m=request.radius_m,
                            query=self._short_text(arguments.get("query"), 100),
                            categories=categories or None,
                            tags=tags or None,
                            city=self._short_text(arguments.get("city"), 80),
                            limit=self._bounded_int(arguments.get("limit"), 2, 20, 12),
                        )
                        for place in candidates:
                            discovered[place.id] = place
                        result = {
                            "success": True,
                            "total": len(candidates),
                            "results": [
                                {
                                    "id": str(place.id),
                                    "name": place.name,
                                    "categories": place.categories,
                                    "tags": place.tags,
                                    "city": place.city,
                                    "district": place.district,
                                    "distance_m": place.distance_m,
                                    "quality_score": place.quality_score,
                                }
                                for place in candidates
                            ],
                        }
                elif name == "build_route_plan":
                    place_ids, error = self._validated_place_ids(
                        arguments.get("place_ids"),
                        discovered,
                        request.max_stops,
                    )
                    if error:
                        result = {"success": False, "error": error}
                    else:
                        selection_reason = self._short_text(
                            arguments.get("selection_reason"),
                            300,
                        )
                        try:
                            return await self.planner.create_agent_plan(
                                request,
                                user_id,
                                place_ids,
                                requested_categories=requested_categories,
                                requested_tags=requested_tags,
                                preferred_tags=self._string_list(
                                    preferences.get("preferred_tags"), 10
                                ),
                                agent_metadata={
                                    "iterations": iteration,
                                    "searches": search_count,
                                    "selection_reason": selection_reason,
                                },
                            )
                        except (ValueError, RoutingError) as exc:
                            result = {"success": False, "error": str(exc)}
                else:
                    result = {"success": False, "error": f"unknown tool: {name}"}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        return None

    async def _fallback(
        self,
        request: RouteRecommendationRequest,
        user_id: str,
        preferences: dict[str, Any] | None,
    ) -> RoutePlanResponse:
        return await self.planner.create_recommendation(
            request,
            user_id,
            preferences=preferences,
        )

    def _apply_query_budgets(
        self,
        request: RouteRecommendationRequest,
    ) -> RouteRecommendationRequest:
        intent = IntentParser.parse_heuristic(request.query)
        max_distance, max_duration = self.planner.resolve_recommendation_budgets(
            request,
            intent.max_distance_m,
            intent.max_duration_s,
        )
        return request.model_copy(
            update={
                "max_distance_m": max_distance,
                "max_duration_s": max_duration,
            }
        )

    @staticmethod
    def _preference_summary(preferences: dict[str, Any]) -> dict[str, Any]:
        return {
            "preferred_cities": RouteRecommendationAgent._string_list(
                preferences.get("preferred_cities"), 5
            ),
            "preferred_difficulty": RouteRecommendationAgent._short_text(
                preferences.get("preferred_difficulty"), 20
            ),
            "preferred_distance_range": preferences.get("preferred_distance_range"),
            "preferred_tags": RouteRecommendationAgent._string_list(
                preferences.get("preferred_tags"), 10
            ),
        }

    @staticmethod
    def _parse_arguments(value: str | None) -> dict[str, Any]:
        try:
            parsed = json.loads(value or "{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _validated_place_ids(
        values: Any,
        discovered: dict[UUID, Any],
        max_stops: int,
    ) -> tuple[list[UUID], str | None]:
        if not isinstance(values, list):
            return [], "place_ids must be an array"
        try:
            place_ids = [UUID(str(value)) for value in values]
        except (TypeError, ValueError, AttributeError):
            return [], "place_ids contains an invalid UUID"
        place_ids = list(dict.fromkeys(place_ids))
        if not 2 <= len(place_ids) <= max_stops:
            return [], f"select between 2 and {max_stops} unique places"
        unknown = [str(place_id) for place_id in place_ids if place_id not in discovered]
        if unknown:
            return [], f"place IDs were not returned by search: {', '.join(unknown)}"
        return place_ids, None

    @staticmethod
    def _string_list(value: Any, limit: int) -> list[str]:
        if not isinstance(value, (list, tuple)):
            return []
        return list(
            dict.fromkeys(
                text
                for item in value[:limit]
                if (text := str(item).strip()[:80])
            )
        )

    @staticmethod
    def _short_text(value: Any, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:limit] or None

    @staticmethod
    def _bounded_int(value: Any, minimum: int, maximum: int, default: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, number))

    @staticmethod
    def _merge(first: list[str], second: list[str]) -> list[str]:
        return list(dict.fromkeys([*first, *second]))
