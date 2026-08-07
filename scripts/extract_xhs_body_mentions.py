"""Extract literal place mentions from selected Xiaohongshu note bodies.

The source bodies are intentionally kept outside the repository.  This script
only emits compact evidence records containing literal place-name spans and
source identifiers.  Every proposed span is revalidated against the source
text before it can reach the output file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = Path("/private/tmp/shenzhen_xhs_selected_note_bodies.json")
DEFAULT_OUTPUT = ROOT / "data" / "shenzhen_xhs_body_mentions.json"

GENERIC_NAMES = {
    "深圳",
    "深圳市",
    "宝安",
    "宝安区",
    "福田",
    "福田区",
    "公园",
    "商场",
    "景点",
    "海边",
    "绿道",
    "古城",
    "古村",
    "美术馆",
    "博物馆",
    "图书馆",
    "书城",
    "展馆",
    "创意园",
    "城中村",
}

SYSTEM_PROMPT = """Extract explicit recommended destination names from Chinese social-note text.

Return one JSON object with this exact shape:
{"items":[{"note_id":"...","place_names":["..."]}]}

Rules:
- Every place name must appear verbatim as a contiguous substring of title or body.
- Never infer, expand, correct, translate, or normalize a name.
- City/district/category words alone are not places.
- Include only destinations introduced as numbered/listed itinerary items or as
  the explicit recommendation target of the note.
- Exclude metro stations, address roads, nearby landmarks, descriptive context,
  hashtags, and businesses mentioned only in an advertisement or aside.
- Named parks, trails, reservoirs, mountains, malls, museums, villages, streets,
  restaurants, public buildings, and venues are valid when they are destinations.
- Prefer the most complete explicit spelling present in the text.
- Do not include descriptive phrases, hashtags, transit directions, or explanations.
"""

SAVE_TOOL = {
    "type": "function",
    "function": {
        "name": "save_body_mentions",
        "description": "Save literal place-name spans found in the supplied notes.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "note_id": {"type": "string"},
                            "place_names": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["note_id", "place_names"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().strip("*#-—｜|:：。,.，")


def parse_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("LLM response must be a JSON object")
    return result


def validated_names(note: dict[str, Any], values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    source = normalize(f"{note['title']}\n{note['body']}")
    accepted: list[str] = []
    for value in values:
        name = normalize(str(value))[:120]
        if (
            len(name) >= 2
            and name not in GENERIC_NAMES
            and name in source
            and name not in accepted
        ):
            accepted.append(name)
    return accepted


async def extract(input_path: Path, output_path: Path) -> None:
    notes = json.loads(input_path.read_text(encoding="utf-8"))
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is required")

    payload = [
        {"note_id": item["note_id"], "title": item["title"], "body": item["body"]}
        for item in notes
    ]
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=90,
        max_retries=1,
    )
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        tools=[SAVE_TOOL],
        tool_choice="auto",
        temperature=0,
    )
    calls = response.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("LLM did not call save_body_mentions")
    parsed = parse_json_object(calls[0].function.arguments or "{}")
    extracted = {
        str(item.get("note_id")): item.get("place_names", [])
        for item in parsed.get("items", [])
        if isinstance(item, dict)
    }

    results = [
        {
            "note_id": note["note_id"],
            "title": note["title"],
            "district_hint": note["district_hint"],
            "canonical_url": f"https://www.xiaohongshu.com/explore/{note['note_id']}",
            "literal_place_names": validated_names(
                note,
                extracted.get(note["note_id"], []),
            ),
        }
        for note in notes
    ]
    unique_names = sorted({name for item in results for name in item["literal_place_names"]})
    output = {
        "dataset": "xiaohongshu:shenzhen:body-mentions:2026-08-07",
        "generated_at": date.today().isoformat(),
        "model": settings.llm_model,
        "evidence_policy": "literal title/body substring only; source bodies are not retained",
        "summary": {
            "selected_notes": len(notes),
            "notes_with_mentions": sum(bool(item["literal_place_names"]) for item in results),
            "unique_literal_names": len(unique_names),
        },
        "unique_literal_names": unique_names,
        "results": results,
    }
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    asyncio.run(extract(args.input, args.output))


if __name__ == "__main__":
    main()
