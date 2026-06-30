"use client";

import { Angry, Frown, Laugh, Meh, Smile, type LucideIcon } from "lucide-react";

import { setCuration } from "@/app/actions";
import {
  nextScore,
  toggleTag,
  type CurationV1,
  type ScoreValue,
} from "@/lib/curation";
import {
  ARTICLE_DOMAINS,
  ARTICLE_TYPES,
} from "@/lib/curation-picklists";

type CurationProps = {
  curation: CurationV1;
  onPatch: (patch: Partial<CurationV1>) => void;
};

const SCORE_ROWS = [
  {
    field: "technical_depth" as const,
    label: "Technical",
    aria: "Technical depth",
  },
  {
    field: "business_relevance" as const,
    label: "Business",
    aria: "Business relevance",
  },
  {
    field: "governance_relevance" as const,
    label: "Governance",
    aria: "Governance relevance",
  },
];

/** MUI-style sentiment scale: red → green (SVG icons respect CSS `color`). */
const SCORE_ICONS: readonly LucideIcon[] = [Angry, Frown, Meh, Smile, Laugh];

export function CurationScores({ curation, onPatch }: CurationProps) {
  return (
    <div className="curation-scores">
      {SCORE_ROWS.map(({ field, label, aria }) => {
        const current = curation[field];
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
                const Icon = SCORE_ICONS[value - 1];
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
                      onPatch({
                        [field]: nextScore(current, value as ScoreValue),
                      })
                    }
                  >
                    <Icon size={20} strokeWidth={2} aria-hidden />
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

export function CurationChips({ curation, onPatch }: CurationProps) {
  const types = curation.article_types ?? [];
  const domains = curation.article_domains ?? [];
  const domainRows = balanceIntoRows([...ARTICLE_DOMAINS], 2, (tag) => tag.length);

  return (
    <div className="curation-chips">
      <div className="curation-chip-group curation-chip-group--types">
        {ARTICLE_TYPES.map((tag) => {
          const active = types.includes(tag);
          return (
            <button
              key={`type-${tag}`}
              type="button"
              className={`curation-chip curation-chip--type${active ? " curation-chip--active" : ""}`}
              aria-pressed={active}
              onClick={() =>
                onPatch({
                  article_types: toggleTag(types, tag),
                })
              }
            >
              {tag}
            </button>
          );
        })}
      </div>
      <div className="curation-chip-group curation-chip-group--domains">
        {domainRows.map((row, rowIndex) => (
          <div key={`domain-row-${rowIndex}`} className="curation-chip-row">
            {row.map((tag) => {
              const active = domains.includes(tag);
              return (
                <button
                  key={`domain-${tag}`}
                  type="button"
                  className={`curation-chip curation-chip--domain${active ? " curation-chip--active" : ""}`}
                  aria-pressed={active}
                  onClick={() =>
                    onPatch({
                      article_domains: toggleTag(domains, tag),
                    })
                  }
                >
                  {tag}
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function balanceIntoRows<T>(
  items: readonly T[],
  rowCount: number,
  weight: (item: T) => number,
): T[][] {
  if (items.length === 0 || rowCount <= 0) {
    return [];
  }

  const perRow = Math.ceil(items.length / rowCount);
  const rows = Array.from({ length: rowCount }, () => [] as T[]);
  const totals = Array.from({ length: rowCount }, () => 0);
  const sorted = [...items].sort((a, b) => weight(b) - weight(a));

  for (const item of sorted) {
    let target = 0;
    for (let index = 1; index < rowCount; index += 1) {
      const rowHasCapacity = rows[index].length < perRow;
      const targetHasCapacity = rows[target].length < perRow;
      if (!rowHasCapacity) {
        continue;
      }
      if (!targetHasCapacity || totals[index] < totals[target]) {
        target = index;
      }
    }
    rows[target].push(item);
    totals[target] += weight(item);
  }

  const order = new Map(items.map((item, index) => [item, index]));
  for (const row of rows) {
    row.sort((a, b) => (order.get(a) ?? 0) - (order.get(b) ?? 0));
  }

  return rows.filter((row) => row.length > 0);
}

export function patchCurationOptimistic(
  itemId: number,
  curation: CurationV1,
  patch: Partial<CurationV1>,
  setCurationLocal: (next: CurationV1) => void,
) {
  const previous = curation;
  const next = { ...curation, v: 1 as const, ...patch };
  setCurationLocal(next);
  void setCuration(itemId, next).catch(() => setCurationLocal(previous));
}
