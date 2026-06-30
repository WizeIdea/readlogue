from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from reader.storage import (
    ArticleRecord,
    IngestStats,
    SyncDelta,
    clear_ingestion_failure,
    connect,
    initialize,
    item_fingerprint,
    log_ingestion_failure,
    upsert_article,
)
from reader.supabase_sync import (
    fetch_runtime_ignores,
    hydrate_sqlite_from_supabase,
    is_supabase_configured,
    sync_sqlite_to_supabase,
)


class SupabaseConfigTests(unittest.TestCase):
    def test_is_supabase_configured_false_when_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_supabase_configured())

    def test_is_supabase_configured_true_when_set(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "service-key",
            },
            clear=True,
        ):
            self.assertTrue(is_supabase_configured())


class SupabaseSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "reader.db"
        initialize(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_hydrate_loads_items_into_sqlite(self, _configured: MagicMock, fetch_all: MagicMock) -> None:
        fetch_all.side_effect = [
            [
                {
                    "id": 1,
                    "name": "source-a",
                    "source_url": "https://example.com/feed",
                    "scraper": "requests",
                    "created_at": "2026-06-27T00:00:00+00:00",
                }
            ],
            [
                {
                    "id": 10,
                    "source_id": 1,
                    "fingerprint": "abc123",
                    "url": "https://example.com/post-1",
                    "title": "Title",
                    "summary": "Summary",
                    "content": "Body",
                    "author": None,
                    "published_at": "2026-06-27T00:00:00+00:00",
                    "source_category": None,
                    "category": None,
                    "read_at": None,
                    "rating": None,
                    "raw_html_path": "raw_html/2026-06-27/file.html",
                    "hero_image_url": "https://example.com/hero.jpg",
                    "curation": {"v": 1, "article_types": ["research"]},
                    "created_at": "2026-06-27T00:00:00+00:00",
                    "updated_at": "2026-06-27T00:00:00+00:00",
                }
            ],
            [],
            [],
        ]

        with connect(self.database) as connection:
            hydrate_sqlite_from_supabase(connection)
            row = connection.execute("select count(*) as cnt from items").fetchone()
            self.assertEqual(int(row["cnt"]), 1)
            curation = connection.execute("select curation from items where id = 10").fetchone()
            self.assertIn("research", curation["curation"])

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync._client")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_sync_empty_delta_makes_no_upserts(
        self,
        _configured: MagicMock,
        client_factory: MagicMock,
        fetch_all: MagicMock,
    ) -> None:
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.upsert.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        client_factory.return_value = client

        with connect(self.database) as connection:
            sync_sqlite_to_supabase(connection, SyncDelta())

        table.upsert.assert_not_called()
        table.delete.assert_not_called()
        fetch_all.assert_not_called()

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync._client")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_sync_upserts_dirty_rows_only(
        self,
        _configured: MagicMock,
        client_factory: MagicMock,
        fetch_all: MagicMock,
    ) -> None:
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.upsert.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        client_factory.return_value = client
        fetch_all.return_value = [{"id": 99, "name": "source-a"}]

        stats = IngestStats()
        with connect(self.database) as connection:
            article = ArticleRecord(
                source_name="source-a",
                source_url="https://example.com/feed",
                url="https://example.com/post-1",
                title="Title",
                summary="Summary",
                content="Body",
                published_at="2026-06-27T00:00:00+00:00",
            )
            upsert_article(connection, article, stats=stats)
            sync_sqlite_to_supabase(connection, stats.sync_delta)

        self.assertEqual(table.upsert.call_count, 2)
        client.table.assert_any_call("sources")
        client.table.assert_any_call("items")

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync._client")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_sync_failure_add_and_delete(
        self,
        _configured: MagicMock,
        client_factory: MagicMock,
        _fetch_all: MagicMock,
    ) -> None:
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.upsert.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        client_factory.return_value = client

        url = "https://example.com/bad"
        fingerprint = item_fingerprint(url)
        stats = IngestStats()

        with connect(self.database) as connection:
            log_ingestion_failure(connection, "source-a", url, "too short", stats=stats)
            sync_sqlite_to_supabase(connection, stats.sync_delta)

        client.table.assert_any_call("ingestion_log")
        table.upsert.assert_called_once()
        table.delete.assert_not_called()

        table.reset_mock()
        stats = IngestStats()
        with connect(self.database) as connection:
            clear_ingestion_failure(connection, url, stats=stats)
            sync_sqlite_to_supabase(connection, stats.sync_delta)

        table.upsert.assert_not_called()
        table.delete.assert_called_once()
        table.eq.assert_called_once_with("article_fingerprint", fingerprint)

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync._client")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_sync_upserts_items(
        self,
        _configured: MagicMock,
        client_factory: MagicMock,
        fetch_all: MagicMock,
    ) -> None:
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table
        table.select.return_value = table
        table.range.return_value = table
        table.upsert.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        client_factory.return_value = client
        fetch_all.return_value = [{"id": 99, "name": "source-a"}]

        stats = IngestStats()
        with connect(self.database) as connection:
            article = ArticleRecord(
                source_name="source-a",
                source_url="https://example.com/feed",
                url="https://example.com/post-1",
                title="Title",
                summary="Summary",
                content="Body",
                published_at="2026-06-27T00:00:00+00:00",
            )
            upsert_article(connection, article, stats=stats)
            sync_sqlite_to_supabase(connection, stats.sync_delta)

        client.table.assert_any_call("items")
        table.upsert.assert_called()

    @patch("reader.supabase_sync._fetch_all")
    @patch("reader.supabase_sync.is_supabase_configured", return_value=True)
    def test_fetch_runtime_ignores_splits_kinds(self, _configured: MagicMock, fetch_all: MagicMock) -> None:
        fetch_all.return_value = [
            {"kind": "exact", "value": "https://example.com/skip"},
            {"kind": "substring", "value": "bad-article"},
        ]
        exact, substrings = fetch_runtime_ignores()
        self.assertEqual(exact, ("https://example.com/skip",))
        self.assertEqual(substrings, ("bad-article",))

    @patch("reader.supabase_sync.is_supabase_configured", return_value=False)
    def test_fetch_runtime_ignores_empty_when_unconfigured(self, _configured: MagicMock) -> None:
        exact, substrings = fetch_runtime_ignores()
        self.assertEqual(exact, ())
        self.assertEqual(substrings, ())
