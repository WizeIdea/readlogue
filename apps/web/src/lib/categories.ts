/** Keep in sync with config.example.yaml categories */
export const CATEGORIES = [
  "Technical Research",
  "AI News",
  "Governance and Policy",
  "Safety and Alignment",
  "Product Updates",
  "Other",
] as const;

export type Category = (typeof CATEGORIES)[number];

export const UNCATEGORIZED = "Uncategorized";
