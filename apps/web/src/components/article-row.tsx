"use client";

import { ChevronDown } from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { ItemRow } from "@/lib/types";

import { ArticleActions } from "./article-actions";

type Props = {
  item: ItemRow;
};

export function ArticleRow({ item }: Props) {
  const hasSummary = Boolean(item.summary?.trim());

  return (
    <article className="article-row">
      <div className="article-thumb-wrap">
        {item.hero_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className="article-thumb"
            src={item.hero_image_url}
            alt=""
            loading="lazy"
          />
        ) : (
          <div className="article-thumb-placeholder" aria-hidden />
        )}
      </div>

      <div>
        <h2 className="article-title">
          <a href={item.url} target="_blank" rel="noopener noreferrer">
            {item.title}
          </a>
        </h2>
        <p className="article-meta">
          {item.source_name}
          {item.source_category ? ` · ${item.source_category}` : ""}
          {item.read_at ? " · Read" : " · Unread"}
        </p>

        {hasSummary && (
          <Collapsible>
            <CollapsibleTrigger className="article-summary-toggle">
              Summary
              <ChevronDown size={16} aria-hidden />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <p className="article-summary">{item.summary}</p>
            </CollapsibleContent>
          </Collapsible>
        )}

        <ArticleActions item={item} />
      </div>
    </article>
  );
}
