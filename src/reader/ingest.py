from __future__ import annotations

import logging
from pathlib import Path

from reader.config import ListingSourceProfile, load_config, load_listing_profile
from reader.scrapers import (
    extract_article,
    parse_rss_feed,
    parse_huggingface_tag_articles,
    parse_listing_articles,
    validate_listing_articles,
)
from reader.storage import ArticleRecord, connect, existing_item_fingerprints, initialize, item_fingerprint, log_ingestion_failure, upsert_article
from reader.validation import validate_content

logger = logging.getLogger(__name__)


def _fetch_article(
    connection,
    article_url: str,
    source_name: str,
    source_url: str,
    listing_article,
    profile: ListingSourceProfile | None,
) -> ArticleRecord | None:
    """Fetch an article page, validate content quality, and return an ArticleRecord
    or None if the article fails validation."""
    if profile is not None:
        title, summary, content, author = extract_article(
            article_url,
            fetcher=profile.fetcher,
            title_selector=profile.title_selector,
            content_selectors=profile.content_selectors,
            paragraph_selector=profile.paragraph_selector,
        )
        listing_summary = listing_article.summary
    else:
        title, summary, content, author = extract_article(article_url, fetcher="requests")
        listing_summary = summary

    quality = validate_content(title, content, article_url, source_name)
    if not quality.is_valid:
        log_ingestion_failure(connection, source_name, article_url, quality.reason or "unknown validation failure")
        logger.warning("Skipping article %s from '%s': %s", article_url, source_name, quality.reason)
        return None

    published_at = listing_article.published_at if listing_article else None
    source_category = listing_article.source_category if listing_article else None
    return ArticleRecord(
        source_name=source_name,
        source_url=source_url,
        url=article_url,
        title=title,
        summary=listing_summary or summary,
        content=content,
        published_at=published_at,
        source_scraper="placeholder",  # caller fixes this via object.__setattr__
        source_category=source_category,
        category=None,
        author=author,
    )


def ingest(config_path: str | Path) -> int:
    config = load_config(config_path)
    initialize(config.database)
    new_items = 0
    skipped_items = 0
    with connect(config.database) as connection:
        for source in config.sources:
            if not source.enabled:
                continue

            if source.kind == "rss":
                articles: list[ArticleRecord | None] = []
                raw_articles = parse_rss_feed(source.name, source.url)
                for raw in raw_articles:
                    quality = validate_content(raw.title, raw.content, raw.url, source.name)
                    if not quality.is_valid:
                        log_ingestion_failure(connection, source.name, raw.url, quality.reason or "unknown validation failure")
                        logger.warning("Skipping article %s from '%s': %s", raw.url, source.name, quality.reason)
                        skipped_items += 1
                        continue
                    articles.append(raw)
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
                    record = _fetch_article(connection, article_url, source.name, source.url, listing_article, profile)
                    if record is None:
                        skipped_items += 1
                        continue
                    article_record = record
                    # preserve source_scraper from source config
                    object.__setattr__(article_record, "source_scraper", source.scraper)
                    articles.append(article_record)
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
                    record = _fetch_article(connection, article_url, source.name, source.url, listing_article, profile)
                    if record is None:
                        skipped_items += 1
                        continue
                    article_record = record
                    object.__setattr__(article_record, "source_scraper", source.scraper)
                    articles.append(article_record)
            else:
                title, summary, content, author = extract_article(source.url, fetcher=source.scraper)
                quality = validate_content(title, content, source.url, source.name)
                if not quality.is_valid:
                    log_ingestion_failure(connection, source.name, source.url, quality.reason or "unknown validation failure")
                    logger.warning("Skipping article %s from '%s': %s", source.url, source.name, quality.reason)
                    skipped_items += 1
                    continue
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
                if article is not None and upsert_article(connection, article):
                    new_items += 1
        connection.commit()

    total_attempted = new_items + skipped_items
    if skipped_items:
        logger.warning("Ingestion complete: %d new items, %d skipped due to content quality", new_items, skipped_items)
    else:
        logger.info("Ingestion complete: %d new items", new_items)
    return new_items
