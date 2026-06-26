# Reader

Reader is a Python RSS/news reader focused on preserving article data for future ML work.

## Goals

- Ingest RSS and scraped pages into a canonical SQLite database.
- Store full article text for later model training.
- Allow read/unread and Like/Dislike state changes from a Streamlit web page.
- Allow manual category labeling from a configurable select list.
- Extract source-specific dates and source categories from non-RSS listing pages.
- Support tag-aware Hugging Face ingestion so Ethics and Research can be tracked separately.
- Export CSV and JSONL snapshots on demand for ML workflows.

## Current structure

- `src/reader/storage.py` handles SQLite schema, upserts, state changes, and exports.
- `src/reader/scrapers.py` contains RSS and page-extraction helpers.
- `src/reader/ingest.py` orchestrates feed ingestion.
- `src/reader/export.py` builds CSV and JSONL datasets.
- `streamlit_app.py` is the UI entrypoint.
- `.github/workflows/ingest.yml` runs ingestion on a schedule or manually.
- `config/sources/*.yaml` hold per-source listing-page instructions for non-RSS news pages.
- `config.example.yaml` now includes the manual category list used by the UI.
- Non-RSS source profiles now also carry source-specific selectors for date and category extraction.
- Hugging Face is handled as a tag-aware source because the public RSS feed does not expose the category split we need.

## Next steps

1. Add real feed URLs to a local config file based on `config.example.yaml`.
2. Add additional source profiles using the same listing-page metadata pattern.
3. Add tests for manual category updates, storage persistence, source metadata extraction, deduping, and exports.
4. Add a richer scraper fallback for harder article pages.