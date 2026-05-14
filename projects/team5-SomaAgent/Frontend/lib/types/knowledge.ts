// docs/features/api/knowledge.md · OpenAPI KnowledgeAskRequest / KnowledgeAskResponse

export type KnowledgeSourceType =
  | "NOTICE"
  | "NOTICE_PDF"
  | "MENTORING"
  | "WEBEX_MESSAGE";

export type KnowledgeAskRequest = {
  query: string;
  source_types?: KnowledgeSourceType[] | null;
  official_only?: boolean;
  room_name?: string | null;
  k?: number;
};

export type KnowledgeSource = {
  chunk_id: string;
  source_type: KnowledgeSourceType;
  source_id: string;
  title: string;
  text: string;
  official: boolean;
  score: number;
  created_at?: string | null;
  source_url?: string | null;
  room_name?: string | null;
};

export type KnowledgeAskResponse = {
  answer: string;
  sources: KnowledgeSource[];
  llm_used: boolean;
  llm_error?: string | null;
};
