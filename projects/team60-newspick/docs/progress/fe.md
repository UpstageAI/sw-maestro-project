# FE 진행 (Next.js)

> 디렉토리: `frontend/`. Spring API는 MSW로 모킹. M3~M6 FE 단계는 모킹 선행으로 먼저 개발하고, 실제 연동 확인 단계에만 필수 의존성을 둔다.

## 초기 시드 (M2까지)

- [x] **FE-001** Tailwind v4 토큰 셋업 — `app/globals.css` 의 `@theme` 에 프로토타입 CSS 변수 모두 매핑 + 시각 회귀 단위 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-001.md)
- [x] **FE-002** 스플래시 페이지 (`app/page.tsx`) — NewPick 로고 + 인트로 + "서비스 시작하기" 버튼 + Vitest 렌더 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-002.md)
- [x] **FE-003** 카테고리 선택 페이지 + Zustand `useCategoryStore` + 토글 인터랙션 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-003.md)
- [x] **FE-004** PhoneFrame / BottomNav 공용 컴포넌트 + Testing Library 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-004.md)
- [x] **FE-005** `/(app)/feed` 페이지 — TanStack Query + MSW로 빈 응답 처리 + 로딩 상태 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-005.md)
- [x] **FE-006** SSE 헬퍼 (`lib/sse.ts`) + MSW의 SSE 모킹 셋업 + 단위 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-006.md)
- [x] **FE-007** 홈 로딩 화면의 진행률 카운터 컴포넌트 (모킹 SSE 이벤트로 동작 확인) — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-007.md)
- [x] **FE-008** NewsCard 컴포넌트 (홈 카드 1개 디자인 1대1 포팅) + 시각 단위 테스트 — 의존성: mockable 없음 / hard 없음 — [step](../steps/fe/FE-008.md)

## M3 — 기사 해피 패스

- [x] **FE-009** 홈 피드 모킹 기사 3개 — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-009.md)
- [x] **FE-010** 기사 상세 조회 함수 — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-010.md)
- [x] **FE-011** 기사 상세 히어로 — 모킹 선행: BE-010, AI-014 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-011.md)
- [x] **FE-012** 카드에서 상세 페이지 이동 — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-012.md)
- [x] **FE-013** 상세 페이지 loading skeleton — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-013.md)
- [x] **FE-014** 상세 페이지 error/404 상태 — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-014.md)
- [x] **FE-015** 본문 typography와 metadata polish — 모킹 선행: BE-009, AI-009 — 의존성: mockable BE-009, AI-009 / hard 없음 — [step](../steps/fe/FE-015.md)
- [x] **FE-016** M3 실제 기사 연동 확인 — 필수 의존 게이트: BE-012, AI-014 — 의존성: mockable 없음 / hard BE-012, AI-014 — [step](../steps/fe/FE-016.md)

## M4 — 인라인 퀴즈

- [x] **FE-017** 인라인 퀴즈 첫 문항 — 모킹 선행: BE-013, AI-017 — 의존성: mockable BE-013, AI-015 / hard 없음 — [step](../steps/fe/FE-017.md)
- [x] **FE-018** 퀴즈 O/X 피드백 — 모킹 선행: BE-013, AI-017 — 의존성: mockable BE-013, AI-015 / hard 없음 — [step](../steps/fe/FE-018.md)
- [x] **FE-019** 퀴즈 다음 문항 진행 — 모킹 선행: BE-013, AI-017 — 의존성: mockable BE-013, AI-015 / hard 없음 — [step](../steps/fe/FE-019.md)
- [x] **FE-020** 퀴즈 결과 요약 — 모킹 선행: BE-013, AI-017 — 의존성: mockable BE-013, AI-015 / hard 없음 — [step](../steps/fe/FE-020.md)
- [x] **FE-021** 기사 상세에 퀴즈 연결 — 모킹 선행: BE-014, AI-017 — 의존성: mockable BE-013, AI-015 / hard 없음 — [step](../steps/fe/FE-021.md)
- [ ] **FE-022** M4 실제 퀴즈 연동 확인 — 필수 의존 게이트: BE-014, AI-017 — 의존성: mockable 없음 / hard BE-014, AI-017 — [step](../steps/fe/FE-022.md)

## M5 — 데일리 리포트

- [x] **FE-023** 데일리 리포트 조회 함수와 타입 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-015, AI-018 / hard 없음 — [step](../steps/fe/FE-023.md)
- [x] **FE-024** 리포트 화면 골격과 브리핑 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-015, AI-018 / hard 없음 — [step](../steps/fe/FE-024.md)
- [x] **FE-025** 리포트 타임라인 카드 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-016, AI-019 / hard 없음 — [step](../steps/fe/FE-025.md)
- [x] **FE-026** 리포트 오늘의 흐름 목록 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-016, AI-020 / hard 없음 — [step](../steps/fe/FE-026.md)
- [x] **FE-027** 리포트 키워드 클라우드 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-016, AI-021 / hard 없음 — [step](../steps/fe/FE-027.md)
- [x] **FE-028** 리포트 로딩/빈/에러 상태 — 모킹 선행: BE-016, BE-017 — 의존성: mockable BE-017, AI-022 / hard 없음 — [step](../steps/fe/FE-028.md)
- [x] **FE-029** 리포트 라우트 브라우저 확인 — 모킹 선행: BE-015, AI-023 — 의존성: mockable BE-017, AI-022 / hard 없음 — [step](../steps/fe/FE-029.md)
- [ ] **FE-030** M5 실제 리포트 연동 확인 — 필수 의존 게이트: BE-017, AI-023 — 의존성: mockable 없음 / hard BE-017, AI-023 — [step](../steps/fe/FE-030.md)

## M6 — AI 챗 RAG

- [x] **FE-031** 챗 화면 골격과 제안 질문 — 모킹 선행: BE-018, AI-024 — 의존성: mockable BE-018, AI-024 / hard 없음 — [step](../steps/fe/FE-031.md)
- [x] **FE-032** 챗 입력과 사용자 말풍선 — 모킹 선행: BE-018, AI-024 — 의존성: mockable BE-019, AI-024 / hard 없음 — [step](../steps/fe/FE-032.md)
- [x] **FE-033** 챗 SSE 토큰 말풍선 — 모킹 선행: BE-019, AI-028 — 의존성: mockable BE-020, AI-027 / hard 없음 — [step](../steps/fe/FE-033.md)
- [x] **FE-034** 챗 완료 이벤트의 기사 카드 — 모킹 선행: BE-020, AI-029 — 의존성: mockable BE-020, AI-029 / hard 없음 — [step](../steps/fe/FE-034.md)
- [x] **FE-035** 챗 에러와 초기화 — 모킹 선행: BE-021, AI-028 — 의존성: mockable BE-021, AI-027 / hard 없음 — [step](../steps/fe/FE-035.md)
- [x] **FE-036** 제안 질문 클릭 전송 — 모킹 선행: BE-019, AI-028 — 의존성: mockable BE-022, AI-024 / hard 없음 — [step](../steps/fe/FE-036.md)
- [x] **FE-037** M6 실제 챗 연동 확인 — 필수 의존 게이트: BE-023, AI-029 — 의존성: mockable 없음 / hard BE-023, AI-029 — [step](../steps/fe/FE-037.md)

## 의존성

- 시작 전 BOOT-000 완료 필요.
- Spring API와의 모든 통신은 [docs/contracts/openapi.yaml](../contracts/openapi.yaml) 동결 스펙 + MSW handlers 로 처리.
- 디자인 1대1 충실도는 원본 `prototype/` 파일이 1차 기준이고, [docs/design.md](../design.md)는 보조 색인이다.
- `모킹 선행` 단계는 외부 단계가 미완료여도 MSW로 진행한다.
- `필수 의존 게이트` 단계는 표시된 BE/AI 단계가 완료되기 전에는 구현하지 않는다.
