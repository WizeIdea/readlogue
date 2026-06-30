"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { signOut } from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  buildFilterQuery,
  CATEGORY_FILTERS,
  READ_FILTERS,
  selectedFromParam,
  type ReadFilter,
} from "@/lib/filters";
import { SOURCES, sourceDisplayName } from "@/lib/sources";

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
  const readParam = searchParams.get("read") ?? undefined;
  const qParam = searchParams.get("q") ?? "";

  const [searchDraft, setSearchDraft] = useState(qParam);

  useEffect(() => {
    setSearchDraft(qParam);
  }, [qParam]);

  const selectedCategories = selectedFromParam(
    categoriesParam,
    CATEGORY_FILTERS,
  );
  const selectedSources = selectedFromParam(sourcesParam, SOURCES);
  const selectedRead = selectedFromParam(readParam, READ_FILTERS);

  function navigate(
    categories: string[],
    sources: string[],
    read: ReadFilter[],
    q?: string,
  ) {
    const trimmedQ = (q ?? searchDraft).trim();
    const query = buildFilterQuery({
      page: 0,
      categories,
      sources,
      read,
      q: trimmedQ || undefined,
    });
    const href = query ? `${pathname}?${query}` : pathname;
    router.push(href);
  }

  useEffect(() => {
    if (searchDraft === qParam) {
      return;
    }
    const timer = window.setTimeout(() => {
      navigate(selectedCategories, selectedSources, selectedRead, searchDraft);
    }, 300);
    return () => window.clearTimeout(timer);
    // Only debounce typing; filter pill clicks call navigate() directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- selected* read from latest closure on timer fire
  }, [searchDraft, qParam]);

  function toggleCategory(category: (typeof CATEGORY_FILTERS)[number]) {
    navigate(
      toggleValue(selectedCategories, category),
      selectedSources,
      selectedRead,
    );
  }

  function toggleSource(source: (typeof SOURCES)[number]) {
    navigate(
      selectedCategories,
      toggleValue(selectedSources, source),
      selectedRead,
    );
  }

  function toggleRead(value: ReadFilter) {
    navigate(
      selectedCategories,
      selectedSources,
      toggleValue(selectedRead, value),
    );
  }

  return (
    <aside className="filter-sidebar" aria-label="Filters">
      <div className="filter-sidebar-brand">
        <Link href="/" className="filter-sidebar-brand-link">
          <Image
            src="/readlogue.svg"
            alt=""
            width={36}
            height={36}
            className="filter-sidebar-logo"
            priority
          />
          <span className="filter-sidebar-title">ReadLogue</span>
        </Link>
      </div>

      <div className="filter-search">
        <label className="filter-search-label" htmlFor="filter-title-search">
          Search titles
        </label>
        <div className="filter-search-row">
          <input
            id="filter-title-search"
            type="search"
            className="filter-search-input"
            placeholder="Search titles…"
            aria-label="Search titles"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
          />
          {searchDraft.trim() ? (
            <button
              type="button"
              className="filter-search-clear"
              aria-label="Clear search"
              onClick={() => setSearchDraft("")}
            >
              ×
            </button>
          ) : null}
        </div>
      </div>

      <FilterSection
        title="Read status"
        onSelectAll={() =>
          navigate(selectedCategories, selectedSources, [...READ_FILTERS])
        }
        onClearAll={() =>
          navigate(selectedCategories, selectedSources, [])
        }
      >
        <FilterPill
          label="Unread"
          active={selectedRead.includes("unread")}
          onClick={() => toggleRead("unread")}
        />
        <FilterPill
          label="Read"
          active={selectedRead.includes("read")}
          onClick={() => toggleRead("read")}
        />
      </FilterSection>

      <FilterSection
        title="Categories"
        onSelectAll={() =>
          navigate([...CATEGORY_FILTERS], selectedSources, selectedRead)
        }
        onClearAll={() => navigate([], selectedSources, selectedRead)}
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
        onSelectAll={() =>
          navigate(selectedCategories, [...SOURCES], selectedRead)
        }
        onClearAll={() => navigate(selectedCategories, [], selectedRead)}
      >
        {SOURCES.map((source) => (
          <FilterPill
            key={source}
            label={sourceDisplayName(source)}
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
