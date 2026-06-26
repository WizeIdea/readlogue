from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    type: str
    scraper: str


@dataclass(frozen=True)
class AppConfig:
    database: Path
    feeds: list[FeedSource]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    feeds = [
        FeedSource(
            name=str(feed["name"]),
            url=str(feed["url"]),
            type=str(feed.get("type", "rss")),
            scraper=str(feed.get("scraper", "rss")),
        )
        for feed in raw.get("feeds", [])
    ]
    return AppConfig(database=Path(raw.get("database", "data/reader.db")), feeds=feeds)