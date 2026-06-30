from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA_VERSION = 5


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def item_fingerprint(url: str) -> str:
    parsed = urlsplit(url.strip())
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()


@dataclass
class SyncDelta:
    source_names: set[str] = field(default_factory=set)
    item_fingerprints: set[str] = field(default_factory=set)
    failure_fingerprints: set[str] = field(default_factory=set)
    deleted_failure_fingerprints: set[str] = field(default_factory=set)


@dataclass
class IngestStats:
    skipped_existing: int = 0
    skipped_ignored: int = 0
    skipped_known_failure: int = 0
    fetched: int = 0
    validation_failed: int = 0
    html_written: int = 0
    html_reused: int = 0
    new_db_rows: int = 0
    sync_delta: SyncDelta = field(default_factory=SyncDelta)


def existing_raw_html_path(
    connection: sqlite3.Connection,
    url: str,
    raw_html_dir: str | Path,
) -> str | None:
    """Return stored raw_html_path if the article exists and the file is on disk."""
    row = connection.execute(
        "select raw_html_path from items where fingerprint = ?",
        (item_fingerprint(url),),
    ).fetchone()
    if not row or not row["raw_html_path"]:
        return None
    path = Path(raw_html_dir) / str(row["raw_html_path"])
    return str(row["raw_html_path"]) if path.is_file() else None


def resolve_raw_html_path(
    connection: sqlite3.Connection,
    url: str,
    raw_html: str,
    raw_html_dir: str | Path,
    *,
    article_date: str | None = None,
    stats: IngestStats | None = None,
) -> str:
    """Reuse an on-disk raw HTML file when present; otherwise write a new one."""
    existing = existing_raw_html_path(connection, url, raw_html_dir)
    if existing is not None:
        if stats is not None:
            stats.html_reused += 1
        return existing
    path = save_raw_html(raw_html, raw_html_dir, article_date=article_date)
    if stats is not None:
        stats.html_written += 1
    return path


def existing_item_fingerprints(connection: sqlite3.Connection, urls: list[str]) -> set[str]:
    fingerprints = [item_fingerprint(url) for url in urls if url.strip()]
    if not fingerprints:
        return set()

    placeholders = ", ".join("?" for _ in fingerprints)
    rows = connection.execute(
        f"select fingerprint from items where fingerprint in ({placeholders})",
        fingerprints,
    ).fetchall()
    return {str(row["fingerprint"]) for row in rows}


@dataclass(frozen=True)
class ArticleRecord:
    source_name: str
    source_url: str
    url: str
    title: str
    summary: str
    content: str
    published_at: str | None
    source_scraper: str = "rss"
    source_category: str | None = None
    category: str | None = None
    author: str | None = None
    raw_html_path: str | None = None
    hero_image_url: str | None = None


@contextmanager
def connect(database: str | Path):
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def initialize(database: str | Path) -> None:
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as connection:
        connection.executescript(
            """
            create table if not exists sources (
                id integer primary key autoincrement,
                name text not null unique,
                source_url text not null,
                scraper text not null,
                created_at text not null default current_timestamp
            );

            create table if not exists items (
                id integer primary key autoincrement,
                source_id integer not null,
                fingerprint text not null unique,
                url text not null,
                title text not null,
                summary text not null default '',
                content text not null default '',
                author text,
                published_at text,
                source_category text,
                category text,
                read_at text,
                rating text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                foreign key(source_id) references sources(id)
            );

            create index if not exists idx_items_source_id on items(source_id);
            create index if not exists idx_items_read_at on items(read_at);
            create index if not exists idx_items_rating on items(rating);

            create table if not exists schema_version (
                version integer not null,
                applied_at text not null default current_timestamp
            );

            create table if not exists ingestion_log (
                id integer primary key autoincrement,
                source_name text not null,
                article_url text not null,
                article_fingerprint text not null unique,
                severity text not null default 'warning',
                message text not null,
                failure_count integer not null default 1,
                created_at text not null default current_timestamp,
                last_seen_at text not null default current_timestamp
            );

            create index if not exists idx_ingestion_log_created on ingestion_log(created_at);
            """
        )
        _run_migrations(connection)
        _ensure_ingestion_log_indexes(connection)
        connection.commit()


def _run_migrations(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "select max(version) as current_version from schema_version"
    ).fetchone()
    current_version = int(row["current_version"]) if row and row["current_version"] is not None else 0

    migrations: list[tuple[int, str, str, str]] = [
        (1, "items", "category", "text"),
        (1, "items", "source_category", "text"),
        (2, "items", "raw_html_path", "text"),
        (4, "items", "hero_image_url", "text"),
        (5, "items", "curation", "text not null default '{}'"),
    ]

    for version, table_name, column_name, column_def in migrations:
        if version > current_version:
            _ensure_column(connection, table_name, column_name, column_def)

    if current_version < SCHEMA_VERSION:
        if current_version < 3:
            _migrate_ingestion_log_v3(connection)
        connection.execute(
            "insert into schema_version(version) values (?)",
            (SCHEMA_VERSION,),
        )


def _ensure_ingestion_log_indexes(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("pragma table_info(ingestion_log)")}
    if "article_fingerprint" in columns:
        connection.execute(
            "create index if not exists idx_ingestion_log_fingerprint on ingestion_log(article_fingerprint)"
        )


def _migrate_ingestion_log_v3(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("pragma table_info(ingestion_log)")}
    if "article_fingerprint" in columns:
        return

    connection.execute(
        """
        create table ingestion_log_v3 (
            id integer primary key autoincrement,
            source_name text not null,
            article_url text not null,
            article_fingerprint text not null unique,
            severity text not null default 'warning',
            message text not null,
            failure_count integer not null default 1,
            created_at text not null,
            last_seen_at text not null
        )
        """
    )
    legacy_rows = connection.execute(
        """
        select source_name, article_url, severity, message, created_at
        from ingestion_log
        order by created_at asc
        """
    ).fetchall()
    grouped: dict[str, dict[str, object]] = {}
    for row in legacy_rows:
        article_url = str(row["article_url"])
        fingerprint = item_fingerprint(article_url)
        bucket = grouped.get(fingerprint)
        if bucket is None:
            grouped[fingerprint] = {
                "source_name": row["source_name"],
                "article_url": article_url,
                "severity": row["severity"],
                "message": row["message"],
                "failure_count": 1,
                "created_at": row["created_at"],
                "last_seen_at": row["created_at"],
            }
            continue
        bucket["failure_count"] = int(bucket["failure_count"]) + 1
        bucket["message"] = row["message"]
        bucket["last_seen_at"] = row["created_at"]

    for entry in grouped.values():
        connection.execute(
            """
            insert into ingestion_log_v3(
                source_name, article_url, article_fingerprint, severity, message,
                failure_count, created_at, last_seen_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["source_name"],
                entry["article_url"],
                item_fingerprint(str(entry["article_url"])),
                entry["severity"],
                entry["message"],
                entry["failure_count"],
                entry["created_at"],
                entry["last_seen_at"],
            ),
        )

    connection.execute("drop table ingestion_log")
    connection.execute("alter table ingestion_log_v3 rename to ingestion_log")
    _ensure_ingestion_log_indexes(connection)


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    columns = {row[1] for row in connection.execute(f"pragma table_info({table_name})")}
    if column_name not in columns:
        connection.execute(f"alter table {table_name} add column {column_name} {column_definition}")


def upsert_source(
    connection: sqlite3.Connection,
    name: str,
    source_url: str,
    scraper: str,
    *,
    stats: IngestStats | None = None,
) -> int:
    connection.execute(
        """
        insert into sources(name, source_url, scraper)
        values(?, ?, ?)
        on conflict(name) do update set source_url=excluded.source_url, scraper=excluded.scraper
        """,
        (name, source_url, scraper),
    )
    if stats is not None:
        stats.sync_delta.source_names.add(name)
    row = connection.execute("select id from sources where name = ?", (name,)).fetchone()
    assert row is not None
    return int(row["id"])


def upsert_article(
    connection: sqlite3.Connection,
    article: ArticleRecord,
    *,
    stats: IngestStats | None = None,
) -> bool:
    source_id = upsert_source(
        connection,
        article.source_name,
        article.source_url,
        article.source_scraper,
        stats=stats,
    )
    fingerprint = item_fingerprint(article.url)
    if stats is not None:
        stats.sync_delta.item_fingerprints.add(fingerprint)
    existing = connection.execute("select id, raw_html_path from items where fingerprint = ?", (fingerprint,)).fetchone()
    if existing is None:
        connection.execute(
            """
            insert into items(
                source_id, fingerprint, url, title, summary, content, author, published_at,
                source_category, category, raw_html_path, hero_image_url, curation,
                created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                fingerprint,
                article.url,
                article.title,
                article.summary,
                article.content,
                article.author,
                article.published_at,
                article.source_category,
                article.category,
                article.raw_html_path,
                article.hero_image_url,
                "{}",
                utc_now(),
                utc_now(),
            ),
        )
        clear_ingestion_failure(connection, article.url, stats=stats)
        return True

    connection.execute(
        """
        update items
        set title = coalesce(nullif(?, ''), title),
            summary = case when content = '' then coalesce(nullif(?, ''), summary) else summary end,
            content = case when content = '' then coalesce(nullif(?, ''), content) else content end,
            author = coalesce(nullif(?, ''), author),
            published_at = coalesce(nullif(?, ''), published_at),
            source_category = coalesce(nullif(?, ''), source_category),
            category = coalesce(category, nullif(?, '')),
            raw_html_path = coalesce(nullif(raw_html_path, ''), nullif(?, '')),
            hero_image_url = coalesce(nullif(hero_image_url, ''), nullif(?, '')),
            updated_at = ?
        where fingerprint = ?
        """,
        (
            article.title,
            article.summary,
            article.content,
            article.author,
            article.published_at,
            article.source_category,
            article.category,
            article.raw_html_path,
            article.hero_image_url,
            utc_now(),
            fingerprint,
        ),
    )
    if article.content.strip():
        clear_ingestion_failure(connection, article.url, stats=stats)
    return False


def mark_read(connection: sqlite3.Connection, item_id: int, read: bool) -> None:
    connection.execute(
        "update items set read_at = ?, updated_at = ? where id = ?",
        (utc_now() if read else None, utc_now(), item_id),
    )


def set_rating(connection: sqlite3.Connection, item_id: int, rating: str | None) -> None:
    connection.execute(
        "update items set rating = ?, updated_at = ? where id = ?",
        (rating, utc_now(), item_id),
    )


def set_category(connection: sqlite3.Connection, item_id: int, category: str | None) -> None:
    connection.execute(
        "update items set category = ?, updated_at = ? where id = ?",
        (category, utc_now(), item_id),
    )


def set_curation(connection: sqlite3.Connection, item_id: int, curation_json: str) -> None:
    connection.execute(
        "update items set curation = ?, updated_at = ? where id = ?",
        (curation_json, utc_now(), item_id),
    )


def list_items(connection: sqlite3.Connection, unread_first: bool = True) -> list[sqlite3.Row]:
    order_clause = (
        "case when items.read_at is null then 0 else 1 end, coalesce(items.published_at, items.created_at) desc"
        if unread_first
        else "coalesce(items.published_at, items.created_at) desc"
    )
    cursor = connection.execute(
        f"""
        select items.*, sources.name as source_name, sources.source_url as source_url
        from items
        join sources on sources.id = items.source_id
        order by {order_clause}
        """
    )
    return list(cursor.fetchall())


def list_items_page(
    connection: sqlite3.Connection,
    offset: int = 0,
    limit: int = 25,
    unread_first: bool = True,
) -> tuple[list[sqlite3.Row], int]:
    order_clause = (
        "case when items.read_at is null then 0 else 1 end, coalesce(items.published_at, items.created_at) desc"
        if unread_first
        else "coalesce(items.published_at, items.created_at) desc"
    )
    base_query = """
        from items
        join sources on sources.id = items.source_id
    """
    count_row = connection.execute(
        f"select count(*) as total {base_query}"
    ).fetchone()
    total = int(count_row["total"]) if count_row else 0

    cursor = connection.execute(
        f"""
        select items.*, sources.name as source_name, sources.source_url as source_url
        {base_query}
        order by {order_clause}
        limit ? offset ?
        """,
        (limit, offset),
    )
    return list(cursor.fetchall()), total


def export_csv(connection: sqlite3.Connection, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list_items(connection, unread_first=False)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        dict_rows = [dict(row) for row in rows]
        writer = csv.DictWriter(handle, fieldnames=list(dict_rows[0].keys()) if dict_rows else ["id"])
        writer.writeheader()
        writer.writerows(dict_rows)
    return output_path


def export_jsonl(connection: sqlite3.Connection, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list_items(connection, unread_first=False)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
    return output_path


def clear_ingestion_failure(
    connection: sqlite3.Connection,
    article_url: str,
    *,
    stats: IngestStats | None = None,
) -> None:
    fingerprint = item_fingerprint(article_url)
    connection.execute(
        "delete from ingestion_log where article_fingerprint = ?",
        (fingerprint,),
    )
    if stats is not None:
        stats.sync_delta.deleted_failure_fingerprints.add(fingerprint)
        stats.sync_delta.failure_fingerprints.discard(fingerprint)


def log_ingestion_failure(
    connection: sqlite3.Connection,
    source_name: str,
    article_url: str,
    message: str,
    severity: str = "warning",
    *,
    stats: IngestStats | None = None,
) -> None:
    now = utc_now()
    fingerprint = item_fingerprint(article_url)
    if stats is not None:
        stats.sync_delta.failure_fingerprints.add(fingerprint)
        stats.sync_delta.deleted_failure_fingerprints.discard(fingerprint)
    connection.execute(
        """
        insert into ingestion_log(
            source_name, article_url, article_fingerprint, severity, message,
            failure_count, created_at, last_seen_at
        ) values (?, ?, ?, ?, ?, 1, ?, ?)
        on conflict(article_fingerprint) do update set
            source_name = excluded.source_name,
            article_url = excluded.article_url,
            severity = excluded.severity,
            message = excluded.message,
            failure_count = failure_count + 1,
            last_seen_at = excluded.last_seen_at
        """,
        (source_name, article_url, fingerprint, severity, message, now, now),
    )


def known_failed_fingerprints(
    connection: sqlite3.Connection,
    *,
    min_failures: int = 3,
) -> set[str]:
    rows = connection.execute(
        """
        select article_fingerprint
        from ingestion_log
        where failure_count >= ?
          and article_fingerprint not in (select fingerprint from items)
        """,
        (min_failures,),
    ).fetchall()
    return {str(row["article_fingerprint"]) for row in rows}


def ingestion_failures(
    connection: sqlite3.Connection,
    *,
    min_failures: int = 1,
    limit: int = 50,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        select source_name, article_url, severity, message, failure_count, created_at, last_seen_at
        from ingestion_log
        where failure_count >= ?
          and article_fingerprint not in (select fingerprint from items)
        order by last_seen_at desc
        limit ?
        """,
        (min_failures, limit),
    ).fetchall()


def recent_ingestion_issues(
    connection: sqlite3.Connection,
    limit: int = 50,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        select source_name, article_url, severity, message, failure_count, created_at, last_seen_at
        from ingestion_log
        order by last_seen_at desc
        limit ?
        """,
        (limit,),
    ).fetchall()


def save_raw_html(
    raw_html: str,
    base_dir: str | Path,
    article_date: str | None = None,
) -> str:
    """Write *raw_html* to a file and return the relative path.

    File is stored at:  *base_dir* / raw_html / YYYY-MM-DD / <uuid>.html

    The folder date is always the ingestion date (current UTC date), not the
    article's publication date. This ensures all articles ingested in a single
    run are grouped together, regardless of when they were published.
    
    The *article_date* parameter is kept for backward compatibility but is not
    used for the storage path.
    
    The returned path is relative to *base_dir*.
    """
    base = Path(base_dir)

    # Always use ingestion date (current UTC) for folder structure
    # This groups all articles from a single ingestion run together
    date_part = utc_now()[:10]

    subdir = base / "raw_html" / date_part
    subdir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.html"
    filepath = subdir / filename
    filepath.write_text(raw_html, encoding="utf-8")

    # return relative path e.g. "raw_html/2026-06-26/a1b2c3d4e5f6.html"
    return f"raw_html/{date_part}/{filename}"


