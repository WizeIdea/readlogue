import { ArticleRow } from "@/components/article-row";
import type { ItemRow } from "@/lib/types";

type Props = {
  items: ItemRow[];
};

export function ArticleList({ items }: Props) {
  if (items.length === 0) {
    return <p className="empty-state">No articles yet. Run ingest to populate the index.</p>;
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
