from __future__ import annotations

from pathlib import Path

from reader.config import ListingSourceProfile, load_config, load_listing_profile
from reader.scrapers import discover_listing_links, extract_article, parse_rss_feed
from reader.storage import ArticleRecord, connect, initialize, upsert_article


def ingest(config_path: str | Path) -> int:
    config = load_config(config_path)
    initialize(config.database)
    new_items = 0
    with connect(config.database) as connection:
        for source in config.sources:
            if not source.enabled:
                continue

            if source.kind == "rss":
                articles = parse_rss_feed(source.name, source.url)
            elif source.kind == "listing":
                profile = load_listing_profile(source.config_path)
                article_urls = discover_listing_links(
                    source.url,
                    link_selector=profile.link_selector,
                    allowed_url_prefixes=profile.allowed_url_prefixes,
                    excluded_url_substrings=profile.excluded_url_substrings,
                    max_links=profile.max_links,
                )
                articles = []
                for article_url in article_urls:
                    title, summary, content, author = extract_article(
                        article_url,
                        title_selector=profile.title_selector,
                        content_selectors=profile.content_selectors,
                        paragraph_selector=profile.paragraph_selector,
                    )
                    articles.append(
                        ArticleRecord(
                            source_name=source.name,
                            source_url=source.url,
                            url=article_url,
                            title=title,
                            summary=summary,
                            content=content,
                            published_at=None,
                            source_scraper=source.scraper,
                            author=author,
                        )
                    )
            else:
                title, summary, content, author = extract_article(source.url)
                articles = [
                    ArticleRecord(
                        source_name=source.name,
                        source_url=source.url,
                        url=source.url,
                        title=title,
                        summary=summary,
                        content=content,
                        published_at=None,
                        source_scraper=source.scraper,
                        author=author,
                    )
                ]

            for article in articles:
                if upsert_article(connection, article):
                    new_items += 1
        connection.commit()
    return new_items