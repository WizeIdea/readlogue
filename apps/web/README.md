# ReadLogue Web UI

Next.js dashboard for curating articles stored in Supabase (like/dislike, read state, categories).

## Setup

1. Copy `.env.example` to `.env.local` and fill in Supabase credentials.
2. Create a user in Supabase Dashboard → Authentication → Users (email/password).
3. Ensure migrations `001`–`004` are applied (see [`../../supabase/README.md`](../../supabase/README.md)).

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Vercel

- Set **Root Directory** to `apps/web`
- Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

## Structure

- `src/app/globals.css` — all visual design (light + dark via `prefers-color-scheme`)
- `src/components/*.tsx` — layout and content wiring (compact sidebar + icon curation)
- `src/components/pagination.tsx` — numbered page navigation
- `src/lib/items.ts` — Supabase queries and patches (shared with future API routes)
