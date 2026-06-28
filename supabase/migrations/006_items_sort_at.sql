-- Coalesced article date for consistent list sorting (matches SQLite storage.py)

ALTER TABLE public.items
  ADD COLUMN IF NOT EXISTS sort_at text
  GENERATED ALWAYS AS (
    coalesce(nullif(trim(published_at), ''), created_at)
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_items_unread_sort
  ON public.items (read_at, sort_at DESC);
