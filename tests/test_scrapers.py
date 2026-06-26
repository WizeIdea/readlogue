from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from reader.scrapers import (
    discover_listing_links_from_html,
    parse_huggingface_tag_articles,
    parse_listing_articles,
)


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

    @patch("reader.scrapers._load_requests")
    def test_parse_huggingface_tag_articles_uses_api_tag_data(self, load_requests: Mock) -> None:
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
        load_requests.return_value.get.return_value = response

        articles = parse_huggingface_tag_articles("ethics")

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "HF Ethics Post")
        self.assertEqual(articles[0].source_category, "Ethics")
        self.assertEqual(articles[0].published_at, "2026-06-24T12:00:00+00:00")
        self.assertEqual(articles[0].url, "https://huggingface.co/blog/hf-ethics-post")


if __name__ == "__main__":
    unittest.main()