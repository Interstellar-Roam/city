"""Idempotently import OSM-verified Xiaohongshu places into PostGIS.

An OSM element is treated as a public-place identity across datasets.  When an
older dataset already contains it, this importer reuses that row and merges the
new dataset membership and Xiaohongshu evidence instead of creating a duplicate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "shenzhen_xhs_verified_places.json"
SHENZHEN_DISTRICTS = {
    "宝安区",
    "福田区",
    "南山区",
    "罗湖区",
    "龙岗区",
    "龙华区",
    "盐田区",
    "坪山区",
    "光明区",
    "大鹏新区",
}


def load_dataset(path: Path) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    places = dataset.get("places", [])
    if not places:
        raise ValueError("可发布地点集不能为空")
    if len({place["dataset_key"] for place in places}) != len(places):
        raise ValueError("dataset_key 重复")
    if len({place["name"] for place in places}) != len(places):
        raise ValueError("地点名称重复")
    for place in places:
        if place["city"] != "深圳" or place["district"] not in SHENZHEN_DISTRICTS:
            raise ValueError(f"非深圳地点: {place['name']}")
        longitude = place["location"]["longitude"]
        latitude = place["location"]["latitude"]
        if not (113.70 <= longitude <= 114.65 and 22.43 <= latitude <= 22.90):
            raise ValueError(f"坐标超出深圳边界框: {place['name']}")
        source = place.get("source", {})
        if source.get("osm_name") != place["name"]:
            raise ValueError(f"地点名不是 OSM 精确匹配: {place['name']}")
        if not source.get("evidence"):
            raise ValueError(f"缺少小红书证据: {place['name']}")
    return dataset


def merge_external_refs(
    existing: dict[str, Any],
    dataset_name: str,
    place: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    old_dataset = merged.get("dataset")
    datasets = set(merged.get("datasets", []))
    if old_dataset:
        datasets.add(str(old_dataset))
    datasets.add(dataset_name)

    old_evidence = merged.get("xiaohongshu_evidence", [])
    evidence_by_key = {
        (item.get("note_id"), item.get("evidence_scope")): item
        for item in old_evidence
        if isinstance(item, dict)
    }
    for item in place["source"]["evidence"]:
        evidence_by_key[(item.get("note_id"), item.get("evidence_scope"))] = item

    if not old_dataset:
        merged["dataset"] = dataset_name
        merged["dataset_key"] = place["dataset_key"]
    merged.update(
        {
            "datasets": sorted(datasets),
            "latest_dataset": dataset_name,
            "osm_type": place["source"]["osm_type"],
            "osm_id": place["source"]["osm_id"],
            "osm_name": place["source"]["osm_name"],
            "coordinate_source": place["source"]["coordinate_source"],
            "xiaohongshu_evidence": list(evidence_by_key.values()),
        }
    )
    return merged


async def import_dataset(path: Path) -> tuple[int, int, int]:
    dataset = load_dataset(path)
    dataset_name = dataset["dataset"]
    settings = get_settings()
    dsn = settings.postgres_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(dsn)
    inserted = 0
    updated = 0
    try:
        async with connection.transaction():
            for place in dataset["places"]:
                source = place["source"]
                existing = await connection.fetchrow(
                    """
                    SELECT id, external_refs
                    FROM places
                    WHERE external_refs->>'osm_type' = $1
                      AND external_refs->>'osm_id' = $2
                    ORDER BY created_at
                    LIMIT 1
                    """,
                    source["osm_type"],
                    str(source["osm_id"]),
                )
                raw_refs = existing["external_refs"] if existing else {}
                existing_refs = (
                    json.loads(raw_refs) if isinstance(raw_refs, str) else dict(raw_refs)
                )
                external_refs = merge_external_refs(
                    existing_refs,
                    dataset_name,
                    place,
                )
                values = (
                    place["name"],
                    place["description"],
                    place["address"],
                    place["categories"],
                    place["tags"],
                    place["location"]["longitude"],
                    place["location"]["latitude"],
                    place["city"],
                    place["district"],
                    json.dumps(place["images"], ensure_ascii=False),
                    json.dumps(external_refs, ensure_ascii=False),
                )
                if existing:
                    await connection.execute(
                        """
                        UPDATE places SET
                            name = $2,
                            description = $3,
                            address = $4,
                            categories = $5,
                            tags = $6,
                            location = ST_SetSRID(ST_MakePoint($7, $8), 4326)::geography,
                            city = $9,
                            district = $10,
                            images = $11::jsonb,
                            source_type = 'platform',
                            external_refs = $12::jsonb,
                            moderation_status = 'published',
                            quality_score = GREATEST(quality_score, 0.90),
                            updated_at = now()
                        WHERE id = $1
                        """,
                        existing["id"],
                        *values,
                    )
                    updated += 1
                else:
                    await connection.execute(
                        """
                        INSERT INTO places(
                            id, name, description, address, categories, tags, location,
                            city, district, images, source_type, external_refs,
                            moderation_status, quality_score
                        ) VALUES(
                            $1, $2, $3, $4, $5, $6,
                            ST_SetSRID(ST_MakePoint($7, $8), 4326)::geography,
                            $9, $10, $11::jsonb, 'platform', $12::jsonb,
                            'published', 0.90
                        )
                        """,
                        uuid4(),
                        *values,
                    )
                    inserted += 1

            count = await connection.fetchval(
                """
                SELECT count(*)
                FROM places
                WHERE external_refs->'datasets' @> jsonb_build_array($1::text)
                   OR external_refs->>'dataset' = $1
                """,
                dataset_name,
            )
            if count != len(dataset["places"]):
                raise RuntimeError(
                    f"导入后数据集数量异常: expected={len(dataset['places'])}, actual={count}"
                )
    finally:
        await connection.close()
    return inserted, updated, count


async def async_main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    inserted, updated, count = await import_dataset(args.dataset)
    print(f"导入完成: inserted={inserted}, updated={updated}, total={count}")


if __name__ == "__main__":
    asyncio.run(async_main())
