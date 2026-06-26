# Reader

Reader is a Python RSS/news reader focused on preserving article data for future ML work.

## Goals

- Ingest RSS and scraped pages into a canonical SQLite database.
- Store full article text for later model training.
- Allow read/unread and Like/Dislike state changes from a Streamlit web page.
- Export CSV and JSONL snapshots on demand for ML workflows.

## Current structure

- `src/reader/storage.py` handles SQLite schema, upserts, state changes, and exports.
- `src/reader/scrapers.py` contains RSS and page-extraction helpers.
- `src/reader/ingest.py` orchestrates feed ingestion.
- `src/reader/export.py` builds CSV and JSONL datasets.
- `streamlit_app.py` is the UI entrypoint.
- `.github/workflows/ingest.yml` runs ingestion on a schedule or manually.
- `config/sources/*.yaml` hold per-source listing-page instructions for non-RSS news pages.

## Next steps

1. Add real feed URLs to a local config file based on `config.example.yaml`.
2. Add tests for storage, deduping, and exports.
3. Add a richer scraper fallback for harder article pages.