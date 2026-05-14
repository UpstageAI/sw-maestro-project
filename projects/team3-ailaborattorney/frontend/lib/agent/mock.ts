import type { AnalyzeRequest, AnalyzeResponse, QaRequest, QaResponse, AnalyzeItem, RiskLevel } from "./types";

export async function analyzeMock(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const ruleViolations = (req.rule_result?.violations as Array<any>) ?? [];
  const items: AnalyzeItem[] = ruleViolations.map((v) => ({
    title: v.title ?? v.type ?? "이슈",
    risk_level: (v.risk as RiskLevel) ?? "medium",
    issue: v.message ?? "위반 가능성 있음",
    law_reference: v.lawReference,
    action: "근거 자료를 모아 회사에 정정 요청 또는 노동청 상담을 고려하세요.",
  }));
  if (items.length === 0) {
    items.push({
      title: "특이사항 없음",
      risk_level: "low",
      issue: "룰 엔진 기준 명백한 위반은 발견되지 않았습니다. 다만 본 분석은 자동 검토이며 법적 자문이 아닙니다.",
      action: "의문 사항이 있으면 고용노동부 1350에 문의하세요.",
    });
  }
  return {
    summary: items.length === 1 && items[0].risk_level === "low"
      ? "특이 위반 사항이 발견되지 않았습니다."
      : `${items.length}건의 검토 항목이 발견되었습니다.`,
    items,
    source: "mock",
  };
}

export async function qaMock(req: QaRequest): Promise<QaResponse> {
  return {
    answer: `[mock 응답] "${req.question}"에 대해서는 LangGraph 서버 연결 후 정확한 답변을 받을 수 있습니다. 일반적으로 근로기준법과 최저임금법을 우선 확인하세요.`,
    references: ["근로기준법", "최저임금법"],
    source: "mock",
  };
}
