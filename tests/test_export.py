from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
import unittest

from reader.export import export_datasets
from reader.storage import ArticleRecord, connect, initialize, upsert_article


class ExportTests(unittest.TestCase):
    def test_exports_include_article_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            database = temp_path / "reader.db"
            initialize(database)
            with connect(database) as connection:
                upsert_article(
                    connection,
                    ArticleRecord(
                        source_name="source-a",
                        source_url="https://example.com/feed",
                        url="https://example.com/post-1",
                        title="First title",
                        summary="Summary",
                        content="Full text",
                        published_at="2026-06-26T00:00:00+00:00",
                        category="AI News",
                    ),
                )
                connection.commit()

            csv_path, jsonl_path = export_datasets(database, temp_path / "exports")

            with csv_path.open(encoding="utf-8") as handle:
                csv_rows = list(csv.DictReader(handle))
            with jsonl_path.open(encoding="utf-8") as handle:
                json_rows = [json.loads(line) for line in handle if line.strip()]

            self.assertEqual(len(csv_rows), 1)
            self.assertEqual(len(json_rows), 1)
            self.assertEqual(csv_rows[0]["title"], "First title")
            self.assertEqual(json_rows[0]["content"], "Full text")
            self.assertEqual(csv_rows[0]["category"], "AI News")
            self.assertEqual(json_rows[0]["category"], "AI News")


if __name__ == "__main__":
    unittest.main()