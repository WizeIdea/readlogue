from __future__ import annotations

import unittest

from reader.scrapers import discover_listing_links_from_html, parse_listing_articles


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


if __name__ == "__main__":
    unittest.main()