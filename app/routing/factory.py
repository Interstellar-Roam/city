"""Routing provider factory."""

from app.config import get_settings
from app.routing.amap import AmapWalkingProvider
from app.routing.base import RoutingProvider
from app.routing.deterministic import DeterministicRoutingProvider
from app.routing.valhalla import ValhallaWalkingProvider


def build_routing_provider() -> RoutingProvider:
    settings = get_settings()
    if settings.routing_provider == "deterministic":
        return DeterministicRoutingProvider()
    if settings.routing_provider == "valhalla":
        return ValhallaWalkingProvider(
            base_url=settings.valhalla_base_url,
            timeout_seconds=settings.routing_request_timeout_seconds,
        )
    return AmapWalkingProvider(
        api_key=settings.amap_api_key_backend or settings.amap_api_key,
        timeout_seconds=settings.routing_request_timeout_seconds,
    )
