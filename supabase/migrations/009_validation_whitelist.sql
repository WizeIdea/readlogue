-- URLs analysts whitelist to bypass voluntary content-quality checks on next successful fetch.

create table if not exists public.validation_whitelist (
    article_fingerprint text primary key,
    article_url text not null,
    created_at text not null default (now() at time zone 'utc')
);

alter table public.validation_whitelist enable row level security;

create policy "Authenticated users can read validation_whitelist"
    on public.validation_whitelist
    for select
    to authenticated
    using (true);
