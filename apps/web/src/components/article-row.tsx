"use client";

import type { ItemRow } from "@/lib/types";

import { ArticleActions } from "./article-actions";

type Props = {
  item: ItemRow;
};

function formatMeta(item: ItemRow): string {
  if (item.source_category) {
    return `${item.source_name} · ${item.source_category}`;
  }
  return item.source_name;
}

export function ArticleRow({ item }: Props) {
  const rowClass = item.read_at ? "article-row article-row--read" : "article-row";

  return (
    <article className={rowClass}>
      <div className="article-sidebar">
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
        <p className="article-meta">{formatMeta(item)}</p>
        <ArticleActions item={item} />
      </div>

      <div className="article-main">
        <h2 className="article-title">
          <a href={item.url} target="_blank" rel="noopener noreferrer">
            {item.title}
          </a>
        </h2>
        {item.summary?.trim() && (
          <p className="article-summary">{item.summary}</p>
        )}
      </div>
    </article>
  );
}
