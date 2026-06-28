import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  CATEGORY_FILTERS,
  hrefWithFilters,
  READ_FILTERS,
  type FilterSelection,
} from "@/lib/filters";

type Props = {
  page: number;
  totalPages: number;
  total: number;
  selection: FilterSelection;
};

export function Pagination({ page, totalPages, total, selection }: Props) {
  const hasPrev = page > 0;
  const hasNext = page < totalPages;
  const pageCount = totalPages + 1;

  return (
    <nav className="page-nav" aria-label="Pagination">
      <div className="page-nav-start">
        {hasPrev ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={hrefWithFilters(page - 1, selection)}>Previous</Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            Previous
          </Button>
        )}
      </div>

      <div className="page-nav-pages">
        {Array.from({ length: pageCount }, (_, index) => {
          const pageIndex = index;
          const label = index + 1;
          if (pageIndex === page) {
            return (
              <span key={label} className="page-nav-current" aria-current="page">
                {label}
              </span>
            );
          }
          return (
            <Link
              key={label}
              className="page-nav-link"
              href={hrefWithFilters(pageIndex, selection)}
            >
              {label}
            </Link>
          );
        })}
      </div>

      <div className="page-nav-end">
        {hasNext ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={hrefWithFilters(page + 1, selection)}>Next</Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" disabled>
            Next
          </Button>
        )}
        <span className="page-nav-info">{total} articles</span>
      </div>
    </nav>
  );
}
