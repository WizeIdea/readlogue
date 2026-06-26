from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from reader.db_backup import backup_database
from reader.storage import initialize


class DatabaseBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.source = self.base / "reader.db"
        initialize(self.source)
        with sqlite3.connect(self.source) as connection:
            connection.execute("create table if not exists marker (value text)")
            connection.execute("insert into marker(value) values ('live')")
            connection.commit()
        self.daily_dir = self.base / "daily"
        self.monthly_dir = self.base / "monthly"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_daily_backup_creates_dated_copy(self) -> None:
        backup_day = date(2026, 6, 27)
        daily_path, monthly_path = backup_database(
            self.source,
            self.daily_dir,
            self.monthly_dir,
            today=backup_day,
        )

        self.assertEqual(daily_path, self.daily_dir / "reader-2026-06-27.db")
        self.assertTrue(daily_path.is_file())
        self.assertIsNone(monthly_path)

        with sqlite3.connect(daily_path) as connection:
            row = connection.execute("select value from marker").fetchone()
            self.assertEqual(row[0], "live")

    def test_daily_backup_overwrites_same_day_and_keeps_seven(self) -> None:
        for offset in range(8):
            backup_database(
                self.source,
                self.daily_dir,
                self.monthly_dir,
                today=date(2026, 6, 20 + offset),
            )

        daily_files = sorted(self.daily_dir.glob("reader-*.db"))
        self.assertEqual(len(daily_files), 7)
        self.assertEqual(daily_files[0].name, "reader-2026-06-21.db")
        self.assertEqual(daily_files[-1].name, "reader-2026-06-27.db")

        backup_database(
            self.source,
            self.daily_dir,
            self.monthly_dir,
            today=date(2026, 6, 27),
        )
        self.assertEqual(len(list(self.daily_dir.glob("reader-*.db"))), 7)

    def test_monthly_backup_created_on_first_of_month(self) -> None:
        backup_day = date(2026, 7, 1)
        daily_path, monthly_path = backup_database(
            self.source,
            self.daily_dir,
            self.monthly_dir,
            today=backup_day,
        )

        self.assertEqual(daily_path, self.daily_dir / "reader-2026-07-01.db")
        self.assertEqual(monthly_path, self.monthly_dir / "reader-2026-07.db")
        self.assertTrue(monthly_path.is_file())

    def test_monthly_backup_is_not_recreated_on_same_month(self) -> None:
        backup_day = date(2026, 7, 1)
        _, first_monthly = backup_database(
            self.source,
            self.daily_dir,
            self.monthly_dir,
            today=backup_day,
        )
        assert first_monthly is not None
        first_mtime = first_monthly.stat().st_mtime

        with sqlite3.connect(self.source) as connection:
            connection.execute("update marker set value = 'updated'")
            connection.commit()

        _, second_monthly = backup_database(
            self.source,
            self.daily_dir,
            self.monthly_dir,
            today=backup_day,
        )

        self.assertEqual(second_monthly, first_monthly)
        self.assertEqual(second_monthly.stat().st_mtime, first_mtime)

    def test_missing_database_raises(self) -> None:
        missing = self.base / "missing.db"
        with self.assertRaises(FileNotFoundError):
            backup_database(missing, self.daily_dir, self.monthly_dir)
