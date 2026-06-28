-- Human curation labels (article types, domains, relevance scores) as JSON.
-- Apply after truncating items during QA; new rows default to {}.

alter table public.items
    add column if not exists curation jsonb not null default '{}';

create index if not exists idx_items_curation_gin
    on public.items using gin (curation);
