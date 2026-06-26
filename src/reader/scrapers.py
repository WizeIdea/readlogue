from __future__ import annotations

import feedparser
import requests
from bs4 import BeautifulSoup

from reader.storage import ArticleRecord


def parse_rss_feed(source_name: str, source_url: str) -> list[ArticleRecord]:
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
                author=entry.get("author"),
            )
        )
    return articles


def extract_article(url: str, timeout: int = 15) -> tuple[str, str, str | None, str | None]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "reader/0.1.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = _first_text(soup, ["h1", "title"]) or url
    paragraphs = [paragraph.get_text(" ", strip=True) for paragraph in soup.select("article p, main p, p")]
    content = "\n\n".join(paragraphs).strip()
    summary = content[:500]
    return title, summary, content, None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text
    return ""