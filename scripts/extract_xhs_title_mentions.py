"""Extract literal place-name mentions from Xiaohongshu lead titles.

The LLM may propose candidates, but this script only keeps names that occur
verbatim in the source title. The output remains an intermediate artifact and
must not be published as verified places before map matching succeeds.
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
DEFAULT_INPUT = ROOT / "data" / "shenzhen_xhs_place_leads_500.json"
DEFAULT_OUTPUT = ROOT / "data" / "shenzhen_xhs_title_mentions.json"

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
    "古村",
    "美术馆",
    "博物馆",
    "图书馆",
    "城中村",
}

SYSTEM_PROMPT = """You extract explicit place or venue names from Chinese social-note titles.

Return one JSON object with this exact shape:
{"items":[{"note_id":"...","place_names":["..."]}]}

Rules:
- A place name must be a proper name that appears verbatim as a contiguous substring of the title.
- Never infer an unnamed park, mountain, mall, restaurant, district, or attraction.
- District/city names alone are not places.
- Include a name only when the title presents it as a leisure/travel/food/culture
  destination to visit, explore, photograph, walk around, or seek recommendations for.
- Exclude names used only as context for rental/property, recruitment, lost-pet or
  adoption, commuting, school/work, construction, or unrelated personal stories.
- Named parks, trails, mountains, malls, museums, villages, streets, restaurants,
  and venues are valid when they are destination targets.
- Return [] when the title does not state a proper place name.
- Preserve the exact title spelling and do not add explanations.
"""

SAVE_MENTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "save_title_mentions",
        "description": "Save only literal place-name spans found in each title.",
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


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def _parse_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


async def _extract_batch(
    client: AsyncOpenAI,
    model: str,
    leads: list[dict[str, Any]],
    semaphore: asyncio.Semaphore,
) -> dict[str, list[str]]:
    payload = [{"note_id": lead["note_id"], "title": lead["title"]} for lead in leads]
    async with semaphore:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False),
                        },
                    ],
                    tools=[SAVE_MENTIONS_TOOL],
                    tool_choice="auto",
                    temperature=0,
                )
                tool_calls = response.choices[0].message.tool_calls or []
                if not tool_calls:
                    raise ValueError("LLM did not call save_title_mentions")
                parsed = _parse_json_object(tool_calls[0].function.arguments or "{}")
                return {
                    str(item.get("note_id")): item.get("place_names", [])
                    for item in parsed.get("items", [])
                    if isinstance(item, dict)
                }
            except Exception as exc:  # pragma: no cover - exercised by live runs
                last_error = exc
                if attempt < 1:
                    await asyncio.sleep(1 + attempt)
        raise RuntimeError(f"LLM batch extraction failed: {last_error}")


def _validated_names(title: str, values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_title = _normalize(title)
    accepted: list[str] = []
    for value in values:
        name = _normalize(str(value))[:100]
        if (
            len(name) >= 2
            and name not in GENERIC_NAMES
            and name in normalized_title
            and name not in accepted
        ):
            accepted.append(name)
    return accepted


async def extract_mentions(input_path: Path, output_path: Path, batch_size: int) -> None:
    dataset = json.loads(input_path.read_text(encoding="utf-8"))
    leads = dataset["leads"]
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is required")

    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=30,
        max_retries=0,
    )
    semaphore = asyncio.Semaphore(4)
    batches = [leads[index : index + batch_size] for index in range(0, len(leads), batch_size)]
    extracted_batches = await asyncio.gather(
        *(_extract_batch(client, settings.llm_model, batch, semaphore) for batch in batches),
        return_exceptions=True,
    )
    extracted: dict[str, list[str]] = {}
    failed_note_ids: list[str] = []
    for batch, batch_result in zip(batches, extracted_batches, strict=True):
        if not isinstance(batch_result, Exception):
            extracted.update(batch_result)
            continue
        for lead in batch:
            try:
                extracted.update(
                    await _extract_batch(
                        client,
                        settings.llm_model,
                        [lead],
                        semaphore,
                    )
                )
            except Exception:  # pragma: no cover - live provider failure
                failed_note_ids.append(lead["note_id"])

    results = [
        {
            "note_id": lead["note_id"],
            "title": lead["title"],
            "district_hint": lead["district_hint"],
            "canonical_url": lead["canonical_url"],
            "literal_place_names": _validated_names(
                lead["title"],
                extracted.get(lead["note_id"], []),
            ),
        }
        for lead in leads
    ]
    unique_names = sorted({name for result in results for name in result["literal_place_names"]})
    output = {
        "dataset": "xiaohongshu:shenzhen:title-mentions:2026-08-07",
        "generated_at": date.today().isoformat(),
        "model": settings.llm_model,
        "source_dataset": dataset["dataset"],
        "evidence_policy": (
            "literal title substring with destination intent; map verification still required"
        ),
        "summary": {
            "input_leads": len(leads),
            "leads_with_mentions": sum(bool(result["literal_place_names"]) for result in results),
            "unique_literal_names": len(unique_names),
            "failed_leads": len(failed_note_ids),
        },
        "failed_note_ids": failed_note_ids,
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
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(extract_mentions(args.input, args.output, args.batch_size))


if __name__ == "__main__":
    main()
