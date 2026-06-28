"use client";

import { setCuration } from "@/app/actions";
import {
  nextScore,
  SCORE_EMOJI,
  toggleTag,
  type CurationV1,
  type ScoreValue,
} from "@/lib/curation";
import {
  ARTICLE_DOMAINS,
  ARTICLE_TYPES,
} from "@/lib/curation-picklists";
import type { ItemRow } from "@/lib/types";

type Props = {
  item: ItemRow;
};

const SCORE_ROWS = [
  {
    field: "technical_depth" as const,
    label: "T",
    aria: "Technical depth",
  },
  {
    field: "business_relevance" as const,
    label: "B",
    aria: "Business relevance",
  },
  {
    field: "governance_relevance" as const,
    label: "G",
    aria: "Governance relevance",
  },
];

async function patchCuration(item: ItemRow, patch: Partial<CurationV1>) {
  await setCuration(item.id, { ...item.curation, v: 1, ...patch });
}

export function CurationScores({ item }: Props) {
  return (
    <div className="curation-scores">
      {SCORE_ROWS.map(({ field, label, aria }) => {
        const current = item.curation[field];
        return (
          <div
            key={field}
            className="curation-score-row"
            role="radiogroup"
            aria-label={aria}
          >
            <span className="curation-score-label" title={aria}>
              {label}
            </span>
            <div className="curation-score-buttons">
              {([1, 2, 3, 4, 5] as const).map((value) => {
                const selected = current === value;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    aria-label={`${aria}: ${value} of 5`}
                    title={`${value}`}
                    className={`curation-score-btn curation-score-btn--${value}${selected ? " curation-score-btn--selected" : ""}`}
                    onClick={() =>
                      void patchCuration(item, {
                        [field]: nextScore(current, value as ScoreValue),
                      })
                    }
                  >
                    {SCORE_EMOJI[value - 1]}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CurationChips({ item }: Props) {
  const types = item.curation.article_types ?? [];
  const domains = item.curation.article_domains ?? [];

  return (
    <div className="curation-chips">
      {ARTICLE_TYPES.map((tag) => {
        const active = types.includes(tag);
        return (
          <button
            key={`type-${tag}`}
            type="button"
            className={`curation-chip curation-chip--type${active ? " curation-chip--active" : ""}`}
            aria-pressed={active}
            onClick={() =>
              void patchCuration(item, {
                article_types: toggleTag(types, tag),
              })
            }
          >
            {tag}
          </button>
        );
      })}
      {ARTICLE_DOMAINS.map((tag) => {
        const active = domains.includes(tag);
        return (
          <button
            key={`domain-${tag}`}
            type="button"
            className={`curation-chip curation-chip--domain${active ? " curation-chip--active" : ""}`}
            aria-pressed={active}
            onClick={() =>
              void patchCuration(item, {
                article_domains: toggleTag(domains, tag),
              })
            }
          >
            {tag}
          </button>
        );
      })}
    </div>
  );
}
