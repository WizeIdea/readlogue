import { CATEGORIES, UNCATEGORIZED } from "@/lib/categories";
import { SOURCES } from "@/lib/sources";

export const CATEGORY_FILTERS = [...CATEGORIES, UNCATEGORIZED] as const;

export const READ_FILTERS = ["read", "unread"] as const;

export type ReadFilter = (typeof READ_FILTERS)[number];

export type ItemFilters = {
  categories?: string[];
  includeUncategorized?: boolean;
  sources?: string[];
  read?: ReadFilter[];
  q?: string;
};

export type FilterSearchParams = {
  page?: string;
  categories?: string;
  sources?: string;
  read?: string;
  q?: string;
};

export type FilterSelection = {
  categories: string[];
  sources: string[];
  read: ReadFilter[];
  q?: string;
};

/** Split search input into title tokens (any-word OR match). */
export function tokenizeTitleSearch(query: string): string[] {
  return query
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

/** Escape special characters for Postgres ILIKE patterns. */
export function escapeIlikePattern(value: string): string {
  return value.replace(/[%_\\]/g, "\\$&");
}

export function firstSearchParam(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

function splitParam(value: string | undefined): string[] {
  if (value === undefined) {
    return [];
  }
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

export function selectedFromParam<T extends string>(
  param: string | undefined,
  all: readonly T[],
): T[] {
  if (param === undefined) {
    return [...all];
  }
  if (param === "") {
    return [];
  }
  const allowed = new Set(all);
  return splitParam(param).filter((value): value is T =>
    allowed.has(value as T),
  );
}

export function parseItemFilters(
  params: FilterSearchParams,
): ItemFilters | undefined {
  const hasCategoryFilter = params.categories !== undefined;
  const hasSourceFilter = params.sources !== undefined;
  const hasReadFilter = params.read !== undefined;
  const trimmedQ = params.q?.trim() ?? "";
  const hasSearchFilter = trimmedQ.length > 0;

  if (
    !hasCategoryFilter &&
    !hasSourceFilter &&
    !hasReadFilter &&
    !hasSearchFilter
  ) {
    return undefined;
  }

  const filters: ItemFilters = {};

  if (hasCategoryFilter) {
    const selected = selectedFromParam(params.categories, CATEGORY_FILTERS);
    filters.categories = selected.filter((value) => value !== UNCATEGORIZED);
    filters.includeUncategorized = selected.includes(UNCATEGORIZED);
  }

  if (hasSourceFilter) {
    filters.sources = selectedFromParam(params.sources, SOURCES);
  }

  if (hasReadFilter) {
    filters.read = selectedFromParam(params.read, READ_FILTERS);
  }

  if (hasSearchFilter) {
    filters.q = trimmedQ;
  }

  return filters;
}

export function isFiltersEmpty(filters: ItemFilters | undefined): boolean {
  if (!filters) {
    return false;
  }
  const noCategories =
    filters.categories !== undefined &&
    filters.categories.length === 0 &&
    !filters.includeUncategorized;
  const noSources =
    filters.sources !== undefined && filters.sources.length === 0;
  const noRead = filters.read !== undefined && filters.read.length === 0;
  return noCategories || noSources || noRead;
}

export function buildFilterQuery(options: {
  page?: number;
  categories?: string[];
  sources?: string[];
  read?: ReadFilter[];
  q?: string;
}): string {
  const parts: string[] = [];

  if (options.page !== undefined && options.page > 0) {
    parts.push(`page=${options.page}`);
  }

  const trimmedQ = options.q?.trim();
  if (trimmedQ) {
    parts.push(`q=${encodeURIComponent(trimmedQ)}`);
  }

  const allCategories = [...CATEGORY_FILTERS];
  const allSources = [...SOURCES];
  const allRead = [...READ_FILTERS];

  if (
    options.categories !== undefined &&
    options.categories.length < allCategories.length
  ) {
    parts.push(
      `categories=${encodeURIComponent(options.categories.join(","))}`,
    );
  }

  if (
    options.sources !== undefined &&
    options.sources.length < allSources.length
  ) {
    parts.push(`sources=${encodeURIComponent(options.sources.join(","))}`);
  }

  if (options.read !== undefined && options.read.length < allRead.length) {
    parts.push(`read=${encodeURIComponent(options.read.join(","))}`);
  }

  return parts.join("&");
}

export function hrefWithFilters(
  page: number,
  selection: FilterSelection,
): string {
  const query = buildFilterQuery({
    page,
    categories: selection.categories,
    sources: selection.sources,
    read: selection.read,
    q: selection.q,
  });
  return query ? `/?${query}` : page === 0 ? "/" : `/?page=${page}`;
}
