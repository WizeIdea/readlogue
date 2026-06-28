# ReadLogue Web UI

Next.js dashboard for curating articles stored in Supabase (like/dislike, read state, `items.curation` labels).

## Setup

1. Copy `.env.example` to `.env.local` and fill in Supabase credentials.
2. Create a user in Supabase Dashboard → Authentication → Users (email/password).
3. Ensure migrations `001`–`005` are applied (see [`../../supabase/README.md`](../../supabase/README.md)).

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Vocab sync

After editing `categories`, `article_types`, `article_domains`, or `sources` in [`../../config.yaml`](../../config.yaml):

```bash
python scripts/sync_web_vocab.py
```

This regenerates `src/lib/categories.ts`, `src/lib/curation-picklists.ts`, and `src/lib/sources.ts` (committed for Vercel builds).

## Vercel

- Set **Root Directory** to `apps/web`
- Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

## Structure

- `src/app/globals.css` — all visual design (light + dark via `prefers-color-scheme`)
- `src/components/filter-sidebar.tsx` — logo, category/source filters, sign out
- `src/components/article-row.tsx` — 3-column card (left controls, middle content, right hero)
- `src/components/article-curation.tsx` — type/domain chips + T/B/G smiley scores
- `src/components/pagination.tsx` — numbered page navigation (preserves filter query string)
- `src/lib/filters.ts` — URL filter parse/build helpers
- `src/lib/items.ts` — Supabase queries and patches

## Filter sidebar

- **Read status** — Unread / Read pills (both active by default; deselect Read to show unread only)
- **Categories** — from `categories.ts` plus an **Uncategorized** pill (`items.category IS NULL`)
- **Sources** — enabled names from `sources.ts`; labels use optional `display_name` from `config.yaml`
- All pills **active by default** (no URL params). Click to exclude; **Select all** / **Clear all** per section.
- URL params: `read`, `categories`, `sources` (comma-separated included values), `page`

### Source display names in config.yaml

Add `display_name` on any source entry (falls back to `name` if omitted):

```yaml
  - name: csail-news
    display_name: CSAIL News
    kind: listing
    ...
```

Then run `python scripts/sync_web_vocab.py` to update `src/lib/sources.ts`.

Sort order: unread first (`read_at` null), then newest article date within each group via `sort_at` (`coalesce(published_at, created_at)`).

## Curation UI

Each article row:

- **Left:** thumbs up/down; T/B/G smiley scores (1–5, click again to clear)
- **Middle:** source meta, title + summary (click to toggle read/unread), type/domain chips
- **Right:** hero image

Labels save to `items.curation` via `setCuration` server action.

## Assets

- Sidebar logo: `public/readlogue.png`
- Favicons / PWA: `src/app/favicon.ico`, `icon` PNGs, `apple-touch-icon.png`, `site.webmanifest`
