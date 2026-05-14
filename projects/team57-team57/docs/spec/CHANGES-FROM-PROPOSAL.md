---
title: CHANGES — Diff from PROPOSAL.md v2
related:
  - 00-overview.md
  - 08-risks-and-deferrals.md
last_updated: 2026-05-08
---

# CHANGES — PROPOSAL.md v2 와의 차이

PROPOSAL.md v2 (학기 초 작성) 이후 10라운드 인터뷰 + 학습-only 렌즈 적용 결과 12개 항목이 변경됨. PROPOSAL.md 자체는 *역사 보존*을 위해 수정하지 않음. 이 문서가 delta 기록.

| # | 영역 | PROPOSAL (원안) | 적용된 변경 (학습-only) | 사유 요약 |
|---|---|---|---|---|
| 1 | 입력 방식 | 붙여넣기 textbox 우선 + CSV 보조 | **Mock JSON 파일 + Streamlit "fetch batch" 버튼** | Tool use surface는 SQL query tool로 노출. 외부 API/cron는 학습 surface 외. → [`03`](./03-input-and-runtime.md) |
| 2 | 매장 처리 | 단일 매장 가정 | **Multi-tenant 2매장 (코드 multi, demo single)** | Memory Store namespace `(place_id, kind)` 학습 surface 노출. → [`02`](./02-data-model.md) |
| 3 | 카테고리 분류 | 5대 카테고리 멀티라벨 + 매장 메뉴 자동 태깅 | **메타데이터로 SQL에만 저장 + Drafter prompt parameter로 주입 (Router는 감정만)** | Send/parallel 미선택 → 멀티라벨 분기 불가. 절충안. → [`02`](./02-data-model.md) |
| 4 | Graph 구조 | Orchestrator → 5-node 직선 (Context/Classifier/Drafter/Pattern/Checklist) | **Router(감정 3분기 + 부정 confidence 추가) + 7~8 노드 + 4 surface** | LangGraph conditional edges 학습 명시. → [`01`](./01-langgraph-architecture.md) |
| 5 | 실행 환경 | Streamlit 단일 페이지 (`make run`) | **Streamlit 단일 프로세스** | (변동 없음 — FastAPI 회귀 결정으로 PROPOSAL 원안 유지) |
| 6 | 모델 | Sonnet 4.6 1순위 + gpt-5.x-mini/Qwen 비교 | **W1 Haiku 단일, W2 D1 Drafter Sonnet 승격 검토** | 학습-only면 멀티 vendor 비교는 surface 외. 비용 절감 + 평가 변수 단순. → [`06`](./06-models-and-evaluation.md) |
| 7 | 자동 발행 | "발행은 사람이" — HITL 강제 | **UI 차원 [복사]/[수정] 버튼, graph 차원 HITL 폐기** | LangGraph `interrupt`/`resume` surface 의도적 제외 (학습 surface 4개 우선). → [`04`](./04-ux-and-streaming.md), [`08`](./08-risks-and-deferrals.md) |
| 8 | 누적 분석 | 자연 시간 경과로 4주 윈도우 누적 | **mock 데이터 사전 주입 (timestamp 4주 분포)** | 학습 단계에 PatternAgent 동작 검증 가능. speed-up 버튼은 미채택. → [`03`](./03-input-and-runtime.md) |
| 9 | CSV 업로드 | 보조 옵션 | **폐기** | mock JSON으로 입력 단일화. → [`03`](./03-input-and-runtime.md) |
| 10 | 매장 입력 UX | 첫 사용 시 컨텍스트 입력 + 답글 수정 후 톤 풀 자동 추가 | **첫 진입 form 강제 + seed 데이터 자동 로드 (단계적 prompt UI 미채택)** | 학습-only 렌즈에서 UI surface는 본 프로젝트 학습 외. → [`05`](./05-personalization.md) |
| 11 | 메모리 계층 | 단/중/장기 3계층 명시 | **LangGraph 공식 모델 매핑: state(단기) + Memory Store(장기) + SQLite(중기 누적)** | LangGraph 공식 패턴으로 학습. PROPOSAL의 3계층은 결과적으로 동일 매핑. → [`02`](./02-data-model.md) |
| 12 | 평가 데이터셋 | Sonnet/mini/Qwen 3종 + 골든셋 50건 (출처 미명시) | **Anthropic 단일 + 자체 작성 50건 + 5명 cross-label + Fleiss kappa** | AIHub 다운로드 부담 + 자체 작성이 빠름. → [`06`](./06-models-and-evaluation.md) |

## PROPOSAL F1~F8 별 매핑

| PROPOSAL feature | 변경 후 상태 | 메모 |
|---|---|---|
| F1 리뷰 입력 (붙여넣기) | **Mock JSON + 버튼**으로 대체 | UX 단순화 |
| F2 감정 분석 | 유지 — Classifier가 sentiment + confidence 출력 | |
| F3 유형 분류 (5대 카테고리 + 메뉴 태깅) | **메타데이터로만 유지** (Router 분기 X, Drafter prompt parameter O) | 멀티라벨 fan-out 폐기 |
| F4 답글 초안 생성 (개인화) | 유지 — Drafter 4종 + tone_samples few-shot + diff hint | |
| F5 반복 불만 TOP 3 (다세션) | 유지 — batch graph + SQL query tool | |
| F6 개선 체크리스트 | 유지 — checklist_generator 노드 (LLM 자유 생성) | |
| F7 매장 컨텍스트 관리 | 유지 — Memory Store metadata 단순화 | |
| F8 사장 피드백 반영 | 유지 — tone_samples + diff hint Haiku로 요약 | |

## PROPOSAL 시나리오별 매핑

| PROPOSAL 시나리오 | 변경 후 상태 |
|---|---|
| 시나리오 A (마감 후 단건) | **Streamlit "5건 가져오기" 버튼**으로 대체 — 사장 액션은 동일 (보고/검토/복사) |
| 시나리오 B (주말 회고 50건) | **mock 사전 주입 50건**으로 대체 — 시간 경과는 데이터 timestamp로 시뮬레이션 |
| 시나리오 C (매장 컨텍스트 등록) | 유지 — 첫 진입 form (skip 미채택), seed 자동 로드 |

## PROPOSAL KPI 6개 별 매핑

| KPI | 변경 후 상태 |
|---|---|
| 분류 정확도 ≥85% | 유지 (자동 — 골든셋) |
| 답글 사용 의향 ≥70% | 유지 (수작업 — 사용성 테스트) |
| 처리 시간 단축 1/3 이하 | 유지 (반자동 — 타이머 비교) |
| TOP 3 정합성 | 유지 (수작업) |
| 사용성 (5분 내 도달) ≥80% | **상향 조정 필요할 수도** — 첫 진입 form 강제로 시간↑ 가능. W2 D4에 측정 후 결정 |
| 개인화 체감 60% | 유지 (수작업 — seed 매장 vs 신규 매장 비교) |

## 회고·평가 시 메시지

PROPOSAL → 변경의 핵심 메시지:

> "PROPOSAL은 *제품 시연* 관점, 변경은 *LangGraph 학습* 관점. 후자가 본 프로젝트의 본질. 변경된 12개는 모두 학습 surface (Router·Memory Store·Streaming·Tool use) 4개 깊이 학습이라는 단일 원칙 위에서 결정됨."

상세 의도적 제외 사유는 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md) 참고.
