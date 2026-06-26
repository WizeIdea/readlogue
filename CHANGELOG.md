# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-06-26

### Added
- Markdown conversion: extracted article content is now converted from HTML to Markdown via `html2text`, preserving structural signal (headings, bold, links, lists, code) for ML training
- `html2text>=2024.2` added to project dependencies
- `_html_to_markdown()` helper in `scrapers.py` with sensible defaults (links/images preserved, no line wrapping)
- Streamlit UI now renders article summaries as Markdown via `st.markdown()` for proper heading/link display

### Changed
- `_extract_content_from_selectors()` now converts selected HTML nodes to Markdown instead of stripping to plain text
- Fallback paragraph extraction also converts to Markdown by wrapping `<p>` elements in a `<div>` before conversion
- `items.content` and `items.summary` now contain Markdown-formatted text rather than plain text

## [0.5.0] - 2026-06-26

### Added
- Raw HTML storage: `extract_article()` now returns the raw HTML as a 5th element, which is saved to `data/raw_html/YYYY-MM-DD/<uuid>.html` via `save_raw_html()`
- `raw_html_path` column added to the `items` table (schema version bumped to 2) with automatic migration
- `raw_html_path` field on `ArticleRecord` dataclass for persistence
- `save_raw_html()` helper in `storage.py` — writes raw HTML to date-partitioned files
- `ingest()` now accepts an optional `raw_html_dir` parameter (defaults to `data/`) for pointing at the data-repo checkout
- Dual-repo GitHub Actions workflow: checks out `WizeIdea/readlogue_data_2026` alongside the main repo and commits new raw HTML files via `stefanzweifel/git-auto-commit-action@v5`

### Changed
- `extract_article()` return type expanded from 4-tuple to 5-tuple `(title, summary, content, author, raw_html)`
- All internal calls to `extract_article()` updated to unpack the 5th element
- `upsert_article()` persists `raw_html_path` on insert and preserves existing paths on update
- `.github/workflows/ingest.yml` now uses dual-checkout pattern with data-repo deploy key

## [0.4.0] - 2026-06-26

### Added
- Content validation module (`src/reader/validation.py`) with three quality checks:
  - Minimum word count (default 50) — catches empty/truncated content
  - HTML markup residue detection — flags when selectors return raw tags instead of text
  - Lexical diversity check — flags repetitive boilerplate or garbage text (< 20% unique words)
- `ingestion_log` table in the SQLite schema to persist validation failures
- `log_ingestion_failure()` and `recent_ingestion_issues()` storage helpers
- Ingestion failure warning banner in the Streamlit UI showing per-source skips and reasons
- Validation test suite (`tests/test_validation.py`) with 11 unit tests

### Changed
- Ingestion no longer raises `RuntimeError` on bad content — bad articles are skipped and logged, remaining articles continue
- All article extraction paths (RSS, API tag, listing, and direct) now pass through `validate_content()`
- `_fetch_article()` helper refactored to accept `source_url` parameter explicitly

## [0.3.0] - 2026-06-26

### Added
- Schema versioning system with `schema_version` table and migration support (`SCHEMA_VERSION = 1`)
- Paginated article listing in the Streamlit UI (25 articles per page with Previous/Next buttons)
- Test coverage for schema versioning, pagination, and URL fingerprinting

### Changed
- URL fingerprints now strip query parameters and fragments before hashing, preventing duplicates from tracking parameters (e.g., `?utm_source=rss`, `?fbclid=...`)
- `initialize()` now runs migrations against a version-tracked schema rather than ad-hoc column checks
- `_ensure_column()` now operates on an open connection instead of opening its own

## [0.2.0] - 2026-06-26

### Added
- GitHub Actions ingest workflow (`.github/workflows/ingest.yml`)
- HuggingFace blog API scraper (`parse_huggingface_tag_articles`)
- BAIR blog listing scraper
- Multiple source configs:
  - Anthropic Research
  - BAIR Blog
  - HuggingFace Ethics
  - HuggingFace Research
  - Stanford HAI News

### Changed
- Replaced Selenium with Playwright for browser-based fetching

## [0.1.0] - 2026-06-26

### Added
- Initial project scaffold
- RSS feed parser (`parse_rss_feed`)
- HTML listing scraper with configurable selectors (`parse_listing_articles`, `discover_listing_links`)
- Article content extractor (`extract_article`)
- SQLite storage with upsert logic
- Streamlit UI with read/like/dislike/category controls
- CSV and JSONL export
- YAML-based configuration for sources and listing profiles
- Test suite for scrapers, storage, and export