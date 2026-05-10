export type RiskLevel = "low" | "medium" | "high";

export interface AnalyzeItem {
  title: string;
  risk_level: RiskLevel;
  issue: string;
  law_reference?: string;
  action?: string;
}

export interface AnalyzeResponse {
  summary: string;
  items: AnalyzeItem[];
  source: "langgraph" | "mock";
}

export interface AnalyzeRequest {
  contract_data: Record<string, unknown>;
  rule_result: Record<string, unknown>;
  user_info?: Record<string, unknown>;
}

export interface QaRequest {
  question: string;
  context?: Record<string, unknown>;
}

export interface QaResponse {
  answer: string;
  references?: string[];
  source: "langgraph" | "mock";
}
