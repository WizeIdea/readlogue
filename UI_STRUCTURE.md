# ReadLogue file structure

Quick reference for where things live. The web UI section is the most detailed — that is the active product surface.

## Repository overview

```
readlogue/
├── apps/web/                 # Next.js dashboard (hosted UI)
├── src/reader/               # Python ingest pipeline
├── config/                   # Source YAML profiles
├── config.yaml                 # Live ingest + category config (GHA + local)
├── supabase/migrations/      # Postgres schema (production index)
├── streamlit_app.py          # Optional local UI (SQLite only)
├── .github/workflows/        # GHA ingest
└── UI_STRUCTURE.md           # This file
```

## Python ingest (`src/reader/`)

| File | Role |
|------|------|
| `ingest.py` | Orchestrates a full ingest run |
| `scrapers.py` | RSS, listing, API handlers; Trafilatura extraction; hero image URLs |
| `storage.py` | SQLite schema, upserts, curation fields, exports |
| `supabase_sync.py` | Hydrate/sync scratch SQLite ↔ Supabase; `fetch_runtime_ignores()` |
| `validation.py` | Content quality checks; failures → `ingestion_log` |
| `config.py` | Loads `config.yaml` |
| `db_backup.py` | Daily/monthly SQLite backups to data repo |

## Supabase (production index)

| Migration | Contents |
|-----------|----------|
| `001_initial_schema.sql` | `sources`, `items`, `ingestion_log` |
| `002_rls_policies.sql` | Authenticated read policies |
| `003_ignored_urls.sql` | Runtime ignore list (UI writes) |
| `004_hero_image_url.sql` | `hero_image_url` on `items` |
| `005_item_curation.sql` | `curation jsonb` on `items` (human labels) |

Setup: [`supabase/README.md`](supabase/README.md)

---

## Web UI (`apps/web/`)

### App routes

| Path | File | Purpose |
|------|------|---------|
| `/` | `src/app/(main)/page.tsx` | Dashboard — article list, failure banner, pagination |
| `/login` | `src/app/login/page.tsx` | Email/password sign-in |
| `POST /api/ignore` | `src/app/api/ignore/route.ts` | Add substring to `ignored_urls`; clear log row |
| `POST /api/dismiss-failure` | `src/app/api/dismiss-failure/route.ts` | Clear log row without ignoring |

### Layout

| File | Purpose |
|------|---------|
| `src/app/layout.tsx` | Root HTML shell |
| `src/app/(main)/layout.tsx` | Sidebar + main content wrapper (no top header) |
| `src/app/globals.css` | **All visual design** (light/dark tokens, article layout, buttons, forms) |
| `src/middleware.ts` | Auth session refresh; redirect to `/login` |

### Components (application)

| File | Purpose |
|------|---------|
| `src/components/filter-sidebar.tsx` | Logo, category/source filter pills, sign out |
| `src/components/header.tsx` | *(removed)* |
| `src/components/login-form.tsx` | Email/password form (client) |
| `src/components/article-list.tsx` | Renders list of `ArticleRow` |
| `src/components/article-row.tsx` | 3-column row: left (thumbs + scores), middle (meta, title/summary read-toggle, chips), right (hero) |
| `src/components/article-curation.tsx` | `CurationScores` (T/B/G smileys) and `CurationChips` (article_types / article_domains) |
| `src/components/article-actions.tsx` | Thumbs up/down only |
| `src/components/pagination.tsx` | Previous, numbered pages, Next, article count |
| `src/components/failure-banner.tsx` | Top-of-page ingestion failure alerts |
| `src/components/failure-actions.tsx` | Ignore / Dismiss buttons per failure (client) |

### Components (UI primitives)

Styled via `globals.css` class names (`.btn`, `.alert`, `.select-trigger`, etc.):

| File | Purpose |
|------|---------|
| `src/components/ui/button.tsx` | Button |
| `src/components/ui/select.tsx` | Category dropdown |
| `src/components/ui/alert.tsx` | Failure banner container |
| `src/components/ui/collapsible.tsx` | Expandable summary |

### Library / data layer

| File | Purpose |
|------|---------|
| `src/lib/items.ts` | `listItemsPage`, `listIngestionFailures`, `patchItem`, `urlIgnoreSubstring` |
| `src/lib/types.ts` | `ItemRow`, `IngestionFailure`, `PAGE_SIZE` |
| `src/lib/categories.ts` | Category list (generated from `config.yaml` via `scripts/sync_web_vocab.py`) |
| `src/lib/sources.ts` | Enabled source names (generated from `config.yaml`) |
| `src/lib/filters.ts` | Filter URL helpers + `ItemFilters` type |
| `src/lib/curation.ts` | `CurationV1` type, parse helpers, `toggleTag` / `nextScore` |
| `src/lib/curation-picklists.ts` | `ARTICLE_TYPES` / `ARTICLE_DOMAINS` (generated from `config.yaml`) |
| `src/lib/utils.ts` | `cn()` class name helper |
| `src/lib/supabase/server.ts` | Server Supabase client (reads, session) |
| `src/lib/supabase/client.ts` | Browser client (login only) |
| `src/lib/supabase/admin.ts` | Service role client (writes, ignore API) |
| `src/lib/supabase/middleware.ts` | Session update helper |
| `src/app/actions.ts` | Server Actions: `setRating`, `setRead`, `setCuration`, `signOut` |

### Config / env

| File | Purpose |
|------|---------|
| `.env.example` | Template for Supabase keys |
| `components.json` | shadcn metadata (minimal components) |
| `README.md` | Local dev and Vercel setup |

### Data flow (curation)

```
Browser form/button
  → Server Action (actions.ts) or API route
    → require authenticated user
    → createAdminClient() patch items / ignored_urls / ingestion_log
    → revalidatePath('/') or router.refresh()
```

Reads on the dashboard use the session client (`createClient()` in server.ts) against RLS-protected tables.

---

## Related docs

- Portfolio / solution documentation: [`docs/README.md`](docs/README.md)
- User guide: [README.md — How to use the reader UI](README.md#how-to-use-the-reader-ui)
- Web setup: [`apps/web/README.md`](apps/web/README.md)
