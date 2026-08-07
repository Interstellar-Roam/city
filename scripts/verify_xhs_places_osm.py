"""Cross-check literal Xiaohongshu place mentions against Shenzhen OSM data.

The verifier uses Nominatim's indexed OSM search at the public-policy limit of
one request per second.  It promotes only exact names whose returned address is
inside a Shenzhen district; missing and ambiguous matches remain pending.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TITLE_MENTIONS = ROOT / "data" / "shenzhen_xhs_title_mentions.json"
DEFAULT_BODY_MENTIONS = ROOT / "data" / "shenzhen_xhs_body_mentions.json"
DEFAULT_OUTPUT = ROOT / "data" / "shenzhen_xhs_verified_places.json"
DEFAULT_CACHE = Path("/private/tmp/shenzhen_xhs_nominatim_cache.json")

NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
SHENZHEN_DISTRICTS = (
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
)
OSM_TYPE_PRIORITY = {"relation": 0, "way": 1, "node": 2}


def normalize_name(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", value).strip()
        if unicodedata.category(character) != "Cf"
    )


def haversine_metres(first: tuple[float, float], second: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(value))


def load_evidence(title_path: Path, body_path: Path) -> dict[str, list[dict[str, str]]]:
    evidence: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path, scope in (
        (title_path, "title_literal"),
        (body_path, "body_recommended_item"),
    ):
        dataset = json.loads(path.read_text(encoding="utf-8"))
        for item in dataset["results"]:
            for raw_name in item["literal_place_names"]:
                name = normalize_name(raw_name)
                record = {
                    "note_id": item["note_id"],
                    "note_title": item["title"],
                    "canonical_url": item["canonical_url"],
                    "evidence_scope": scope,
                    "district_hint": item["district_hint"],
                }
                if record not in evidence[name]:
                    evidence[name].append(record)
    return dict(evidence)


def result_name(result: dict[str, Any]) -> str:
    return normalize_name(str(result.get("name", "")))


def result_district(result: dict[str, Any]) -> str | None:
    address = result.get("address", {})
    values = list(address.values()) + [result.get("display_name", "")]
    for district in SHENZHEN_DISTRICTS:
        if any(district in str(value) for value in values):
            return district
    return None


def result_coordinates(result: dict[str, Any]) -> tuple[float, float]:
    return float(result["lon"]), float(result["lat"])


def category_for(result: dict[str, Any], name: str) -> str:
    category = result.get("category")
    kind = result.get("type")
    if name.endswith(("创意园", "文化街区")):
        return "文化街区"
    if name.endswith(("古城", "古墟", "村")):
        return "街区"
    if category == "tourism" and kind in {"museum", "gallery"}:
        return "展馆"
    if category == "tourism":
        return "景点"
    if category == "leisure" and kind in {"park", "nature_reserve", "garden"}:
        return "公园"
    if category == "amenity" and kind == "library":
        return "图书馆"
    if category == "amenity" and kind in {"arts_centre", "theatre", "community_centre"}:
        return "文化场馆"
    if category == "amenity" and kind == "place_of_worship":
        return "寺庙"
    if category == "amenity" and kind in {"restaurant", "food_court", "cafe"}:
        return "餐饮"
    if category == "shop" and kind in {"mall", "department_store"}:
        return "商场"
    if category == "landuse" and kind == "retail":
        return "商场"
    if category == "landuse" and kind == "religious":
        return "寺庙"
    if category == "landuse" and kind == "commercial":
        return "商业区"
    if category == "natural":
        return "自然"
    if category in {"water", "waterway"} or kind == "reservoir":
        return "水域"
    if category == "highway" and kind in {"footway", "path", "pedestrian"}:
        return "徒步路线"
    if category in {"highway", "place"}:
        return "街区"
    if category in {"railway", "public_transport"}:
        return "交通"
    return "地点"


def expected_result(result: dict[str, Any], name: str) -> bool | None:
    """Prefer the entity type implied by an unambiguous Chinese suffix."""
    category = result.get("category")
    kind = result.get("type")
    if name.endswith("公园"):
        return category == "leisure" and kind in {"park", "nature_reserve", "garden"}
    if name.endswith(("美术馆", "博物馆", "艺术馆")):
        return category in {"tourism", "amenity"} and kind in {
            "museum",
            "gallery",
            "arts_centre",
        }
    if name.endswith("山"):
        return category == "natural" and kind == "peak"
    if name.endswith(("站", "机场")):
        return category in {"railway", "aeroway", "public_transport"} or (
            category == "building" and kind in {"train_station", "transportation"}
        )
    return None


def is_transit_result(result: dict[str, Any]) -> bool:
    return result.get("category") in {"railway", "aeroway", "public_transport"} or (
        result.get("category") == "highway" and result.get("type") == "bus_stop"
    )


def evidence_allows_transit(name: str, evidence: list[dict[str, str]]) -> bool:
    if name.endswith(("站", "机场")):
        return True
    return any(
        f"{name}站" in item["note_title"] or f"{name}地铁" in item["note_title"]
        for item in evidence
    )


def select_match(
    name: str,
    raw_results: list[dict[str, Any]],
    evidence: list[dict[str, str]],
) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    candidates = [
        result
        for result in raw_results
        if result_name(result) == name
        and "深圳市" in result.get("display_name", "")
        and result_district(result) is not None
    ]
    expected = [result for result in candidates if expected_result(result, name) is True]
    has_suffix_expectation = any(expected_result(result, name) is not None for result in candidates)
    if has_suffix_expectation:
        if not expected:
            return None, "osm_semantic_type_mismatch", candidates
        candidates = expected
    else:
        non_transit = [result for result in candidates if not is_transit_result(result)]
        if non_transit:
            candidates = non_transit
        elif candidates and not evidence_allows_transit(name, evidence):
            return None, "osm_semantic_type_mismatch", candidates
    unique = {
        (result.get("osm_type"), int(result["osm_id"])): result
        for result in candidates
    }
    candidates = list(unique.values())
    if not candidates:
        return None, "no_exact_osm_match", []
    if len(candidates) == 1:
        return candidates[0], None, candidates

    districts = {result_district(result) for result in candidates}
    points = [result_coordinates(result) for result in candidates]
    max_distance = max(
        haversine_metres(first, second)
        for index, first in enumerate(points)
        for second in points[index + 1 :]
    )
    if len(districts) == 1 and max_distance <= 500:
        selected = min(
            candidates,
            key=lambda result: (
                OSM_TYPE_PRIORITY.get(str(result.get("osm_type")), 3),
                int(result["osm_id"]),
            ),
        )
        return selected, None, candidates
    return None, "ambiguous_exact_osm_matches", candidates


async def fetch_name(client: httpx.AsyncClient, name: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(
                NOMINATIM_ENDPOINT,
                params={
                    "q": f"{name},深圳市,中国",
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "namedetails": 1,
                    "extratags": 1,
                    "limit": 10,
                },
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Nominatim query failed for {name}: {last_error}")


async def resolve_names(
    names: list[str],
    cache_path: Path,
) -> dict[str, list[dict[str, Any]]]:
    cache: dict[str, list[dict[str, Any]]] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30),
        headers={"User-Agent": "city-route-recommender/1.0 (OSM verification)"},
    ) as client:
        for index, name in enumerate(names, start=1):
            if name not in cache:
                cache[name] = await fetch_name(client, name)
                cache_path.write_text(
                    json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                await asyncio.sleep(1.05)
            if index % 10 == 0 or index == len(names):
                print(f"resolved {index}/{len(names)}", flush=True)
    return cache


async def verify(
    title_path: Path,
    body_path: Path,
    output_path: Path,
    cache_path: Path,
) -> dict[str, Any]:
    evidence = load_evidence(title_path, body_path)
    names = sorted(evidence)
    resolved = await resolve_names(names, cache_path)

    places: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for name in names:
        result, reason, candidates = select_match(
            name,
            resolved.get(name, []),
            evidence[name],
        )
        if result is None:
            pending.append(
                {
                    "name": name,
                    "reason": reason,
                    "evidence": evidence[name],
                    "osm_candidates": [
                        {
                            "osm_type": item.get("osm_type"),
                            "osm_id": item.get("osm_id"),
                            "display_name": item.get("display_name"),
                            "location": {
                                "longitude": float(item["lon"]),
                                "latitude": float(item["lat"]),
                            },
                        }
                        for item in candidates
                    ],
                }
            )
            continue

        longitude, latitude = result_coordinates(result)
        district = result_district(result)
        assert district is not None
        category = category_for(result, name)
        places.append(
            {
                "dataset_key": f"osm:{result['osm_type']}:{result['osm_id']}",
                "name": name,
                "description": (
                    f"小红书公开笔记明确提及的{category}，"
                    "名称、坐标及深圳区属已通过 OpenStreetMap 数据核验。"
                ),
                "address": result.get("display_name"),
                "location": {"longitude": longitude, "latitude": latitude},
                "categories": [category],
                "tags": ["小红书线索", "OSM核验", district],
                "city": "深圳",
                "district": district,
                "images": [],
                "source": {
                    "evidence": evidence[name],
                    "coordinate_source": "OpenStreetMap Nominatim",
                    "osm_type": result["osm_type"],
                    "osm_id": int(result["osm_id"]),
                    "osm_name": result_name(result),
                    "osm_category": result.get("category"),
                    "osm_type_name": result.get("type"),
                },
            }
        )

    places.sort(key=lambda item: (item["district"], item["name"]))
    pending.sort(key=lambda item: item["name"])
    output = {
        "dataset": "xiaohongshu:shenzhen:osm-verified:2026-08-07",
        "generated_at": date.today().isoformat(),
        "promotion_policy": (
            "literal Xiaohongshu title/recommended-item mention + exact OSM name "
            "inside one Shenzhen district; ambiguous or missing matches stay pending"
        ),
        "generated_from": {
            "title_mentions": title_path.name,
            "body_mentions": body_path.name,
            "coordinate_source": "OpenStreetMap Nominatim",
            "coordinate_licence": "ODbL 1.0",
        },
        "summary": {
            "candidate_names": len(names),
            "verified_places": len(places),
            "pending_candidates": len(pending),
            "verified_by_district": {
                district: sum(place["district"] == district for place in places)
                for district in SHENZHEN_DISTRICTS
                if any(place["district"] == district for place in places)
            },
        },
        "places": places,
        "pending": pending,
    }
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title-mentions", type=Path, default=DEFAULT_TITLE_MENTIONS)
    parser.add_argument("--body-mentions", type=Path, default=DEFAULT_BODY_MENTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    output = asyncio.run(
        verify(args.title_mentions, args.body_mentions, args.output, args.cache)
    )
    print(json.dumps(output["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
