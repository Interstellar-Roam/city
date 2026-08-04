"""Move legacy user-owned PostGIS rows to MongoDB before schema cleanup."""

from __future__ import annotations

import json
from typing import Any

from asyncpg import Connection
from loguru import logger

from app.database import Database


def _decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


async def migrate_legacy_private_geo_data(connection: Connection) -> None:
    """Idempotently copy legacy contribution and route-plan rows to MongoDB."""

    database = Database.get_db()
    contribution_count = 0
    route_count = 0

    if await _table_exists(connection, "place_contributions"):
        rows = await connection.fetch(
            """
            SELECT place_id, user_id, operation, payload,
                   moderation_status, created_at
            FROM place_contributions
            WHERE user_id IS NOT NULL
            """
        )
        for row in rows:
            contribution_id = f"{row['user_id']}:{row['operation']}:{row['place_id']}"
            await database.user_place_contributions.update_one(
                {"_id": contribution_id},
                {
                    "$setOnInsert": {
                        "user_id": row["user_id"],
                        "place_id": str(row["place_id"]),
                        "operation": row["operation"],
                        "payload": _decode_json(row["payload"], {}),
                        "created_at": row["created_at"],
                    },
                    "$set": {
                        "status": row["moderation_status"],
                        "updated_at": row["created_at"],
                        "migrated_from": "postgis",
                    },
                },
                upsert=True,
            )
            contribution_count += 1

    if await _table_exists(connection, "route_plans"):
        plan_rows = await connection.fetch(
            """
            SELECT id, user_id, plan_kind, query,
                   CASE WHEN origin IS NULL THEN NULL ELSE ST_X(origin::geometry) END
                       AS origin_longitude,
                   CASE WHEN origin IS NULL THEN NULL ELSE ST_Y(origin::geometry) END
                       AS origin_latitude,
                   ST_AsGeoJSON(geometry::geometry) AS geometry,
                   travel_mode, total_distance_m, total_duration_s,
                   routing_provider, routing_version, is_simulated,
                   constraints, score_breakdown, created_at, expires_at
            FROM route_plans
            """
        )
        for row in plan_rows:
            route_plan_id = str(row["id"])
            stop_rows = await connection.fetch(
                """
                SELECT stop_order, planned_stay_seconds, place_snapshot
                FROM route_plan_stops
                WHERE route_plan_id = $1
                ORDER BY stop_order
                """,
                row["id"],
            )
            leg_rows = await connection.fetch(
                """
                SELECT leg_order, from_label, to_label,
                       ST_AsGeoJSON(geometry::geometry) AS geometry,
                       distance_m, duration_s, instructions, reachable
                FROM route_plan_legs
                WHERE route_plan_id = $1
                ORDER BY leg_order
                """,
                row["id"],
            )
            origin = None
            if row["origin_longitude"] is not None:
                origin = {
                    "longitude": row["origin_longitude"],
                    "latitude": row["origin_latitude"],
                    "coordinate_system": "WGS84",
                }
            document = {
                "_id": route_plan_id,
                "user_id": row["user_id"],
                "plan_kind": row["plan_kind"],
                "query": row["query"],
                "origin": origin,
                "geometry": {
                    **_decode_json(row["geometry"], {}),
                    "coordinate_system": "WGS84",
                },
                "travel_mode": row["travel_mode"],
                "total_distance_m": row["total_distance_m"],
                "total_duration_s": row["total_duration_s"],
                "routing_provider": row["routing_provider"],
                "routing_version": row["routing_version"],
                "is_simulated": row["is_simulated"],
                "constraints": _decode_json(row["constraints"], {}),
                "score_breakdown": _decode_json(row["score_breakdown"], {}),
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "stops": [
                    {
                        "order": stop["stop_order"],
                        "planned_stay_seconds": stop["planned_stay_seconds"],
                        "place": _decode_json(stop["place_snapshot"], {}),
                    }
                    for stop in stop_rows
                ],
                "legs": [
                    {
                        "order": leg["leg_order"],
                        "from_label": leg["from_label"],
                        "to_label": leg["to_label"],
                        "geometry": {
                            **_decode_json(leg["geometry"], {}),
                            "coordinate_system": "WGS84",
                        },
                        "distance_m": leg["distance_m"],
                        "duration_s": leg["duration_s"],
                        "instructions": _decode_json(leg["instructions"], []),
                        "reachable": leg["reachable"],
                    }
                    for leg in leg_rows
                ],
                "migrated_from": "postgis",
            }
            await database.user_route_plans.replace_one(
                {"_id": route_plan_id},
                document,
                upsert=True,
            )
            route_count += 1

    if contribution_count or route_count:
        logger.info(
            f"已将 PostGIS 私域数据迁移到 MongoDB: "
            f"贡献 {contribution_count} 条，路线 {route_count} 条"
        )


async def _table_exists(connection: Connection, table_name: str) -> bool:
    return bool(
        await connection.fetchval(
            "SELECT to_regclass($1) IS NOT NULL",
            f"public.{table_name}",
        )
    )
