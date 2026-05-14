// BFF 에러 응답 스키마. 11 endpoint 모두 4xx/5xx에 본 형태로 응답.

export type ErrorCode =
  | 'UNAUTHENTICATED'         // 401 — /login redirect
  | 'NOT_FOUND'               // 404 — / redirect + 토스트 (자원 종류는 endpoint 컨텍스트로 추론)
  | 'VALIDATION_FAILED'       // 422 — form 인라인 메시지
  | 'PET_DELETED'             // 409 — soft-deleted 펫에 일기 생성 시도
  | 'DAILY_QUOTA_EXCEEDED'    // 429 — 오늘 신규 5회 초과
  | 'REGEN_QUOTA_EXCEEDED'    // 429 — 세션 재생성 3회 초과
  | 'GATEWAY_ERROR'           // 502/504 — Gateway/OpenAI 실패
  | 'INTERNAL_ERROR';         // 500 — 그 외

export interface ErrorBody {
  error: {
    code: ErrorCode;
    message: string;
  };
}
