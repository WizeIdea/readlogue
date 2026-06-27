import type { SupabaseClient } from "@supabase/supabase-js";

import type { IngestionFailure, ItemRow } from "@/lib/types";
import { PAGE_SIZE } from "@/lib/types";

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
    source_name: sourceName ?? "Unknown",
  };
}

export async function listItemsPage(
  supabase: SupabaseClient,
  page: number,
): Promise<{ items: ItemRow[]; total: number }> {
  const offset = page * PAGE_SIZE;

  const { data, error, count } = await supabase
    .from("items")
    .select("*, sources(name)", { count: "exact" })
    .order("read_at", { ascending: true, nullsFirst: true })
    .order("published_at", { ascending: false, nullsFirst: false })
    .order("created_at", { ascending: false })
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
