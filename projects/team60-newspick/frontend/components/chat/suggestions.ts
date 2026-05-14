export type ChatSuggestionContext = {
  category?: string;
  page: "feed" | "report";
  topKeyword?: string;
};

const MAX_SUGGESTIONS = 3;
const MAX_SUGGESTION_LENGTH = 40;

export function buildChatSuggestions(context: ChatSuggestionContext) {
  const topKeyword = context.topKeyword?.trim();
  const category = context.category?.trim();
  const suggestions = [
    topKeyword ? `${topKeyword} 관련 핵심 기사 알려줘` : "",
    category ? `${category} 흐름 요약해줘` : "",
    context.page === "report" ? "오늘 리포트 핵심만 정리해줘" : "오늘 뉴스 요약해줘",
  ];

  return [...new Set(suggestions)]
    .filter((suggestion) => suggestion.length > 0 && suggestion.length <= MAX_SUGGESTION_LENGTH)
    .slice(0, MAX_SUGGESTIONS);
}
