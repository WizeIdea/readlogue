from __future__ import annotations

import logging
from pathlib import Path

from reader.config import load_config
from reader.scrapers import SOURCE_HANDLERS
from reader.storage import IngestStats, connect, initialize, upsert_article

logger = logging.getLogger(__name__)


def ingest(config_path: str | Path, raw_html_dir: str | Path = "data") -> int:
    config = load_config(config_path)
    initialize(config.database)
    stats = IngestStats()
    with connect(config.database) as connection:
        for source in config.sources:
            if not source.enabled:
                continue

            handler = SOURCE_HANDLERS.get(source.kind)
            if handler is None:
                logger.warning("Unknown source kind '%s' for source '%s', skipping", source.kind, source.name)
                continue
            try:
                articles = handler(source, connection, raw_html_dir=raw_html_dir, stats=stats)
            except Exception as exc:
                logger.error("Failed to ingest source '%s': %s", source.name, exc)
                continue
            articles = [a for a in articles if a is not None]

            for article in articles:
                if upsert_article(connection, article):
                    stats.new_db_rows += 1
        connection.commit()

    logger.info(
        "Ingestion summary: skipped_existing=%d fetched=%d validation_failed=%d "
        "html_written=%d html_reused=%d new_db_rows=%d",
        stats.skipped_existing,
        stats.fetched,
        stats.validation_failed,
        stats.html_written,
        stats.html_reused,
        stats.new_db_rows,
    )
    return stats.new_db_rows
