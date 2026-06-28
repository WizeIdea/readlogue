# Supabase setup (Phase 1)

Production index lives in Supabase Postgres. GitHub Actions hydrates a scratch SQLite file from Supabase at the start of each ingest run, then syncs changes back after ingest completes.

## One-time setup

1. Create a Supabase project.
2. Run migrations in order in the Supabase SQL editor (or via CLI):
   - [`migrations/001_initial_schema.sql`](migrations/001_initial_schema.sql)
   - [`migrations/002_rls_policies.sql`](migrations/002_rls_policies.sql)
   - [`migrations/003_ignored_urls.sql`](migrations/003_ignored_urls.sql)
   - [`migrations/004_hero_image_url.sql`](migrations/004_hero_image_url.sql)
   - [`migrations/005_item_curation.sql`](migrations/005_item_curation.sql) — apply after truncating `items` during QA
   - [`migrations/006_items_sort_at.sql`](migrations/006_items_sort_at.sql) — generated `sort_at` column for list ordering
3. Add GitHub Actions secrets on the main repo:
   - `SUPABASE_URL` — project URL
   - `SUPABASE_SERVICE_ROLE_KEY` — **service role** key (never expose to frontend)

## Fresh bootstrap cutover

Existing SQLite and raw HTML can be discarded; the first ingest repopulates everything.

1. Apply the schema migration to an **empty** Supabase database.
2. Merge Phase 1 code and add secrets.
3. Delete `data/reader.db` from the main repo (no longer committed).
4. In the **data repo**, delete `raw_html/` (and optionally old `db_backups/`) so HTML is rewritten cleanly on the first run.
5. Trigger **workflow_dispatch** on the ingest workflow.
6. Verify rows in Supabase Table Editor; run ingest again and confirm `skipped_existing` in logs.

**After changing the content extractor or per-source content cleaners** (e.g. Trafilatura upgrade, new `content_clean` rules): truncate `items`, `sources`, and `ingestion_log` in Supabase, delete `raw_html/` in the data repo, and run `workflow_dispatch` for a clean re-ingest.

## Local development

Without `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`, ingest uses local `data/reader.db` only (legacy behavior).

## Phase 2 additions

- **`ignored_urls` table** — runtime ignore list written by the web UI; GHA ingest merges these with YAML `ignored_urls` / `ignored_url_substrings`.
- **`hero_image_url` on `items`** — optional Open Graph / Twitter image URL extracted during ingest.
- **RLS read policies** — authenticated users can read `sources`, `items`, `ingestion_log`, and `ignored_urls`; writes use the service role (ingest) or server routes (UI, later).
