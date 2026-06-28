-- Fix list ordering: text sort_at breaks on RFC 2822 published_at values from RSS feeds.
-- Replaces 006 text column with timestamptz + explicit unread_rank.

DROP INDEX IF EXISTS public.idx_items_unread_sort;

ALTER TABLE public.items
  DROP COLUMN IF EXISTS sort_at;

CREATE OR REPLACE FUNCTION public.safe_parse_timestamptz(value text)
RETURNS timestamptz
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
  trimmed text;
BEGIN
  trimmed := nullif(btrim(value), '');
  IF trimmed IS NULL THEN
    RETURN NULL;
  END IF;
  RETURN trimmed::timestamptz;
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$;

ALTER TABLE public.items
  ADD COLUMN IF NOT EXISTS unread_rank smallint
  GENERATED ALWAYS AS (
    CASE
      WHEN read_at IS NULL OR btrim(read_at) = '' THEN 0
      ELSE 1
    END
  ) STORED;

ALTER TABLE public.items
  ADD COLUMN sort_at timestamptz
  GENERATED ALWAYS AS (
    coalesce(
      public.safe_parse_timestamptz(published_at),
      public.safe_parse_timestamptz(created_at)
    )
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_items_list_order
  ON public.items (unread_rank ASC, sort_at DESC NULLS LAST);
