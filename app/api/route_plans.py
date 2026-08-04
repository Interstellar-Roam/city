"""Road-validated multi-place planning and recommendation APIs."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.agent.route_recommendation import RouteRecommendationAgent
from app.database import Database
from app.geo.repositories import PlaceRepository
from app.geo.schemas import RoutePlanCreate, RouteRecommendationRequest
from app.geo.services import (
    PlaceNotFoundError,
    RouteConstraintError,
    RoutePlanningError,
    RoutePlanningService,
)
from app.geo.user_repositories import MongoRoutePlanRepository
from app.middleware.auth import get_current_user
from app.routing import RoutingError, UnreachableRouteError, build_routing_provider
from app.schemas.common import APIResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/route-plans", tags=["多地点路线规划"])


def get_route_planning_service() -> RoutePlanningService:
    return RoutePlanningService(
        places=PlaceRepository(),
        plans=MongoRoutePlanRepository(),
        routing=build_routing_provider(),
    )


def get_route_plan_repository() -> MongoRoutePlanRepository:
    return MongoRoutePlanRepository()


def get_session_service() -> SessionService:
    return SessionService(Database.get_db())


def get_route_recommendation_agent(
    service: RoutePlanningService = Depends(get_route_planning_service),
) -> RouteRecommendationAgent:
    return RouteRecommendationAgent(places=service.places, planner=service)


@router.post("", summary="连接多个指定地点")
async def create_route_plan(
    request: RoutePlanCreate,
    user_id: str = Depends(get_current_user),
    service: RoutePlanningService = Depends(get_route_planning_service),
) -> dict[str, Any]:
    try:
        plan = await service.create_explicit_plan(request, user_id)
    except PlaceNotFoundError as exc:
        return APIResponse(code=4104, message=str(exc)).model_dump()
    except RouteConstraintError as exc:
        return APIResponse(code=4102, message=str(exc)).model_dump()
    except UnreachableRouteError as exc:
        return APIResponse(code=4101, message=str(exc)).model_dump()
    except RoutingError as exc:
        return APIResponse(code=5101, message=str(exc)).model_dump()
    return APIResponse(data=plan.model_dump(mode="json")).model_dump(mode="json")


@router.post("/recommend", summary="根据文字与历史偏好推荐可达路线")
async def recommend_route_plan(
    request: RouteRecommendationRequest,
    user_id: str = Depends(get_current_user),
    agent: RouteRecommendationAgent = Depends(get_route_recommendation_agent),
    session_service: SessionService = Depends(get_session_service),
) -> dict[str, Any]:
    preference = await session_service.get_user_preference(user_id)
    preference_data = preference.model_dump() if preference else None

    try:
        plan = await agent.recommend(
            request,
            user_id,
            preferences=preference_data,
        )
    except RouteConstraintError as exc:
        return APIResponse(code=4102, message=str(exc)).model_dump()
    except (RoutePlanningError, UnreachableRouteError) as exc:
        return APIResponse(code=4101, message=str(exc)).model_dump()
    except RoutingError as exc:
        return APIResponse(code=5101, message=str(exc)).model_dump()

    inferred = plan.score_breakdown
    await session_service.update_user_preference(
        user_id=user_id,
        distance=plan.total_distance_m,
        tags=list(dict.fromkeys([
            *inferred.get("requested_categories", []),
            *inferred.get("requested_tags", []),
        ])),
    )
    return APIResponse(data=plan.model_dump(mode="json")).model_dump(mode="json")


@router.get("/{route_plan_id}", summary="获取路线规划结果")
async def get_route_plan(
    route_plan_id: UUID,
    user_id: str = Depends(get_current_user),
    repository: MongoRoutePlanRepository = Depends(get_route_plan_repository),
) -> dict[str, Any]:
    plan = await repository.get_plan(route_plan_id)
    if plan is None or plan["user_id"] != user_id:
        return APIResponse(code=4104, message="路线规划不存在").model_dump()
    return APIResponse(data=plan).model_dump(mode="json")
