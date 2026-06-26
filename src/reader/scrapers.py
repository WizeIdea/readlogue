from __future__ import annotations

import contextlib
import feedparser
import re
import requests
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from reader.storage import ArticleRecord, IngestStats


@dataclass(slots=True)
class ListingArticle:
    url: str
    title: str
    summary: str
    published_at: str | None
    source_category: str | None
    author: str | None = None


HF_API_URL = "https://huggingface.co/api/blog"

# Registry of source-kind handlers. Each handler receives the source config,
# the database connection, and raw_html_dir, and returns a list of
# ArticleRecord (or None for skipped items).
SOURCE_HANDLERS: dict[str, object] = {}


def build_url_ignore_checker(
    *,
    ignored_urls: tuple[str, ...] = (),
    ignored_url_substrings: tuple[str, ...] = (),
) -> Callable[[str], bool]:
    from reader.storage import item_fingerprint

    fingerprints = {
        item_fingerprint(_normalize_url(url))
        for url in ignored_urls
        if url and url.strip()
    }
    substrings = tuple(fragment for fragment in ignored_url_substrings if fragment)

    def url_is_ignored(url: str) -> bool:
        if not url or not url.strip():
            return False
        normalized = _normalize_url(url)
        if item_fingerprint(normalized) in fingerprints:
            return True
        return any(fragment in normalized for fragment in substrings)

    return url_is_ignored


def _skip_ignored_url(
    article_url: str,
    source_name: str,
    *,
    url_is_ignored: Callable[[str], bool] | None,
    stats: IngestStats | None,
) -> bool:
    if url_is_ignored is None or not url_is_ignored(article_url):
        return False

    import logging

    logger = logging.getLogger(__name__)
    if stats is not None:
        stats.skipped_ignored += 1
    logger.info("Skipping ignored URL from '%s': %s", source_name, article_url)
    return True


def _skip_known_failure(
    article_url: str,
    source_name: str,
    *,
    known_failed_fingerprints: set[str] | None,
    stats: IngestStats | None,
) -> bool:
    if not known_failed_fingerprints:
        return False

    from reader.storage import item_fingerprint

    if item_fingerprint(article_url) not in known_failed_fingerprints:
        return False

    import logging

    logger = logging.getLogger(__name__)
    if stats is not None:
        stats.skipped_known_failure += 1
    logger.info("Skipping known failed URL from '%s': %s", source_name, article_url)
    return True


def _handle_rss_source(
    source_config,
    connection,
    raw_html_dir: str | Path = "data",
    *,
    stats: IngestStats | None = None,
    url_is_ignored: Callable[[str], bool] | None = None,
    known_failed_fingerprints: set[str] | None = None,
) -> list:
    """Handle RSS sources: discover from feed, then fetch full article pages."""
    import logging

    logger = logging.getLogger(__name__)
    from reader.storage import existing_item_fingerprints, item_fingerprint

    max_entries = int(source_config.settings.get("max_entries", 25))
    fetcher = str(source_config.settings.get("fetcher", "requests"))
    articles = []
    raw_articles = parse_rss_feed(source_config.name, source_config.url, max_entries=max_entries)
    existing_fingerprints = existing_item_fingerprints(connection, [raw.url for raw in raw_articles])
    pending = [
        raw
        for raw in raw_articles
        if not (raw.url and item_fingerprint(raw.url) in existing_fingerprints)
    ]
    if stats is not None:
        stats.skipped_existing += len(raw_articles) - len(pending)

    logger.info(
        "RSS source '%s': %d feed entries (max_entries=%d), %d already in database, %d to fetch",
        source_config.name,
        len(raw_articles),
        max_entries,
        len(raw_articles) - len(pending),
        len(pending),
    )

    for raw in pending:
        if _skip_ignored_url(
            raw.url,
            source_config.name,
            url_is_ignored=url_is_ignored,
            stats=stats,
        ):
            continue
        if _skip_known_failure(
            raw.url,
            source_config.name,
            known_failed_fingerprints=known_failed_fingerprints,
            stats=stats,
        ):
            continue
        fingerprint = item_fingerprint(raw.url) if raw.url and raw.url.strip() else None
        record = _fetch_article(
            connection, raw.url, source_config.name, source_config.url, None, None,
            raw_html_dir=raw_html_dir, source_scraper=source_config.scraper,
            fetcher=fetcher, stats=stats,
        )
        if record is None:
            continue
        if fingerprint:
            existing_fingerprints.add(fingerprint)
        # Use RSS feed metadata as fallback
        object.__setattr__(record, "title", record.title or raw.title)
        object.__setattr__(record, "published_at", record.published_at or raw.published_at)
        object.__setattr__(record, "source_category", record.source_category or raw.source_category)
        object.__setattr__(record, "author", record.author or raw.author)
        articles.append(record)
    return articles


def _handle_listing_source(
    source_config,
    connection,
    raw_html_dir: str | Path = "data",
    *,
    stats: IngestStats | None = None,
    url_is_ignored: Callable[[str], bool] | None = None,
    known_failed_fingerprints: set[str] | None = None,
) -> list:
    """Handle listing sources: discover links, then fetch full article pages."""
    from reader.config import load_listing_profile
    from reader.storage import existing_item_fingerprints, item_fingerprint

    profile = load_listing_profile(source_config.config_path)
    discovered_articles = parse_listing_articles(
        source_config.url,
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
    validate_listing_articles(source_config.name, source_config.url, discovered_articles)
    existing_fingerprints = existing_item_fingerprints(connection, [la.url for la in discovered_articles])

    articles = []
    for listing_article in discovered_articles:
        article_url = listing_article.url
        fingerprint = item_fingerprint(article_url) if article_url and article_url.strip() else None
        if fingerprint and fingerprint in existing_fingerprints:
            if stats is not None:
                stats.skipped_existing += 1
            continue
        if _skip_ignored_url(
            article_url,
            source_config.name,
            url_is_ignored=url_is_ignored,
            stats=stats,
        ):
            continue
        if _skip_known_failure(
            article_url,
            source_config.name,
            known_failed_fingerprints=known_failed_fingerprints,
            stats=stats,
        ):
            continue
        record = _fetch_article(
            connection, article_url, source_config.name, source_config.url, listing_article, profile,
            raw_html_dir=raw_html_dir, source_scraper=source_config.scraper, stats=stats,
        )
        if record is None:
            continue
        if fingerprint:
            existing_fingerprints.add(fingerprint)
        articles.append(record)
    return articles


def _handle_api_tag_source(
    source_config,
    connection,
    raw_html_dir: str | Path = "data",
    *,
    stats: IngestStats | None = None,
    url_is_ignored: Callable[[str], bool] | None = None,
    known_failed_fingerprints: set[str] | None = None,
) -> list:
    """Handle API tag sources (e.g., HuggingFace blog tags)."""
    from reader.config import load_listing_profile
    from reader.storage import existing_item_fingerprints, item_fingerprint

    profile = load_listing_profile(source_config.config_path)
    tag = profile.api_tag or source_config.settings.get("tag") or source_config.name
    discovered_articles = parse_huggingface_tag_articles(str(tag))[: profile.max_links]
    validate_listing_articles(source_config.name, source_config.url, discovered_articles)
    existing_fingerprints = existing_item_fingerprints(connection, [la.url for la in discovered_articles])

    articles = []
    for listing_article in discovered_articles:
        article_url = listing_article.url
        fingerprint = item_fingerprint(article_url) if article_url and article_url.strip() else None
        if fingerprint and fingerprint in existing_fingerprints:
            if stats is not None:
                stats.skipped_existing += 1
            continue
        if _skip_ignored_url(
            article_url,
            source_config.name,
            url_is_ignored=url_is_ignored,
            stats=stats,
        ):
            continue
        if _skip_known_failure(
            article_url,
            source_config.name,
            known_failed_fingerprints=known_failed_fingerprints,
            stats=stats,
        ):
            continue
        record = _fetch_article(
            connection, article_url, source_config.name, source_config.url, listing_article, profile,
            raw_html_dir=raw_html_dir, source_scraper=source_config.scraper, stats=stats,
        )
        if record is None:
            continue
        if fingerprint:
            existing_fingerprints.add(fingerprint)
        articles.append(record)
    return articles


def _handle_direct_source(
    source_config,
    connection,
    raw_html_dir: str | Path = "data",
    *,
    stats: IngestStats | None = None,
    url_is_ignored: Callable[[str], bool] | None = None,
    known_failed_fingerprints: set[str] | None = None,
) -> list:
    """Handle direct URL sources: fetch a single article page."""
    import logging
    logger = logging.getLogger(__name__)
    from reader.storage import existing_item_fingerprints, item_fingerprint, log_ingestion_failure, resolve_raw_html_path
    from reader.validation import validate_content

    if stats is not None:
        existing = existing_item_fingerprints(connection, [source_config.url])
        if item_fingerprint(source_config.url) in existing:
            stats.skipped_existing += 1
            return []

    if _skip_ignored_url(
        source_config.url,
        source_config.name,
        url_is_ignored=url_is_ignored,
        stats=stats,
    ):
        return []

    if _skip_known_failure(
        source_config.url,
        source_config.name,
        known_failed_fingerprints=known_failed_fingerprints,
        stats=stats,
    ):
        return []

    articles = []
    if stats is not None:
        stats.fetched += 1
    title, summary, content, author, raw_html = extract_article(source_config.url, fetcher=source_config.scraper)
    quality = validate_content(title, content, source_config.url, source_config.name)
    if not quality.is_valid:
        if stats is not None:
            stats.validation_failed += 1
        log_ingestion_failure(connection, source_config.name, source_config.url, quality.reason or "unknown validation failure")
        logger.warning("Skipping article %s from '%s': %s", source_config.url, source_config.name, quality.reason)
        return articles

    raw_html_path = resolve_raw_html_path(
        connection,
        source_config.url,
        raw_html,
        raw_html_dir,
        stats=stats,
    )
    articles.append(
        ArticleRecord(
            source_name=source_config.name,
            source_url=source_config.url,
            url=source_config.url,
            title=title,
            summary=summary,
            content=content,
            published_at=None,
            source_scraper=source_config.scraper,
            source_category=None,
            category=None,
            author=author,
            raw_html_path=raw_html_path,
        )
    )
    return articles


def _fetch_article(
    connection,
    article_url: str,
    source_name: str,
    source_url: str,
    listing_article,
    profile: ListingSourceProfile | None,
    *,
    raw_html_dir: str | Path = "data",
    source_scraper: str = "requests",
    fetcher: str = "requests",
    stats: IngestStats | None = None,
) -> ArticleRecord | None:
    """Fetch an article page, validate content quality, and return an ArticleRecord
    or None if the article fails validation."""
    import logging
    import time

    logger = logging.getLogger(__name__)
    fetch_started = time.monotonic()
    if stats is not None:
        stats.fetched += 1

    if profile is not None:
        title, summary, content, author, raw_html = extract_article(
            article_url,
            fetcher=profile.fetcher,
            title_selector=profile.title_selector,
            content_selectors=profile.content_selectors,
            paragraph_selector=profile.paragraph_selector,
        )
        listing_summary = listing_article.summary
    else:
        title, summary, content, author, raw_html = extract_article(article_url, fetcher=fetcher)
        listing_summary = summary

    from reader.storage import log_ingestion_failure, resolve_raw_html_path
    from reader.validation import validate_content

    quality = validate_content(title, content, article_url, source_name)
    elapsed = time.monotonic() - fetch_started
    logger.info(
        "Fetched %s in %.1fs (%d words, accepted=%s)",
        article_url,
        elapsed,
        quality.word_count,
        quality.is_valid,
    )
    if not quality.is_valid:
        if stats is not None:
            stats.validation_failed += 1
        # Log debug info to help diagnose extraction issues
        logger.debug(
            "Content extraction details for %s:\n  Title: %s\n  Content length: %d chars\n  Content preview: %s",
            article_url, title, len(content), content[:200] if content else "(empty)"
        )
        log_ingestion_failure(connection, source_name, article_url, quality.reason or "unknown validation failure")
        logger.warning("Skipping article %s from '%s': %s", article_url, source_name, quality.reason)
        return None

    # Save raw HTML to file when not already stored for this article
    published_at = listing_article.published_at if listing_article else None
    raw_html_path = resolve_raw_html_path(
        connection,
        article_url,
        raw_html,
        raw_html_dir,
        article_date=published_at,
        stats=stats,
    )

    source_category = listing_article.source_category if listing_article else None
    return ArticleRecord(
        source_name=source_name,
        source_url=source_url,
        url=article_url,
        title=title,
        summary=listing_summary or summary,
        content=content,
        published_at=published_at,
        source_scraper=source_scraper,
        source_category=source_category,
        category=None,
        author=author,
        raw_html_path=raw_html_path,
    )


# Register handlers
SOURCE_HANDLERS = {
    "rss": _handle_rss_source,
    "listing": _handle_listing_source,
    "api_tag": _handle_api_tag_source,
    "direct": _handle_direct_source,
}


def parse_rss_feed(source_name: str, source_url: str, *, max_entries: int = 25) -> list[ArticleRecord]:
    parsed = feedparser.parse(source_url)
    articles: list[ArticleRecord] = []
    for entry in parsed.entries[:max_entries]:
        link = entry.get("link", "").strip()
        if not link:
            continue
        url = _normalize_url(link)
        summary_html = entry.get("summary", "")
        summary_markdown = _html_to_markdown(summary_html) if summary_html else ""
        articles.append(
            ArticleRecord(
                source_name=source_name,
                source_url=source_url,
                url=url,
                title=entry.get("title", url),
                summary=summary_markdown,
                content=summary_markdown,
                published_at=entry.get("published") or entry.get("updated"),
                source_scraper="rss",
                source_category=_extract_rss_category(entry),
                author=entry.get("author"),
            )
        )
    return articles


def parse_huggingface_tag_articles(tag: str, *, max_pages: int = 10) -> list[ListingArticle]:
    all_articles: list[ListingArticle] = []
    seen_links: set[str] = set()
    page = 0

    while page < max_pages:
        response = requests.get(HF_API_URL, params={"tag": tag, "page": page}, timeout=15, headers={"User-Agent": "reader/0.1.0"})
        response.raise_for_status()
        payload = response.json()
        blogs = payload.get("allBlogs", []) or []
        if not blogs:
            break

        new_on_page = 0
        for blog in blogs:
            title = _clean_text(blog.get("title"))
            if not title:
                continue

            url_value = blog.get("url") or f"/blog/{blog.get('slug', '')}"
            link = _normalize_url(f"https://huggingface.co{url_value}" if str(url_value).startswith("/") else str(url_value))
            if link in seen_links:
                continue

            seen_links.add(link)
            new_on_page += 1
            published_at = _parse_iso_date(str(blog.get("publishedAt") or ""))
            tags = [
                _clean_text(tag_value)
                for tag_value in (blog.get("tags") or [])
                if _clean_text(tag_value)
            ]
            source_category = tags[0] if tags else tag.title()
            description = _clean_text(blog.get("description") or "")
            if not description:
                description = title if not tags else f"{title} ({', '.join(tags)})"

            all_articles.append(
                ListingArticle(
                    url=link,
                    title=title,
                    summary=description[:500],
                    published_at=published_at,
                    source_category=source_category,
                    author=_clean_text(blog.get("author")) or None,
                )
            )

        if new_on_page == 0:
            break

        total = payload.get("numTotalItems")
        if total is not None and len(seen_links) >= int(total):
            break
        page += 1

    return all_articles


def parse_listing_articles(
    listing_url: str,
    html: str | None = None,
    fetcher: str = "requests",
    item_selector: str = "a[href]",
    link_selector: str = "a[href]",
    title_selector: str | None = None,
    title_selectors: tuple[str, ...] = (),
    date_selectors: tuple[str, ...] = (),
    date_formats: tuple[str, ...] = (),
    category_selectors: tuple[str, ...] = (),
    allowed_url_prefixes: tuple[str, ...] = (),
    excluded_url_substrings: tuple[str, ...] = (),
    max_links: int = 25,
    timeout: int = 15,
) -> list[ListingArticle]:
    BeautifulSoup = _load_beautifulsoup()
    if html is None:
        html = _fetch_html(listing_url, fetcher=fetcher, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(item_selector) if item_selector else soup.select(link_selector)
    articles: list[ListingArticle] = []
    seen: set[str] = set()

    for item in items:
        link = _extract_href(item, listing_url, link_selector)
        if not link:
            continue
        if allowed_url_prefixes and not any(link.startswith(prefix) for prefix in allowed_url_prefixes):
            continue
        if excluded_url_substrings and any(fragment in link for fragment in excluded_url_substrings):
            continue
        if link in seen:
            continue
        seen.add(link)

        title = _first_text(item, [title_selector] if title_selector else [])
        if not title and title_selectors:
            title = _first_text(item, list(title_selectors))
        if not title:
            title = _first_text(item, ["h1", "h2", "h3", "h4", "title"]) or link

        published_at = _extract_date_from_item(item, date_selectors, date_formats)
        source_category = _extract_category_from_item(item, category_selectors, published_at)
        summary = _clean_text(item.get_text(" ", strip=True))[:500]

        articles.append(
            ListingArticle(
                url=link,
                title=title,
                summary=summary,
                published_at=published_at,
                source_category=source_category,
                author=_first_meta_content(item, "author"),
            )
        )

        if len(articles) >= max_links:
            break

    return articles


def discover_listing_links(
    listing_url: str,
    fetcher: str = "requests",
    link_selector: str = "a[href]",
    allowed_url_prefixes: tuple[str, ...] = (),
    excluded_url_substrings: tuple[str, ...] = (),
    max_links: int = 25,
    timeout: int = 15,
) -> list[str]:
    BeautifulSoup = _load_beautifulsoup()
    html = _fetch_html(listing_url, fetcher=fetcher, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    discovered = _discover_listing_links_from_soup(
        soup,
        listing_url,
        link_selector=link_selector,
        allowed_url_prefixes=allowed_url_prefixes,
        excluded_url_substrings=excluded_url_substrings,
        max_links=max_links,
    )
    return discovered


def discover_listing_links_from_html(
    html: str,
    listing_url: str,
    link_selector: str = "a[href]",
    allowed_url_prefixes: tuple[str, ...] = (),
    excluded_url_substrings: tuple[str, ...] = (),
    max_links: int = 25,
) -> list[str]:
    BeautifulSoup = _load_beautifulsoup()
    soup = BeautifulSoup(html, "html.parser")
    return _discover_listing_links_from_soup(
        soup,
        listing_url,
        link_selector=link_selector,
        allowed_url_prefixes=allowed_url_prefixes,
        excluded_url_substrings=excluded_url_substrings,
        max_links=max_links,
    )


def extract_article(
    url: str,
    fetcher: str = "requests",
    title_selector: str | None = None,
    content_selectors: tuple[str, ...] = (),
    paragraph_selector: str = "article p, main p, p",
    timeout: int = 15,
) -> tuple[str, str, str | None, str | None, str]:
    """Fetch *url*, parse it, and return (title, summary, content, author, raw_html).

    The last element is the raw HTML fetched from the page, saved for ML pipelines.
    """
    BeautifulSoup = _load_beautifulsoup()
    html = _fetch_html(url, fetcher=fetcher, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    title = _first_text(soup, [title_selector] if title_selector else ["h1", "title"]) or url

    body = soup.find("body")
    if fetcher == "requests" and body is not None and len(body.get_text(" ", strip=True)) < 20:
        author = _first_meta_content(soup, "author")
        return title, "", "", author, html

    content = ""
    if content_selectors:
        content = _extract_content_from_selectors(soup, content_selectors)
    if not content:
        # Try semantic HTML5 tags first
        content = _extract_content_from_selectors(soup, ("article", "main"))
    if not content:
        # Fallback to common modern web patterns (divs with content-related classes)
        content = _extract_content_from_selectors(
            soup,
            (
                "div[class*='content']",
                "div[class*='article']",
                "div[class*='post']",
                "div[class*='body']",
                "div[class*='entry']",
            ),
        )
    if not content:
        paragraphs = soup.select(paragraph_selector)
        if paragraphs:
            # Wrap paragraphs in a <div> and convert to Markdown
            paragraph_html = "<div>" + "".join(str(p) for p in paragraphs) + "</div>"
            content = _html_to_markdown(paragraph_html)

    summary = content[:500]
    author = _first_meta_content(soup, "author")
    return title, summary, content, author, html


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        if not selector:
            continue
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text
    return ""


def validate_listing_page(source_name: str, listing_url: str, article_urls: list[str]) -> None:
    if not article_urls:
        raise RuntimeError(f"No article links found for listing source '{source_name}' at {listing_url}")


def validate_article_payload(source_name: str, article_url: str, title: str, content: str) -> None:
    if not title or len(title.strip()) < 3:
        raise RuntimeError(f"Missing or invalid title for article '{article_url}' from source '{source_name}'")
    if not content or len(content.strip()) < 40:
        raise RuntimeError(f"Missing or invalid content for article '{article_url}' from source '{source_name}'")


def validate_listing_articles(source_name: str, listing_url: str, articles: list[ListingArticle]) -> None:
    if not articles:
        raise RuntimeError(f"No listing articles found for source '{source_name}' at {listing_url}")


def _first_meta_content(soup: BeautifulSoup, name: str) -> str | None:
    meta = soup.select_one(f'meta[name="{name}"]')
    if meta and meta.get("content"):
        return str(meta["content"]).strip() or None
    return None


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).split())


def _extract_href(element, listing_url: str, link_selector: str) -> str | None:
    href = element.get("href") if hasattr(element, "get") else None
    if not href and link_selector:
        link = element.select_one(link_selector)
        href = link.get("href") if link else None
    if not href:
        return None
    return _normalize_url(urljoin(listing_url, str(href)))


def _extract_rss_category(entry) -> str | None:
    for tag in entry.get("tags", []) or []:
        term = _clean_text(tag.get("term"))
        if term:
            return term
    return None


def _extract_date_from_item(item, date_selectors: tuple[str, ...], date_formats: tuple[str, ...]) -> str | None:
    candidates: list[str] = []
    for selector in date_selectors:
        for element in item.select(selector):
            if element.get("datetime"):
                candidates.append(_clean_text(element.get("datetime")))
            text = _clean_text(element.get_text(" ", strip=True))
            if text:
                candidates.append(text)

    for candidate in candidates:
        parsed = _parse_date_text(candidate, date_formats)
        if parsed:
            return parsed
    return None


def _extract_category_from_item(item, category_selectors: tuple[str, ...], date_text: str | None) -> str | None:
    for selector in category_selectors:
        for element in item.select(selector):
            text = _clean_text(element.get_text(" ", strip=True))
            if not text:
                continue
            if date_text and text == date_text:
                continue
            if _looks_like_date(text):
                continue
            return text
    return None


def _parse_date_text(text: str, date_formats: tuple[str, ...]) -> str | None:
    cleaned = _clean_text(text)
    if not cleaned:
        return None

    iso_candidate = _parse_iso_date(cleaned)
    if iso_candidate:
        return iso_candidate

    for date_format in date_formats:
        try:
            parsed = datetime.strptime(cleaned, date_format)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _parse_iso_date(text: str) -> str | None:
    candidate = text.replace("Z", "+00:00")
    with contextlib.suppress(ValueError):
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    return None


def _looks_like_date(text: str) -> bool:
    return bool(re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", text)) or bool(
        re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
    )


def _extract_content_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    best_node = None
    best_length = 0

    for selector in selectors:
        if not selector:
            continue
        node = soup.select_one(selector)
        if not node:
            continue
        text_length = len(node.get_text(" ", strip=True))
        if text_length > best_length:
            best_length = text_length
            best_node = node

    if best_node is None:
        return ""

    BeautifulSoup = _load_beautifulsoup()
    fragment = BeautifulSoup(str(best_node), "html.parser")
    for tag in fragment.select("iframe, script, style, noscript"):
        tag.decompose()

    markdown = _html_to_markdown(str(fragment))
    return _strip_embed_markup(markdown)


def _strip_embed_markup(markdown: str) -> str:
    """Remove iframe embed markup that may survive as text inside code samples."""
    stripped = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", markdown, flags=re.IGNORECASE | re.DOTALL)
    stripped = re.sub(r"<iframe\b[^>]*/?>", "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def _html_to_markdown(html: str) -> str:
    """Convert HTML to Markdown using html2text."""
    converter = _load_html2text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0  # don't wrap lines
    return converter.handle(html).strip()


def _discover_listing_links_from_soup(
    soup: BeautifulSoup,
    listing_url: str,
    link_selector: str,
    allowed_url_prefixes: tuple[str, ...],
    excluded_url_substrings: tuple[str, ...],
    max_links: int,
) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()

    for anchor in soup.select(link_selector):
        href = anchor.get("href")
        if not href:
            continue

        candidate = _normalize_url(urljoin(listing_url, str(href)))
        if not candidate or candidate in seen:
            continue
        if allowed_url_prefixes and not any(candidate.startswith(prefix) for prefix in allowed_url_prefixes):
            continue
        if excluded_url_substrings and any(fragment in candidate for fragment in excluded_url_substrings):
            continue

        seen.add(candidate)
        discovered.append(candidate)
        if len(discovered) >= max_links:
            break

    return discovered


def _normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _load_playwright_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("playwright is required for browser-based fetching") from exc
    return sync_playwright


def _load_beautifulsoup():
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("beautifulsoup4 is required for scraping") from exc
    return BeautifulSoup


def _load_html2text():
    try:
        import html2text
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("html2text is required for Markdown conversion") from exc
    return html2text.HTML2Text()


def _fetch_html(url: str, fetcher: str, timeout: int) -> str:
    if fetcher == "playwright":
        playwright = _load_playwright_browser()
        with playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000)
            html = page.content()
            browser.close()
            return html

    response = requests.get(url, timeout=timeout, headers={"User-Agent": "reader/0.1.0"})
    response.raise_for_status()
    return response.text
