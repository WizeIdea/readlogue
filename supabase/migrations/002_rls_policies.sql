-- Phase 2: authenticated read-only access for the web UI.
-- Ingest continues via service role (bypasses RLS).

create policy "Authenticated users can read sources"
    on public.sources
    for select
    to authenticated
    using (true);

create policy "Authenticated users can read items"
    on public.items
    for select
    to authenticated
    using (true);

create policy "Authenticated users can read ingestion_log"
    on public.ingestion_log
    for select
    to authenticated
    using (true);
