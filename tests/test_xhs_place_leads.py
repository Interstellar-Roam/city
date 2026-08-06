"""Contract checks for the unverified Xiaohongshu place-lead dataset."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def test_xhs_place_leads_have_expected_unique_allocation() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "shenzhen_xhs_place_leads_500.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))
    leads = dataset["leads"]

    assert dataset["status"] == "candidate_leads"
    assert len(leads) == 500
    assert len({lead["note_id"] for lead in leads}) == 500
    assert all(lead["title"].strip() for lead in leads)
    assert all(lead["verification_status"] == "unverified" for lead in leads)

    allocation = Counter(lead["district_hint"] for lead in leads)
    assert allocation == {
        "宝安区": 125,
        "福田区": 125,
        "深圳其他区域": 250,
    }
    assert allocation["宝安区"] + allocation["福田区"] == 250

    for lead in leads:
        expected_url = f"https://www.xiaohongshu.com/explore/{lead['note_id']}"
        assert lead["canonical_url"] == expected_url
        assert "xsec_token" not in lead["canonical_url"]
