"""API and service schemas for places and route planning."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GeoPoint(BaseModel):
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    coordinate_system: Literal["WGS84"] = "WGS84"


class GeoLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(..., min_length=2)
    coordinate_system: Literal["WGS84"] = "WGS84"


class PlaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    address: str | None = Field(None, max_length=500)
    location: GeoPoint
    categories: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=30)
    city: str | None = Field(None, max_length=80)
    district: str | None = Field(None, max_length=80)
    images: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("地点名称不能为空")
        return value

    @field_validator("categories", "tags")
    @classmethod
    def normalize_terms(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    address: str | None = None
    location: GeoPoint
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    city: str | None = None
    district: str | None = None
    images: list[str] = Field(default_factory=list)
    source_type: str
    external_refs: dict[str, Any] = Field(default_factory=dict)
    moderation_status: str
    quality_score: float = 0
    created_at: datetime
    updated_at: datetime
    distance_m: float | None = None


class PlaceSearchResponse(BaseModel):
    items: list[PlaceResponse]
    total: int


class RoutePlanCreate(BaseModel):
    place_ids: list[UUID] = Field(..., min_length=2, max_length=12)
    origin: GeoPoint | None = None
    optimize_order: bool = True
    return_to_origin: bool = False
    max_distance_m: float | None = Field(None, gt=0, le=100_000)
    max_duration_s: int | None = Field(None, gt=0, le=86_400)
    planned_stay_seconds: int = Field(0, ge=0, le=14_400)

    @field_validator("place_ids")
    @classmethod
    def unique_places(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError("place_ids 不能重复")
        return values


class RouteRecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    origin: GeoPoint
    radius_m: float = Field(5000, gt=0, le=50_000)
    max_stops: int = Field(4, ge=2, le=8)
    categories: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=30)
    return_to_origin: bool = False
    max_distance_m: float | None = Field(None, gt=0, le=100_000)
    max_duration_s: int | None = Field(None, gt=0, le=86_400)
    planned_stay_seconds: int = Field(0, ge=0, le=14_400)

class RoutePlanStopResponse(BaseModel):
    order: int
    place: PlaceResponse
    planned_stay_seconds: int = 0


class RouteLegResponse(BaseModel):
    order: int
    from_label: str
    to_label: str
    geometry: GeoLineString
    distance_m: float
    duration_s: int
    instructions: list[dict[str, Any]] = Field(default_factory=list)
    reachable: bool = True


class RoutePlanResponse(BaseModel):
    id: UUID
    user_id: str
    plan_kind: Literal["explicit", "recommendation"]
    query: str | None = None
    origin: GeoPoint | None = None
    geometry: GeoLineString
    travel_mode: Literal["walking"] = "walking"
    total_distance_m: float
    total_duration_s: int
    routing_provider: str
    routing_version: str | None = None
    is_simulated: bool = False
    constraints: dict[str, Any] = Field(default_factory=dict)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    stops: list[RoutePlanStopResponse]
    legs: list[RouteLegResponse]
    created_at: datetime
    expires_at: datetime | None = None
