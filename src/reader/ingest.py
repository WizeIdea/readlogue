from __future__ import annotations

from pathlib import Path

from reader.config import load_config
from reader.scrapers import extract_article, parse_rss_feed
from reader.storage import ArticleRecord, connect, initialize, upsert_article


def ingest(config_path: str | Path) -> int:
    config = load_config(config_path)
    initialize(config.database)
    new_items = 0
    with connect(config.database) as connection:
        for feed in config.feeds:
            if feed.scraper == "rss":
                articles = parse_rss_feed(feed.name, feed.url)
            else:
                title, summary, content, author = extract_article(feed.url)
                articles = [
                    ArticleRecord(
                        source_name=feed.name,
                        source_url=feed.url,
                        url=feed.url,
                        title=title,
                        summary=summary,
                        content=content,
                        published_at=None,
                        author=author,
                    )
                ]

            for article in articles:
                if upsert_article(connection, article):
                    new_items += 1
        connection.commit()
    return new_items