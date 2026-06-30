import type { CurationV1 } from "@/lib/curation";

export type ItemRow = {
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
  curation: CurationV1;
  source_name: string;
};

export type IngestionFailure = {
  id: number;
  source_name: string;
  article_url: string;
  article_fingerprint: string;
  article_title: string | null;
  message: string;
  failure_count: number;
};

export const PAGE_SIZE = 25;
