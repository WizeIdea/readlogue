"use client";

import { useEffect, useState } from "react";
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
  const [rating, setRatingLocal] = useState(item.rating);

  useEffect(() => {
    setRatingLocal(item.rating);
  }, [item.rating]);

  function updateRating(target: "like" | "dislike") {
    const previous = rating;
    const next = nextRating(rating, target);
    setRatingLocal(next);
    void setRating(item.id, next).catch(() => setRatingLocal(previous));
  }

  return (
    <div className="article-actions">
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={`btn-icon ${rating === "like" ? "btn-like-active" : ""}`}
        aria-label="Like"
        aria-pressed={rating === "like"}
        onClick={() => updateRating("like")}
      >
        <ThumbsUp size={20} aria-hidden />
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className={`btn-icon ${rating === "dislike" ? "btn-dislike-active" : ""}`}
        aria-label="Dislike"
        aria-pressed={rating === "dislike"}
        onClick={() => updateRating("dislike")}
      >
        <ThumbsDown size={20} aria-hidden />
      </Button>
    </div>
  );
}
