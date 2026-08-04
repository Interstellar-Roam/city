"""Live Docker E2E flow using multiple real PostGIS place records."""

from __future__ import annotations

import asyncio
import os
import time

import asyncpg
import httpx
import pytest
from pymongo import MongoClient

pytestmark = pytest.mark.e2e


def _base_url() -> str:
    value = os.getenv("E2E_BASE_URL")
    if not value:
        pytest.skip("set E2E_BASE_URL to run Docker E2E tests")
    return value.rstrip("/")


def _wait_for_api(base_url: str, timeout_s: float = 60) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(f"API did not become ready within {timeout_s}s: {last_error}")


def _login(client: httpx.Client) -> tuple[dict[str, str], str]:
    suffix = str(time.time_ns())[-8:]
    phone = f"139{suffix}"
    send = client.post("/api/v1/auth/send-code", json={"phone": phone})
    assert send.status_code == 200
    assert send.json()["code"] == 0
    login = client.post("/api/v1/auth/login", json={"phone": phone, "code": "123456"})
    assert login.status_code == 200
    payload = login.json()
    assert payload["code"] == 0
    return (
        {"Authorization": f"Bearer {payload['data']['access_token']}"},
        payload["data"]["user"]["id"],
    )


def _assert_storage_boundary(
    contributor_id: str,
    route_owner_id: str,
    place_ids: list[str],
    route_plan_id: str,
) -> None:
    mongo_url = os.getenv("E2E_MONGODB_URL", "mongodb://127.0.0.1:27017")
    mongo_db_name = os.getenv("E2E_MONGODB_DB_NAME", "citywalk")
    with MongoClient(mongo_url, serverSelectionTimeoutMS=5000) as mongo:
        db = mongo[mongo_db_name]
        contributions = list(
            db.user_place_contributions.find(
                {"user_id": contributor_id, "place_id": {"$in": place_ids}}
            )
        )
        assert {item["place_id"] for item in contributions} == set(place_ids)
        assert all(item["status"] == "published" for item in contributions)

        route_plan = db.user_route_plans.find_one({"_id": route_plan_id})
        assert route_plan is not None
        assert route_plan["user_id"] == route_owner_id

    async def assert_postgis_is_public_only() -> None:
        dsn = os.getenv(
            "E2E_POSTGRES_DSN",
            "postgresql://citywalk:citywalk@127.0.0.1:5432/citywalk",
        )
        connection = await asyncpg.connect(dsn)
        try:
            private_columns = await connection.fetch(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (
                    table_name IN (
                        'place_contributions', 'route_plans',
                        'route_plan_stops', 'route_plan_legs'
                    )
                    OR (table_name = 'places' AND column_name = 'created_by')
                  )
                """
            )
            assert private_columns == []
        finally:
            await connection.close()

    asyncio.run(assert_postgis_is_public_only())


def test_contributed_places_become_public_and_user_routes_stay_private() -> None:
    base_url = _base_url()
    _wait_for_api(base_url)
    suffix = str(time.time_ns())[-7:]
    coordinates = [
        (121.44300, 31.20500, "咖啡", ["安静"]),
        (121.44600, 31.20700, "公园", ["树荫"]),
        (121.44900, 31.20900, "建筑", ["历史", "拍照"]),
        (121.45200, 31.21100, "文化", ["安静"]),
    ]

    with httpx.Client(base_url=base_url, timeout=30) as client:
        contributor_headers, contributor_id = _login(client)
        place_ids: list[str] = []
        for index, (longitude, latitude, category, tags) in enumerate(coordinates):
            response = client.post(
                "/api/v1/places",
                headers=contributor_headers,
                json={
                    "name": f"E2E-{suffix}-{index}-{category}",
                    "description": "Docker E2E 多地点测试数据",
                    "location": {"longitude": longitude, "latitude": latitude},
                    "categories": [category],
                    "tags": tags,
                    "city": "上海",
                    "district": "徐汇区",
                },
            )
            assert response.status_code == 201, response.text
            place_ids.append(response.json()["data"]["id"])

        search = client.get(
            "/api/v1/places/search",
            params={
                "query": f"E2E-{suffix}",
                "longitude": 121.447,
                "latitude": 31.208,
                "radius_m": 5000,
            },
        )
        assert search.status_code == 200
        assert search.json()["data"]["total"] == 4
        assert all("created_by" not in item for item in search.json()["data"]["items"])

        viewer_headers, viewer_id = _login(client)
        assert viewer_id != contributor_id

        explicit = client.post(
            "/api/v1/route-plans",
            headers=viewer_headers,
            json={
                "place_ids": place_ids,
                "optimize_order": True,
                "return_to_origin": True,
                "max_distance_m": 20_000,
            },
        )
        assert explicit.status_code == 200, explicit.text
        explicit_payload = explicit.json()
        assert explicit_payload["code"] == 0, explicit_payload
        explicit_plan = explicit_payload["data"]
        assert len(explicit_plan["stops"]) == 4
        assert len(explicit_plan["legs"]) == 4
        assert explicit_plan["is_simulated"] is True
        assert explicit_plan["geometry"]["coordinates"][0] == explicit_plan["geometry"]["coordinates"][-1]

        fetched = client.get(
            f"/api/v1/route-plans/{explicit_plan['id']}",
            headers=viewer_headers,
        )
        assert fetched.status_code == 200
        assert fetched.json()["data"]["id"] == explicit_plan["id"]

        private_fetch = client.get(
            f"/api/v1/route-plans/{explicit_plan['id']}",
            headers=contributor_headers,
        )
        assert private_fetch.json()["code"] == 4104

        recommendation = client.post(
            "/api/v1/route-plans/recommend",
            headers=viewer_headers,
            json={
                "query": "推荐安静、有树荫的咖啡、公园和建筑路线",
                "origin": {"longitude": 121.442, "latitude": 31.204},
                "radius_m": 5000,
                "max_stops": 4,
                "max_distance_m": 20_000,
            },
        )
        assert recommendation.status_code == 200, recommendation.text
        recommendation_payload = recommendation.json()
        assert recommendation_payload["code"] == 0, recommendation_payload
        recommended_plan = recommendation_payload["data"]
        assert 2 <= len(recommended_plan["stops"]) <= 4
        assert len(recommended_plan["legs"]) >= 2
        assert all(leg["reachable"] for leg in recommended_plan["legs"])
        assert recommended_plan["total_distance_m"] > 0

        _assert_storage_boundary(
            contributor_id,
            viewer_id,
            place_ids,
            explicit_plan["id"],
        )
