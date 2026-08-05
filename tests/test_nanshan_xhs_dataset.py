from pathlib import Path

from scripts.import_nanshan_xhs_places import load_dataset


def test_nanshan_xhs_dataset_has_100_verified_public_places() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "nanshan_xhs_places.json"
    dataset = load_dataset(path)

    assert dataset["dataset"] == "xiaohongshu:nanshan:2026-08-05"
    assert len(dataset["places"]) == 100
    assert all(place["source"]["xiaohongshu_note_id"] for place in dataset["places"])
    assert all(place["source"]["osm_id"] for place in dataset["places"])
