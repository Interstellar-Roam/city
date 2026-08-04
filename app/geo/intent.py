"""Structured intent extraction for geographic recommendations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from loguru import logger
from openai import AsyncOpenAI

from app.config import get_settings


@dataclass(slots=True)
class RecommendationIntent:
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    city: str | None = None
    max_distance_m: float | None = None
    max_duration_s: int | None = None


CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "咖啡": ("咖啡", "手冲"),
    "公园": ("公园", "绿地", "花园"),
    "建筑": ("建筑", "老洋房", "历史建筑"),
    "文化": ("文化", "博物馆", "美术馆", "展览"),
    "餐饮": ("美食", "餐厅", "小吃", "吃饭"),
    "景点": ("景点", "地标", "风景"),
    "购物": ("购物", "商场", "市集"),
}

TAG_TERMS: dict[str, tuple[str, ...]] = {
    "安静": ("安静", "清静", "人少"),
    "树荫": ("树荫", "林荫", "有树"),
    "拍照": ("拍照", "摄影", "出片"),
    "夜景": ("夜景", "晚上"),
    "历史": ("历史", "古迹"),
    "亲子": ("亲子", "带孩子"),
    "无障碍": ("无障碍", "轮椅", "少台阶"),
}


class IntentParser:
    """Heuristic parser with an optional OpenAI-compatible structured LLM pass."""

    def __init__(self):
        self.settings = get_settings()

    async def parse(self, query: str) -> RecommendationIntent:
        heuristic = self.parse_heuristic(query)
        if not self.settings.recommendation_use_llm or not self.settings.llm_api_key:
            return heuristic

        try:
            client = AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
            )
            response = await client.chat.completions.create(
                model=self.settings.llm_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract CityWalk constraints as JSON with keys categories, tags, city, "
                            "max_distance_m and max_duration_s. Do not invent places."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0,
            )
            payload = json.loads(response.choices[0].message.content or "{}")
            return RecommendationIntent(
                categories=_merge_terms(heuristic.categories, payload.get("categories", [])),
                tags=_merge_terms(heuristic.tags, payload.get("tags", [])),
                city=payload.get("city") or heuristic.city,
                max_distance_m=_positive_number(payload.get("max_distance_m")) or heuristic.max_distance_m,
                max_duration_s=int(_positive_number(payload.get("max_duration_s")) or 0)
                or heuristic.max_duration_s,
            )
        except Exception as exc:
            logger.warning(f"推荐意图 LLM 解析失败，使用本地解析结果: {exc}")
            return heuristic

    @staticmethod
    def parse_heuristic(query: str) -> RecommendationIntent:
        categories = [
            category
            for category, terms in CATEGORY_TERMS.items()
            if any(term in query for term in terms)
        ]
        tags = [
            tag
            for tag, terms in TAG_TERMS.items()
            if any(term in query for term in terms)
        ]

        max_distance_m = None
        distance_match = re.search(r"(\d+(?:\.\d+)?)\s*(公里|千米|km|KM|米|m)", query)
        if distance_match:
            value = float(distance_match.group(1))
            max_distance_m = value * 1000 if distance_match.group(2) in {"公里", "千米", "km", "KM"} else value

        max_duration_s = None
        duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(小时|分钟|min)", query)
        if duration_match:
            value = float(duration_match.group(1))
            max_duration_s = round(value * (3600 if duration_match.group(2) == "小时" else 60))

        return RecommendationIntent(
            categories=categories,
            tags=tags,
            max_distance_m=max_distance_m,
            max_duration_s=max_duration_s,
        )


def _merge_terms(first: list[str], second: list[str]) -> list[str]:
    return list(dict.fromkeys([*first, *(str(value).strip() for value in second if str(value).strip())]))


def _positive_number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
