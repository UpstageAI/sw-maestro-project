// ADR-0011 AI Gateway endpoint. BFF만 호출 (X-Internal-Secret 미들웨어).
// Gateway는 stateless — 응답에 LLM 산출물만 포함하고 session/generation 메타는 BFF가 합성.
//
// 본 패키지(TS)는 BFF 측 fetch 클라이언트의 type-safe 호출용이다. Gateway 측 실제 구현은
// apps/ai-gateway의 Pydantic 모델로 별도 정의되며, 두 정의가 일치하도록 수동 동기화.

import type { Gender, DiaryGenerationResult } from './domain';

// POST /diary/generate
export interface GatewayGenerateRequest {
  session_id: string;
  seq: 1;
  pet_id: string;
  photo_signed_url: string;     // BFF가 사용자 JWT로 발급, TTL 1h (ADR-0009)
  keywords: string;
  honorific: string;
  species: string;
  gender: Gender;
  recent_diaries: string[];     // BFF가 fetch한 최근 3개 diary_text
}
export type GatewayGenerateResponse = DiaryGenerationResult;

// POST /diary/regenerate
export interface GatewayRegenerateRequest {
  session_id: string;
  seq: number;                  // 2~4
  pet_id: string;
  photo_signed_url: string;
  keywords: string;
  honorific: string;
  species: string;
  gender: Gender;
  recent_diaries: string[];
  previous_diary_text: string;
  feedback?: string;            // 1~500자, NULL 허용
  vision_description?: string;  // 직전 generation의 vision 결과 echo. 있으면 graph가 vision 호출 skip.
}
export type GatewayRegenerateResponse = DiaryGenerationResult;

// GET /health — X-Internal-Secret 검증 제외 (Railway healthcheck용).
export interface HealthResponse {
  status: 'ok';
}
