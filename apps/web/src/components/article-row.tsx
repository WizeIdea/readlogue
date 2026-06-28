"use client";

import { useEffect, useState, type KeyboardEvent } from "react";

import { setRead } from "@/app/actions";
import type { CurationV1 } from "@/lib/curation";
import { sourceDisplayNameLoose } from "@/lib/sources";
import type { ItemRow } from "@/lib/types";

import { ArticleActions } from "./article-actions";
import {
  CurationChips,
  CurationScores,
  patchCurationOptimistic,
} from "./article-curation";

type Props = {
  item: ItemRow;
};

function formatArticleDate(item: ItemRow): string | null {
  if (!item.published_at) {
    return null;
  }
  return new Date(item.published_at).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatMeta(item: ItemRow): string {
  const parts = [sourceDisplayNameLoose(item.source_name)];
  if (item.source_category) {
    parts.push(item.source_category);
  }
  const articleDate = formatArticleDate(item);
  if (articleDate) {
    parts.push(articleDate);
  }
  return parts.join(" · ");
}

export function ArticleRow({ item }: Props) {
  const [readAt, setReadAt] = useState(item.read_at);
  const [curation, setCuration] = useState<CurationV1>(item.curation);

  useEffect(() => {
    setReadAt(item.read_at);
  }, [item.read_at]);

  useEffect(() => {
    setCuration(item.curation);
  }, [item.curation]);

  const isRead = Boolean(readAt);
  const rowClass = isRead ? "article-row article-row--read" : "article-row";

  function toggleRead() {
    const previous = readAt;
    const nextRead = !isRead;
    setReadAt(nextRead ? new Date().toISOString() : null);
    void setRead(item.id, nextRead).catch(() => setReadAt(previous));
  }

  function onReadTargetKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleRead();
    }
  }

  function onCurationPatch(patch: Partial<CurationV1>) {
    patchCurationOptimistic(item.id, curation, patch, setCuration);
  }

  const curationProps = {
    curation,
    onPatch: onCurationPatch,
  };

  return (
    <article className={rowClass}>
      <div className="article-col-left">
        <ArticleActions item={item} />
        <CurationScores {...curationProps} />
        <CurationChips {...curationProps} />
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
