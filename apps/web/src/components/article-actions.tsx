"use client";

import { Mail, MailOpen, ThumbsDown, ThumbsUp } from "lucide-react";

import { setCategory, setRating, setRead } from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CATEGORIES, UNCATEGORIZED } from "@/lib/categories";
import type { ItemRow } from "@/lib/types";

type Props = {
  item: ItemRow;
};

const categoryOptions = [UNCATEGORIZED, ...CATEGORIES];

function nextRating(
  current: string | null,
  target: "like" | "dislike",
): "like" | "dislike" | null {
  return current === target ? null : target;
}

export function ArticleActions({ item }: Props) {
  const currentCategory = item.category ?? UNCATEGORIZED;
  const isRead = Boolean(item.read_at);

  return (
    <div className="article-actions">
      <div className="article-actions-row">
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

      <div className="article-actions-row">
        <form action={setRead.bind(null, item.id, true)}>
          <Button
            type="submit"
            size="sm"
            variant="outline"
            className="btn-icon"
            aria-label="Mark read"
          >
            <Mail size={16} aria-hidden />
          </Button>
        </form>
        <form action={setRead.bind(null, item.id, false)}>
          <Button
            type="submit"
            size="sm"
            variant="outline"
            className={`btn-icon ${isRead ? "btn-read-active" : ""}`}
            aria-label="Mark unread"
          >
            <MailOpen size={16} aria-hidden />
          </Button>
        </form>
      </div>

      <Select
        value={currentCategory}
        onValueChange={(value) => {
          const category = value === UNCATEGORIZED ? null : value;
          void setCategory(item.id, category);
        }}
      >
        <SelectTrigger className="select-trigger-sidebar" aria-label="Category">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent>
          {categoryOptions.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
