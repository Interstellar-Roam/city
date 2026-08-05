import httpx
import pytest

from app.geo.schemas import GeoPoint
from app.routing.valhalla import ValhallaWalkingProvider, decode_polyline6


def _encode_polyline6(coordinates: list[tuple[float, float]]) -> str:
    previous_latitude = 0
    previous_longitude = 0
    encoded: list[str] = []
    for longitude, latitude in coordinates:
        current = [round(latitude * 1_000_000), round(longitude * 1_000_000)]
        for value, previous in zip(current, [previous_latitude, previous_longitude]):
            delta = value - previous
            shifted = ~(delta << 1) if delta < 0 else delta << 1
            while shifted >= 0x20:
                encoded.append(chr((0x20 | (shifted & 0x1F)) + 63))
                shifted >>= 5
            encoded.append(chr(shifted + 63))
        previous_latitude, previous_longitude = current
    return "".join(encoded)


def test_decode_polyline6_preserves_wgs84_coordinate_order() -> None:
    expected = [(113.912, 22.487), (113.910697, 22.487014)]

    assert decode_polyline6(_encode_polyline6(expected)) == expected


@pytest.mark.asyncio
async def test_valhalla_provider_returns_real_pedestrian_leg() -> None:
    coordinates = [(113.912, 22.487), (113.910697, 22.487014)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/route"
        return httpx.Response(
            200,
            json={
                "trip": {
                    "status": 0,
                    "legs": [
                        {
                            "shape": _encode_polyline6(coordinates),
                            "summary": {"length": 0.299, "time": 245.2},
                            "maneuvers": [
                                {
                                    "instruction": "Walk east.",
                                    "length": 0.299,
                                    "time": 245.2,
                                }
                            ],
                        }
                    ],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = ValhallaWalkingProvider(
            "https://routing.test/route",
            client=client,
        )
        leg = await provider.route(
            GeoPoint(longitude=113.912, latitude=22.487),
            GeoPoint(longitude=113.910697, latitude=22.487014),
        )

    assert provider.is_simulated is False
    assert leg.geometry == coordinates
    assert leg.distance_m == 299
    assert leg.duration_s == 245
    assert leg.instructions[0]["distance_m"] == 299
