"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";

import { setRating } from "@/app/actions";
import { Button } from "@/components/ui/button";
import type { ItemRow } from "@/lib/types";

type Props = {
  item: ItemRow;
};

function nextRating(
  current: string | null,
  target: "like" | "dislike",
): "like" | "dislike" | null {
  return current === target ? null : target;
}

export function ArticleActions({ item }: Props) {
  return (
    <div className="article-actions">
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={`btn-icon ${item.rating === "like" ? "btn-like-active" : ""}`}
        aria-label="Like"
        aria-pressed={item.rating === "like"}
        onClick={() => void setRating(item.id, nextRating(item.rating, "like"))}
      >
        <ThumbsUp size={16} aria-hidden />
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={`btn-icon ${item.rating === "dislike" ? "btn-dislike-active" : ""}`}
        aria-label="Dislike"
        aria-pressed={item.rating === "dislike"}
        onClick={() =>
          void setRating(item.id, nextRating(item.rating, "dislike"))
        }
      >
        <ThumbsDown size={16} aria-hidden />
      </Button>
    </div>
  );
}
