"""Valhalla pedestrian routing backed by OpenStreetMap road data."""

from __future__ import annotations

from typing import Any

import httpx

from app.geo.schemas import GeoPoint
from app.routing.base import RouteLeg, RoutingError, RoutingProvider, UnreachableRouteError


def decode_polyline6(shape: str) -> list[tuple[float, float]]:
    """Decode a Valhalla precision-6 polyline into WGS-84 (longitude, latitude)."""
    coordinates: list[tuple[float, float]] = []
    index = 0
    latitude = 0
    longitude = 0
    while index < len(shape):
        deltas: list[int] = []
        for _ in range(2):
            result = 0
            shift = 0
            while True:
                if index >= len(shape):
                    raise RoutingError("Valhalla 路线 shape 格式无效")
                value = ord(shape[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += deltas[0]
        longitude += deltas[1]
        coordinates.append((longitude / 1_000_000, latitude / 1_000_000))
    return coordinates


class ValhallaWalkingProvider(RoutingProvider):
    name = "valhalla-pedestrian"
    version = "route-v1"
    is_simulated = False

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        *,
        client: httpx.AsyncClient | None = None,
    ):
        if not base_url:
            raise RoutingError("VALHALLA_BASE_URL 未配置")
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.client = client

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteLeg:
        payload = {
            "locations": [
                {"lat": origin.latitude, "lon": origin.longitude},
                {"lat": destination.latitude, "lon": destination.longitude},
            ],
            "costing": "pedestrian",
            "units": "kilometers",
            "directions_options": {"units": "kilometers"},
        }
        try:
            if self.client is not None:
                response = await self.client.post(self.base_url, json=payload)
                response.raise_for_status()
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.base_url, json=payload)
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RoutingError(f"Valhalla 步行路径请求失败: {exc}") from exc

        data: dict[str, Any] = response.json()
        if data.get("error_code") is not None:
            code = data.get("error_code")
            message = data.get("error", "unknown error")
            if code in {170, 171, 442, 443}:
                raise UnreachableRouteError(f"Valhalla 未找到可步行路线: {message}")
            raise RoutingError(f"Valhalla 步行路径返回错误: {message}")

        trip = data.get("trip", {})
        if trip.get("status") not in {0, None}:
            raise RoutingError(f"Valhalla 路线状态异常: {trip.get('status_message')}")
        legs = trip.get("legs", [])
        if not legs:
            raise UnreachableRouteError("Valhalla 未返回步行路径")

        leg = legs[0]
        coordinates = decode_polyline6(leg.get("shape", ""))
        if len(coordinates) < 2:
            raise RoutingError("Valhalla 返回的路线 geometry 不完整")

        summary = leg.get("summary", {})
        instructions = [
            {
                "instruction": maneuver.get("instruction", ""),
                "street_names": maneuver.get("street_names", []),
                "distance_m": round(float(maneuver.get("length", 0)) * 1000, 2),
                "duration_s": int(round(float(maneuver.get("time", 0)))),
            }
            for maneuver in leg.get("maneuvers", [])
        ]
        return RouteLeg(
            geometry=coordinates,
            distance_m=round(float(summary.get("length", 0)) * 1000, 2),
            duration_s=max(1, int(round(float(summary.get("time", 0))))),
            instructions=instructions,
            provider_metadata={
                "costing": "pedestrian",
                "has_time_restrictions": summary.get("has_time_restrictions", False),
            },
        )
