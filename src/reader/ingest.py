from __future__ import annotations

import logging
from pathlib import Path

from reader.config import load_config
from reader.scrapers import SOURCE_HANDLERS
from reader.storage import connect, initialize, upsert_article

logger = logging.getLogger(__name__)


def ingest(config_path: str | Path, raw_html_dir: str | Path = "data") -> int:
    config = load_config(config_path)
    initialize(config.database)
    new_items = 0
    skipped_items = 0
    with connect(config.database) as connection:
        for source in config.sources:
            if not source.enabled:
                continue

            handler = SOURCE_HANDLERS.get(source.kind)
            if handler is None:
                logger.warning("Unknown source kind '%s' for source '%s', skipping", source.kind, source.name)
                continue
            try:
                articles = handler(source, connection, raw_html_dir=raw_html_dir)
            except Exception as exc:
                logger.error("Failed to ingest source '%s': %s", source.name, exc)
                skipped_items += 1
                continue
            skipped_items += len([a for a in articles if a is None])
            articles = [a for a in articles if a is not None]

            for article in articles:
                if article is not None and upsert_article(connection, article):
                    new_items += 1
        connection.commit()

    if skipped_items:
        logger.warning("Ingestion complete: %d new items, %d skipped due to content quality", new_items, skipped_items)
    else:
        logger.info("Ingestion complete: %d new items", new_items)
    return new_items