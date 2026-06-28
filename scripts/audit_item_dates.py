#!/usr/bin/env python3
"""Audit items.published_at in a SQLite backup (inventory + live verify)."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from reader.config import load_config, load_listing_profile  # noqa: E402
from reader.scrapers import (  # noqa: E402
    _extract_article_published_at,
    _load_beautifulsoup,
    _normalize_published_at,
    extract_article,
)

CANONICAL_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


def classify_published_at(value: str | None) -> str:
    if value is None or not str(value).strip():
        return "NULL"
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T", text):
        return "ISO"
    if re.match(r"^[A-Za-z]{3}, \d", text):
        return "RFC2822"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return "DATE_ONLY"
    return "OTHER"


def parse_datetime_lenient(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


@dataclass
class ItemRow:
    item_id: int
    source_id: int
    source_name: str
    scraper: str
    url: str
    title: str
    published_at: str | None
    created_at: str | None


def load_items(database: Path) -> list[ItemRow]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT i.id AS item_id, i.source_id, s.name AS source_name, s.scraper,
               i.url, i.title, i.published_at, i.created_at
        FROM items i
        JOIN sources s ON s.id = i.source_id
        ORDER BY s.name, i.url
        """
    ).fetchall()
    return [
        ItemRow(
            item_id=int(row["item_id"]),
            source_id=int(row["source_id"]),
            source_name=str(row["source_name"]),
            scraper=str(row["scraper"]),
            url=str(row["url"]),
            title=str(row["title"]),
            published_at=row["published_at"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def cmd_inventory(args: argparse.Namespace) -> int:
    items = load_items(args.database)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    global_counts: dict[str, int] = defaultdict(int)
    per_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    null_rows: list[dict[str, object]] = []
    non_canonical: list[dict[str, object]] = []
    unparseable: list[dict[str, object]] = []

    for item in items:
        fmt = classify_published_at(item.published_at)
        global_counts[fmt] += 1
        per_source[item.source_name][fmt] += 1

        if fmt == "NULL":
            null_rows.append(asdict(item))
            continue

        if parse_datetime_lenient(item.published_at) is None:
            unparseable.append(asdict(item))
            continue

        if fmt == "ISO" and item.published_at and not CANONICAL_ISO.match(item.published_at.strip()):
            non_canonical.append(asdict(item))

    mixed_sources = [
        name
        for name, counts in per_source.items()
        if sum(1 for key, value in counts.items() if key != "NULL" and value > 0) > 1
    ]

    report = {
        "database": str(args.database),
        "total_items": len(items),
        "global_format_counts": dict(global_counts),
        "per_source": {name: dict(counts) for name, counts in sorted(per_source.items())},
        "mixed_format_sources": mixed_sources,
        "null_count": len(null_rows),
        "non_canonical_iso_count": len(non_canonical),
        "unparseable_count": len(unparseable),
        "null_rows": null_rows,
        "non_canonical_rows": non_canonical,
        "unparseable_rows": unparseable,
    }

    json_path = output_dir / "inventory.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        f"# Date inventory — {args.database.name}",
        "",
        f"Total items: **{len(items)}**",
        "",
        "## Global format counts",
        "",
    ]
    for key in ("ISO", "RFC2822", "DATE_ONLY", "NULL", "OTHER"):
        lines.append(f"- {key}: {global_counts.get(key, 0)}")
    lines.extend(
        [
            "",
            f"- NULL `published_at`: {len(null_rows)}",
            f"- Non-canonical ISO: {len(non_canonical)}",
            f"- Unparseable: {len(unparseable)}",
            f"- Mixed-format sources: {len(mixed_sources)}",
            "",
            "## Per source",
            "",
        ]
    )
    for name in sorted(per_source):
        counts = per_source[name]
        total = sum(counts.values())
        parts = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()) if value)
        lines.append(f"- **{name}** ({total}): {parts}")

    md_path = output_dir / "inventory.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Total: {len(items)} | NULL: {len(null_rows)} | RFC2822: {global_counts.get('RFC2822', 0)}")
    return 0


def _source_profile_map(config_path: Path) -> dict[str, object | None]:
    config = load_config(config_path)
    profiles: dict[str, object | None] = {}
    for source in config.sources:
        if not source.enabled:
            continue
        profiles[source.name] = (
            load_listing_profile(source.config_path) if source.config_path else None
        )
    return profiles


def cmd_verify(args: argparse.Namespace) -> int:
    items = load_items(args.database)
    if args.source:
        items = [item for item in items if item.source_name == args.source]
    profiles = _source_profile_map(args.config)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "html"
    if args.cache_html:
        cache_dir.mkdir(parents=True, exist_ok=True)

    failures: list[dict[str, object]] = []
    total = len(items)

    for index, item in enumerate(items, start=1):
        print(f"Checking {index}/{total}: {item.source_name} — {item.url[:70]}…", flush=True)
        profile = profiles.get(item.source_name)
        stored = _normalize_published_at(item.published_at)
        extracted: str | None = None
        error: str | None = None

        try:
            fetcher = getattr(profile, "fetcher", "requests") if profile is not None else "requests"
            timeout = int(getattr(profile, "timeout", 15)) if profile is not None else 15
            playwright_wait = None
            if profile is not None:
                playwright_wait = profile.playwright_article_wait_selector or profile.playwright_wait_selector

            _title, _summary, _content, _author, raw_html, _hero = extract_article(
                item.url,
                fetcher=fetcher,
                title_selector=getattr(profile, "title_selector", None) if profile else None,
                content_selectors=getattr(profile, "content_selectors", ()) if profile else (),
                content_root_selector=getattr(profile, "content_root_selector", None) if profile else None,
                paragraph_selector=getattr(profile, "paragraph_selector", "article p, main p, p")
                if profile
                else "article p, main p, p",
                timeout=timeout,
                playwright_wait_selector=playwright_wait,
            )
            if args.cache_html:
                slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", item.url)[:120]
                (cache_dir / f"{item.item_id}_{slug}.html").write_text(raw_html, encoding="utf-8")

            soup = _load_beautifulsoup()(raw_html, "html.parser")
            extracted = _extract_article_published_at(raw_html, item.url, soup, profile)
            extracted = _normalize_published_at(extracted)
        except Exception as exc:  # noqa: BLE001 — audit report
            error = str(exc)

        status = "ok"
        if error:
            status = "fetch_error"
        elif extracted is None:
            status = "no_extracted_date"
        elif stored is None:
            status = "stored_null"
        elif stored != extracted:
            stored_dt = parse_datetime_lenient(stored)
            extracted_dt = parse_datetime_lenient(extracted)
            if stored_dt and extracted_dt and stored_dt.date() == extracted_dt.date():
                status = "time_mismatch"
            else:
                status = "date_mismatch"

        if status != "ok":
            failures.append(
                {
                    "status": status,
                    "source_name": item.source_name,
                    "url": item.url,
                    "stored": stored,
                    "extracted": extracted,
                    "error": error,
                }
            )

        if args.delay > 0 and index < total:
            time.sleep(args.delay)

    report = {
        "database": str(args.database),
        "checked": total,
        "failures": failures,
        "failure_count": len(failures),
    }
    json_path = output_dir / "verify.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Checked {total} | failures {len(failures)}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=REPO_ROOT / "reader-2026-06-28.db",
        help="SQLite backup path",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "config.yaml",
        help="Main config for source profiles",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "date_audit",
        help="Report output directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("inventory", help="Offline scan of every row")

    verify_parser = subparsers.add_parser("verify", help="Re-fetch every URL and compare dates")
    verify_parser.add_argument("--source", help="Limit to one source name")
    verify_parser.add_argument("--delay", type=float, default=0.25, help="Seconds between fetches")
    verify_parser.add_argument("--cache-html", action="store_true", help="Cache fetched HTML")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.database.is_file():
        print(f"Database not found: {args.database}", file=sys.stderr)
        return 2
    if args.command == "inventory":
        return cmd_inventory(args)
    if args.command == "verify":
        return cmd_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
