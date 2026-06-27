-- ReadLogue production schema (mirrors SQLite v3 in src/reader/storage.py)

create table if not exists public.sources (
    id bigint generated always as identity primary key,
    name text not null unique,
    source_url text not null,
    scraper text not null,
    created_at text not null default (now() at time zone 'utc')
);

create table if not exists public.items (
    id bigint generated always as identity primary key,
    source_id bigint not null references public.sources (id) on delete cascade,
    fingerprint text not null unique,
    url text not null,
    title text not null,
    summary text not null default '',
    content text not null default '',
    author text,
    published_at text,
    source_category text,
    category text,
    read_at text,
    rating text,
    raw_html_path text,
    created_at text not null default (now() at time zone 'utc'),
    updated_at text not null default (now() at time zone 'utc')
);

create index if not exists idx_items_source_id on public.items (source_id);
create index if not exists idx_items_read_at on public.items (read_at);
create index if not exists idx_items_rating on public.items (rating);
create index if not exists idx_items_fingerprint on public.items (fingerprint);

create table if not exists public.ingestion_log (
    id bigint generated always as identity primary key,
    source_name text not null,
    article_url text not null,
    article_fingerprint text not null unique,
    severity text not null default 'warning',
    message text not null,
    failure_count integer not null default 1,
    created_at text not null default (now() at time zone 'utc'),
    last_seen_at text not null default (now() at time zone 'utc')
);

create index if not exists idx_ingestion_log_created on public.ingestion_log (created_at);
create index if not exists idx_ingestion_log_fingerprint on public.ingestion_log (article_fingerprint);

-- Phase 1: ingest uses service role (bypasses RLS). No anon policies until Next.js UI.
alter table public.sources enable row level security;
alter table public.items enable row level security;
alter table public.ingestion_log enable row level security;
