import type { SupabaseClient } from "@supabase/supabase-js";

import type { ItemFilters } from "@/lib/filters";
import { escapeIlikePattern, tokenizeTitleSearch } from "@/lib/filters";
import type { IngestionFailure, ItemRow } from "@/lib/types";
import { PAGE_SIZE } from "@/lib/types";
import { parseCuration, type CurationV1 } from "@/lib/curation";

type ItemWithSource = {
  id: number;
  fingerprint: string;
  url: string;
  title: string;
  summary: string;
  published_at: string | null;
  created_at: string;
  read_at: string | null;
  rating: string | null;
  category: string | null;
  source_category: string | null;
  hero_image_url: string | null;
  curation: unknown;
  sources: { name: string } | { name: string }[] | null;
};

function mapItem(row: ItemWithSource): ItemRow {
  const source = row.sources;
  const sourceName = Array.isArray(source) ? source[0]?.name : source?.name;
  return {
    id: row.id,
    fingerprint: row.fingerprint,
    url: row.url,
    title: row.title,
    summary: row.summary,
    published_at: row.published_at,
    created_at: row.created_at,
    read_at: row.read_at,
    rating: row.rating,
    category: row.category,
    source_category: row.source_category,
    hero_image_url: row.hero_image_url,
    curation: parseCuration(row.curation),
    source_name: sourceName ?? "Unknown",
  };
}

function categoryFilterIsEmpty(filters: ItemFilters): boolean {
  const categories = filters.categories ?? [];
  const includeUncategorized = filters.includeUncategorized ?? false;
  return categories.length === 0 && !includeUncategorized;
}

export async function listItemsPage(
  supabase: SupabaseClient,
  page: number,
  filters?: ItemFilters,
): Promise<{ items: ItemRow[]; total: number }> {
  if (filters?.categories !== undefined && categoryFilterIsEmpty(filters)) {
    return { items: [], total: 0 };
  }
  if (filters?.sources !== undefined && filters.sources.length === 0) {
    return { items: [], total: 0 };
  }
  if (filters?.read !== undefined && filters.read.length === 0) {
    return { items: [], total: 0 };
  }

  let query = supabase
    .from("items")
    .select("*, sources(name)", { count: "exact" });

  if (filters?.categories !== undefined || filters?.includeUncategorized) {
    const categories = filters.categories ?? [];
    const includeUncategorized = filters.includeUncategorized ?? false;

    if (categories.length > 0 && includeUncategorized) {
      const quoted = categories
        .map((category) => `"${category.replace(/"/g, '\\"')}"`)
        .join(",");
      query = query.or(`category.in.(${quoted}),category.is.null`);
    } else if (categories.length > 0) {
      query = query.in("category", categories);
    } else if (includeUncategorized) {
      query = query.is("category", null);
    }
  }

  if (filters?.sources !== undefined) {
    const { data: sourceRows, error: sourceError } = await supabase
      .from("sources")
      .select("id")
      .in("name", filters.sources);

    if (sourceError) {
      throw new Error(sourceError.message);
    }

    const sourceIds = (sourceRows ?? []).map((row) => row.id);
    if (sourceIds.length === 0) {
      return { items: [], total: 0 };
    }

    query = query.in("source_id", sourceIds);
  }

  if (filters?.read !== undefined) {
    const includeUnread = filters.read.includes("unread");
    const includeRead = filters.read.includes("read");
    if (includeUnread && !includeRead) {
      query = query.is("read_at", null);
    } else if (includeRead && !includeUnread) {
      query = query.not("read_at", "is", null);
    }
  }

  if (filters?.q) {
    const tokens = tokenizeTitleSearch(filters.q);
    if (tokens.length > 0) {
      const orClause = tokens
        .map((token) => `title.ilike.%${escapeIlikePattern(token)}%`)
        .join(",");
      query = query.or(orClause);
    }
  }

  const offset = page * PAGE_SIZE;

  const { data, error, count } = await query
    .order("unread_rank", { ascending: true })
    .order("sort_at", { ascending: false, nullsFirst: false })
    .range(offset, offset + PAGE_SIZE - 1);

  if (error) {
    throw new Error(error.message);
  }

  return {
    items: (data ?? []).map((row) => mapItem(row as ItemWithSource)),
    total: count ?? 0,
  };
}

export async function listIngestionFailures(
  supabase: SupabaseClient,
): Promise<IngestionFailure[]> {
  const { data, error } = await supabase
    .from("ingestion_log")
    .select(
      "id, source_name, article_url, article_fingerprint, message, failure_count",
    )
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(error.message);
  }

  return data ?? [];
}

export async function patchItem(
  supabase: SupabaseClient,
  itemId: number,
  fields: {
    read_at?: string | null;
    rating?: string | null;
    category?: string | null;
    curation?: CurationV1;
  },
): Promise<void> {
  const { error } = await supabase
    .from("items")
    .update({ ...fields, updated_at: new Date().toISOString() })
    .eq("id", itemId);

  if (error) {
    throw new Error(error.message);
  }
}

export function urlIgnoreSubstring(articleUrl: string): string {
  try {
    const path = new URL(articleUrl.trim()).pathname.replace(/\/$/, "");
    if (!path) {
      return articleUrl.trim();
    }
    const segment = path.split("/").pop();
    return segment || path;
  } catch {
    return articleUrl.trim();
  }
}
