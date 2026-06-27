import Link from "next/link";

import { ArticleList } from "@/components/article-list";
import { FailureBanner } from "@/components/failure-banner";
import { Button } from "@/components/ui/button";
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
  const hasPrev = page > 0;
  const hasNext = page < totalPages;

  return (
    <>
      <FailureBanner failures={failures} />
      <ArticleList items={items} />
      {total > 0 && (
        <nav className="page-nav" aria-label="Pagination">
          {hasPrev ? (
            <Button variant="outline" size="sm" asChild>
              <Link href={`/?page=${page - 1}`}>Previous</Link>
            </Button>
          ) : (
            <Button variant="outline" size="sm" disabled>
              Previous
            </Button>
          )}
          <span className="page-nav-info">
            Page {page + 1} of {totalPages + 1} ({total} articles)
          </span>
          {hasNext ? (
            <Button variant="outline" size="sm" asChild>
              <Link href={`/?page=${page + 1}`}>Next</Link>
            </Button>
          ) : (
            <Button variant="outline" size="sm" disabled>
              Next
            </Button>
          )}
        </nav>
      )}
    </>
  );
}
