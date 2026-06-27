import { ArticleList } from "@/components/article-list";
import { FailureBanner } from "@/components/failure-banner";
import { Pagination } from "@/components/pagination";
import { listIngestionFailures, listItemsPage } from "@/lib/items";
import { createClient } from "@/lib/supabase/server";
import { PAGE_SIZE } from "@/lib/types";

type Props = {
  searchParams: Promise<{ page?: string }>;
};

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;
  const page = Math.max(0, Number(params.page ?? "0") || 0);
  const supabase = await createClient();

  const [{ items, total }, failures] = await Promise.all([
    listItemsPage(supabase, page),
    listIngestionFailures(supabase),
  ]);

  const totalPages = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <>
      <FailureBanner failures={failures} />
      <ArticleList items={items} />
      {total > 0 && (
        <Pagination page={page} totalPages={totalPages} total={total} />
      )}
    </>
  );
}
