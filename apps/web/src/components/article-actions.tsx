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

export function ArticleActions({ item }: Props) {
  const currentCategory = item.category ?? UNCATEGORIZED;
  const isRead = Boolean(item.read_at);

  return (
    <div className="article-actions">
      <div className="article-actions-row">
        <form action={setRating.bind(null, item.id, "like")}>
          <Button
            type="submit"
            size="sm"
            variant="outline"
            className={`btn-icon ${item.rating === "like" ? "btn-like-active" : ""}`}
            aria-label="Like"
          >
            <ThumbsUp size={16} aria-hidden />
          </Button>
        </form>
        <form action={setRating.bind(null, item.id, "dislike")}>
          <Button
            type="submit"
            size="sm"
            variant="outline"
            className={`btn-icon ${item.rating === "dislike" ? "btn-dislike-active" : ""}`}
            aria-label="Dislike"
          >
            <ThumbsDown size={16} aria-hidden />
          </Button>
        </form>
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
