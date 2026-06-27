from __future__ import annotations

import logging
from pathlib import Path

from reader.config import load_config
from reader.scrapers import SOURCE_HANDLERS, build_url_ignore_checker
from reader.storage import IngestStats, connect, initialize, known_failed_fingerprints, upsert_article
from reader.supabase_sync import hydrate_sqlite_from_supabase, is_supabase_configured, sync_sqlite_to_supabase

logger = logging.getLogger(__name__)


def ingest(config_path: str | Path, raw_html_dir: str | Path = "data") -> int:
    config = load_config(config_path)
    initialize(config.database)
    stats = IngestStats()
    with connect(config.database) as connection:
        if is_supabase_configured():
            hydrate_sqlite_from_supabase(connection)
            connection.commit()

        failed_fingerprints = known_failed_fingerprints(
            connection,
            min_failures=config.auto_skip_failure_threshold,
        )
        for source in config.sources:
            if not source.enabled:
                continue

            handler = SOURCE_HANDLERS.get(source.kind)
            if handler is None:
                logger.warning("Unknown source kind '%s' for source '%s', skipping", source.kind, source.name)
                continue
            try:
                url_is_ignored = build_url_ignore_checker(
                    ignored_urls=config.ignored_urls
                    + tuple(str(value) for value in source.settings.get("ignored_urls", [])),
                    ignored_url_substrings=config.ignored_url_substrings
                    + tuple(str(value) for value in source.settings.get("ignored_url_substrings", [])),
                )
                articles = handler(
                    source,
                    connection,
                    raw_html_dir=raw_html_dir,
                    stats=stats,
                    url_is_ignored=url_is_ignored,
                    known_failed_fingerprints=failed_fingerprints,
                )
            except Exception as exc:
                logger.error("Failed to ingest source '%s': %s", source.name, exc)
                continue
            articles = [a for a in articles if a is not None]

            for article in articles:
                if upsert_article(connection, article):
                    stats.new_db_rows += 1
        connection.commit()

        if is_supabase_configured():
            sync_sqlite_to_supabase(connection)

    logger.info(
        "Ingestion summary: skipped_existing=%d skipped_ignored=%d skipped_known_failure=%d "
        "fetched=%d validation_failed=%d html_written=%d html_reused=%d new_db_rows=%d",
        stats.skipped_existing,
        stats.skipped_ignored,
        stats.skipped_known_failure,
        stats.fetched,
        stats.validation_failed,
        stats.html_written,
        stats.html_reused,
        stats.new_db_rows,
    )
    return stats.new_db_rows
