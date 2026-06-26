from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from reader.storage import ArticleRecord, connect, existing_item_fingerprints, initialize, item_fingerprint, list_items, list_items_page, set_category, upsert_article


class FingerprintTests(unittest.TestCase):
    def test_canonical_urls_produce_same_fingerprint(self) -> None:
        clean = item_fingerprint("https://example.com/article")
        with_utm = item_fingerprint("https://example.com/article?utm_source=rss&utm_medium=social")
        with_multiple = item_fingerprint("https://example.com/article?foo=bar&fbclid=abc123")
        with_fragment = item_fingerprint("https://example.com/article#section-1")
        self.assertEqual(clean, with_utm)
        self.assertEqual(clean, with_multiple)
        self.assertEqual(clean, with_fragment)

    def test_different_urls_produce_different_fingerprints(self) -> None:
        fp1 = item_fingerprint("https://example.com/article-1")
        fp2 = item_fingerprint("https://example.com/article-2")
        self.assertNotEqual(fp1, fp2)

    def test_whitespace_is_stripped(self) -> None:
        fp1 = item_fingerprint("  https://example.com/article  ")
        fp2 = item_fingerprint("https://example.com/article")
        self.assertEqual(fp1, fp2)


class StorageTests(unittest.TestCase):
    def test_existing_item_fingerprints_ignores_tracking_params(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="First title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    source_category="Technical Research",
                )
                self.assertTrue(upsert_article(connection, article))
                connection.commit()

                # Query with a URL that has tracking params — should still match
                fingerprints = existing_item_fingerprints(
                    connection,
                    ["https://example.com/post-1?utm_source=rss", "https://example.com/post-2"],
                )

                self.assertEqual(len(fingerprints), 1)

    def test_upsert_preserves_single_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="First title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    source_category="Technical Research",
                )
                self.assertTrue(upsert_article(connection, article))
                set_category(connection, 1, "Technical Research")
                connection.commit()
                self.assertFalse(upsert_article(connection, article))
                rows = list_items(connection)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["title"], "First title")
                self.assertEqual(rows[0]["source_category"], "Technical Research")
                self.assertEqual(rows[0]["category"], "Technical Research")


class PaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "reader.db"
        initialize(self.database)
        with connect(self.database) as connection:
            for i in range(10):
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url=f"https://example.com/post-{i}",
                    title=f"Article {i}",
                    summary="Summary",
                    content="Full text",
                    published_at=f"2026-06-{26 - i:02d}T00:00:00+00:00",
                    source_category="Technical Research",
                )
                upsert_article(connection, article)
            connection.commit()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_first_page_returns_correct_count(self) -> None:
        with connect(self.database) as connection:
            items, total = list_items_page(connection, offset=0, limit=5)
            self.assertEqual(len(items), 5)
            self.assertEqual(total, 10)

    def test_second_page_returns_remaining_items(self) -> None:
        with connect(self.database) as connection:
            items, total = list_items_page(connection, offset=5, limit=5)
            self.assertEqual(len(items), 5)
            self.assertEqual(total, 10)

    def test_partial_last_page(self) -> None:
        with connect(self.database) as connection:
            items, total = list_items_page(connection, offset=8, limit=5)
            self.assertEqual(len(items), 2)
            self.assertEqual(total, 10)

    def test_offset_beyond_end_returns_empty(self) -> None:
        with connect(self.database) as connection:
            items, total = list_items_page(connection, offset=20, limit=5)
            self.assertEqual(len(items), 0)
            self.assertEqual(total, 10)

    def test_empty_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_db = Path(temp_dir) / "empty.db"
            initialize(empty_db)
            with connect(empty_db) as connection:
                items, total = list_items_page(connection, offset=0, limit=5)
                self.assertEqual(len(items), 0)
                self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
