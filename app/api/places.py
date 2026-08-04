"""Place sharing and PostGIS spatial-search APIs."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.geo.repositories import PlaceRepository
from app.geo.schemas import PlaceCreate
from app.geo.services import DuplicatePlaceError, PlaceService
from app.geo.user_repositories import MongoPlaceContributionRepository
from app.middleware.auth import get_current_user
from app.schemas.common import APIResponse

router = APIRouter(prefix="/places", tags=["地点"])


def get_place_repository() -> PlaceRepository:
    return PlaceRepository()


def get_place_service(
    repository: PlaceRepository = Depends(get_place_repository),
) -> PlaceService:
    return PlaceService(repository, MongoPlaceContributionRepository())


@router.post("", summary="分享地点")
async def share_place(
    request: PlaceCreate,
    user_id: str = Depends(get_current_user),
    service: PlaceService = Depends(get_place_service),
) -> JSONResponse:
    try:
        place = await service.share_place(request, user_id)
    except DuplicatePlaceError as exc:
        return JSONResponse(
            status_code=409,
            content=APIResponse(
                code=4001,
                message=str(exc),
                data={"duplicate": exc.duplicate.model_dump(mode="json")},
            ).model_dump(mode="json"),
        )
    return JSONResponse(
        status_code=201,
        content=APIResponse(data=place.model_dump(mode="json")).model_dump(mode="json"),
    )


@router.get("/search", summary="搜索附近地点")
async def search_places(
    query: str | None = Query(None, max_length=200),
    longitude: float | None = Query(None, ge=-180, le=180),
    latitude: float | None = Query(None, ge=-90, le=90),
    radius_m: float | None = Query(5000, gt=0, le=50_000),
    categories: str | None = Query(None, description="逗号分隔的分类"),
    tags: str | None = Query(None, description="逗号分隔的标签"),
    city: str | None = Query(None, max_length=80),
    limit: int = Query(20, ge=1, le=100),
    repository: PlaceRepository = Depends(get_place_repository),
) -> dict[str, Any]:
    if (longitude is None) != (latitude is None):
        return APIResponse(code=4002, message="longitude 和 latitude 必须同时提供").model_dump()

    items = await repository.search_places(
        longitude=longitude,
        latitude=latitude,
        radius_m=radius_m if longitude is not None else None,
        query=query,
        categories=_split_terms(categories),
        tags=_split_terms(tags),
        city=city,
        limit=limit,
    )
    return APIResponse(
        data={
            "items": [item.model_dump(mode="json") for item in items],
            "total": len(items),
        }
    ).model_dump(mode="json")


@router.get("/{place_id}", summary="获取地点详情")
async def get_place(
    place_id: UUID,
    repository: PlaceRepository = Depends(get_place_repository),
) -> dict[str, Any]:
    place = await repository.get_place(place_id)
    if place is None:
        return APIResponse(code=4004, message="地点不存在").model_dump()
    return APIResponse(data=place.model_dump(mode="json")).model_dump(mode="json")


def _split_terms(value: str | None) -> list[str] | None:
    if not value:
        return None
    terms = list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))
    return terms or None
