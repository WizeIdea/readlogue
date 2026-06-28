/** Human curation labels stored in items.curation (jsonb). Schema version 1. */

export type CurationV1 = {
  v?: 1;
  article_types?: string[];
  article_domains?: string[];
  technical_depth?: 1 | 2 | 3 | 4 | 5;
  business_relevance?: 1 | 2 | 3 | 4 | 5;
  governance_relevance?: 1 | 2 | 3 | 4 | 5;
};

export const EMPTY_CURATION: CurationV1 = {};

export function parseCuration(raw: unknown): CurationV1 {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return EMPTY_CURATION;
  }
  return raw as CurationV1;
}

export function isEmptyCuration(curation: CurationV1): boolean {
  return (
    !curation.article_types?.length &&
    !curation.article_domains?.length &&
    curation.technical_depth == null &&
    curation.business_relevance == null &&
    curation.governance_relevance == null
  );
}
