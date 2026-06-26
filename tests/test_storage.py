from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from reader.storage import ArticleRecord, connect, initialize, list_items, set_category, upsert_article


class StorageTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()