from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from reader.scrapers import (
    _extract_content_from_selectors,
    _extract_hero_image_url,
    _extract_main_content,
    _extract_with_trafilatura,
    _strip_embed_markup,
    _handle_listing_source,
    build_url_ignore_checker,
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
    @patch("reader.scrapers.requests.get")
    def test_parse_rss_feed_normalizes_trailing_slash_urls(
        self, requests_get: Mock, feedparser_mock: Mock
    ) -> None:
        response = Mock()
        response.content = b"<rss></rss>"
        response.status_code = 200
        response.raise_for_status.return_value = None
        requests_get.return_value = response

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

    @patch("reader.scrapers.feedparser")
    @patch("reader.scrapers.requests.get")
    def test_parse_rss_feed_respects_max_entries(
        self, requests_get: Mock, feedparser_mock: Mock
    ) -> None:
        response = Mock()
        response.content = b"<rss></rss>"
        response.status_code = 200
        response.raise_for_status.return_value = None
        requests_get.return_value = response

        def make_entry(index: int) -> Mock:
            entry = Mock()
            entry.get = lambda key, default=None, i=index: {
                "link": f"https://example.com/post-{i}",
                "title": f"Example {i}",
                "summary": "",
                "published": None,
                "updated": None,
                "author": None,
                "tags": [],
            }.get(key, default)
            return entry

        parsed = Mock()
        parsed.entries = [make_entry(index) for index in range(5)]
        feedparser_mock.parse.return_value = parsed

        articles = parse_rss_feed("test-source", "https://example.com/feed.xml", max_entries=2)

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].url, "https://example.com/post-0")
        self.assertEqual(articles[1].url, "https://example.com/post-1")


class RssSourceHandlerTests(unittest.TestCase):
    @patch("reader.scrapers._fetch_article")
    @patch("reader.scrapers.parse_listing_articles")
    def test_listing_applies_default_category(
        self, parse_listing: Mock, fetch_article: Mock
    ) -> None:
        from reader.config import SourceConfig
        from reader.scrapers import ListingArticle
        from reader.storage import ArticleRecord, connect, initialize

        parse_listing.return_value = [
            ListingArticle(
                url="https://oecd.ai/en/wonk/example-post",
                title="Example",
                summary=None,
                published_at=None,
                source_category=None,
            )
        ]
        fetch_article.return_value = ArticleRecord(
            source_name="oecd-ai-wonk",
            source_url="https://oecd.ai/en/wonk",
            url="https://oecd.ai/en/wonk/example-post",
            title="Example",
            summary="Summary",
            content="Full article body with enough words for validation downstream in other tests.",
            published_at=None,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reader.db"
            initialize(db_path)
            with connect(db_path) as connection:
                source = SourceConfig(
                    name="oecd-ai-wonk",
                    kind="listing",
                    url="https://oecd.ai/en/wonk",
                    config_path=Path("config/sources/oecd-ai-wonk.yaml"),
                    settings={"default_category": "Governance and Policy"},
                )
                articles = _handle_listing_source(source, connection)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].category, "Governance and Policy")

    @patch("reader.scrapers._fetch_article")
    @patch("reader.scrapers.parse_rss_feed")
    def test_rss_with_config_profile_and_no_listing_article(
        self, parse_feed: Mock, fetch_article: Mock
    ) -> None:
        from reader.config import SourceConfig
        from reader.scrapers import _handle_rss_source
        from reader.storage import ArticleRecord, connect, initialize

        parse_feed.return_value = [
            ArticleRecord(
                source_name="aisi-blog",
                source_url="https://example.com/feed.xml",
                url="https://www.aisi.gov.uk/blog/first-progress-report",
                title="First Progress Report",
                summary="RSS summary",
                content="RSS summary",
                published_at="2023-09-07",
            )
        ]
        fetch_article.return_value = ArticleRecord(
            source_name="aisi-blog",
            source_url="https://example.com/feed.xml",
            url="https://www.aisi.gov.uk/blog/first-progress-report",
            title="First Progress Report",
            summary="Full article summary",
            content="Full article body with enough words for validation downstream in other tests.",
            published_at=None,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reader.db"
            initialize(db_path)
            with connect(db_path) as connection:
                source = SourceConfig(
                    name="aisi-blog",
                    kind="rss",
                    url="https://example.com/feed.xml",
                    config_path=Path("config/sources/aisi-blog.yaml"),
                    settings={"max_entries": 25, "default_category": "Governance and Policy"},
                )
                articles = _handle_rss_source(source, connection)

        self.assertEqual(len(articles), 1)
        fetch_article.assert_called_once()

    @patch("reader.scrapers._fetch_article")
    @patch("reader.scrapers.parse_rss_feed")
    def test_rss_applies_default_category(self, parse_feed: Mock, fetch_article: Mock) -> None:
        from reader.config import SourceConfig
        from reader.scrapers import _handle_rss_source
        from reader.storage import ArticleRecord, connect, initialize

        parse_feed.return_value = [
            ArticleRecord(
                source_name="importai",
                source_url="https://importai.substack.com/feed",
                url="https://importai.substack.com/p/example",
                title="Import AI 462",
                summary="Digest summary",
                content="Digest summary",
                published_at="2026-06-01",
            )
        ]
        fetch_article.return_value = ArticleRecord(
            source_name="importai",
            source_url="https://importai.substack.com/feed",
            url="https://importai.substack.com/p/example",
            title="Import AI 462",
            summary="Full article summary",
            content="Full article body with enough words for validation downstream in other tests.",
            published_at=None,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reader.db"
            initialize(db_path)
            with connect(db_path) as connection:
                source = SourceConfig(
                    name="importai",
                    kind="rss",
                    url="https://importai.substack.com/feed",
                    settings={"max_entries": 25, "default_category": "Research Digests"},
                )
                articles = _handle_rss_source(source, connection)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].category, "Research Digests")

    @patch("reader.scrapers._fetch_article")
    @patch("reader.scrapers.parse_rss_feed")
    def test_rss_use_feed_content_skips_fetch(self, parse_feed: Mock, fetch_article: Mock) -> None:
        from reader.config import SourceConfig
        from reader.scrapers import _handle_rss_source
        from reader.storage import ArticleRecord, connect, initialize

        digest_body = " ".join(f"word{i}" for i in range(60))
        parse_feed.return_value = [
            ArticleRecord(
                source_name="acm-technews",
                source_url="https://rss.acm.org/technews/technews.xml",
                url="https://example.com/external-story",
                title="External Story",
                summary=digest_body,
                content=digest_body,
                published_at="2026-06-25",
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reader.db"
            initialize(db_path)
            with connect(db_path) as connection:
                source = SourceConfig(
                    name="acm-technews",
                    kind="rss",
                    url="https://rss.acm.org/technews/technews.xml",
                    settings={
                        "max_entries": 25,
                        "default_category": "News Digests",
                        "use_feed_content": True,
                    },
                )
                articles = _handle_rss_source(source, connection)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].content, digest_body)
        self.assertEqual(articles[0].category, "News Digests")
        fetch_article.assert_not_called()

    @patch("reader.scrapers._fetch_article")
    @patch("reader.scrapers.parse_rss_feed")
    def test_rss_continues_after_http_error_on_one_url(
        self, parse_feed: Mock, fetch_article: Mock
    ) -> None:
        import requests

        from reader.config import SourceConfig
        from reader.scrapers import _handle_rss_source
        from reader.storage import ArticleRecord, connect, initialize

        parse_feed.return_value = [
            ArticleRecord(
                source_name="the-batch",
                source_url="https://example.com/feed.xml",
                url="https://example.com/blocked",
                title="Blocked",
                summary="",
                content="",
                published_at=None,
            ),
            ArticleRecord(
                source_name="the-batch",
                source_url="https://example.com/feed.xml",
                url="https://example.com/ok",
                title="OK",
                summary="",
                content="",
                published_at=None,
            ),
        ]
        fetch_article.side_effect = [
            requests.HTTPError("403 Client Error: Forbidden"),
            ArticleRecord(
                source_name="the-batch",
                source_url="https://example.com/feed.xml",
                url="https://example.com/ok",
                title="OK",
                summary="Full article body with enough words for validation downstream.",
                content="Full article body with enough words for validation downstream.",
                published_at=None,
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "reader.db"
            initialize(db_path)
            with connect(db_path) as connection:
                source = SourceConfig(
                    name="the-batch",
                    kind="rss",
                    url="https://example.com/feed.xml",
                )
                articles = _handle_rss_source(source, connection)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].url, "https://example.com/ok")
        self.assertEqual(fetch_article.call_count, 2)


class TrafilaturaExtractionTests(unittest.TestCase):
    def _hf_blog_html(self, *, intro: str, body: str) -> str:
        return f"""
        <html>
          <body>
            <aside>
              <article class="overview-card-wrapper">
                <a href="https://huggingface.co/papers/2502.02649">
                  Paper • 2502.02649 • Published • 36
                </a>
              </article>
            </aside>
            <div class="blog-content prose">
              <div class="not-prose mb-6 font-sans xl:hidden">Upvote 42 +36</div>
              <div class="mb-4"><a href="/blog">Back to Articles</a></div>
              <h1>Cybersecurity and Openness</h1>
              <div>Published April 21, 2026</div>
              <p>{intro}</p>
              <h2>What is Mythos?</h2>
              <p>{body}</p>
            </div>
          </body>
        </html>
        """

    def _article_paragraphs(self) -> str:
        return " ".join(
            [
                "Openness in cybersecurity research helps teams share findings responsibly.",
                "We describe how transparent disclosure supports safer deployment of machine learning systems.",
                "Collaboration across industry and academia reduces duplicated effort on threat modeling.",
                "Practical guidelines help practitioners balance publication with operational security needs.",
                "The community benefits when reproducible benchmarks and datasets are released openly.",
                "Long-term trust depends on clear norms for reporting vulnerabilities in shared infrastructure.",
            ]
        )

    def test_extract_with_trafilatura_excludes_site_chrome(self) -> None:
        body = self._article_paragraphs()
        html = f"""
        <html>
          <body>
            <main>
              <a href="/blog">Back to Articles</a>
              <a href="https://github.com/huggingface/blog">Update on GitHub</a>
              <a href="/login">Upvote 42</a>
              <nav aria-label="Breadcrumb">
                <a href="/">Home</a>
                <a href="/blog">Blog</a>
              </nav>
              <div class="share">
                <a href="https://twitter.com/intent/tweet">Share on x.com</a>
                <a href="https://www.facebook.com/sharer">Facebook</a>
              </div>
              <article>
                <h1>Cybersecurity and Openness</h1>
                <p>{body}</p>
              </article>
            </main>
          </body>
        </html>
        """
        url = "https://huggingface.co/blog/cybersecurity-openness"
        content = _extract_with_trafilatura(html, url)

        self.assertIsNotNone(content)
        assert content is not None
        self.assertIn("Openness in cybersecurity research", content)
        self.assertNotIn("Back to Articles", content)
        self.assertNotIn("Upvote 42", content)
        self.assertNotIn("Share on x.com", content)

    def test_extract_content_from_root_preserves_hf_intro_with_links(self) -> None:
        from reader.scrapers import _extract_content_from_root, _extract_main_content, _load_beautifulsoup

        intro = (
            'Following the announcement of '
            '<a href="https://www.anthropic.com/glasswing">Mythos and Project Glasswing</a>, '
            "institutions throughout the world are grappling with the potential dawn of a new era "
            "of cybersecurity."
        )
        body = self._article_paragraphs()
        html = self._hf_blog_html(intro=intro, body=body)
        soup = _load_beautifulsoup()(html, "html.parser")

        content = _extract_content_from_root(soup, ".blog-content")

        self.assertIn("Following the announcement of", content)
        self.assertIn("Mythos and Project Glasswing", content)
        self.assertIn("institutions throughout the world", content)
        self.assertNotIn("Paper • 2502.02649", content)
        self.assertNotIn("Upvote 42", content)
        self.assertNotIn("Back to Articles", content)

    def test_extract_main_content_prefers_content_root_selector(self) -> None:
        from reader.scrapers import _extract_main_content, _load_beautifulsoup

        intro = (
            'On March 14, we submitted Hugging Face\'s response to the White House Office of '
            'Science and Technology Policy\'s request for information on the '
            '<a href="https://www.whitehouse.gov/plan">White House AI Action Plan</a>. '
            "We took this opportunity to assert the role of open AI systems."
        )
        body = self._article_paragraphs()
        html = self._hf_blog_html(intro=intro, body=body)
        soup = _load_beautifulsoup()(html, "html.parser")
        url = "https://huggingface.co/blog/ai-action-wh-2025"

        with patch("reader.scrapers._extract_with_trafilatura") as trafilatura_mock:
            trafilatura_mock.return_value = (
                "[ Paper • 2502.02649 • Published • 36 ](https://huggingface.co/papers/2502.02649)\n\n"
                "[White House AI Action Plan](https://www.whitehouse.gov/plan). "
                "We took this opportunity to assert the role of open AI systems."
            )
            content = _extract_main_content(
                html,
                url,
                soup,
                content_root_selector=".blog-content",
            )

        trafilatura_mock.assert_not_called()
        self.assertIn("On March 14, we submitted Hugging Face's response", content)
        self.assertIn("White House AI Action Plan", content)
        self.assertNotIn("Paper • 2502.02649", content)

    def test_extract_main_content_falls_back_to_selectors(self) -> None:
        from reader.scrapers import _load_beautifulsoup

        filler = " ".join(f"word{i}" for i in range(60))
        html = f"""
        <html>
          <body>
            <main>
              <p>{filler}</p>
              <p>More article text continues here with additional context and detail.</p>
            </main>
          </body>
        </html>
        """
        soup = _load_beautifulsoup()(html, "html.parser")

        with patch("reader.scrapers._extract_with_trafilatura", return_value=None):
            content = _extract_main_content(
                html,
                "https://example.com/minimal",
                soup,
                content_selectors=("main",),
            )

        self.assertIn("word0", content)
        self.assertGreater(len(content.split()), 10)


class HeroImageExtractionTests(unittest.TestCase):
    def test_extract_hero_image_url_prefers_open_graph(self) -> None:
        from reader.scrapers import _load_beautifulsoup

        soup = _load_beautifulsoup()(
            """
            <html>
              <head>
                <meta property="og:image" content="/images/hero.png" />
              </head>
            </html>
            """,
            "html.parser",
        )
        self.assertEqual(
            _extract_hero_image_url(soup, "https://example.com/article"),
            "https://example.com/images/hero.png",
        )


class UrlIgnoreCheckerTests(unittest.TestCase):
    def test_exact_url_match_ignores_normalized_url(self) -> None:
        checker = build_url_ignore_checker(
            ignored_urls=("https://deepmind.google/blog/introducing-google-antigravity/",),
        )
        self.assertTrue(
            checker("https://deepmind.google/blog/introducing-google-antigravity")
        )

    def test_substring_match(self) -> None:
        checker = build_url_ignore_checker(
            ignored_url_substrings=("introducing-google-antigravity",),
        )
        self.assertTrue(
            checker("https://deepmind.google/blog/introducing-google-antigravity-2-0/")
        )
        self.assertFalse(checker("https://deepmind.google/blog/other-post"))

    def test_non_ignored_url(self) -> None:
        checker = build_url_ignore_checker(ignored_url_substrings=("introducing-google-antigravity",))
        self.assertFalse(checker("https://example.com/article"))


if __name__ == "__main__":
    unittest.main()