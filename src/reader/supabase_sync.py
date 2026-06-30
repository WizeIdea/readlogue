from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

from reader.curation import parse_curation_json, serialize_curation
from reader.storage import SyncDelta

logger = logging.getLogger(__name__)

_PAGE_SIZE = 1000


def is_supabase_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL", "").strip()) and bool(
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def _client():
    from supabase import create_client

    url = os.environ["SUPABASE_URL"].strip()
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
    return create_client(url, key)


def _fetch_all(table: str, select: str = "*") -> list[dict[str, Any]]:
    client = _client()
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        end = start + _PAGE_SIZE - 1
        response = client.table(table).select(select).range(start, end).execute()
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        start += _PAGE_SIZE
    return rows


def _clear_sqlite_state(connection: sqlite3.Connection) -> None:
    connection.execute("delete from ingestion_log")
    connection.execute("delete from items")
    connection.execute("delete from sources")
    connection.execute("delete from validation_whitelist")


def fetch_validation_whitelist() -> frozenset[str]:
    """Load analyst-whitelisted article fingerprints from Supabase."""
    if not is_supabase_configured():
        return frozenset()

    rows = _fetch_all("validation_whitelist", "article_fingerprint")
    return frozenset(str(row["article_fingerprint"]) for row in rows)


def fetch_runtime_ignores() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Load UI-managed ignore rules from Supabase."""
    if not is_supabase_configured():
        return (), ()

    rows = _fetch_all("ignored_urls", "kind,value")
    exact_urls: list[str] = []
    substrings: list[str] = []
    for row in rows:
        kind = str(row.get("kind", "")).strip()
        value = str(row.get("value", "")).strip()
        if not value:
            continue
        if kind == "exact":
            exact_urls.append(value)
        elif kind == "substring":
            substrings.append(value)
    return tuple(exact_urls), tuple(substrings)


def hydrate_sqlite_from_supabase(connection: sqlite3.Connection) -> None:
    """Load production state from Supabase into the ephemeral scratch SQLite DB."""
    if not is_supabase_configured():
        return

    sources = _fetch_all("sources")
    items = _fetch_all("items")
    failures = _fetch_all("ingestion_log")
    whitelist = _fetch_all("validation_whitelist")

    _clear_sqlite_state(connection)

    for source in sources:
        connection.execute(
            """
            insert into sources(id, name, source_url, scraper, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                source["id"],
                source["name"],
                source["source_url"],
                source["scraper"],
                source["created_at"],
            ),
        )

    for item in items:
        connection.execute(
            """
            insert into items(
                id, source_id, fingerprint, url, title, summary, content, author,
                published_at, source_category, category, read_at, rating,
                raw_html_path, hero_image_url, curation, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["source_id"],
                item["fingerprint"],
                item["url"],
                item["title"],
                item.get("summary", ""),
                item.get("content", ""),
                item.get("author"),
                item.get("published_at"),
                item.get("source_category"),
                item.get("category"),
                item.get("read_at"),
                item.get("rating"),
                item.get("raw_html_path"),
                item.get("hero_image_url"),
                serialize_curation(item.get("curation")),
                item["created_at"],
                item["updated_at"],
            ),
        )

    for failure in failures:
        connection.execute(
            """
            insert into ingestion_log(
                source_name, article_url, article_fingerprint, severity, message,
                article_title, failure_count, created_at, last_seen_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                failure["source_name"],
                failure["article_url"],
                failure["article_fingerprint"],
                failure.get("severity", "warning"),
                failure["message"],
                failure.get("article_title"),
                failure["failure_count"],
                failure["created_at"],
                failure["last_seen_at"],
            ),
        )

    for entry in whitelist:
        connection.execute(
            """
            insert into validation_whitelist(article_fingerprint, article_url, created_at)
            values (?, ?, ?)
            """,
            (
                entry["article_fingerprint"],
                entry["article_url"],
                entry["created_at"],
            ),
        )

    logger.info(
        "Hydrated scratch SQLite from Supabase: sources=%d items=%d ingestion_log=%d validation_whitelist=%d",
        len(sources),
        len(items),
        len(failures),
        len(whitelist),
    )
    for table in ("sources", "items"):
        row = connection.execute(f"select max(id) as max_id from {table}").fetchone()
        max_id = row["max_id"] if row else None
        if max_id is not None:
            connection.execute(
                "insert or replace into sqlite_sequence(name, seq) values (?, ?)",
                (table, int(max_id)),
            )



def sync_sqlite_to_supabase(connection: sqlite3.Connection, delta: SyncDelta) -> None:
    """Push rows changed during ingest from scratch SQLite to Supabase."""
    if not is_supabase_configured():
        return

    client = _client()

    total_sources = int(connection.execute("select count(*) from sources").fetchone()[0])
    total_items = int(connection.execute("select count(*) from items").fetchone()[0])
    total_failures = int(connection.execute("select count(*) from ingestion_log").fetchone()[0])

    source_rows: list[sqlite3.Row] = []
    if delta.source_names:
        placeholders = ", ".join("?" for _ in delta.source_names)
        source_rows = connection.execute(
            f"""
            select name, source_url, scraper, created_at
            from sources
            where name in ({placeholders})
            """,
            tuple(delta.source_names),
        ).fetchall()
        for row in source_rows:
            client.table("sources").upsert(
                {
                    "name": row["name"],
                    "source_url": row["source_url"],
                    "scraper": row["scraper"],
                    "created_at": row["created_at"],
                },
                on_conflict="name",
            ).execute()

    remote_sources = _fetch_all("sources", "id,name") if delta.source_names or delta.item_fingerprints else []
    name_to_id = {str(source["name"]): int(source["id"]) for source in remote_sources}

    item_rows: list[sqlite3.Row] = []
    if delta.item_fingerprints:
        placeholders = ", ".join("?" for _ in delta.item_fingerprints)
        item_rows = connection.execute(
            f"""
            select items.*, sources.name as source_name
            from items
            join sources on sources.id = items.source_id
            where items.fingerprint in ({placeholders})
            """,
            tuple(delta.item_fingerprints),
        ).fetchall()
        for row in item_rows:
            source_id = name_to_id.get(str(row["source_name"]))
            if source_id is None:
                logger.warning("Skipping item sync; unknown source %s", row["source_name"])
                continue
            client.table("items").upsert(
                {
                    "source_id": source_id,
                    "fingerprint": row["fingerprint"],
                    "url": row["url"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "content": row["content"],
                    "author": row["author"],
                    "published_at": row["published_at"],
                    "source_category": row["source_category"],
                    "category": row["category"],
                    "read_at": row["read_at"],
                    "rating": row["rating"],
                    "raw_html_path": row["raw_html_path"],
                    "hero_image_url": row["hero_image_url"],
                    "curation": parse_curation_json(row["curation"] if "curation" in row.keys() else "{}"),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
                on_conflict="fingerprint",
            ).execute()

    failure_rows: list[sqlite3.Row] = []
    if delta.failure_fingerprints:
        placeholders = ", ".join("?" for _ in delta.failure_fingerprints)
        failure_rows = connection.execute(
            f"""
            select source_name, article_url, article_fingerprint, severity, message,
                   article_title, failure_count, created_at, last_seen_at
            from ingestion_log
            where article_fingerprint in ({placeholders})
            """,
            tuple(delta.failure_fingerprints),
        ).fetchall()
        for row in failure_rows:
            client.table("ingestion_log").upsert(
                {
                    "source_name": row["source_name"],
                    "article_url": row["article_url"],
                    "article_fingerprint": row["article_fingerprint"],
                    "severity": row["severity"],
                    "message": row["message"],
                    "article_title": row["article_title"],
                    "failure_count": row["failure_count"],
                    "created_at": row["created_at"],
                    "last_seen_at": row["last_seen_at"],
                },
                on_conflict="article_fingerprint",
            ).execute()

    failures_deleted = 0
    for fingerprint in delta.deleted_failure_fingerprints:
        client.table("ingestion_log").delete().eq("article_fingerprint", fingerprint).execute()
        failures_deleted += 1

    logger.info(
        "Synced to Supabase: sources=%d/%d items=%d/%d ingestion_log=%d/%d (failures deleted=%d)",
        len(source_rows),
        total_sources,
        len(item_rows),
        total_items,
        len(failure_rows),
        total_failures,
        failures_deleted,
    )
