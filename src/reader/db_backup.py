from __future__ import annotations

import logging
import sqlite3
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

DAILY_BACKUP_PREFIX = "reader-"
DAILY_BACKUP_SUFFIX = ".db"
MONTHLY_BACKUP_PREFIX = "reader-"
MONTHLY_BACKUP_SUFFIX = ".db"
DAILY_RETENTION = 7


def _daily_backup_name(day: date) -> str:
    return f"{DAILY_BACKUP_PREFIX}{day.isoformat()}{DAILY_BACKUP_SUFFIX}"


def _monthly_backup_name(day: date) -> str:
    return f"{MONTHLY_BACKUP_PREFIX}{day:%Y-%m}{MONTHLY_BACKUP_SUFFIX}"


def _copy_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)


def _rotate_daily_backups(daily_dir: Path, *, keep: int = DAILY_RETENTION) -> None:
    daily_files = sorted(daily_dir.glob(f"{DAILY_BACKUP_PREFIX}*{DAILY_BACKUP_SUFFIX}"))
    while len(daily_files) > keep:
        daily_files[0].unlink()
        daily_files = daily_files[1:]


def backup_database(
    source: Path,
    daily_dir: Path,
    monthly_dir: Path,
    *,
    today: date | None = None,
    daily_retention: int = DAILY_RETENTION,
) -> tuple[Path | None, Path | None]:
    """Copy the live database to daily and optional monthly backup locations."""
    if not source.is_file():
        raise FileNotFoundError(f"Database not found: {source}")

    backup_day = today or date.today()
    daily_path = daily_dir / _daily_backup_name(backup_day)
    _copy_database(source, daily_path)
    logger.info("Daily DB backup written: %s", daily_path)
    _rotate_daily_backups(daily_dir, keep=daily_retention)

    monthly_path: Path | None = None
    if backup_day.day == 1:
        monthly_path = monthly_dir / _monthly_backup_name(backup_day)
        if not monthly_path.exists():
            _copy_database(source, monthly_path)
            logger.info("Monthly DB backup written: %s", monthly_path)

    return daily_path, monthly_path
