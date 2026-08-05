"""Resolve the curated Xiaohongshu Nanshan list against an Overpass snapshot."""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPECS = ROOT / "data" / "nanshan_xhs_place_specs.json"
DEFAULT_OUTPUT = ROOT / "data" / "nanshan_xhs_places.json"


def _normalized_name(value: str) -> str:
    return "".join(
        character for character in value.strip() if unicodedata.category(character) != "Cf"
    )


def _element_coordinates(element: dict[str, Any]) -> tuple[float, float]:
    center = element.get("center", {})
    return float(element.get("lon", center.get("lon"))), float(
        element.get("lat", center.get("lat"))
    )


def _element_priority(element: dict[str, Any]) -> tuple[int, int]:
    priority = {"relation": 0, "way": 1, "node": 2}
    return priority.get(element["type"], 3), int(element["id"])


def build_dataset(specs_path: Path, overpass_path: Path) -> dict[str, Any]:
    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    overpass = json.loads(overpass_path.read_text(encoding="utf-8"))
    sources = specs["sources"]

    by_name: dict[str, list[dict[str, Any]]] = {}
    for element in overpass["elements"]:
        name = element.get("tags", {}).get("name")
        if not name:
            continue
        by_name.setdefault(_normalized_name(name), []).append(element)

    places: list[dict[str, Any]] = []
    missing: list[str] = []
    for spec in specs["places"]:
        candidates = by_name.get(_normalized_name(spec["osm_name"]), [])
        if not candidates:
            missing.append(spec["osm_name"])
            continue
        element = sorted(candidates, key=_element_priority)[0]
        longitude, latitude = _element_coordinates(element)
        if not (113.69 <= longitude <= 114.03 and 22.25 <= latitude <= 22.66):
            raise ValueError(f"坐标超出南山区边界框: {spec['osm_name']}")

        source = sources[spec["source"]]
        note_id = source["note_id"]
        name = spec.get("name", spec["osm_name"])
        places.append(
            {
                "dataset_key": f"osm:{element['type']}:{element['id']}",
                "name": name,
                "description": (
                    f"小红书南山地点清单收录的{spec['category']}，"
                    "坐标已使用 OpenStreetMap 南山区数据核验。"
                ),
                "address": None,
                "location": {"longitude": longitude, "latitude": latitude},
                "categories": [spec["category"]],
                "tags": spec["tags"],
                "city": "深圳",
                "district": "南山区",
                "images": [],
                "source": {
                    "xiaohongshu_note_id": note_id,
                    "xiaohongshu_note_title": source["title"],
                    "xiaohongshu_url": f"https://www.xiaohongshu.com/explore/{note_id}",
                    "coordinate_source": "OpenStreetMap",
                    "osm_type": element["type"],
                    "osm_id": element["id"],
                    "osm_name": element.get("tags", {}).get("name"),
                },
            }
        )

    if missing:
        raise ValueError(f"Overpass 快照中缺少地点: {', '.join(missing)}")
    if len(places) != 100:
        raise ValueError(f"数据集必须恰好包含 100 个地点，当前为 {len(places)}")
    if len({place["dataset_key"] for place in places}) != len(places):
        raise ValueError("OSM 元素重复")
    if len({place["name"] for place in places}) != len(places):
        raise ValueError("地点名称重复")

    return {
        "dataset": specs["dataset"],
        "generated_from": {
            "place_source": "Xiaohongshu public note pages",
            "coordinate_source": "OpenStreetMap Overpass",
            "coordinate_licence": "ODbL 1.0",
            "nanshan_osm_relation": 5664195,
        },
        "places": places,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--specs", type=Path, default=DEFAULT_SPECS)
    parser.add_argument("--overpass", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    dataset = build_dataset(args.specs, args.overpass)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已生成 {len(dataset['places'])} 个地点: {args.output}")


if __name__ == "__main__":
    main()
