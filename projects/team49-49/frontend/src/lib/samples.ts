import type { SourcePayload } from "@/lib/api"

export const sourceTypes = [
  { value: "manual", label: "Manual", hint: "직접 붙여넣은 메모. content 필드에 텍스트를 채워주세요." },
  { value: "notion", label: "Notion", hint: "page URL 또는 Notion export 본문. URL만 넣으면 ICH_NOTION_TOKEN으로 자동 fetch." },
  { value: "github", label: "GitHub", hint: "raw/blob/issue/pull URL. 공개 raw는 토큰 없이 동작, private은 ICH_GITHUB_TOKEN 필요." },
  { value: "web", label: "Web Link", hint: "http/https 읽기 가능한 페이지. 본문이 비어 있으면 HTML을 텍스트로 정제." },
  { value: "slack", label: "Slack", hint: "thread URL 또는 channel:ts. ICH_SLACK_TOKEN 필요." },
  { value: "linear", label: "Linear", hint: "issue URL 또는 identifier. ICH_LINEAR_TOKEN 필요." },
  { value: "mcp", label: "MCP Resource", hint: "MCP resource URI. ICH_MCP_SERVER_URL (+ ICH_MCP_ACCESS_TOKEN) 필요." },
  { value: "md", label: "Markdown", hint: ".md / .markdown 본문" },
  { value: "txt", label: "Text", hint: ".txt 본문" },
  { value: "pdf", label: "PDF", hint: "텍스트 기반 PDF. 스캔 PDF는 OCR이 없으므로 실패할 수 있음." },
  { value: "csv", label: "CSV", hint: "pandas로 정규화한 후 행 단위 chunk로 저장." },
]

export const sampleSources: SourcePayload[] = [
  {
    source_type: "notion",
    source_url: "https://notion.so/team/ideation-context-hub-architecture",
    external_id: "demo:strategy:architecture",
    title: "demo-strategy-architecture.md",
    content:
      "Decision: Ideation Context Hub should start with SQLite plus a relation table instead of adding a GraphDB for the first demo.\n\nEvidence: the product needs fast source intake, searchable cards, and explainable links before it needs deep graph traversal. A SQLite-backed relation table can store source-to-card, card-to-card, and decision-to-evidence edges with lower operational risk.\n\nQuestion: keep the schema easy to migrate if relation depth, graph visualization, or multi-hop recommendations become core workflows.",
  },
  {
    source_type: "manual",
    source_url: "",
    external_id: "demo:mentor:feedback",
    title: "demo-mentor-feedback.md",
    content:
      "Evidence: mentor feedback says the demo should prove that a new teammate can understand why the project chose a SQLite relation table over GraphDB without reading every note.\n\nRisk: 중복 카드 duplicate cards will damage trust. If the same idea appears in a strategy memo, a Slack thread, and GitHub notes, the system should merge or flag likely duplicates while preserving each source citation.\n\nFeature: ask, \"Why not GraphDB now?\" and show a grounded answer with linked cards and original source snippets.",
  },
  {
    source_type: "github",
    source_url: "https://github.com/team/ideation-context-hub/blob/main/docs/intake-pipeline.md",
    external_id: "demo:engineering:intake",
    title: "demo-engineering-intake.md",
    content:
      "Feature: source intake should normalize manual notes, GitHub docs, web pages, Slack threads, and Notion pages into one SourcePayload contract.\n\nDecision: fetch or accept content, parse metadata, chunk long text, extract candidate cards, attach source spans, dedupe near-identical cards, then persist both cards and source relationships.\n\nEvidence: card extraction must keep enough source context for grounded LLM search to quote or summarize evidence accurately.",
  },
  {
    source_type: "github",
    source_url: "https://github.com/team/ideation-context-hub/blob/main/docs/relation-performance.md",
    external_id: "demo:engineering:performance",
    title: "demo-engineering-performance.md",
    content:
      "Problem: relation linking can become the slowest step if every new card is compared with every existing card.\n\nDecision: use keyword overlap and embedding similarity to produce a small candidate set, then write typed edges such as supports, contradicts, duplicates, refines, and depends_on into the SQLite relation table.\n\nFeature: demo imports should show progress per stage and keep linking responsive for dozens of sources and hundreds of cards.",
  },
  {
    source_type: "web",
    source_url: "https://example.com/ideation-context-hub-grounded-search",
    external_id: "demo:search:grounded-llm",
    title: "demo-search-grounded-llm.txt",
    content:
      "Feature: 근거 기반 답변 grounded LLM answers must be grounded in stored source chunks and extracted cards, not general model memory.\n\nEvidence: a query about GraphDB tradeoffs retrieves the architecture decision, mentor feedback, and performance notes, then answers with citations back to the source payloads.\n\nRisk: if chunks are too coarse, the answer cites large documents without proving the claim. If chunks are too small, the model loses the reasoning chain across related cards.",
  },
  {
    source_type: "slack",
    source_url: "https://slack.com/archives/C12345678/p1712345678901234",
    external_id: "demo:ux:workflow",
    title: "demo-ux-workflow.md",
    content:
      "Problem: users need visible progress from source added to chunks created, cards extracted, duplicates flagged, relations linked, and search-ready.\n\nFeature: paste a source, watch stage-level status update, inspect extracted cards, approve or merge duplicate-card candidates, then open the relationship graph for the project decision.\n\nRisk: if processing feels like a black box, users will not trust the extracted cards or the grounded LLM answer even when the backend is correct.",
  },
]
