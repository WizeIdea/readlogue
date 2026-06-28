from __future__ import annotations

import json
from typing import Any

CURATION_VERSION = 1
EMPTY_CURATION_JSON = "{}"

SCORE_FIELDS = ("technical_depth", "business_relevance", "governance_relevance")
TAG_FIELDS = ("article_types", "article_domains")


def empty_curation() -> dict[str, Any]:
    return {}


def parse_curation_json(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return empty_curation()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return empty_curation()
    return parsed if isinstance(parsed, dict) else empty_curation()


def serialize_curation(value: dict[str, Any] | str | None) -> str:
    if isinstance(value, str):
        return value if value.strip() else EMPTY_CURATION_JSON
    if not value:
        return EMPTY_CURATION_JSON
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def normalize_curation(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return empty_curation()

    normalized: dict[str, Any] = {"v": CURATION_VERSION}
    for field in TAG_FIELDS:
        tags = raw.get(field)
        if isinstance(tags, list):
            cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
            if cleaned:
                normalized[field] = cleaned
    for field in SCORE_FIELDS:
        score = raw.get(field)
        if score is None or score == "":
            continue
        try:
            value = int(score)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 5:
            normalized[field] = value
    if len(normalized) == 1 and normalized.get("v") == CURATION_VERSION:
        return empty_curation()
    return normalized
