from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA_VERSION = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def item_fingerprint(url: str) -> str:
    parsed = urlsplit(url.strip())
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()


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
                severity text not null default 'warning',
                message text not null,
                created_at text not null default current_timestamp
            );

            create index if not exists idx_ingestion_log_created on ingestion_log(created_at);
            """
        )
        _run_migrations(connection)
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
    ]

    for version, table_name, column_name, column_def in migrations:
        if version > current_version:
            _ensure_column(connection, table_name, column_name, column_def)

    if current_version < SCHEMA_VERSION:
        connection.execute(
            "insert into schema_version(version) values (?)",
            (SCHEMA_VERSION,),
        )


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_definition: str) -> None:
    columns = {row[1] for row in connection.execute(f"pragma table_info({table_name})")}
    if column_name not in columns:
        connection.execute(f"alter table {table_name} add column {column_name} {column_definition}")


def upsert_source(connection: sqlite3.Connection, name: str, source_url: str, scraper: str) -> int:
    connection.execute(
        """
        insert into sources(name, source_url, scraper)
        values(?, ?, ?)
        on conflict(name) do update set source_url=excluded.source_url, scraper=excluded.scraper
        """,
        (name, source_url, scraper),
    )
    row = connection.execute("select id from sources where name = ?", (name,)).fetchone()
    assert row is not None
    return int(row["id"])


def upsert_article(connection: sqlite3.Connection, article: ArticleRecord) -> bool:
    source_id = upsert_source(connection, article.source_name, article.source_url, article.source_scraper)
    fingerprint = item_fingerprint(article.url)
    existing = connection.execute("select id, raw_html_path from items where fingerprint = ?", (fingerprint,)).fetchone()
    if existing is None:
        connection.execute(
            """
            insert into items(
                source_id, fingerprint, url, title, summary, content, author, published_at,
                source_category, category, raw_html_path, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                utc_now(),
                utc_now(),
            ),
        )
        return True

    # On update: preserve the existing raw_html_path if the new article doesn't have one
    # (this handles the case where an RSS article later gets a scraped version)
    raw_path = article.raw_html_path or existing["raw_html_path"]
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
            raw_html_path = coalesce(nullif(?, ''), raw_html_path),
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
            raw_path,
            utc_now(),
            fingerprint,
        ),
    )
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


def log_ingestion_failure(
    connection: sqlite3.Connection,
    source_name: str,
    article_url: str,
    message: str,
    severity: str = "warning",
) -> None:
    connection.execute(
        """
        insert into ingestion_log(source_name, article_url, severity, message, created_at)
        values (?, ?, ?, ?, ?)
        """,
        (source_name, article_url, severity, message, utc_now()),
    )


def recent_ingestion_issues(
    connection: sqlite3.Connection,
    limit: int = 50,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        select source_name, article_url, severity, message, created_at
        from ingestion_log
        order by created_at desc
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


