from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from reader.scrapers import (
    _extract_content_from_selectors,
    _strip_embed_markup,
    discover_listing_links_from_html,
    parse_huggingface_tag_articles,
    parse_listing_articles,
    parse_rss_feed,
)
from reader.validation import validate_content


class ScraperDiscoveryTests(unittest.TestCase):
    def test_discover_listing_links_from_html_filters_and_dedupes(self) -> None:
        html = """
        <html>
          <body>
            <a href="/news/alpha">Alpha</a>
            <a href="https://example.com/ignore">Ignore</a>
            <a href="/news/alpha">Duplicate</a>
            <a href="/news/beta">Beta</a>
          </body>
        </html>
        """

        links = discover_listing_links_from_html(
            html,
            "https://hai.stanford.edu/news",
            allowed_url_prefixes=("https://hai.stanford.edu/news/",),
        )

        self.assertEqual(
            links,
            [
                "https://hai.stanford.edu/news/alpha",
                "https://hai.stanford.edu/news/beta",
            ],
        )

    def test_parse_listing_articles_extracts_date_and_category(self) -> None:
        html = """
        <html>
          <body>
            <a href="/research/example-1">
              <article>
                <h3>Example Research Story</h3>
                <span class="caption bold">Technical Research</span>
                <time datetime="2026-06-24T16:30:01+00:00">Jun 24, 2026</time>
                <p>Summary text for the first example article.</p>
              </article>
            </a>
          </body>
        </html>
        """

        articles = parse_listing_articles(
            "https://www.anthropic.com/research",
            html=html,
            item_selector="a[href*='/research/']",
            link_selector="a[href*='/research/']",
            title_selectors=("h3", "h2", "h1"),
            date_selectors=("time",),
            date_formats=("%b %d, %Y", "%Y-%m-%d"),
            category_selectors=("span.caption.bold",),
        )

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Example Research Story")
        self.assertEqual(articles[0].source_category, "Technical Research")
        self.assertEqual(articles[0].published_at, "2026-06-24T16:30:01+00:00")

    @patch("reader.scrapers.requests")
    def test_parse_huggingface_tag_articles_uses_api_tag_data(self, requests_mock: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "allBlogs": [
                {
                    "title": "HF Ethics Post",
                    "url": "/blog/hf-ethics-post",
                    "publishedAt": "2026-06-24T12:00:00Z",
                    "tags": ["Ethics", "Research"],
                    "description": "Ethics-focused post",
                }
            ],
            "numTotalItems": 1,
        }
        response.raise_for_status.return_value = None
        requests_mock.get.return_value = response

        articles = parse_huggingface_tag_articles("ethics")

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "HF Ethics Post")
        self.assertEqual(articles[0].source_category, "Ethics")
        self.assertEqual(articles[0].published_at, "2026-06-24T12:00:00+00:00")
        self.assertEqual(articles[0].url, "https://huggingface.co/blog/hf-ethics-post")

    @patch("reader.scrapers.requests")
    def test_parse_huggingface_tag_articles_stops_on_duplicate_page(self, requests_mock: Mock) -> None:
        blog = {
            "title": "HF Ethics Post",
            "url": "/blog/hf-ethics-post",
            "publishedAt": "2026-06-24T12:00:00Z",
            "tags": ["Ethics"],
            "description": "Ethics-focused post",
        }
        response = Mock()
        response.json.return_value = {
            "allBlogs": [blog],
            "numTotalItems": 22,
        }
        response.raise_for_status.return_value = None
        requests_mock.get.return_value = response

        articles = parse_huggingface_tag_articles("ethics")

        self.assertEqual(len(articles), 1)
        self.assertEqual(requests_mock.get.call_count, 2)

    def test_extract_content_from_selectors_prefers_longest_node(self) -> None:
        from bs4 import BeautifulSoup

        html = """
        <html>
          <body>
            <article><p>Short teaser card.</p></article>
            <main>
              <p>This is the full article body with substantially more content.</p>
              <p>It includes multiple paragraphs of real article text for extraction.</p>
              <p>Additional paragraphs ensure the main region is clearly the richest node.</p>
            </main>
          </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_content_from_selectors(soup, ("article", "main"))

        self.assertIn("full article body", content)
        self.assertNotIn("Short teaser card", content)
        self.assertGreater(len(content.split()), 10)

    def test_extract_content_strips_iframe_before_markdown(self) -> None:
        from bs4 import BeautifulSoup

        filler = " ".join(f"word{i}" for i in range(60))
        html = f"""
        <html>
          <body>
            <main>
              <p>{filler}</p>
              <iframe src="https://example.com/embed"></iframe>
              <p>More article text continues here with additional context and detail.</p>
            </main>
          </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        content = _extract_content_from_selectors(soup, ("main",))
        quality = validate_content("Title", content, "https://example.com/a", "test-source")

        self.assertNotIn("<iframe", content.lower())
        self.assertTrue(quality.is_valid)

    def test_strip_embed_markup_removes_iframe_text(self) -> None:
        markdown = "Example embed:\n<iframe src=\"https://example.com\"></iframe>\nMore text."
        cleaned = _strip_embed_markup(markdown)
        self.assertNotIn("<iframe", cleaned.lower())
        self.assertIn("More text", cleaned)

    @patch("reader.scrapers.feedparser")
    def test_parse_rss_feed_normalizes_trailing_slash_urls(self, feedparser_mock: Mock) -> None:
        entry = Mock()
        entry.get = lambda key, default=None: {
            "link": "https://example.com/post/",
            "title": "Example",
            "summary": "",
            "published": "2026-06-26T00:00:00+00:00",
            "updated": None,
            "author": None,
            "tags": [],
        }.get(key, default)

        parsed = Mock()
        parsed.entries = [entry]
        feedparser_mock.parse.return_value = parsed

        articles = parse_rss_feed("test-source", "https://example.com/feed.xml")

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].url, "https://example.com/post")


if __name__ == "__main__":
    unittest.main()