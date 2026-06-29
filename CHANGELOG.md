# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.3] - 2026-06-29

### Changed

- Click-to-read applies to the **summary** only in [`article-row.tsx`](apps/web/src/components/article-row.tsx) — opening the title/URL no longer marks the article read, so you can read externally and still rate/curate before toggling read via the summary
- T/B/G score buttons use **Lucide sentiment icons** (Angry → Laugh) with MUI-style `--score-1`…`--score-5` colours — replaces Unicode emoji, which ignored CSS `color`

## [2.1.2] - 2026-06-29

### Added

- [`_extract_article_published_at()`](src/reader/scrapers.py) — article-page `published_at` with priority: trafilatura metadata → Open Graph / meta tags → `time[datetime]` → optional per-source YAML (`article_date_selectors` / `article_date_formats`) → URL path patterns (`/YYYY/MM/DD/`, `/YYYY-MM-DD-`)
- [`_normalize_published_at()`](src/reader/scrapers.py) — all ingest paths persist canonical ISO UTC (`YYYY-MM-DDTHH:MM:SS+00:00`); accepts RFC 2822, ISO, and date-only input; strips fractional seconds (e.g. Hugging Face API microseconds)
- [`scripts/audit_item_dates.py`](scripts/audit_item_dates.py) — date QA gate before/after re-import:
  - `inventory` — offline scan of **every** `items` row (format class, NULLs, non-canonical ISO, per-source summary)
  - `verify` — live re-fetch of **every** URL; compares stored vs extracted vs page truth
- [`ListingSourceProfile`](src/reader/config.py) — optional `article_date_selectors` / `article_date_formats` for article-page overrides (separate from listing `date_selectors`)
- Unit tests for `_normalize_published_at`, URL-path extraction, and meta-tag article dates in [`tests/test_scrapers.py`](tests/test_scrapers.py)

### Changed

- `_fetch_article` — prefers article-page date over listing-card date; both normalized before storage
- RSS ingest — article-page date wins over feed `pubDate`; merge path and RSS-only path normalize `published_at`
- `parse_rss_feed`, `parse_huggingface_tag_articles`, and `_parse_date_text` — emit normalized ISO via `_normalize_published_at`
- Article meta line in [`article-row.tsx`](apps/web/src/components/article-row.tsx) — shows **`published_at` only** (omits date when null; no `created_at` fallback). `sort_at` still falls back to `created_at` for ordering only.

### Fixed

- **Wrong or missing dates at ingest** — listing sources with dates outside the link element (e.g. BAIR), RSS syndication dates disagreeing with article pages (e.g. Allen AI `molmo-motion`: feed Jun 30 → page Jun 17), and 122 rows with null `published_at` on full re-import now populated from article-page extraction
- **Mixed `published_at` string formats in storage** — legacy RFC 2822 from pre-2.1.1 RSS rows (e.g. `Thu, 25 Jun 2026…` vs `2026-02-18T00:00:00+00:00` on listing sources). Full re-import with normalization yields one format everywhere.
- [`bair-blog.yaml`](config/sources/bair-blog.yaml) — `item_selector: div.post` (BAIR listing has no `<article>` tags; bare `a[href*="/blog/"]` missed parent-card dates; `article, main section` matched nothing and skipped the entire source). Hub URLs excluded (`/blog/about`, `/blog/archive`, `/blog/page/`, etc.). Article dates from URL path on fetch when listing card has no date text.

### Notes

- **Workflow:** fix ingest (Python) → truncate → full re-import → audit. Do not backfill `published_at` in Supabase in place.
- **Supabase migration `007`** — confirm `sort_at` is `timestamptz` and `unread_rank` is `smallint` before relying on dashboard sort (see [`007_sort_at_timestamptz.sql`](supabase/migrations/007_sort_at_timestamptz.sql)).
- **Truncate for re-import** (keeps `sources`; wipes articles and failure log):
  ```sql
  TRUNCATE TABLE public.ingestion_log, public.items RESTART IDENTITY;
  ```
- **Post re-import audit** (example):
  ```bash
  python scripts/audit_item_dates.py --database reader-YYYY-MM-DD.db inventory
  python scripts/audit_item_dates.py --database reader-YYYY-MM-DD.db verify
  ```
- **Validated on 2026-06-28 backup after re-import:** 511 items — 511 canonical ISO, 0 RFC 2822, 0 NULL; live `verify` passed for `groq-blog` (24/24, previously all NULL) and `allenai-news` (9/9, including corrected `molmo-motion` date). Re-run ingest after the `div.post` BAIR selector fix to restore ~10 BAIR posts (missed when `item_selector` matched no listing cards).

## [2.1.1] - 2026-06-29

### Added

- Supabase migration [`007_sort_at_timestamptz.sql`](supabase/migrations/007_sort_at_timestamptz.sql) — `sort_at` as `timestamptz` (via `safe_parse_timestamptz()`), `unread_rank` for unread-first ordering, and `idx_items_list_order`
- [`_rss_published_iso()`](src/reader/scrapers.py) — RSS feeds now store ISO `published_at` from feedparser struct time (not raw RFC 2822 strings)

### Changed

- `listItemsPage` orders by `unread_rank` asc, then `sort_at` desc (`timestamptz`)

### Fixed

- Article list date order — text `sort_at` from migration `006` sorted RFC 2822 dates lexically (e.g. `Mon, 27 May 2024…`), so newest-first was wrong for many RSS sources; `007` parses dates before sorting

### Notes

- Apply migration `007` after `006` (`supabase db push` or SQL editor). `007` drops and replaces the text `sort_at` column from `006`
- Existing rows sort correctly after `007` without re-ingest; new RSS ingests store cleaner ISO `published_at`

## [2.1.0] - 2026-06-29

### Added

- **Read / Unread** filter pills in the sidebar (`read` URL param; server-side filter in `listItemsPage`)
- Optional `display_name` per source in [`config.yaml`](config.yaml) — sidebar labels, article meta, and failure cards use human-readable names via [`sourceDisplayNameLoose()`](apps/web/src/lib/sources.ts) (generated by [`scripts/sync_web_vocab.py`](scripts/sync_web_vocab.py))
- Article meta line shows **source display name + article date** (`published_at`, falling back to `created_at`)
- Supabase migration [`006_items_sort_at.sql`](supabase/migrations/006_items_sort_at.sql) — generated `sort_at` column (`coalesce(published_at, created_at)`) for reliable list ordering
- **Optimistic UI** for like/dislike, read/unread toggle, and curation chips/scores — controls update instantly; server actions run in the background with revert on failure
- Sidebar logo [`public/readlogue.svg`](apps/web/public/readlogue.svg)

### Changed

- **Ingestion failures** — responsive grid of compact cards; heading is a link to the article URL labelled with `display_name`
- Article card **left column** widened; **type/domain chips moved** from middle column alongside thumbs and T/B/G scores (4 type chips per row; 8 domain chips in two balanced rows of 4)
- T/B/G score labels use full words (Technical, Business, Governance); smiley buttons use **MUI radio-group colours** at all times (red → green per level)
- Larger like/dislike buttons; title and summary typography tweaks; curation chip hover is **bold text only** (no background change)
- List sort: unread first, then `sort_at` descending (matches SQLite `coalesce(published_at, created_at)` logic)
- [`load_web_sources()`](src/reader/config.py) returns `name` + `display_name`; vocab sync test covers `SOURCE_DISPLAY_NAMES`

### Fixed

- Article list date order within the unread group — previously broken when `published_at` was null or secondary sort did not coalesce ingest date

### Notes

- Apply migrations `006` then `007` before deploying the web app (`supabase db push` or SQL editor)
- After editing `display_name` in `config.yaml`, run `python scripts/sync_web_vocab.py`

## [2.0.1] - 2026-06-28

### Added

- Left **filter sidebar** (ChatGPT-style): toggle pills for `config.yaml` categories (plus Uncategorized) and enabled sources; Select all / Clear all per section
- `[apps/web/src/lib/sources.ts](apps/web/src/lib/sources.ts)` generated from enabled sources in `config.yaml`
- `[apps/web/src/lib/filters.ts](apps/web/src/lib/filters.ts)` — URL param parse/build; server-side filter queries in `listItemsPage`
- PWA icons and `[site.webmanifest](apps/web/src/app/site.webmanifest)`; sidebar logo `[public/readlogue.png](apps/web/public/readlogue.png)`

### Changed

- Dashboard layout: full-height sidebar + main column; **removed top header** (sign out moved to sidebar footer)
- Pagination and filter state preserved in URL (`categories`, `sources`, `page`)

### Removed

- `[apps/web/src/components/header.tsx](apps/web/src/components/header.tsx)`

## [2.0.0] - 2026-06-28

### Added

- `[scripts/sync_web_vocab.py](scripts/sync_web_vocab.py)` — generates `[apps/web/src/lib/categories.ts](apps/web/src/lib/categories.ts)` and `[apps/web/src/lib/curation-picklists.ts](apps/web/src/lib/curation-picklists.ts)` from `config.yaml` (single source of truth)
- `[apps/web/src/components/article-curation.tsx](apps/web/src/components/article-curation.tsx)` — per-article `article_types` / `article_domains` toggle chips and T/B/G smiley relevance scores (`items.curation` jsonb)
- CI drift test `[tests/test_vocab_sync.py](tests/test_vocab_sync.py)`

### Changed

- Dashboard article cards: **3-column layout** — left (thumbs + scores), middle (meta, title/summary, chips), right (larger hero image)
- Click title/summary to **toggle read/unread**; chips excluded from read target
- Typography bump: title, meta, and summary each one step larger
- `[scripts/sync_categories.py](scripts/sync_categories.py)` delegates to `sync_web_vocab.py`

### Removed

- Manual **category dropdown** from article rows (`items.category` still set at ingest for future filters)
- Mail read/unread icon buttons (replaced by click-to-toggle on title/summary)

## [1.4.9] - 2026-06-28

### Added

- Vendor/lab blog sources: `thinking-machines-blog` (native RSS at `thinkingmachines.ai`), `google-developers-blog-ai`, `meta-ai-blog`, `groq-blog` — listing profiles under `[config/sources/](config/sources/)`
- `[docs/BLOCKED_SOURCES.md](docs/BLOCKED_SOURCES.md)` — blocked, digest-only, and deferred sources with GHA failure notes and alternatives
- RSS `settings.allowed_url_prefixes` — filter feed entries to a URL prefix (e.g. `ai-gov-blog` blog-only from site-wide RSS)
- `VendorBlogListingProfileTests` and config guard ensuring only `[docs/BLOCKED_SOURCES.md](docs/BLOCKED_SOURCES.md)` entries stay disabled

### Changed

- GHA ingest enables **all configured sources** except the eight listed in `[docs/BLOCKED_SOURCES.md](docs/BLOCKED_SOURCES.md)` (`the-batch`, `turing-blog`, `acm-technews`, `unimelb-newsroom-`*, `ai-gov-blog`, `dta-news-ai`, `industry-gov-news`)
- `meta-ai-blog` listing profile targets card containers (`div._8xiz`, featured hero) instead of every blog anchor
- HTTP read-timeout on `requests` auto-retries via Playwright in `_fetch_html` (shared fallback for listing and article fetches)

### Fixed

- `_fetch_article` prefers article-extracted summary over listing-page teaser text — Meta AI `items.summary` no longer stores `"FEATURED"` or `"Learn More"` from index cards
- `atse-news` listing selector matches relative `/news/…` paths (validated on GHA: 9 articles per run)
- Industry.gov.au listing: Playwright `--disable-http2` and `wait_until` retry chain (still times out on GHA; documented as blocked)

### Notes

- Truncate DB before re-ingest to refresh Meta AI summaries on existing rows (ingest skips known fingerprints)
- `oaic-ai-blog` and `atse-news` re-enabled with the full source set
- Wiley AI Magazine, Sydney/Monash/CAIDE/CSIRO probes documented in `BLOCKED_SOURCES.md` but not added to config

## [1.4.8] - 2026-06-28

### Added

- IEEE Spectrum RSS sources: `ieee-spectrum-ai`, `ieee-spectrum-computing` (AI News), `ieee-spectrum` (News Digests) — topic/main feeds, not homepage scrape
- Australian university sources (Education): `unimelb-newsroom-*`, `rmit-news-technology`, `anu-integrated-ai-news`, `qut-genailab`
- Australian government/policy listing sources (Governance and Policy): `ai-gov-blog`, `atse-news`, `dta-news-ai`, `oaic-ai-blog`, `industry-gov-news`
- Listing profiles under `[config/sources/](config/sources/)` for the above; OAIC redirect link decoding in `[scrapers.py](src/reader/scrapers.py)`
- RSS `settings.use_feed_content: true` — optional digest mode via `_record_from_rss_entry()` (stores validated RSS body without fetching the article URL)
- Tests: `use_feed_content` handler, ANU/RMIT listing profile link discovery

### Changed

- `the-batch` disabled — DeepLearning.ai returns 403 from GHA datacenter IPs; proxy RSS has teaser-only descriptions
- `acm-technews` disabled — external article fetches are patchy and RSS digests (~80 words) are not suitable for full-text storage
- UniMelb newsroom profile uses `fetcher: playwright` for articles (not requests-first) — GHA datacenter IPs always 403 on article pages; skips redundant retry round-trips
- `unimelb-newsroom-eng-it` and `unimelb-newsroom-education` disabled pending stable GHA ingest cadence

### Fixed

- UniMelb newsroom sources switched from RSS to topic **listing** scrape — `/newsroom/feed?queries_category_query=…` returns 403 from GHA; topic pages return static article links
- UniMelb listing uses `listing_fetcher: playwright` with Cloudflare-tolerant browser context; HTTP 403 on `requests` auto-retries via Playwright for other sources (`playwright_wait_selector` on listing profiles)

### Notes

- Apply Supabase migration `[005_item_curation.sql](supabase/migrations/005_item_curation.sql)` before sync if the `curation` column is missing
- `ai-gov-blog`, `dta-news-ai`, `industry-gov-news` disabled — `www.ai.gov.au`, `www.dta.gov.au`, and `www.industry.gov.au` read-timeout from GitHub Actions datacenter IPs (requests and Playwright); work locally
- `atse-news` disabled after successful GHA validation
- GHA test batch (Jun 2026): only `thinking-machines-blog`, `google-developers-blog-ai`, `meta-ai-blog`, `groq-blog` enabled
- RMIT technology listing exposes ~9 articles per run (Load More is JS-only)
- IEEE topic feeds overlap with the main feed; URL fingerprint dedupe prevents duplicate rows

## [1.4.7] - 2026-06-27

### Added

- `items.curation` jsonb column for human labeling (multi-tag `article_types` / `article_domains`, 1–5 relevance scores) — migration `[005_item_curation.sql](supabase/migrations/005_item_curation.sql)`
- `[src/reader/curation.py](src/reader/curation.py)` helpers; SQLite schema v5; sync via `[supabase_sync.py](src/reader/supabase_sync.py)`
- `article_types` and `article_domains` vocabularies in `[config.yaml](config.yaml)`
- Web types `[apps/web/src/lib/curation.ts](apps/web/src/lib/curation.ts)` and `setCuration` server action (UI controls follow-up)

### Notes

- Truncate Supabase before applying migration 005, then re-ingest; ingest never overwrites existing `curation` on re-fetch

## [1.4.6] - 2026-06-27

### Changed

- Renamed `config.example.yaml` → `[config.yaml](config.yaml)` (live operational config for GHA ingest, not a template)
- Categories are defined only in `config.yaml`; removed duplicate `DEFAULT_CATEGORIES` from `[src/reader/config.py](src/reader/config.py)`
- `[apps/web/src/lib/categories.ts](apps/web/src/lib/categories.ts)` is generated from `config.yaml` via `[scripts/sync_categories.py](scripts/sync_categories.py)`
- CI test guards against category list drift between config and web UI

## [1.4.5] - 2026-06-27

### Fixed

- Reject Cloudflare / bot-protection challenge pages during validation (prevents turing.ac.uk interstitial text being stored as articles)
- RSS sources with a `config:` profile no longer crash when `listing_article` is `None` (`aisi-blog` `'NoneType' object has no attribute 'summary'`)
- `aisi-blog` uses `fetcher: playwright` for full gov.uk article bodies; `the-batch` back to `requests` (Playwright returned teaser-only HTML on GHA)
- `turing-blog` disabled until manual import or a working fetch path (datacenter Playwright still lands on challenge pages)

## [1.4.4] - 2026-06-27

### Added

- Governance and Policy batch: `csail-news`, `oecd-ai-wonk`, `partnership-on-ai-blog`, `ainow-publications`, `eu-digital-strategy-news` (enabled for next GHA run)
- Listing profiles: `[config/sources/csail-news.yaml](config/sources/csail-news.yaml)`, `[config/sources/oecd-ai-wonk.yaml](config/sources/oecd-ai-wonk.yaml)`, `[config/sources/eu-digital-strategy-news.yaml](config/sources/eu-digital-strategy-news.yaml)`
- `settings.default_category` now applied to listing and `api_tag` sources (same as RSS)

### Notes

- CSAIL listing exposes ~3 spotlight articles per run (Load More is JS); daily incremental ingest picks up new posts. Archive backfill deferred.

## [1.4.3] - 2026-06-27

### Fixed

- `aisi-blog` profile strips the leading AISI → AI Security Institute rename disclaimer from `items.content`

## [1.4.2] - 2026-06-27

### Fixed

- RSS ingest no longer aborts an entire source on the first HTTP 403 — per-URL errors are logged and skipped
- `the-batch` and `turing-blog` use `fetcher: playwright` to bypass Cloudflare blocks on GHA datacenter IPs

### Changed

- README Phase 2 roadmap: RSS metadata stubs + manual full-text import for bot-protected publishers

## [1.4.1] - 2026-06-27

### Added

- Batch 3 RSS sources via [Alan Turing Institute ai-rss-feeds](https://github.com/alan-turing-institute/ai-rss-feeds): `allenai-news`, `mistral-news`, `aisi-blog`, `turing-blog`, `the-batch`, `tldr-ai` (all `enabled: false` until QA)

## [1.4.0] - 2026-06-27

### Added

- RSS sources: `microsoft-research-blog`, `importai`, `nist-news`, `nist-it-news`, `huggingface-blog`, `openai-news` (main HF feed)
- `Research Digests` category (Import AI and future digest sources)
- `settings.default_category` on RSS sources — pre-labels ingested items for the dashboard
- `[config/sources/huggingface-blog.yaml](config/sources/huggingface-blog.yaml)` — `.blog-content` extraction and model-card cleanup for the main HF RSS feed
- RSS sources with `config:` paths now load listing profiles for `content_root_selector` / `content_clean`

### Changed

- `openai-engineering` and `openai-news` RSS sources with `default_category` Technical Research / AI News

## [1.3.1] - 2026-06-27

### Added

- `content_root_selector` on listing source profiles — prefer a DOM subtree (e.g. Hugging Face `.blog-content`) before Trafilatura
- Hugging Face `huggingface-research` and `huggingface-ethics` profiles use `.blog-content` extraction plus model-card / GitHub-link cleanup rules

### Fixed

- Hugging Face blog posts no longer start with sidebar model-card banners or drop the opening paragraph text before inline links

## [1.3.0] - 2026-06-27

### Added

- Per-source content cleaners: `ContentCleanRules` in source YAML (`content_clean.strip_leading_lines_matching`, optional `strip_prefix_literals`)
- `[src/reader/content_clean.py](src/reader/content_clean.py)` — post-extraction cleanup after Trafilatura, before validation and `summary = content[:500]`
- Anthropic source profiles strip footer newsletter CTAs from the start of `items.content`
- `[tests/test_content_clean.py](tests/test_content_clean.py)` — unit tests for Anthropic junk-line removal

### Changed

- `extract_article()` and ingest handlers pass loaded `content_clean` rules from listing profiles or RSS `settings`

## [1.2.2] - 2026-06-27

### Changed

- Dashboard max content width increased to `96rem` (~1536px) for large displays
- Article typography adjusted: title ~17px, source meta ~13px, summary 14px, category ~13px
- Read rows keep a visible border while retaining the flat page-background style
- Like/dislike icon buttons toggle off to `null` on second click (unlike / undislike)

## [1.2.1] - 2026-06-27

### Added

- `[components/pagination.tsx](apps/web/src/components/pagination.tsx)` — clickable page numbers plus Previous / Next

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
- `[supabase/README.md](supabase/README.md)` documents migrations 002–004 and Phase 2 schema additions

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

