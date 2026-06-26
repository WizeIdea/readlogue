from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def item_fingerprint(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


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
    author: str | None = None


def connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    return connection


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
                read_at text,
                rating text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                foreign key(source_id) references sources(id)
            );

            create index if not exists idx_items_source_id on items(source_id);
            create index if not exists idx_items_read_at on items(read_at);
            create index if not exists idx_items_rating on items(rating);
            """
        )


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
    existing = connection.execute("select id from items where fingerprint = ?", (fingerprint,)).fetchone()
    if existing is None:
        connection.execute(
            """
            insert into items(
                source_id, fingerprint, url, title, summary, content, author, published_at, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                utc_now(),
                utc_now(),
            ),
        )
        return True

    connection.execute(
        """
        update items
        set title = coalesce(nullif(?, ''), title),
            summary = case when content = '' then coalesce(nullif(?, ''), summary) else summary end,
            content = case when content = '' then coalesce(nullif(?, ''), content) else content end,
            author = coalesce(nullif(?, ''), author),
            published_at = coalesce(nullif(?, ''), published_at),
            updated_at = ?
        where fingerprint = ?
        """,
        (
            article.title,
            article.summary,
            article.content,
            article.author,
            article.published_at,
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