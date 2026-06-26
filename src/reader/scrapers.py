from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

from reader.storage import ArticleRecord


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
                author=entry.get("author"),
            )
        )
    return articles


def discover_listing_links(
    listing_url: str,
    link_selector: str = "a[href]",
    allowed_url_prefixes: tuple[str, ...] = (),
    excluded_url_substrings: tuple[str, ...] = (),
    max_links: int = 25,
    timeout: int = 15,
) -> list[str]:
    requests = _load_requests()
    response = requests.get(listing_url, timeout=timeout, headers={"User-Agent": "reader/0.1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
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
    title_selector: str | None = None,
    content_selectors: tuple[str, ...] = (),
    paragraph_selector: str = "article p, main p, p",
    timeout: int = 15,
) -> tuple[str, str, str | None, str | None]:
    requests = _load_requests()
    BeautifulSoup = _load_beautifulsoup()
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "reader/0.1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = _first_text(soup, [title_selector] if title_selector else ["h1", "title"]) or listing_url

    content = ""
    if content_selectors:
        content = _extract_content_from_selectors(soup, content_selectors)
    if not content:
        content = _extract_content_from_selectors(soup, ("article", "main"))
    if not content:
        paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in soup.select(paragraph_selector)]
        content = "\n\n".join(paragraphs).strip()

    summary = content[:500]
    author = _first_meta_content(soup, "author")
    return title, summary, content, author


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


def _first_meta_content(soup: BeautifulSoup, name: str) -> str | None:
    meta = soup.select_one(f'meta[name="{name}"]')
    if meta and meta.get("content"):
        return str(meta["content"]).strip() or None
    return None


def _extract_content_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        if not selector:
            continue
        node = soup.select_one(selector)
        if not node:
            continue
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return ""


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


def _load_beautifulsoup():
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exc:  # pragma: no cover - optional in tests.
        raise RuntimeError("beautifulsoup4 is required for scraping") from exc
    return BeautifulSoup