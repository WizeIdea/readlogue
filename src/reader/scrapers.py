from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

from reader.storage import ArticleRecord


@dataclass(slots=True)
class ListingArticle:
    url: str
    title: str
    summary: str
    published_at: str | None
    source_category: str | None
    author: str | None = None


HF_API_URL = "https://huggingface.co/api/blog"


def parse_rss_feed(source_name: str, source_url: str) -> list[ArticleRecord]:
    feedparser = _load_feedparser()
    parsed = feedparser.parse(source_url)
    articles: list[ArticleRecord] = []
    for entry in parsed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue
        summary = entry.get("summary", "")
        articles.append(
            ArticleRecord(
                source_name=source_name,
                source_url=source_url,
                url=url,
                title=entry.get("title", url),
                summary=summary,
                content=summary,
                published_at=entry.get("published") or entry.get("updated"),
                source_scraper="rss",
                source_category=_extract_rss_category(entry),
                author=entry.get("author"),
            )
        )
    return articles


def parse_huggingface_tag_articles(tag: str) -> list[ListingArticle]:
    requests = _load_requests()
    all_articles: list[ListingArticle] = []
    seen_links: set[str] = set()
    page = 0

    while True:
        response = requests.get(HF_API_URL, params={"tag": tag, "page": page}, timeout=15, headers={"User-Agent": "reader/0.1.0"})
        response.raise_for_status()
        payload = response.json()
        blogs = payload.get("allBlogs", []) or []
        if not blogs:
            break

        for blog in blogs:
            title = _clean_text(blog.get("title"))
            if not title:
                continue

            url_value = blog.get("url") or f"/blog/{blog.get('slug', '')}"
            link = _normalize_url(f"https://huggingface.co{url_value}" if str(url_value).startswith("/") else str(url_value))
            if link in seen_links:
                continue

            seen_links.add(link)
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

    content = ""
    if content_selectors:
        content = _extract_content_from_selectors(soup, content_selectors)
    if not content:
        content = _extract_content_from_selectors(soup, ("article", "main"))
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
    for selector in selectors:
        if not selector:
            continue
        node = soup.select_one(selector)
        if not node:
            continue
        html = str(node)
        markdown = _html_to_markdown(html)
        if markdown:
            return markdown
    return ""


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


def _load_feedparser():
    try:
        import feedparser
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("feedparser is required for RSS ingestion") from exc
    return feedparser


def _load_requests():
    try:
        import requests
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("requests is required for scraping") from exc
    return requests


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

    requests = _load_requests()
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "reader/0.1.0"})
    response.raise_for_status()
    return response.text
