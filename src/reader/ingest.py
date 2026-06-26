from __future__ import annotations

from pathlib import Path

from reader.config import ListingSourceProfile, load_config, load_listing_profile
from reader.scrapers import (
    discover_listing_links,
    extract_article,
    parse_rss_feed,
    parse_huggingface_tag_articles,
    parse_listing_articles,
    validate_article_payload,
    validate_listing_page,
    validate_listing_articles,
)
from reader.storage import ArticleRecord, connect, existing_item_fingerprints, initialize, item_fingerprint, upsert_article


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
            elif source.kind == "api_tag":
                profile = load_listing_profile(source.config_path)
                tag = profile.api_tag or source.settings.get("tag") or source.name
                discovered_articles = parse_huggingface_tag_articles(str(tag))
                validate_listing_articles(source.name, source.url, discovered_articles)
                existing_fingerprints = existing_item_fingerprints(
                    connection,
                    [listing_article.url for listing_article in discovered_articles],
                )
                articles = []
                for listing_article in discovered_articles:
                    article_url = listing_article.url
                    if article_url and article_url.strip() and item_fingerprint(article_url) in existing_fingerprints:
                        continue
                    title, summary, content, author = extract_article(
                        article_url,
                        fetcher=profile.fetcher,
                        title_selector=profile.title_selector,
                        content_selectors=profile.content_selectors,
                        paragraph_selector=profile.paragraph_selector,
                    )
                    validate_article_payload(source.name, article_url, title, content)
                    articles.append(
                        ArticleRecord(
                            source_name=source.name,
                            source_url=source.url,
                            url=article_url,
                            title=title,
                            summary=listing_article.summary or summary,
                            content=content,
                            published_at=listing_article.published_at,
                            source_scraper=source.scraper,
                            source_category=listing_article.source_category,
                            category=None,
                            author=author,
                        )
                    )
            elif source.kind == "listing":
                profile = load_listing_profile(source.config_path)
                discovered_articles = parse_listing_articles(
                    source.url,
                    fetcher=profile.fetcher,
                    item_selector=profile.item_selector,
                    link_selector=profile.link_selector,
                    title_selector=profile.title_selector,
                    title_selectors=profile.title_selectors,
                    date_selectors=profile.date_selectors,
                    date_formats=profile.date_formats,
                    category_selectors=profile.category_selectors,
                    allowed_url_prefixes=profile.allowed_url_prefixes,
                    excluded_url_substrings=profile.excluded_url_substrings,
                    max_links=profile.max_links,
                )
                validate_listing_articles(source.name, source.url, discovered_articles)
                existing_fingerprints = existing_item_fingerprints(
                    connection,
                    [listing_article.url for listing_article in discovered_articles],
                )
                articles = []
                for listing_article in discovered_articles:
                    article_url = listing_article.url
                    if article_url and article_url.strip() and item_fingerprint(article_url) in existing_fingerprints:
                        continue
                    title, summary, content, author = extract_article(
                        article_url,
                        fetcher=profile.fetcher,
                        title_selector=profile.title_selector,
                        content_selectors=profile.content_selectors,
                        paragraph_selector=profile.paragraph_selector,
                    )
                    validate_article_payload(source.name, article_url, title, content)
                    articles.append(
                        ArticleRecord(
                            source_name=source.name,
                            source_url=source.url,
                            url=article_url,
                            title=title,
                            summary=listing_article.summary or summary,
                            content=content,
                            published_at=listing_article.published_at,
                            source_scraper=source.scraper,
                            source_category=listing_article.source_category,
                            category=None,
                            author=author,
                        )
                    )
            else:
                title, summary, content, author = extract_article(source.url, fetcher=source.scraper)
                validate_article_payload(source.name, source.url, title, content)
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
                        source_category=None,
                        category=None,
                        author=author,
                    )
                ]

            for article in articles:
                if upsert_article(connection, article):
                    new_items += 1
        connection.commit()
    return new_items