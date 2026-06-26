from __future__ import annotations

import unittest

from reader.scrapers import discover_listing_links_from_html


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


if __name__ == "__main__":
    unittest.main()