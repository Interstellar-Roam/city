"""MongoDB repositories for user-owned geographic activity.

PostGIS deliberately contains no user identifiers. These repositories keep the
private attribution and personalized route plans in MongoDB.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import Database
from app.geo.schemas import PlaceCreate


class PlaceContributionRepositoryProtocol(Protocol):
    async def start_create(self, user_id: str, place_id: UUID, data: PlaceCreate) -> None: ...

    async def mark_published(self, user_id: str, place_id: UUID) -> None: ...

    async def mark_failed(self, user_id: str, place_id: UUID, reason: str) -> None: ...


class RoutePlanRepositoryProtocol(Protocol):
    async def save_plan(self, plan: dict[str, Any]) -> dict[str, Any]: ...

    async def get_plan(self, route_plan_id: UUID) -> dict[str, Any] | None: ...


class MongoPlaceContributionRepository:
    """Private link between a user and a public PostGIS place."""

    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        database = db if db is not None else Database.get_db()
        self.collection = database.user_place_contributions

    async def start_create(self, user_id: str, place_id: UUID, data: PlaceCreate) -> None:
        now = datetime.now(timezone.utc)
        contribution_id = self._contribution_id(user_id, place_id)
        await self.collection.update_one(
            {"_id": contribution_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "place_id": str(place_id),
                    "operation": "create",
                    "payload": data.model_dump(mode="json"),
                    "created_at": now,
                },
                "$set": {"status": "pending", "updated_at": now},
                "$unset": {"failure_reason": ""},
            },
            upsert=True,
        )

    async def mark_published(self, user_id: str, place_id: UUID) -> None:
        await self._mark_status(user_id, place_id, "published")

    async def mark_failed(self, user_id: str, place_id: UUID, reason: str) -> None:
        await self._mark_status(user_id, place_id, "failed", reason=reason[:500])

    async def _mark_status(
        self,
        user_id: str,
        place_id: UUID,
        status: str,
        *,
        reason: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        }
        if reason:
            update["$set"]["failure_reason"] = reason
        else:
            update["$unset"] = {"failure_reason": ""}
        await self.collection.update_one(
            {"_id": self._contribution_id(user_id, place_id)},
            update,
        )

    @staticmethod
    def _contribution_id(user_id: str, place_id: UUID) -> str:
        return f"{user_id}:create:{place_id}"


class MongoRoutePlanRepository:
    """Personalized route plans, including origin and recommendation text."""

    def __init__(self, db: AsyncIOMotorDatabase | None = None):
        database = db if db is not None else Database.get_db()
        self.collection = database.user_route_plans

    async def save_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        route_plan_id = str(plan["id"])
        document = jsonable_encoder(plan)
        document.pop("id", None)
        document["_id"] = route_plan_id
        document["created_at"] = datetime.now(timezone.utc)
        document["expires_at"] = plan.get("expires_at")
        self._normalize_geometries(document)
        await self.collection.replace_one(
            {"_id": route_plan_id},
            document,
            upsert=True,
        )
        return self._to_response(document)

    async def get_plan(self, route_plan_id: UUID) -> dict[str, Any] | None:
        document = await self.collection.find_one(
            {
                "_id": str(route_plan_id),
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gt": datetime.now(timezone.utc)}},
                ],
            }
        )
        return self._to_response(document) if document else None

    @staticmethod
    def _to_response(document: dict[str, Any]) -> dict[str, Any]:
        response = dict(document)
        response["id"] = response.pop("_id")
        MongoRoutePlanRepository._normalize_geometries(response)
        return response

    @staticmethod
    def _normalize_geometries(document: dict[str, Any]) -> None:
        geometry = document.get("geometry")
        if isinstance(geometry, list):
            document["geometry"] = {
                "type": "LineString",
                "coordinates": geometry,
                "coordinate_system": "WGS84",
            }
        for leg in document.get("legs", []):
            leg_geometry = leg.get("geometry")
            if isinstance(leg_geometry, list):
                leg["geometry"] = {
                    "type": "LineString",
                    "coordinates": leg_geometry,
                    "coordinate_system": "WGS84",
                }
