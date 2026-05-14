# AI 진행 (Python LangGraph)

> 디렉토리: `ai/`. Solar API 호출은 langchain-upstage SDK의 가짜 모드 또는 VCR 카세트로 모킹한다.

## 초기 시드 (M2까지)

- [x] **AI-001** FastAPI 스켈레톤 + `/health` 엔드포인트 + pytest httpx 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-001.md)
- [x] **AI-002** Solar `ChatUpstage` 호출 헬퍼 (1문장 입력 → 1문장 출력) + VCR 모킹 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-002.md)
- [x] **AI-003** `UpstageEmbeddings` 헬퍼 (passage/query 분리) + 4096차원 출력 검증 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-003.md)
- [x] **AI-004** LangGraph 빈 그래프 + 1개 노드(Collector 모킹) + State 정의 + pytest — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-004.md)
- [x] **AI-005** RSS 1개 피드 가져오기(feedparser) + Collector 노드 통합 + 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-005.md)
- [x] **AI-006** Deduplicator 노드 (URL 기준) + 단위 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-006.md)
- [x] **AI-007** `/refresh-stream` SSE 엔드포인트 — 가짜 그래프가 `step`/`done` 이벤트 발행 + 통합 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-007.md)
- [x] **AI-008** Persistor 노드 — asyncpg로 DB에 빈 `article` 행 1건 INSERT (Testcontainers PG) — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-008.md)

## M3 — 기사 해피 패스

- [x] **AI-009** 기사 본문 추출 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-009.md)
- [x] **AI-010** 요약 생성 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-010.md)
- [x] **AI-011** 요약 검증 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-011.md)
- [x] **AI-012** 요약 저장 업데이트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-012.md)
- [x] **AI-013** Embedding 생성과 pgvector 저장 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-013.md)
- [x] **AI-014** 저장된 요약 기사 ID 반환 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-014.md)

## M4 — 인라인 퀴즈

- [x] **AI-015** 퀴즈 생성 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-015.md)
- [x] **AI-016** 퀴즈 스키마 파서 검증 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-016.md)
- [x] **AI-017** 기사와 퀴즈 함께 저장 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-017.md)

## M5 — 데일리 리포트

- [x] **AI-018** 기사 클러스터링 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-018.md)
- [x] **AI-019** 리포트 브리핑/흐름 생성 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-019.md)
- [x] **AI-020** 리포트 키워드 가중치 계산 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-020.md)
- [x] **AI-021** 데일리 리포트 조립 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-021.md)
- [x] **AI-022** 리포트 저장 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-022.md)
- [x] **AI-023** 데일리 리포트 그래프 통합 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-023.md)

## M6 — AI 챗 RAG

- [x] **AI-024** 질의 임베딩 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-024.md)
- [x] **AI-025** 기사 검색 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-025.md)
- [x] **AI-026** 컨텍스트 구성 노드 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-026.md)
- [x] **AI-027** 응답 토큰 스트림 생성 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-027.md)
- [x] **AI-028** /chat-stream 토큰/완료 엔드포인트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-028.md)
- [x] **AI-029** 챗 그래프 기사 카드/에러 처리 — 의존성: mockable 없음 / hard 없음 — [step](../steps/ai/AI-029.md)

## 의존성

- 시작 전 BOOT-000 완료 필요.
- BE 트랙과의 인터페이스는 [docs/contracts/python-ai.yaml](../contracts/python-ai.yaml)에 동결.
- DB 스키마는 [docs/contracts/db-init.sql](../contracts/db-init.sql) 동결.
- Solar API 키(`UPSTAGE_API_KEY`)는 `.env`로 받으며 CI/테스트는 가짜 모드/VCR 기준으로 작성한다.
