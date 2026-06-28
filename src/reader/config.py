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
class ContentCleanRules:
    strip_leading_lines_matching: tuple[str, ...] = ()
    strip_prefix_literals: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not self.strip_leading_lines_matching and not self.strip_prefix_literals


@dataclass(frozen=True)
class ListingSourceProfile:
    fetcher: str = "requests"
    listing_fetcher: str = "requests"
    playwright_wait_selector: str | None = None
    playwright_article_wait_selector: str | None = None
    api_tag: str | None = None
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
    content_root_selector: str | None = None
    paragraph_selector: str = "article p, main p, p"
    max_links: int = 25
    content_clean: ContentCleanRules = ContentCleanRules()


@dataclass(frozen=True)
class AppConfig:
    database: Path
    sources: list[SourceConfig]
    categories: list[str]
    article_types: tuple[str, ...] = ()
    article_domains: tuple[str, ...] = ()
    ignored_urls: tuple[str, ...] = ()
    ignored_url_substrings: tuple[str, ...] = ()
    auto_skip_failure_threshold: int = 3


def _load_string_list(raw: dict, key: str) -> tuple[str, ...]:
    values = raw.get(key)
    if not values:
        return ()
    if not isinstance(values, list):
        raise ValueError(f"Config file '{key}' must be a list when present")
    return tuple(str(value) for value in values)


def load_categories(path: str | Path) -> list[str]:
    """Return the category list from the main config file."""
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if "categories" not in raw:
        raise ValueError(
            f"Config file must include a 'categories' list: {config_path}"
        )
    categories = raw["categories"]
    if not isinstance(categories, list) or not categories:
        raise ValueError(
            f"Config file 'categories' must be a non-empty list: {config_path}"
        )
    return [str(category) for category in categories]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    source_entries = raw.get("sources") or raw.get("feeds") or []
    categories = load_categories(config_path)
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
    return AppConfig(
        database=Path(raw.get("database", "data/reader.db")),
        sources=sources,
        categories=categories,
        article_types=_load_string_list(raw, "article_types"),
        article_domains=_load_string_list(raw, "article_domains"),
        ignored_urls=tuple(str(value) for value in raw.get("ignored_urls", [])),
        ignored_url_substrings=tuple(str(value) for value in raw.get("ignored_url_substrings", [])),
        auto_skip_failure_threshold=int(raw.get("auto_skip_failure_threshold", 3)),
    )


def load_listing_profile(path: str | Path | None) -> ListingSourceProfile:
    if path is None:
        return ListingSourceProfile()

    profile_path = Path(path)
    raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    fetcher = str(raw.get("fetcher", "requests"))
    return ListingSourceProfile(
        fetcher=fetcher,
        listing_fetcher=str(raw.get("listing_fetcher", fetcher)),
        playwright_wait_selector=(
            str(raw["playwright_wait_selector"]) if raw.get("playwright_wait_selector") else None
        ),
        playwright_article_wait_selector=(
            str(raw["playwright_article_wait_selector"])
            if raw.get("playwright_article_wait_selector")
            else None
        ),
        api_tag=(str(raw["api_tag"]) if raw.get("api_tag") else None),
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
        content_root_selector=(
            str(raw["content_root_selector"]) if raw.get("content_root_selector") else None
        ),
        paragraph_selector=str(raw.get("paragraph_selector", "article p, main p, p")),
        max_links=int(raw.get("max_links", 25)),
        content_clean=load_content_clean_rules(raw),
    )


def load_content_clean_rules(raw: dict | None) -> ContentCleanRules:
    if not raw:
        return ContentCleanRules()

    block = raw.get("content_clean", raw)
    if not isinstance(block, dict):
        return ContentCleanRules()

    return ContentCleanRules(
        strip_leading_lines_matching=tuple(
            str(value) for value in block.get("strip_leading_lines_matching", [])
        ),
        strip_prefix_literals=tuple(str(value) for value in block.get("strip_prefix_literals", [])),
    )


def _resolve_optional_path(base_path: Path, value: object | None) -> Path | None:
    if value in (None, ""):
        return None

    candidate = Path(str(value))
    if candidate.is_absolute():
        return candidate
    return (base_path.parent / candidate).resolve()