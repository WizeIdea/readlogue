import { ArticleRow } from "@/components/article-row";
import type { ItemRow } from "@/lib/types";

type Props = {
  items: ItemRow[];
  filtered?: boolean;
};

export function ArticleList({ items, filtered = false }: Props) {
  if (items.length === 0) {
    return (
      <p className="empty-state">
        {filtered
          ? "No articles match the current filters."
          : "No articles yet. Run ingest to populate the index."}
      </p>
    );
  }

  return (
    <ul className="article-list">
      {items.map((item) => (
        <li key={item.id}>
          <ArticleRow item={item} />
        </li>
      ))}
    </ul>
  );
}
