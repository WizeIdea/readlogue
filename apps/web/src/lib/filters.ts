import { CATEGORIES, UNCATEGORIZED } from "@/lib/categories";
import { SOURCES } from "@/lib/sources";

export const CATEGORY_FILTERS = [...CATEGORIES, UNCATEGORIZED] as const;

export type ItemFilters = {
  categories?: string[];
  includeUncategorized?: boolean;
  sources?: string[];
};

export type FilterSearchParams = {
  page?: string;
  categories?: string;
  sources?: string;
};

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

  if (!hasCategoryFilter && !hasSourceFilter) {
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
  return noCategories || noSources;
}

export function buildFilterQuery(options: {
  page?: number;
  categories?: string[];
  sources?: string[];
}): string {
  const parts: string[] = [];

  if (options.page !== undefined && options.page > 0) {
    parts.push(`page=${options.page}`);
  }

  const allCategories = [...CATEGORY_FILTERS];
  const allSources = [...SOURCES];

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

  return parts.join("&");
}

export function hrefWithFilters(
  page: number,
  categories: string[],
  sources: string[],
): string {
  const query = buildFilterQuery({ page, categories, sources });
  return query ? `/?${query}` : page === 0 ? "/" : `/?page=${page}`;
}
