export const CATEGORY_IDS = ["tech", "economy", "policy", "issue"] as const;

export type CategoryId = (typeof CATEGORY_IDS)[number];

const categoryIdSet = new Set<string>(CATEGORY_IDS);
const categoryLabels = {
  tech: "테크",
  economy: "경제",
  policy: "정책",
  issue: "이슈",
} satisfies Record<CategoryId, string>;

export type CategoryLabel = (typeof categoryLabels)[CategoryId];

const categoryBadgeClasses: Record<CategoryLabel, string> = {
  테크: "bg-brand-50 text-brand-500",
  경제: "bg-[#eef4ff] text-economy",
  정책: "bg-[#ecfdf5] text-policy",
  이슈: "bg-[#f3eeff] text-issue",
};

export function isCategoryId(value: string): value is CategoryId {
  return categoryIdSet.has(value);
}

export function parseCategoryQuery(value: string | null | undefined): CategoryId[] {
  if (!value) {
    return [];
  }

  const seen = new Set<CategoryId>();
  const categories: CategoryId[] = [];
  for (const part of value.split(",")) {
    const categoryId = part.trim();
    if (isCategoryId(categoryId) && !seen.has(categoryId)) {
      categories.push(categoryId);
      seen.add(categoryId);
    }
  }

  return categories;
}

export function categoryQuery(categories: readonly CategoryId[]) {
  return categories.join(",");
}

export function categoryLabel(category: CategoryId) {
  return categoryLabels[category];
}

export function categoryBadgeClass(category: string) {
  if (category in categoryBadgeClasses) {
    return categoryBadgeClasses[category as CategoryLabel];
  }

  return categoryBadgeClasses.테크;
}

export function feedHref(categories: readonly CategoryId[]) {
  const params = new URLSearchParams({
    categories: categoryQuery(categories),
    refresh: "1",
  });

  return `/feed?${params.toString()}`;
}
