# Readlogue

Readlogue is a Python RSS/news reader focused on preserving article data for future ML work.

## Goals

- Ingest RSS and scraped pages into a canonical SQLite database.
- Store full article text for later model training.
- Allow read/unread and Like/Dislike state changes from a Streamlit web page.
- Allow manual category labeling from a configurable select list.
- Extract source-specific dates and source categories from non-RSS listing pages.
- Support tag-aware Hugging Face ingestion so Ethics and Research can be tracked separately.
- Export CSV and JSONL snapshots on demand for ML workflows.

## Current structure

- `src/reader/storage.py` handles SQLite schema (with version-tracked migrations), upserts, state changes, exports, and raw HTML file storage.
- `src/reader/scrapers.py` contains RSS and page-extraction helpers; `extract_article()` now returns raw HTML for ML pipelines.
- `src/reader/validation.py` contains content-quality checks (word count, HTML residue, lexical diversity).
- `src/reader/ingest.py` orchestrates feed ingestion with content validation, failure logging, and raw HTML archival.
- `src/reader/export.py` builds CSV and JSONL datasets.
- `streamlit_app.py` is the UI entrypoint; displays a warning banner when the last ingestion skipped articles.
- `.github/workflows/ingest.yml` runs ingestion on a schedule or manually using a dual-repo checkout pattern.
- Raw HTML is saved to `data/raw_html/YYYY-MM-DD/<uuid>.html` and committed to a separate data repository (`WizeIdea/readlogue_data_2026`) via `stefanzweifel/git-auto-commit-action`.
- The scheduled GitHub Action runs daily and only fetches article pages that are not already in SQLite.
- `config/sources/*.yaml` hold per-source listing-page instructions for non-RSS news pages.
- `config.example.yaml` now includes the manual category list used by the UI.
- Non-RSS source profiles now also carry source-specific selectors for date and category extraction.
- Hugging Face is handled as a tag-aware source because the public RSS feed does not expose the category split we need.

## How to use the reader UI

The UI is the Streamlit app in `streamlit_app.py`.

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
- `content`: full article body text.
- `summary`: short preview text.
- `published_at`: parsed publication timestamp when available.

Useful metadata fields that should be populated when the source exposes them:

- `author`: article author or authors.
- `source_category`: category or tag reported by the source itself.
- `category`: manual label chosen in the UI.
- `read_at`: read/unread state stored by the UI.
- `rating`: Like/Dislike state stored by the UI.

The ingestion pipeline must never overwrite the manual `category`, `read_at`, or `rating` fields when new items are discovered later.

## Next steps

1. Add real feed URLs to a local config file based on `config.example.yaml`.
2. Add additional source profiles using the same listing-page metadata pattern.
3. Add tests for manual category updates, storage persistence, source metadata extraction, deduping, and exports.
4. Add a richer scraper fallback for harder article pages.
5. Decide whether ingestion should run in a hosted environment, a local cron job, or only GitHub Actions.
6. Add an operator checklist for initial backfill, validation, and recovery from broken pages.
7. Add more robust monitoring for failed source fetches, parse failures, and empty ingests.
