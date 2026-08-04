"""Repositories for the PostGIS geographic domain."""

from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import UUID, uuid4

from asyncpg import Pool, Record

from app.geo.database import GeoDatabase
from app.geo.schemas import GeoPoint, PlaceCreate, PlaceResponse


def _decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _place_from_row(row: Record | dict[str, Any]) -> PlaceResponse:
    data = dict(row)
    return PlaceResponse(
        id=data["id"],
        name=data["name"],
        description=data.get("description"),
        address=data.get("address"),
        location=GeoPoint(longitude=data["longitude"], latitude=data["latitude"]),
        categories=list(data.get("categories") or []),
        tags=list(data.get("tags") or []),
        city=data.get("city"),
        district=data.get("district"),
        images=_decode_json(data.get("images"), []),
        source_type=data["source_type"],
        external_refs=_decode_json(data.get("external_refs"), {}),
        moderation_status=data["moderation_status"],
        quality_score=data.get("quality_score") or 0,
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        distance_m=float(data["distance_m"]) if data.get("distance_m") is not None else None,
    )


PLACE_SELECT = """
    id, name, description, address, categories, tags, city, district,
    images, source_type, external_refs, moderation_status, quality_score,
    created_at, updated_at,
    ST_X(location::geometry) AS longitude,
    ST_Y(location::geometry) AS latitude
"""


class PlaceRepositoryProtocol(Protocol):
    async def create_place(
        self,
        data: PlaceCreate,
        *,
        source_type: str,
        place_id: UUID | None = None,
        external_refs: dict[str, Any] | None = None,
        quality_score: float = 0,
    ) -> PlaceResponse: ...

    async def find_duplicate(self, data: PlaceCreate, radius_m: float) -> PlaceResponse | None: ...

    async def get_place(self, place_id: UUID) -> PlaceResponse | None: ...

    async def get_places(self, place_ids: list[UUID]) -> list[PlaceResponse]: ...

    async def search_places(
        self,
        *,
        longitude: float | None = None,
        latitude: float | None = None,
        radius_m: float | None = None,
        query: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[PlaceResponse]: ...


class PlaceRepository:
    def __init__(self, pool: Pool | None = None):
        self.pool = pool or GeoDatabase.get_pool()

    async def find_duplicate(self, data: PlaceCreate, radius_m: float) -> PlaceResponse | None:
        row = await self.pool.fetchrow(
            f"""
            SELECT {PLACE_SELECT},
                   ST_Distance(
                       location,
                       ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography
                   ) AS distance_m
            FROM places
            WHERE lower(name) = lower($1)
              AND moderation_status <> 'archived'
              AND ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography,
                    $4
              )
            ORDER BY distance_m
            LIMIT 1
            """,
            data.name,
            data.location.longitude,
            data.location.latitude,
            radius_m,
        )
        return _place_from_row(row) if row else None

    async def create_place(
        self,
        data: PlaceCreate,
        *,
        source_type: str,
        place_id: UUID | None = None,
        external_refs: dict[str, Any] | None = None,
        quality_score: float = 0,
    ) -> PlaceResponse:
        place_id = place_id or uuid4()

        async with self.pool.acquire() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO places(
                    id, name, description, address, categories, tags, location,
                    city, district, images, source_type, external_refs,
                    moderation_status, quality_score
                ) VALUES(
                    $1, $2, $3, $4, $5, $6,
                    ST_SetSRID(ST_MakePoint($7, $8), 4326)::geography,
                    $9, $10, $11::jsonb, $12, $13::jsonb,
                    'published', $14
                )
                """,
                place_id,
                data.name,
                data.description,
                data.address,
                data.categories,
                data.tags,
                data.location.longitude,
                data.location.latitude,
                data.city,
                data.district,
                json.dumps(data.images, ensure_ascii=False),
                source_type,
                json.dumps(external_refs or {}, ensure_ascii=False),
                quality_score,
            )

        place = await self.get_place(place_id)
        if place is None:  # pragma: no cover - protects against unexpected DB failure
            raise RuntimeError("地点写入后无法读取")
        return place

    async def get_place(self, place_id: UUID) -> PlaceResponse | None:
        row = await self.pool.fetchrow(
            f"SELECT {PLACE_SELECT} FROM places WHERE id = $1",
            place_id,
        )
        return _place_from_row(row) if row else None

    async def get_places(self, place_ids: list[UUID]) -> list[PlaceResponse]:
        if not place_ids:
            return []
        rows = await self.pool.fetch(
            f"SELECT {PLACE_SELECT} FROM places WHERE id = ANY($1::uuid[])",
            place_ids,
        )
        by_id = {place.id: place for place in (_place_from_row(row) for row in rows)}
        return [by_id[place_id] for place_id in place_ids if place_id in by_id]

    async def search_places(
        self,
        *,
        longitude: float | None = None,
        latitude: float | None = None,
        radius_m: float | None = None,
        query: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[PlaceResponse]:
        conditions = ["moderation_status = 'published'"]
        args: list[Any] = []

        def bind(value: Any, cast: str = "") -> str:
            args.append(value)
            return f"${len(args)}{cast}"

        distance_expression = "NULL::double precision AS distance_m"
        order_parts = ["quality_score DESC", "created_at DESC"]
        if longitude is not None and latitude is not None:
            lon_ref = bind(longitude)
            lat_ref = bind(latitude)
            point = f"ST_SetSRID(ST_MakePoint({lon_ref}, {lat_ref}), 4326)::geography"
            distance_expression = f"ST_Distance(location, {point}) AS distance_m"
            order_parts.insert(0, "distance_m ASC")
            if radius_m is not None:
                radius_ref = bind(radius_m)
                conditions.append(f"ST_DWithin(location, {point}, {radius_ref})")

        if query:
            query_ref = bind(f"%{query.strip()}%")
            conditions.append(
                "concat_ws(' ', name, coalesce(description, ''), coalesce(address, ''), "
                f"array_to_string(categories, ' '), array_to_string(tags, ' ')) ILIKE {query_ref}"
            )
        if categories:
            conditions.append(f"categories && {bind(categories, '::text[]')}")
        if tags:
            conditions.append(f"tags && {bind(tags, '::text[]')}")
        if city:
            conditions.append(f"city = {bind(city)}")

        limit_ref = bind(limit)
        sql = f"""
            SELECT {PLACE_SELECT}, {distance_expression}
            FROM places
            WHERE {' AND '.join(conditions)}
            ORDER BY {', '.join(order_parts)}
            LIMIT {limit_ref}
        """
        rows = await self.pool.fetch(sql, *args)
        return [_place_from_row(row) for row in rows]
