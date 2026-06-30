import { ArticleList } from "@/components/article-list";
import { FailureBanner } from "@/components/failure-banner";
import { Pagination } from "@/components/pagination";
import {
  CATEGORY_FILTERS,
  firstSearchParam,
  isFiltersEmpty,
  parseItemFilters,
  READ_FILTERS,
  selectedFromParam,
} from "@/lib/filters";
import { listIngestionFailures, listItemsPage } from "@/lib/items";
import { SOURCES } from "@/lib/sources";
import { createClient } from "@/lib/supabase/server";
import { PAGE_SIZE } from "@/lib/types";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function HomePage({ searchParams }: Props) {
  const raw = await searchParams;
  const page = Math.max(0, Number(firstSearchParam(raw.page) ?? "0") || 0);
  const params = {
    page: firstSearchParam(raw.page),
    categories: firstSearchParam(raw.categories),
    sources: firstSearchParam(raw.sources),
    read: firstSearchParam(raw.read),
    q: firstSearchParam(raw.q),
  };
  const filters = parseItemFilters(params);
  const filtered = filters !== undefined;
  const emptyFilters = isFiltersEmpty(filters);

  const selection = {
    categories: selectedFromParam(params.categories, CATEGORY_FILTERS),
    sources: selectedFromParam(params.sources, SOURCES),
    read: selectedFromParam(params.read, READ_FILTERS),
    q: params.q?.trim() || undefined,
  };

  const supabase = await createClient();

  const [{ items, total }, failures] = await Promise.all([
    emptyFilters
      ? Promise.resolve({ items: [], total: 0 })
      : listItemsPage(supabase, page, filters),
    listIngestionFailures(supabase),
  ]);

  const totalPages = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <>
      <FailureBanner failures={failures} />
      <ArticleList items={items} filtered={filtered} />
      {total > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          selection={selection}
        />
      )}
    </>
  );
}
