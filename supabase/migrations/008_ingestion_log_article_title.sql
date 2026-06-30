-- Optional article title captured when logging ingestion failures.

alter table public.ingestion_log
    add column if not exists article_title text;
