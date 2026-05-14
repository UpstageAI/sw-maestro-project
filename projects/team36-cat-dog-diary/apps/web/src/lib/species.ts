// ADR-0013 §종 매핑. 백엔드 normalize_species(prompts_loader.py)와 키워드 셋 정합.

export type SpeciesKind = "cat" | "dog" | "other";

const CAT_KEYWORDS = ["고양이", "냥이", "냥", "cat", "kitty", "kitten"];
const DOG_KEYWORDS = ["강아지", "멍멍이", "멍멍", "댕댕이", "dog", "puppy"];

export function normalizeSpecies(text: string): SpeciesKind {
  const s = text.toLowerCase();
  if (CAT_KEYWORDS.some((k) => s.includes(k))) return "cat";
  if (DOG_KEYWORDS.some((k) => s.includes(k))) return "dog";
  return "other";
}
