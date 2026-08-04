"""Deterministic routing provider for local development and E2E tests."""

from __future__ import annotations

from app.geo.schemas import GeoPoint
from app.routing.base import RouteLeg, RoutingProvider, UnreachableRouteError, haversine_m


class DeterministicRoutingProvider(RoutingProvider):
    """Builds a reproducible orthogonal path and clearly marks it as simulated."""

    name = "deterministic-test"
    version = "1"
    is_simulated = True

    def __init__(self, max_leg_distance_m: float = 50_000, walking_speed_mps: float = 1.3):
        self.max_leg_distance_m = max_leg_distance_m
        self.walking_speed_mps = walking_speed_mps

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteLeg:
        direct_distance = haversine_m(origin, destination)
        if direct_distance > self.max_leg_distance_m:
            raise UnreachableRouteError("测试路由器判定该路段超出最大步行距离")

        corner = GeoPoint(longitude=destination.longitude, latitude=origin.latitude)
        first = haversine_m(origin, corner)
        second = haversine_m(corner, destination)
        distance = max(direct_distance, first + second)
        geometry = [
            (origin.longitude, origin.latitude),
            (corner.longitude, corner.latitude),
            (destination.longitude, destination.latitude),
        ]
        geometry = list(dict.fromkeys(geometry))
        if len(geometry) < 2:
            geometry = [
                (origin.longitude, origin.latitude),
                (destination.longitude + 1e-9, destination.latitude),
            ]

        return RouteLeg(
            geometry=geometry,
            distance_m=round(distance, 2),
            duration_s=max(1, round(distance / self.walking_speed_mps)),
            instructions=[{"instruction": "模拟步行至下一地点", "distance_m": round(distance, 2)}],
            provider_metadata={"simulated": True},
        )
