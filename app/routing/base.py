"""Routing provider contracts and shared geometry helpers."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.geo.schemas import GeoPoint


class RoutingError(RuntimeError):
    """Base routing provider failure."""


class UnreachableRouteError(RoutingError):
    """Raised when no walkable path exists between two points."""


@dataclass(slots=True)
class RouteLeg:
    geometry: list[tuple[float, float]]
    distance_m: float
    duration_s: int
    instructions: list[dict[str, Any]] = field(default_factory=list)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    reachable: bool = True


class RoutingProvider(ABC):
    name: str
    version: str | None = None
    is_simulated: bool = False

    @abstractmethod
    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteLeg:
        """Return a road-network walking route between two WGS-84 points."""


def haversine_m(origin: GeoPoint, destination: GeoPoint) -> float:
    radius = 6_371_000.0
    lat1 = math.radians(origin.latitude)
    lat2 = math.radians(destination.latitude)
    delta_lat = math.radians(destination.latitude - origin.latitude)
    delta_lon = math.radians(destination.longitude - origin.longitude)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def merge_leg_geometries(legs: list[RouteLeg]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for leg in legs:
        for coordinate in leg.geometry:
            if not merged or coordinate != merged[-1]:
                merged.append(coordinate)
    if len(merged) < 2:
        raise RoutingError("路线 geometry 至少需要两个不同坐标")
    return merged
