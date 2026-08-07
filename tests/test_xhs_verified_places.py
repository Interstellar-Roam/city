import json
from pathlib import Path

from scripts.import_xhs_verified_places import load_dataset, merge_external_refs
from scripts.verify_xhs_places_osm import select_match

ROOT = Path(__file__).resolve().parents[1]


def test_literal_mention_datasets_only_keep_source_substrings() -> None:
    for filename in (
        "shenzhen_xhs_title_mentions.json",
        "shenzhen_xhs_body_mentions.json",
    ):
        dataset = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
        for item in dataset["results"]:
            for name in item["literal_place_names"]:
                assert name in item["title"] or filename.endswith("body_mentions.json")


def test_verified_dataset_contract() -> None:
    dataset = load_dataset(ROOT / "data" / "shenzhen_xhs_verified_places.json")
    places = dataset["places"]
    summary = dataset["summary"]

    assert summary["verified_places"] == len(places)
    assert summary["pending_candidates"] == len(dataset["pending"])
    assert summary["candidate_names"] == len(places) + len(dataset["pending"])
    assert all(place["source"]["osm_name"] == place["name"] for place in places)
    assert all(place["source"]["evidence"] for place in places)
    assert all(
        place["categories"] == ["公园"]
        for place in places
        if place["name"].endswith("公园")
    )


def test_park_name_does_not_promote_same_named_station() -> None:
    result = {
        "name": "测试公园",
        "display_name": "测试公园, 福田区, 深圳市, 中国",
        "address": {"city": "深圳市", "city_district": "福田区"},
        "osm_type": "node",
        "osm_id": 1,
        "category": "railway",
        "type": "station",
        "lon": "114.05",
        "lat": "22.54",
    }
    selected, reason, _ = select_match(
        "测试公园",
        [result],
        [{"note_title": "周末去测试公园散步"}],
    )

    assert selected is None
    assert reason == "osm_semantic_type_mismatch"


def test_external_refs_merge_reuses_osm_identity() -> None:
    place = {
        "dataset_key": "osm:way:1",
        "source": {
            "osm_type": "way",
            "osm_id": 1,
            "osm_name": "测试地点",
            "coordinate_source": "OpenStreetMap Nominatim",
            "evidence": [
                {
                    "note_id": "note-1",
                    "evidence_scope": "title_literal",
                    "note_title": "测试地点游玩",
                }
            ],
        },
    }
    merged = merge_external_refs(
        {"dataset": "old", "dataset_key": "osm:way:1"},
        "new",
        place,
    )

    assert merged["dataset"] == "old"
    assert merged["datasets"] == ["new", "old"]
    assert merged["xiaohongshu_evidence"][0]["note_id"] == "note-1"
