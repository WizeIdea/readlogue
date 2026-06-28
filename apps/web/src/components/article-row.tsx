"use client";

import type { KeyboardEvent } from "react";

import { setRead } from "@/app/actions";
import type { ItemRow } from "@/lib/types";

import { ArticleActions } from "./article-actions";
import { CurationChips, CurationScores } from "./article-curation";

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
  const isRead = Boolean(item.read_at);

  function toggleRead() {
    void setRead(item.id, !isRead);
  }

  function onReadTargetKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleRead();
    }
  }

  return (
    <article className={rowClass}>
      <div className="article-col-left">
        <ArticleActions item={item} />
        <CurationScores item={item} />
      </div>

      <div className="article-col-middle">
        <p className="article-meta">{formatMeta(item)}</p>
        <div
          className="article-read-target"
          role="button"
          tabIndex={0}
          aria-pressed={isRead}
          aria-label={isRead ? "Mark as unread" : "Mark as read"}
          onClick={toggleRead}
          onKeyDown={onReadTargetKeyDown}
        >
          <h2 className="article-title">
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              {item.title}
            </a>
          </h2>
          {item.summary?.trim() && (
            <p className="article-summary">{item.summary}</p>
          )}
        </div>
        <CurationChips item={item} />
      </div>

      <div className="article-col-hero">
        <div className="article-hero-wrap">
          {item.hero_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              className="article-hero"
              src={item.hero_image_url}
              alt=""
              loading="lazy"
            />
          ) : (
            <div className="article-hero-placeholder" aria-hidden />
          )}
        </div>
      </div>
    </article>
  );
}
