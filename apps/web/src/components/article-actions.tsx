"use client";

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

  return (
    <div className="article-actions">
      <form action={setRating.bind(null, item.id, "like")}>
        <Button
          type="submit"
          size="sm"
          variant="outline"
          className={item.rating === "like" ? "btn-like-active" : undefined}
        >
          Like
        </Button>
      </form>
      <form action={setRating.bind(null, item.id, "dislike")}>
        <Button
          type="submit"
          size="sm"
          variant="outline"
          className={item.rating === "dislike" ? "btn-dislike-active" : undefined}
        >
          Dislike
        </Button>
      </form>
      <form action={setRead.bind(null, item.id, true)}>
        <Button type="submit" size="sm" variant="outline">
          Mark read
        </Button>
      </form>
      <form action={setRead.bind(null, item.id, false)}>
        <Button type="submit" size="sm" variant="outline">
          Mark unread
        </Button>
      </form>

      <Select
        value={currentCategory}
        onValueChange={(value) => {
          const category = value === UNCATEGORIZED ? null : value;
          void setCategory(item.id, category);
        }}
      >
        <SelectTrigger aria-label="Category">
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
