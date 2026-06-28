from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from reader.storage import (
    ArticleRecord,
    IngestStats,
    SCHEMA_VERSION,
    clear_ingestion_failure,
    connect,
    existing_item_fingerprints,
    existing_raw_html_path,
    initialize,
    ingestion_failures,
    item_fingerprint,
    known_failed_fingerprints,
    list_items,
    list_items_page,
    log_ingestion_failure,
    resolve_raw_html_path,
    save_raw_html,
    set_category,
    upsert_article,
)


class SchemaVersionTests(unittest.TestCase):
    def test_fresh_database_has_current_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                row = connection.execute(
                    "select max(version) as v from schema_version"
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(int(row["v"]), SCHEMA_VERSION)

    def test_initialize_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            initialize(database)  # second call
            with connect(database) as connection:
                rows = connection.execute(
                    "select count(*) as cnt from schema_version"
                ).fetchone()
                self.assertEqual(int(rows["cnt"]), 1)

    def test_migration_does_not_overwrite_existing_data(self) -> None:
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
                upsert_article(connection, article)
                connection.commit()
                row = connection.execute("select id from items").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(int(row["id"]), 1)

    def test_schema_version_table_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                columns = {
                    row[1] for row in connection.execute("pragma table_info(schema_version)")
                }
                self.assertIn("version", columns)
                self.assertIn("applied_at", columns)


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

    def test_upsert_preserves_curation_on_reingest(self) -> None:
        from reader.curation import serialize_curation
        from reader.storage import set_curation

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
                )
                self.assertTrue(upsert_article(connection, article))
                labels = serialize_curation(
                    {
                        "v": 1,
                        "article_types": ["research"],
                        "article_domains": ["LLMs"],
                        "governance_relevance": 5,
                    }
                )
                set_curation(connection, 1, labels)
                connection.commit()

                updated = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="Updated title",
                    summary="Updated summary",
                    content="Updated full text with enough words for validation.",
                    published_at="2026-06-27T00:00:00+00:00",
                )
                self.assertFalse(upsert_article(connection, updated))
                row = connection.execute("select title, curation from items where id = 1").fetchone()
                self.assertEqual(row["title"], "Updated title")
                self.assertEqual(row["curation"], labels)

    def test_existing_raw_html_path_returns_path_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            database = base / "reader.db"
            initialize(database)
            with connect(database) as connection:
                stored_path = save_raw_html("<html>saved</html>", base)
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="Title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    raw_html_path=stored_path,
                )
                upsert_article(connection, article)
                connection.commit()
                self.assertEqual(
                    existing_raw_html_path(connection, "https://example.com/post-1", base),
                    stored_path,
                )

    def test_resolve_raw_html_path_reuses_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            database = base / "reader.db"
            initialize(database)
            stats = IngestStats()
            with connect(database) as connection:
                stored_path = save_raw_html("<html>saved</html>", base)
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="Title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    raw_html_path=stored_path,
                )
                upsert_article(connection, article)
                connection.commit()

                resolved = resolve_raw_html_path(
                    connection,
                    "https://example.com/post-1",
                    "<html>new fetch</html>",
                    base,
                    stats=stats,
                )

                self.assertEqual(resolved, stored_path)
                self.assertEqual(stats.html_reused, 1)
                self.assertEqual(stats.html_written, 0)
                self.assertEqual((base / stored_path).read_text(encoding="utf-8"), "<html>saved</html>")

    def test_upsert_update_preserves_existing_raw_html_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                original = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="Title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    raw_html_path="raw_html/2026-06-26/original.html",
                )
                self.assertTrue(upsert_article(connection, original))
                updated = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url="https://example.com/post-1",
                    title="Updated title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                    raw_html_path="raw_html/2026-06-27/duplicate.html",
                )
                self.assertFalse(upsert_article(connection, updated))
                row = connection.execute(
                    "select raw_html_path from items where fingerprint = ?",
                    (item_fingerprint("https://example.com/post-1"),),
                ).fetchone()
                self.assertEqual(row["raw_html_path"], "raw_html/2026-06-26/original.html")


class IngestionLogTests(unittest.TestCase):
    def test_log_ingestion_failure_upserts_and_increments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                log_ingestion_failure(connection, "source-a", "https://example.com/bad", "too short")
                log_ingestion_failure(connection, "source-a", "https://example.com/bad", "too short again")
                connection.commit()
                row = connection.execute(
                    "select failure_count, message from ingestion_log where article_fingerprint = ?",
                    (item_fingerprint("https://example.com/bad"),),
                ).fetchone()
                self.assertEqual(int(row["failure_count"]), 2)
                self.assertEqual(row["message"], "too short again")

    def test_known_failed_fingerprints_respects_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                url = "https://example.com/repeat-offender"
                for _ in range(2):
                    log_ingestion_failure(connection, "source-a", url, "failed")
                connection.commit()
                self.assertEqual(len(known_failed_fingerprints(connection, min_failures=3)), 0)
                log_ingestion_failure(connection, "source-a", url, "failed")
                connection.commit()
                failed = known_failed_fingerprints(connection, min_failures=3)
                self.assertEqual(failed, {item_fingerprint(url)})

    def test_ingestion_failures_excludes_items_in_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                url = "https://example.com/fixed-later"
                log_ingestion_failure(connection, "source-a", url, "failed")
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url=url,
                    title="Title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                )
                upsert_article(connection, article)
                connection.commit()
                self.assertEqual(len(ingestion_failures(connection)), 0)

    def test_clear_ingestion_failure_on_successful_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                url = "https://example.com/recovered"
                log_ingestion_failure(connection, "source-a", url, "failed")
                article = ArticleRecord(
                    source_name="source-a",
                    source_url="https://example.com/feed",
                    url=url,
                    title="Title",
                    summary="Summary",
                    content="Full text",
                    published_at="2026-06-26T00:00:00+00:00",
                )
                upsert_article(connection, article)
                connection.commit()
                count = connection.execute("select count(*) as cnt from ingestion_log").fetchone()
                self.assertEqual(int(count["cnt"]), 0)

    def test_v2_ingestion_log_migrates_to_unique_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir) / "reader.db"
            initialize(database)
            with connect(database) as connection:
                connection.execute(
                    "delete from schema_version where version >= 3"
                )
                connection.execute("drop table if exists ingestion_log")
                connection.execute(
                    """
                    create table ingestion_log (
                        id integer primary key autoincrement,
                        source_name text not null,
                        article_url text not null,
                        severity text not null default 'warning',
                        message text not null,
                        created_at text not null default current_timestamp
                    )
                    """
                )
                connection.executemany(
                    """
                    insert into ingestion_log(source_name, article_url, message, created_at)
                    values (?, ?, ?, ?)
                    """,
                    [
                        ("source-a", "https://example.com/dup", "first", "2026-06-01T00:00:00+00:00"),
                        ("source-a", "https://example.com/dup", "second", "2026-06-02T00:00:00+00:00"),
                    ],
                )
                connection.commit()
            initialize(database)
            with connect(database) as connection:
                row = connection.execute(
                    """
                    select failure_count, message, article_fingerprint
                    from ingestion_log
                    where article_url = 'https://example.com/dup'
                    """
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(int(row["failure_count"]), 2)
                self.assertEqual(row["message"], "second")
                self.assertEqual(row["article_fingerprint"], item_fingerprint("https://example.com/dup"))


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
