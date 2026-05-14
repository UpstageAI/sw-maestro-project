# BE 진행 (Spring Boot)

> 디렉토리: `backend/`. 다른 트랙(`frontend/`, `ai/`)을 건드리는 단계는 없다.
>
> Python AI 서비스는 WireMock으로 모킹한다. M3~M6 BE 단계는 FE 실제 연동 게이트가 의존할 Spring API 계약을 점진적으로 완성한다.

## 초기 시드 (M2까지)

- [x] **BE-001** Flyway V1 초기화 — `articles`, `daily_reports` 테이블 생성 + 통합 테스트로 스키마 검증 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-001.md)
- [x] **BE-002** `Article` 엔티티 + 리포지토리 + 단위 테스트 (`save → findById`) — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-002.md)
- [x] **BE-003** `GET /api/feed` 빈 배열 응답 + MockMvc 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-003.md)
- [x] **BE-004** `GET /api/feed`가 DB의 `articles`를 `status='summarized'` 필터로 반환 + Testcontainers 통합 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-004.md)
- [x] **BE-005** `GET /api/articles/{id}` + 404 처리 + 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-005.md)
- [x] **BE-006** `PythonAiClient` (WebClient) — `/refresh-stream` GET (mock) + WireMock 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-006.md)
- [x] **BE-007** `GET /api/refresh-stream` SseEmitter가 WireMock의 SSE 이벤트를 그대로 프록시 + 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-007.md)
- [x] **BE-008** `GET /api/report/today` — `DailyReport` 조회 + 빈 결과 처리 + 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-008.md)

## M3 — 기사 해피 패스

- [x] **BE-009** 피드 `ArticleSummary` DTO 확장 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-009.md)
- [x] **BE-010** 전체 기사 상세 DTO — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-010.md)
- [x] **BE-011** 기사 상세 404 처리 — 의존성: mockable 없음 / hard 없음 — [step](../steps/be/BE-011.md)
- [x] **BE-012** M3 피드-상세 테스트 데이터 일관성 — 의존성: mockable AI-014 / hard 없음 — [step](../steps/be/BE-012.md)

## M4 — 인라인 퀴즈

- [x] **BE-013** 기사 상세 퀴즈 배열 응답 — 모킹 선행: AI-017 — 의존성: mockable AI-015 / hard 없음 — [step](../steps/be/BE-013.md)
- [x] **BE-014** 퀴즈 매핑 회귀 테스트 — 모킹 선행: AI-017 — 의존성: mockable AI-017 / hard 없음 — [step](../steps/be/BE-014.md)

## M5 — 데일리 리포트

- [x] **BE-015** 오늘 데일리 리포트 DTO — 모킹 선행: AI-023 — 의존성: mockable AI-018 / hard 없음 — [step](../steps/be/BE-015.md)
- [x] **BE-016** 날짜별 데일리 리포트 엔드포인트 — 모킹 선행: AI-023 — 의존성: mockable AI-021 / hard 없음 — [step](../steps/be/BE-016.md)
- [x] **BE-017** 데일리 리포트 404/빈 상태 처리 — 모킹 선행: AI-023 — 의존성: mockable AI-023 / hard 없음 — [step](../steps/be/BE-017.md)

## M6 — AI 챗 RAG

- [x] **BE-018** Python 챗 스트림 클라이언트 — 모킹 선행: AI-028 — 의존성: mockable AI-024 / hard 없음 — [step](../steps/be/BE-018.md)
- [x] **BE-019** 챗 토큰 SSE 프록시 — 모킹 선행: AI-028 — 의존성: mockable AI-024 / hard 없음 — [step](../steps/be/BE-019.md)
- [x] **BE-020** 챗 완료 이벤트 기사 카드 프록시 — 모킹 선행: AI-029 — 의존성: mockable AI-029 / hard 없음 — [step](../steps/be/BE-020.md)
- [x] **BE-021** 챗 에러 SSE 프록시 — 모킹 선행: AI-028 — 의존성: mockable AI-027 / hard 없음 — [step](../steps/be/BE-021.md)
- [x] **BE-022** 챗 질의 파라미터 검증 — 의존성: mockable AI-024 / hard 없음 — [step](../steps/be/BE-022.md)
- [x] **BE-023** M6 챗 스트림 계약 회귀 테스트 — 모킹 선행: AI-029 — 의존성: mockable AI-029 / hard 없음 — [step](../steps/be/BE-023.md)

## 의존성

- 시작 전 BOOT-000 완료 필요.
- 이 트랙 안에서는 BE-001 → BE-023 순차 진행 권장.
- AI 트랙과의 인터페이스는 [docs/contracts/python-ai.yaml](../contracts/python-ai.yaml)에 동결되어 있어 WireMock으로 진행한다.
- `모킹 선행` 의존성은 AI 미완료 상태에서도 WireMock으로 대체한다.
