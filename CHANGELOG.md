# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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