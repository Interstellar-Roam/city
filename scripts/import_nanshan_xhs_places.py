"""Idempotently import the curated Xiaohongshu Nanshan dataset into PostGIS."""

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
DEFAULT_DATASET = ROOT / "data" / "nanshan_xhs_places.json"


def load_dataset(path: Path) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    places = dataset.get("places", [])
    if len(places) != 100:
        raise ValueError(f"数据集必须恰好包含 100 个地点，当前为 {len(places)}")
    if len({place["dataset_key"] for place in places}) != len(places):
        raise ValueError("dataset_key 重复")
    if len({place["name"] for place in places}) != len(places):
        raise ValueError("地点名称重复")
    for place in places:
        if place["city"] != "深圳" or place["district"] != "南山区":
            raise ValueError(f"非南山区地点: {place['name']}")
        location = place["location"]
        if not (
            113.69 <= location["longitude"] <= 114.03 and 22.25 <= location["latitude"] <= 22.66
        ):
            raise ValueError(f"坐标超出南山区边界框: {place['name']}")
    return dataset


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
                external_refs = {
                    "dataset": dataset_name,
                    "dataset_key": place["dataset_key"],
                    **place["source"],
                }
                was_inserted = await connection.fetchval(
                    """
                    INSERT INTO places(
                        id, name, description, address, categories, tags, location,
                        city, district, images, source_type, external_refs,
                        moderation_status, quality_score
                    ) VALUES(
                        $1, $2, $3, $4, $5, $6,
                        ST_SetSRID(ST_MakePoint($7, $8), 4326)::geography,
                        $9, $10, $11::jsonb, 'platform', $12::jsonb,
                        'published', 0.85
                    )
                    ON CONFLICT ((external_refs->>'dataset'), (external_refs->>'dataset_key'))
                    WHERE external_refs ? 'dataset' AND external_refs ? 'dataset_key'
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        address = EXCLUDED.address,
                        categories = EXCLUDED.categories,
                        tags = EXCLUDED.tags,
                        location = EXCLUDED.location,
                        city = EXCLUDED.city,
                        district = EXCLUDED.district,
                        images = EXCLUDED.images,
                        source_type = 'platform',
                        external_refs = EXCLUDED.external_refs,
                        moderation_status = 'published',
                        quality_score = EXCLUDED.quality_score,
                        updated_at = now()
                    RETURNING (xmax = 0) AS inserted
                    """,
                    uuid4(),
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
                if was_inserted:
                    inserted += 1
                else:
                    updated += 1

            count = await connection.fetchval(
                "SELECT count(*) FROM places WHERE external_refs->>'dataset' = $1",
                dataset_name,
            )
            if count != 100:
                raise RuntimeError(f"导入后数据集数量异常: {count}")
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
