from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceConfig:
    name: str
    kind: str
    url: str
    config_path: Path | None = None
    scraper: str = "rss"
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ListingSourceProfile:
    fetcher: str = "requests"
    item_selector: str = "a[href]"
    link_selector: str = "a[href]"
    allowed_url_prefixes: tuple[str, ...] = ()
    excluded_url_substrings: tuple[str, ...] = ()
    title_selector: str | None = None
    title_selectors: tuple[str, ...] = ()
    date_selectors: tuple[str, ...] = ()
    date_formats: tuple[str, ...] = ()
    category_selectors: tuple[str, ...] = ()
    content_selectors: tuple[str, ...] = ()
    paragraph_selector: str = "article p, main p, p"
    max_links: int = 25


@dataclass(frozen=True)
class AppConfig:
    database: Path
    sources: list[SourceConfig]
    categories: list[str]


DEFAULT_CATEGORIES = [
    "Technical Research",
    "AI News",
    "Governance and Policy",
    "Safety and Alignment",
    "Product Updates",
    "Other",
]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    source_entries = raw.get("sources") or raw.get("feeds") or []
    categories = [str(category) for category in raw.get("categories", DEFAULT_CATEGORIES)]
    sources = [
        SourceConfig(
            name=str(feed["name"]),
            kind=str(feed.get("kind") or feed.get("type", "rss")),
            url=str(feed["url"]),
            config_path=_resolve_optional_path(config_path, feed.get("config") or feed.get("config_path")),
            scraper=str(feed.get("scraper", "rss")),
            enabled=bool(feed.get("enabled", True)),
            settings=dict(feed.get("settings") or {}),
        )
        for feed in source_entries
    ]
    return AppConfig(database=Path(raw.get("database", "data/reader.db")), sources=sources, categories=categories)


def load_listing_profile(path: str | Path | None) -> ListingSourceProfile:
    if path is None:
        return ListingSourceProfile()

    profile_path = Path(path)
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    return ListingSourceProfile(
        fetcher=str(raw.get("fetcher", "requests")),
        item_selector=str(raw.get("item_selector", raw.get("link_selector", "a[href]"))),
        link_selector=str(raw.get("link_selector", "a[href]")),
        allowed_url_prefixes=tuple(str(value) for value in raw.get("allowed_url_prefixes", [])),
        excluded_url_substrings=tuple(str(value) for value in raw.get("excluded_url_substrings", [])),
        title_selector=(str(raw["title_selector"]) if raw.get("title_selector") else None),
        title_selectors=tuple(str(value) for value in raw.get("title_selectors", [])),
        date_selectors=tuple(str(value) for value in raw.get("date_selectors", [])),
        date_formats=tuple(str(value) for value in raw.get("date_formats", [])),
        category_selectors=tuple(str(value) for value in raw.get("category_selectors", [])),
        content_selectors=tuple(str(value) for value in raw.get("content_selectors", [])),
        paragraph_selector=str(raw.get("paragraph_selector", "article p, main p, p")),
        max_links=int(raw.get("max_links", 25)),
    )


def _resolve_optional_path(base_path: Path, value: object | None) -> Path | None:
    if value in (None, ""):
        return None

    candidate = Path(str(value))
    if candidate.is_absolute():
        return candidate
    return (base_path.parent / candidate).resolve()