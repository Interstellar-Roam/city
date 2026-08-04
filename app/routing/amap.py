"""Amap walking-route provider with explicit coordinate conversion boundaries."""

from __future__ import annotations

from typing import Any

import httpx

from app.geo.schemas import GeoPoint
from app.routing.base import RouteLeg, RoutingError, RoutingProvider, UnreachableRouteError
from app.services.amap_service import wgs84_to_gcj02


def gcj02_to_wgs84(longitude: float, latitude: float) -> tuple[float, float]:
    """Iteratively approximate the inverse of the existing WGS84→GCJ02 transform."""
    wgs_lon, wgs_lat = longitude, latitude
    for _ in range(3):
        converted_lon, converted_lat = wgs84_to_gcj02(wgs_lon, wgs_lat)
        wgs_lon -= converted_lon - longitude
        wgs_lat -= converted_lat - latitude
    return wgs_lon, wgs_lat


class AmapWalkingProvider(RoutingProvider):
    name = "amap-walking"
    version = "v3"
    is_simulated = False
    base_url = "https://restapi.amap.com/v3/direction/walking"

    def __init__(self, api_key: str, timeout_seconds: float = 10.0):
        if not api_key:
            raise RoutingError("AMAP_API_KEY_BACKEND 未配置")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteLeg:
        origin_gcj = wgs84_to_gcj02(origin.longitude, origin.latitude)
        destination_gcj = wgs84_to_gcj02(destination.longitude, destination.latitude)
        params = {
            "key": self.api_key,
            "origin": f"{origin_gcj[0]:.6f},{origin_gcj[1]:.6f}",
            "destination": f"{destination_gcj[0]:.6f},{destination_gcj[1]:.6f}",
            "output": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RoutingError(f"高德步行路径请求失败: {exc}") from exc

        data: dict[str, Any] = response.json()
        if data.get("status") != "1":
            info = data.get("info", "unknown error")
            if info in {"ROUTE_FAIL", "NO_ROADS_NEARBY"}:
                raise UnreachableRouteError(f"高德未找到可步行路线: {info}")
            raise RoutingError(f"高德步行路径返回错误: {info}")

        paths = data.get("route", {}).get("paths", [])
        if not paths:
            raise UnreachableRouteError("高德未返回步行路径")

        path = paths[0]
        coordinates: list[tuple[float, float]] = []
        instructions: list[dict[str, Any]] = []
        for step in path.get("steps", []):
            instructions.append(
                {
                    "instruction": step.get("instruction", ""),
                    "road": step.get("road", ""),
                    "distance_m": float(step.get("distance", 0) or 0),
                    "duration_s": int(float(step.get("duration", 0) or 0)),
                }
            )
            for pair in step.get("polyline", "").split(";"):
                if not pair or "," not in pair:
                    continue
                lon_text, lat_text = pair.split(",", 1)
                wgs = gcj02_to_wgs84(float(lon_text), float(lat_text))
                if not coordinates or wgs != coordinates[-1]:
                    coordinates.append(wgs)

        if len(coordinates) < 2:
            coordinates = [
                (origin.longitude, origin.latitude),
                (destination.longitude, destination.latitude),
            ]

        return RouteLeg(
            geometry=coordinates,
            distance_m=float(path.get("distance", 0) or 0),
            duration_s=int(float(path.get("duration", 0) or 0)),
            instructions=instructions,
            provider_metadata={"amap_count": data.get("count")},
        )
