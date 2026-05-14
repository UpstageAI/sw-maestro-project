import type { KnowledgeCardPayload, SourcePayload } from "@/lib/api"

export const initialSourceForm: SourcePayload = {
  source_type: "txt",
  source_url: "",
  external_id: "",
  title: "",
  content: "",
}

export type IngestionStepId =
  | "validate"
  | "intake"
  | "chunk"
  | "extract"
  | "link"
  | "persist"
  | "refreshWorkspace"
  | "refreshDocuments"
  | "refreshCards"
  | "refreshGraph"
  | "refreshWorkflows"
  | "render"

export type IngestionProgressStatus = "idle" | "running" | "complete" | "error"

export type IngestionProgress = {
  status: IngestionProgressStatus
  activeStep: IngestionStepId
  summary: string
  detail: string
}

export const ingestionFlowSteps: Array<{ id: IngestionStepId; label: string; description: string }> = [
  { id: "validate", label: "Validate input", description: "workspace, source type, title, content 검증" },
  { id: "intake", label: "Source intake", description: "LangGraph source_intake 정규화" },
  { id: "chunk", label: "Chunk & filter", description: "문단 chunk 분할과 재사용성 필터" },
  { id: "extract", label: "Card extraction", description: "결정, 근거, 리스크, 질문 카드 추출" },
  { id: "link", label: "Relation linking", description: "카드 간 관련 관계 계산" },
  { id: "persist", label: "SQLite persist", description: "raw document, chunk, card, relation 저장" },
  { id: "refreshWorkspace", label: "Reload workspace", description: "workspace 목록과 선택 상태 갱신" },
  { id: "refreshDocuments", label: "Reload documents", description: "source 문서 목록 다시 읽기" },
  { id: "refreshCards", label: "Reload cards", description: "추출된 카드 목록 다시 읽기" },
  { id: "refreshGraph", label: "Fetch graph payload", description: "노드와 링크 payload 재구성" },
  { id: "refreshWorkflows", label: "Reload workflow metadata", description: "LangGraph flow registry 갱신" },
  { id: "render", label: "Render update", description: "최신 상태를 UI에 반영" },
]

export const serverIngestionStepIds: IngestionStepId[] = ["validate", "intake", "chunk", "extract", "link", "persist"]

export const initialIngestionProgress: IngestionProgress = {
  status: "idle",
  activeStep: "validate",
  summary: "소스를 저장하면 LangGraph 처리 단계가 여기에 표시됩니다.",
  detail: "긴 텍스트를 넣어도 현재 단계와 완료 결과를 확인할 수 있습니다.",
}

export const cardTypeOptions = ["idea", "problem", "target_user", "hypothesis", "evidence", "decision", "risk", "feature", "question"]
export const cardStatusOptions = ["proposed", "needs_validation", "validated", "rejected", "decided", "needs_review"]
export const confidenceOptions = ["low", "medium", "high"]

export const initialCardForm: KnowledgeCardPayload = {
  card_type: "idea",
  title: "",
  summary: "",
  evidence_quote: "",
  keywords: [],
  tags: ["manual"],
  status: "proposed",
  confidence: "medium",
}

export const sourceContentPlaceholder = `# 신규 기능 아이디어 문서: 멘토링 준비 자동 브리프

## 문제
팀은 멘토링이나 주간 리뷰를 준비할 때 이전 회의록, Notion 기획안, GitHub 이슈, Slack 피드백을 따로 찾아야 한다. 특히 "왜 이 기능을 보류했는지", "어떤 근거로 우선순위를 바꿨는지"가 문서마다 흩어져 있어 신규 팀원이 맥락을 따라오기 어렵다.

## 목표 사용자
- SOMA 프로젝트 팀의 PM/기획 담당자
- 멘토링 전에 의사결정 근거를 빠르게 정리해야 하는 팀원
- 기능 후보, 리스크, 검증 질문을 카드 단위로 재사용하고 싶은 개발자

## 핵심 가설
가설: 원문 문서를 붙여넣으면 결정, 근거, 리스크, 질문을 자동 카드로 나누고 각 카드에 출처 문장을 함께 저장하면 회의 준비 시간이 30% 이상 줄어든다.

## MVP 범위
1. 텍스트/마크다운 기획 문서를 입력한다.
2. 문서를 chunk로 나누고 재사용 가능한 문장만 Knowledge Card로 추출한다.
3. 카드 간 관련 관계를 그래프로 보여준다.
4. 사용자는 저장된 카드와 원문 근거만 기반으로 LLM에 질문한다.

## 성공 기준
- 멘토링 전 10분 안에 이번 주 결정/리스크/검증 질문을 찾을 수 있다.
- 답변에는 반드시 근거 카드와 원문 chunk가 함께 표시된다.
- 근거가 부족하면 LLM이 추측하지 않고 부족한 근거를 명시한다.`

export function parseTokens(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

export function serializeTokens(value: string[]) {
  return value.join(", ")
}
