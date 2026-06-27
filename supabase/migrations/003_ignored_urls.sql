-- Runtime ignore list (UI writes; GHA ingest merges with YAML ignores).

create table if not exists public.ignored_urls (
    id bigint generated always as identity primary key,
    kind text not null check (kind in ('substring', 'exact')),
    value text not null,
    source_url text,
    created_at text not null default (now() at time zone 'utc'),
    unique (kind, value)
);

create index if not exists idx_ignored_urls_kind on public.ignored_urls (kind);

alter table public.ignored_urls enable row level security;

create policy "Authenticated users can read ignored_urls"
    on public.ignored_urls
    for select
    to authenticated
    using (true);

-- No direct authenticated insert; UI uses server routes with service role.
