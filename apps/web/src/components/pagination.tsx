import Link from "next/link";

import { Button } from "@/components/ui/button";

type Props = {
  page: number;
  totalPages: number;
  total: number;
};

export function Pagination({ page, totalPages, total }: Props) {
  const hasPrev = page > 0;
  const hasNext = page < totalPages;
  const pageCount = totalPages + 1;

  return (
    <nav className="page-nav" aria-label="Pagination">
      <div className="page-nav-start">
        {hasPrev ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={page === 1 ? "/" : `/?page=${page - 1}`}>Previous</Link>
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
          const href = pageIndex === 0 ? "/" : `/?page=${pageIndex}`;
          return (
            <Link key={label} className="page-nav-link" href={href}>
              {label}
            </Link>
          );
        })}
      </div>

      <div className="page-nav-end">
        {hasNext ? (
          <Button variant="outline" size="sm" asChild>
            <Link href={`/?page=${page + 1}`}>Next</Link>
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
