"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { signOut } from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  buildFilterQuery,
  CATEGORY_FILTERS,
  selectedFromParam,
} from "@/lib/filters";
import { SOURCES } from "@/lib/sources";

function toggleValue<T extends string>(selected: T[], value: T): T[] {
  return selected.includes(value)
    ? selected.filter((item) => item !== value)
    : [...selected, value];
}

export function FilterSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const categoriesParam = searchParams.get("categories") ?? undefined;
  const sourcesParam = searchParams.get("sources") ?? undefined;

  const selectedCategories = selectedFromParam(
    categoriesParam,
    CATEGORY_FILTERS,
  );
  const selectedSources = selectedFromParam(sourcesParam, SOURCES);

  function navigate(categories: string[], sources: string[]) {
    const query = buildFilterQuery({ page: 0, categories, sources });
    const href = query ? `${pathname}?${query}` : pathname;
    router.push(href);
  }

  function toggleCategory(category: (typeof CATEGORY_FILTERS)[number]) {
    navigate(
      toggleValue(selectedCategories, category),
      selectedSources,
    );
  }

  function toggleSource(source: (typeof SOURCES)[number]) {
    navigate(
      selectedCategories,
      toggleValue(selectedSources, source),
    );
  }

  return (
    <aside className="filter-sidebar" aria-label="Filters">
      <div className="filter-sidebar-brand">
        <Link href="/">
          <Image
            src="/readlogue.png"
            alt="ReadLogue"
            width={160}
            height={40}
            className="filter-sidebar-logo"
            priority
          />
        </Link>
      </div>

      <FilterSection
        title="Categories"
        onSelectAll={() => navigate([...CATEGORY_FILTERS], selectedSources)}
        onClearAll={() => navigate([], selectedSources)}
      >
        {CATEGORY_FILTERS.map((category) => (
          <FilterPill
            key={category}
            label={category}
            active={selectedCategories.includes(category)}
            onClick={() => toggleCategory(category)}
          />
        ))}
      </FilterSection>

      <FilterSection
        title="Sources"
        onSelectAll={() => navigate(selectedCategories, [...SOURCES])}
        onClearAll={() => navigate(selectedCategories, [])}
      >
        {SOURCES.map((source) => (
          <FilterPill
            key={source}
            label={source}
            active={selectedSources.includes(source)}
            onClick={() => toggleSource(source)}
          />
        ))}
      </FilterSection>

      <div className="filter-sidebar-footer">
        <form action={signOut}>
          <Button type="submit" variant="outline" size="sm" className="filter-sign-out">
            Sign out
          </Button>
        </form>
      </div>
    </aside>
  );
}

function FilterSection({
  title,
  onSelectAll,
  onClearAll,
  children,
}: {
  title: string;
  onSelectAll: () => void;
  onClearAll: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="filter-section">
      <h2 className="filter-section-title">{title}</h2>
      <div className="filter-pills">{children}</div>
      <div className="filter-section-actions">
        <button type="button" className="filter-action-link" onClick={onSelectAll}>
          Select all
        </button>
        <span className="filter-action-sep" aria-hidden>
          |
        </span>
        <button type="button" className="filter-action-link" onClick={onClearAll}>
          Clear all
        </button>
      </div>
    </section>
  );
}

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`filter-pill${active ? " filter-pill--active" : ""}`}
      aria-pressed={active}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
