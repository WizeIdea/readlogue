# ReadLogue

Licensed under the [Apache License, Version 2.0](LICENSE).

![Ingestion Workflow](https://github.com/WizeIdea/readlogue/actions/workflows/ingest.yml/badge.svg)

**ReadLogue** is a modular, automated research pipeline designed to aggregate, curate, and persist technical literature from diverse sources—including those without native RSS feeds. 

Unlike traditional RSS readers that prioritize consumption, ReadLogue is built as a **Data Ingestion Pipeline**, designed to serve as a persistent, research-grade corpus for downstream AI implementation.

## The "Why": Architectural Philosophy
In the age of AI, information overload is a technical problem, not just a lifestyle one. ReadLogue was built to solve the "RSS Bottleneck" and prepare for Machine Learning efficiencies.

*   **Hybrid Ingestion:** Combines efficient feed-parsing (`feedparser`) with resilient site-scraping (`newspaper4k`) to create a single, unified data stream.
*   **Decoupled Storage:** We separate the **index** (Supabase Postgres) from the **raw HTML corpus** (GitHub data repository). Article Markdown lives in Postgres; bulk HTML stays out of Supabase to respect free-tier limits.
*   **Researcher-First Design:** By persisting raw HTML/Markdown in a version-controlled, date-nested file structure, ReadLogue builds a "Ground Truth" dataset. This allows for reproducible experimentation, feature engineering, and training for future Deep Learning models.
*   **Zero-Cost Infrastructure:** GitHub Actions for ingest, Supabase free tier for the index, GitHub for raw HTML archival.

## Data Pipeline
1.  **Ingest:** GitHub Actions execute the Python pipeline daily, fetching content from configured URLs.
2.  **Normalize:** Raw HTML is processed and stored in a date-nested directory structure (`/YYYY-MM-DD/uuid.html`) in the **data repository**.
3.  **Index:** Metadata, clean Markdown content, and labels are stored in **Supabase Postgres** (production). A scratch SQLite file on the GHA runner is hydrated from Supabase before each run for dedup/skip logic.
4.  **Visualize:** Next.js on Vercel (Phase 2, in progress); Streamlit remains available for local SQLite dev.

## Storage layout

| Asset | Location | Path |
|-------|------------|------|
| Production index | **Supabase Postgres** | `sources`, `items`, `ingestion_log`, `ignored_urls` |
| Raw HTML | **Data repo** (`readlogue_data_2026`) | `raw_html/YYYY-MM-DD/<uuid>.html` |
| Scratch SQLite (GHA only) | Ephemeral runner | `data/reader.db` (gitignored) |
| SQLite file backups (optional) | **Data repo** | `db_backups/daily/`, `db_backups/monthly/` |

### Backup policy

- **Supabase Postgres** is the production source of truth for the index and article Markdown.
- **Daily backups:** after each ingest, GHA copies the scratch SQLite file to `db_backups/daily/reader-YYYY-MM-DD.db` in the data repo (7-day retention).
- **Monthly backups:** on the 1st of each month, a monthly copy is written to `db_backups/monthly/`. Monthly files are **never deleted**.
- **`data/reader.db` is not committed** to the main repo (avoids binary git bloat).

### GitHub Actions flow

Each ingest job:

1. Checks out the main repo and the data repo (`data-repo/`).
2. **Hydrates** scratch SQLite from Supabase (existing articles, failures, `raw_html_path`, `hero_image_url` values).
3. Runs ingestion — merges YAML and Supabase ignore lists, skips known URLs, fetches new articles, extracts hero images from page meta tags, writes raw HTML under `data-repo/raw_html/`.
4. **Syncs** scratch SQLite deltas back to Supabase.
5. Copies optional SQLite backups to `data-repo/db_backups/`.
6. Commits new HTML and backup files to the **data** repo.

Setup: see [`supabase/README.md`](supabase/README.md). Apply migrations `001`–`004` in order. Required secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATA_REPO_DEPLOY_KEY`.

**Fresh bootstrap:** truncate `items` and `ingestion_log` in Supabase (or delete `raw_html/` in the data repo) and run `workflow_dispatch` once to repopulate the index and HTML cleanly.

## Intended Outcomes
ReadLogue is designed to evolve with future ML projects:
*   **Short-term:** A low-friction, dashboard for managing technical reading.
*   **Mid-term:** A labeled, high-quality corpus for training custom classification models (Naive Bayes, Logistic Regression, and Neural Networks).
*   **Long-term:** An automated "Research Assistant" that uses Vector Search and RAG to surface information based on historical interests.

## Goals

- Ingest RSS and scraped pages into Supabase Postgres (production) with optional local SQLite for development.
- Store full article text for later model training.
- Allow read/unread and Like/Dislike state changes from a Streamlit web page.
- Allow manual category labeling from a configurable select list.
- Extract source-specific dates and source categories from non-RSS listing pages.
- Support tag-aware Hugging Face ingestion so Ethics and Research can be tracked separately.
- Export CSV and JSONL snapshots on demand for ML workflows.

## Requirements

- **Python 3.11+** — required to run the ingestion pipeline and Streamlit UI
- **pip** — for local development and dependency management
- **GitHub Actions** — for scheduled, serverless ingestion (no local cron needed)
- **Optional: Playwright** — for browser-based scraping of JavaScript-heavy sites (most sources work with `requests` only)

## Contributing

ReadLogue is designed to be extended by adding new source configurations. If you want to add a new RSS feed, blog, or API endpoint:

1. Check the existing `config/sources/` profiles for examples
2. Add your source to `config.example.yaml` or a local config file
3. If the source needs custom selectors, create a new profile in `config/sources/`
4. Run ingestion and verify the output
5. Open a PR with your config and any new scraper logic

See [Adding a new news source](#adding-a-new-news-source) below for the full pattern.

## Current structure

- `src/reader/storage.py` handles SQLite schema (with version-tracked migrations), upserts, state changes, exports, and raw HTML file storage.
- `src/reader/scrapers.py` contains RSS and page-extraction helpers; `extract_article()` uses **Trafilatura** for main body text (Markdown), falls back to CSS selectors + html2text, and returns raw HTML plus optional `hero_image_url`.
- `src/reader/validation.py` contains content-quality checks (word count, HTML residue, lexical diversity).
- `src/reader/supabase_sync.py` hydrates scratch SQLite from Supabase before ingest, syncs changes back after (GHA), and loads runtime ignore rules from the `ignored_urls` table.
- `src/reader/ingest.py` orchestrates feed ingestion with content validation, failure logging, and raw HTML archival.
- `src/reader/db_backup.py` rotates daily (7) and monthly SQLite backups into the data repository after ingest.
- `streamlit_app.py` is the local UI entrypoint (reads local `data/reader.db`; hosted UI planned via Next.js + Supabase).
- `.github/workflows/ingest.yml` runs ingestion on a schedule or manually; requires Supabase secrets.
- Raw HTML is saved to `raw_html/YYYY-MM-DD/<uuid>.html` in the **data** repository.
- DB backups are saved to `db_backups/daily/` and `db_backups/monthly/` in the data repository.
- The scheduled GitHub Action hydrates from Supabase and only fetches article pages not already indexed.
- `config/sources/*.yaml` hold per-source listing-page instructions for non-RSS news pages.
- `config.example.yaml` now includes the manual category list used by the UI.
- Non-RSS source profiles now also carry source-specific selectors for date and category extraction.
- Hugging Face is handled as a tag-aware source because the public RSS feed does not expose the category split we need.

## How to use the reader UI

The UI is the Streamlit app in `streamlit_app.py`. It reads and writes the same `data/reader.db` file that ingestion uses.

**Note:** Automatic sync of UI changes to GitHub is not yet implemented. For now, the UI is intended for local development against a cloned database. Hosted deployment with auto-commit is planned for a later phase.

1. Start the app with Streamlit using the repo's configured Python environment.
2. Open the page and load the same config file that ingestion uses.
3. Articles are paginated (25 per page). Use the `← Previous` / `Next →` buttons at the bottom to navigate.
4. Each article card shows the title, source, URL, summary, read status, rating, source category, and manual category.
5. Use `Mark read` and `Mark unread` to update the read state.
6. Use `Like` and `Dislike` to set the article rating.
7. Use the category dropdown to assign a manual label from the configured category list.

These actions update the SQLite database directly:

- `read_at` stores the read/unread state.
- `rating` stores `like` or `dislike`.
- `category` stores the manual label chosen in the UI.

## Backfill / recovery checklist

Use this when you are doing the first full import or recovering from a broken source.

1. Confirm the local config contains all sources you want to ingest.
2. Run ingestion once to create the SQLite database and populate initial items.
3. Open the UI and spot-check that articles render with the expected title, summary, and source metadata.
4. Mark a few items read, unread, like, and dislike to confirm the UI writes back to SQLite correctly.
5. If a source changes layout or starts failing, fix its source config or scraper settings first.
6. Re-run ingestion after the fix and confirm only new URLs are fetched.
7. If a source produces bad or duplicated rows, remove or repair those rows in SQLite before the next scheduled run.
8. Re-export the dataset after recovery so CSV and JSONL stay aligned with the current database.

### Ingestion failures and ignore list

When validation rejects an article (empty body, HTML residue, low lexical diversity, etc.), the pipeline records one row per URL in `ingestion_log` with an incrementing `failure_count`. The Streamlit UI shows these from the **first** failure with the error message and attempt count.

- **`ignored_url_substrings` / `ignored_urls` (YAML)** — skip matching URLs before fetch (no HTTP request). Use for repeat offenders such as JavaScript shells that will never pass validation.
- **`ignored_urls` (Supabase)** — same semantics, managed at runtime from the hosted UI; merged with YAML on each ingest run.
- **`auto_skip_failure_threshold`** (default `3`) — after this many failures for a URL that is not yet in `items`, ingest stops re-fetching it (`skipped_known_failure` in the summary).
- **Ignore button** in the UI appends the URL to your config and clears the log row locally. With `READLOGUE_GITHUB_TOKEN` set, `git_sync` can commit the config change (Phase 2).

Successful ingest removes the matching `ingestion_log` row. A **validation whitelist** (bypass checks for known-good URLs such as `cyber-toolkits-update`) is planned — see Next steps item 11.

## Adding a new news source

Use the same pattern for every future source so ingestion stays config-driven.

1. Add a source entry to your local config based on `config.example.yaml`.
2. Choose the source kind:
	- `rss` for a plain RSS/Atom feed.
	- `listing` for a web page that exposes article cards or article links.
	- `api_tag` for a tag-filtered endpoint like Hugging Face's blog tags.
3. Add a source profile file in `config/sources/` when the source is not a plain RSS feed.
4. Run ingestion once and confirm the page extracts a stable title, URL, and body text.
5. Add or update tests for the new source shape before treating it as complete.

### Source config fields

Every source entry should define these fields:

- `name`: unique source name used in the database.
- `kind`: `rss`, `listing`, or `api_tag`.
- `url`: feed URL, listing URL, or source landing page.
- `scraper`: fetch method used by the ingestion path.
- `config`: optional path to a source profile file.
- `enabled`: optional flag for turning a source on or off.

For non-RSS sources, the profile file may also define:

- `fetcher`: `requests` or `playwright`.
- `item_selector` and `link_selector`: how article entries are discovered.
- `title_selector` / `title_selectors`: how the title is extracted.
- `date_selectors` and `date_formats`: how published dates are parsed.
- `category_selectors`: how source-specific categories are extracted.
- `content_selectors` and `paragraph_selector`: how article body text is extracted.
- `api_tag`: the tag name for tag-filtered sources such as Hugging Face.
- `allowed_url_prefixes` / `excluded_url_substrings`: filters that keep discovery focused.

### Database fields used by each ingested item

The database stores the source itself in `sources` and the article data in `items`. Schema migrations are tracked in a `schema_version` table so the database can be upgraded safely across releases.

Required or strongly recommended item fields for ingestion:

- `source_id`: internal link back to the source row.
- `fingerprint`: unique item key derived from the article URL (query parameters and fragments are stripped before hashing to prevent duplicates from tracking params).
- `url`: canonical article URL.
- `title`: article title.
- `content`: full article body as Markdown (Trafilatura-extracted; raw HTML archived separately for reprocessing).
- `summary`: short preview text.
- `published_at`: parsed publication timestamp when available.

Useful metadata fields that should be populated when the source exposes them:

- `author`: article author or authors.
- `source_category`: category or tag reported by the source itself.
- `category`: manual label chosen in the UI.
- `read_at`: read/unread state stored by the UI.
- `rating`: Like/Dislike state stored by the UI (primary signal for planned ML training).
- `hero_image_url`: absolute URL of the article hero/thumbnail image from Open Graph or Twitter meta tags when available.
- `raw_html_path`: relative path to archived HTML in the data repository.

The ingestion pipeline must never overwrite the manual `category`, `read_at`, or `rating` fields when new items are discovered later.

**Ignore lists:** `config.example.yaml` holds seed `ignored_urls` / `ignored_url_substrings`. The Supabase `ignored_urls` table holds additional runtime rules (written by the hosted UI). GHA ingest merges both sources on each run.

## Next steps

1. ~~Add real feed URLs to a local config file based on `config.example.yaml`.~~ — 5 sources configured (Anthropic, BAIR, HuggingFace x2, Stanford HAI)
2. ~~Add additional source profiles using the same listing-page metadata pattern.~~ — BAIR, HuggingFace, Stanford HAI profiles added
3. ~~Add tests for manual category updates, storage persistence, source metadata extraction, deduping, and exports.~~ — 70 tests passing
4. ~~Enhance scraper fallback heuristics for harder article pages (e.g., Readability, boilerpipe-style extraction).~~ — Trafilatura primary extraction + selector fallback (v1.2.0).
5. ~~Decide whether ingestion should run in a hosted environment, a local cron job, or only GitHub Actions.~~ — GitHub Actions workflow configured
6. ~~Add an operator checklist for initial backfill, validation, and recovery from broken pages.~~ — See "Backfill / recovery checklist" above
7. ~~Add more robust monitoring for failed source fetches, parse failures, and empty ingests.~~ — Content validation + ingestion_log + exception handling implemented. Remaining enhancements: retry logic for transient failures, optional alerting.

### New items

8. Set up the data repo deploy key (SSH key) to activate the dual-repo raw HTML archival workflow.
9. Next.js hosted UI on Vercel (Phase 2).
10. Document the source-kind registry pattern (`SOURCE_HANDLERS`) in CONTRIBUTING.md for future contributors.
11. Add a validation **whitelist** for URLs that should bypass lexical-diversity or similar checks (e.g. `cyber-toolkits-update` on Anthropic Research).
