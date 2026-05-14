import { describe, expect, it } from "vitest";
import { buildChatSuggestions } from "../components/chat/suggestions";

describe("buildChatSuggestions", () => {
  it("suggestions_include_category_and_report_context", () => {
    const suggestions = buildChatSuggestions({
      category: "테크",
      page: "feed",
      topKeyword: "AI",
    });

    expect(suggestions[0]).toBe("AI 관련 핵심 기사 알려줘");
    expect(suggestions.length).toBeLessThanOrEqual(3);
    for (const suggestion of suggestions) {
      expect(suggestion.length).toBeLessThanOrEqual(40);
    }
  });
});
