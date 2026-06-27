# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2026-06-27

### Added
- [`components/pagination.tsx`](apps/web/src/components/pagination.tsx) — clickable page numbers plus Previous / Next

### Changed
- Dashboard compact layout: left sidebar (hero image, source meta, icon actions); right column (title, always-visible summary)
- Read articles styled via `.article-row--read` only (page background, muted title); unread rows unchanged
- Curation controls use icon buttons (thumbs up/down, mail read/unread) instead of text labels
- Removed collapsible summary and Read/Unread text from article rows
- Tighter vertical spacing across article list and main content area

## [1.2.0] - 2026-06-27

### Added
- [Trafilatura](https://github.com/adbar/trafilatura) as primary article body extractor for ML-ready Markdown (`items.content`)
- `_extract_with_trafilatura()`, `_extract_main_content()` — Trafilatura first; CSS selector + html2text fallback when extraction is empty or too short
- Tests with HF-style chrome fixtures verifying nav/share text is excluded from content
- `apps/web/` — Next.js dashboard: Supabase email/password auth, paginated article list with hero thumbnails, like/dislike/read/category curation, ingestion failure banner with ignore and dismiss actions
- Server Actions for curation writes via service role; API routes `POST /api/ignore` and `POST /api/dismiss-failure`
- Dual light/dark theme via CSS variables in `apps/web/src/app/globals.css` (`prefers-color-scheme`, no toggle)
- Minimal shadcn-style UI primitives (button, select, alert, collapsible) styled from `globals.css`

### Changed
- `extract_article()` uses Trafilatura before legacy `article`/`main` html2text conversion
- Trafilatura metadata title used when available

## [1.1.0] - 2026-06-27

### Added
- Supabase migrations `002`–`004`: authenticated read RLS policies, `ignored_urls` table, `hero_image_url` column on `items`
- `hero_image_url` on ingested items — extracted from Open Graph / Twitter meta tags during article fetch (SQLite schema v4)
- `_extract_hero_image_url()` in `scrapers.py`; `extract_article()` now returns a 6-tuple including the image URL
- `fetch_runtime_ignores()` in `supabase_sync.py` — loads UI-managed ignore rules from Supabase `ignored_urls`
- Tests for hero image extraction and runtime ignore fetch

### Changed
- Ingest merges YAML `ignored_urls` / `ignored_url_substrings` with Supabase `ignored_urls` when Supabase is configured
- `supabase_sync` hydrate/sync includes `hero_image_url`
- [`supabase/README.md`](supabase/README.md) documents migrations 002–004 and Phase 2 schema additions

## [1.0.0] - 2026-06-27

### Added
- Supabase Postgres as production index: schema in `supabase/migrations/001_initial_schema.sql`
- `src/reader/supabase_sync.py` — hydrate scratch SQLite from Supabase before ingest; sync back after
- `supabase/README.md` with setup, secrets, and fresh-bootstrap cutover (including clearing data-repo `raw_html/`)

### Changed
- GitHub Actions ingest requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`; no longer commits `data/reader.db` to main
- `data/reader.db` gitignored — ephemeral scratch file on GHA runners only
- Local dev without Supabase env vars continues to use SQLite only

## [0.4.7] - 2026-06-27

### Added
- `ingestion_log` upsert: one row per article URL with `failure_count` and `last_seen_at` (schema v3 migration)
- Auto-skip re-fetch when `failure_count >= auto_skip_failure_threshold` (default 3); `skipped_known_failure` in ingestion summary
- Streamlit red error banner for ingestion failures (from first failure) with per-URL **Ignore** button that appends to config
- `append_ignored_url()` config helper and `git_sync.commit_config_files()` stub for optional config push when `READLOGUE_GITHUB_TOKEN` is set

### Changed
- Successful ingest clears matching `ingestion_log` rows

## [0.4.6] - 2026-06-27

### Added
- Configurable URL ignore list: `ignored_urls` and `ignored_url_substrings` in config (plus optional per-source overrides in `settings`) skip known-bad articles before fetch
- `skipped_ignored` counter in ingestion summary

### Changed
- Per-article fetch log uses `accepted=True/False` instead of `valid=True/False` for clarity

## [0.4.5] - 2026-06-27

### Fixed
- Data-repo auto-commit: use `db_backups/**/*.db` with `disable_globbing: true` so daily DB backups are staged and pushed (multiline pattern with empty monthly glob was skipping backup files)

### Changed
- Backup step logs written paths at INFO and lists `db_backups/daily/` and `db_backups/monthly/` after copy for GHA verification

## [0.4.4] - 2026-06-27

### Fixed
- RSS ingestion capped at `max_entries` (default 25) so feeds like DeepMind (100+ items) no longer trigger a full historical backfill on every first run
- Hugging Face tag sources now respect `max_links` from their source profile

### Changed
- RSS handler logs feed size, skip count, and pending fetch count at INFO before downloading article pages
- GitHub Actions ingest step enables INFO logging so per-article fetch timing is visible in workflow logs
- Empty JavaScript-rendered pages (e.g. DeepMind Antigravity stubs) fail fast without running the full extraction pipeline

## [0.4.3] - 2026-06-27

### Added
- Live SQLite index `data/reader.db` is tracked in the main repository and committed by GitHub Actions after each ingest
- `src/reader/db_backup.py`: daily DB backups (7-day rotation) and permanent monthly backups (on the 1st) written to the data repository under `db_backups/daily/` and `db_backups/monthly/`
- GitHub Actions: `contents: write` permission, post-ingest backup step, main-repo commit for `data/reader.db`, expanded data-repo commit for HTML and DB backups

### Changed
- Storage split documented: live DB on main repo; raw HTML and DB backups on `readlogue_data_2026`
- `.gitignore` now allows only `data/reader.db` under `data/` (other `data/` contents remain ignored)

## [0.4.2] - 2026-06-27

### Fixed
- Raw HTML storage: skip writing a new file when the article already has `raw_html_path` in SQLite and the file exists on disk; reuse the existing path instead
- `upsert_article` update path now preserves the first captured `raw_html_path` instead of overwriting it with a duplicate file
- RSS ingestion: normalize feed entry URLs with `_normalize_url()` so trailing-slash drift does not re-fetch and duplicate HTML

### Added
- In-run dedup: add each fetched fingerprint to the handler's in-memory set to avoid duplicate fetches within the same source batch
- Ingestion summary counters logged at INFO (`skipped_existing`, `fetched`, `validation_failed`, `html_written`, `html_reused`, `new_db_rows`)
- GitHub Actions: restrict data-repo auto-commit to `raw_html/**/*.html`

## [0.4.1] - 2026-06-27

### Fixed
- Content validation: HTML residue check now flags only known HTML5 tag names (whitelist), ignoring pseudo-tags like `<bash>`, `<mask>`, and `</think>` that appear in HuggingFace and Anthropic article prose
- Content validation: fenced Markdown code blocks are excluded from the HTML residue scan
- Content extraction: strip `iframe`, `script`, `style`, and `noscript` nodes before Markdown conversion; also strip iframe markup left as text in code samples

### Added
- Per-article fetch timing logged at INFO in `_fetch_article()` for diagnosing slow ingestion runs in GitHub Actions

## [0.4.0] - 2026-06-27

### Fixed
- Content extraction: `_extract_content_from_selectors()` now picks the selector node with the most text instead of the first match, fixing DeepMind and similar sites where a small `<article>` teaser was chosen over `<main>`
- Anthropic sources: switched listing profiles from Playwright to `requests` because Anthropic pages are server-rendered; fixes empty listing discovery and ~47-word partial article bodies in GitHub Actions
- Content validation: reduced HTML residue false positives by ignoring Markdown inline code, angle-bracket URLs (`<https://...>`), and PascalCase pseudo-tags like `<Parallel>`
- HuggingFace API ingestion: stop pagination when a page returns no new URLs and cap pages at 10, preventing infinite loops that caused 429 errors
- BAIR blog: exclude `/blog/subscribe` (without trailing slash) from listing discovery

## [0.3.9] - 2026-06-27

### Fixed
- Raw HTML storage: changed `save_raw_html()` to use ingestion date (current UTC) instead of article publication date for folder structure, ensuring all articles from a single run are grouped together

## [0.3.8] - 2026-06-27

### Fixed
- Config parsing: quoted CSS attribute selectors in `config/sources/stanford-hai-news.yaml` to prevent YAML from parsing square brackets as list syntax instead of CSS selector strings
- Added debug logging for content extraction failures to help diagnose why articles are being skipped

## [0.3.7] - 2026-06-27

### Fixed
- Content validation: fixed HTML residue regex false positive that incorrectly flagged Markdown link syntax `[text](url)` as HTML tags
- Content extraction: added fallback selectors for modern web patterns (divs with content/article/post/body/entry classes) to better handle sites like Anthropic and DeepMind that don't use semantic `<article>` or `<main>` tags

## [0.3.6] - 2026-06-27

### Fixed
- GitHub Actions workflow: removed stale reference to deleted `reader.export` module that caused ImportError on workflow execution

## [0.3.5] - 2026-06-26

### Added
- Exception handling in the ingestion loop: if a source handler raises (e.g., HTTP 5xx, network timeout), the error is logged and ingestion continues with the next source instead of failing the entire run

## [0.3.4] - 2026-06-26

### Changed
- `feedparser` and `requests` are now imported directly at the top of `scrapers.py` instead of through lazy loader functions (`_load_feedparser`, `_load_requests`) — removes unnecessary indirection for required dependencies

## [0.3.3] - 2026-06-26

### Changed
- `source_scraper` is now passed as a parameter to `_fetch_article()` instead of being set to `"placeholder"` and patched via `object.__setattr__` — eliminates the hack in all four source-kind handlers

## [0.3.2] - 2026-06-26

### Removed
- `src/reader/export.py` deleted — it was a thin wrapper with no logic of its own; `export_csv` and `export_jsonl` are now imported directly from `reader.storage`

### Changed
- `tests/test_export.py` updated to call `export_csv` and `export_jsonl` directly instead of going through the removed wrapper

## [0.3.1] - 2026-06-26

### Added
- Source-kind registry pattern: `SOURCE_HANDLERS` dict in `scrapers.py` maps kind names to handler functions, replacing the `if/elif` chain in `ingest.py`
- `_fetch_article()` helper moved from `ingest.py` to `scrapers.py` to break circular imports and co-locate scraping logic

### Changed
- `ingest.py` is now a thin orchestrator: loads config, iterates sources, dispatches to `SOURCE_HANDLERS[kind]`, and upserts results
- Adding a new source kind now requires only a handler function and one line in the `SOURCE_HANDLERS` dict — no changes to the core ingestion loop
- All per-kind discovery logic (RSS, listing, api_tag, direct) lives in `scrapers.py` alongside the parsers

## [0.3.0] - 2026-06-26

### Added
- RSS sources now fetch the full article page for each feed entry, extracting complete content and saving raw HTML to the data repo — same treatment as listing and API tag sources
- RSS metadata (title, published_at, source_category, author) from the feed is used as fallback when the scraped page doesn't find them

### Changed
- `parse_rss_feed()` return values are now used as metadata fallback rather than primary content; the actual content comes from `extract_article()` on the article page
- All source kinds (RSS, listing, api_tag, direct) now consistently produce Markdown content and raw HTML files

## [0.2.2] - 2026-06-26

### Added
- Markdown conversion: extracted article content is now converted from HTML to Markdown via `html2text`, preserving structural signal (headings, bold, links, lists, code) for ML training
- `html2text>=2024.2` added to project dependencies
- `_html_to_markdown()` helper in `scrapers.py` with sensible defaults (links/images preserved, no line wrapping)
- Streamlit UI now renders article summaries as Markdown via `st.markdown()` for proper heading/link display

### Changed
- `_extract_content_from_selectors()` now converts selected HTML nodes to Markdown instead of stripping to plain text
- Fallback paragraph extraction also converts to Markdown by wrapping `<p>` elements in a `<div>` before conversion
- `items.content` and `items.summary` now contain Markdown-formatted text rather than plain text

## [0.2.1] - 2026-06-26

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

## [0.2.0] - 2026-06-26

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

## [0.1.2] - 2026-06-26

### Added
- Schema versioning system with `schema_version` table and migration support (`SCHEMA_VERSION = 1`)
- Paginated article listing in the Streamlit UI (25 articles per page with Previous/Next buttons)
- Test coverage for schema versioning, pagination, and URL fingerprinting

### Changed
- URL fingerprints now strip query parameters and fragments before hashing, preventing duplicates from tracking parameters (e.g., `?utm_source=rss`, `?fbclid=...`)
- `initialize()` now runs migrations against a version-tracked schema rather than ad-hoc column checks
- `_ensure_column()` now operates on an open connection instead of opening its own

## [0.1.1] - 2026-06-26

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
