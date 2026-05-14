---
title: 00 — Overview & Decision Index
related:
  - 01-langgraph-architecture.md
  - 02-data-model.md
  - 03-input-and-runtime.md
  - 04-ux-and-streaming.md
  - 05-personalization.md
  - 06-models-and-evaluation.md
  - 07-team-and-demo.md
  - 08-risks-and-deferrals.md
  - CHANGES-FROM-PROPOSAL.md
last_updated: 2026-05-08
---

# Overview

`review-ops-agent`는 SOMA 17기 57조의 멀티 Agent 시스템으로, "소상공인 리뷰 응대"라는 도메인을 통해 LangGraph 위에서 multi-tenant Memory · conditional Router · Tool calling · Streaming을 구성합니다.

## LangGraph 활용 surface

| Surface | 적용 지점 |
|---|---|
| **Conditional Edges (Router)** | 감정 + 신뢰도 기반 4분기 (`add_conditional_edges` + 분기 함수) |
| **Cross-thread Store (Memory)** | `(place_id, kind)` namespace로 매장별 장기 메모리. `Store` API의 `put`/`get`/`search` |
| **Streaming** | `graph.stream(stream_mode='updates')` 로 노드 진행 사이드바 표시 |
| **Tool use** | PatternAgent의 SQL query tool (`bind_tools` + structured output) |

**의도적으로 채택하지 않은 기능**: HITL(`interrupt`/`resume`), Checkpointer, Subgraph, Send/parallel, FastAPI 분리 워커, cron, 외부 API 연동. 사유와 대체 설계는 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md).

## 우선순위

1. **graph 구조 정확성** (1순위) — surface 4개를 공식 패턴에 맞게 적용. 표면적 사용이 아닌 깊이 있는 구성.
2. 데모 안정성 (2순위) — W2 D5 발표일 고정. recorded fallback 준비.
3. 데모 임팩트 (3순위) — 화려함보다 graph 구조 전달.
4. 양산성/실서비스성 (점수 외) — 의도하지 않음.

## 일정 제약

- **W2 D5 (2026-05-22) 고정** — 발표일 확정.
- 인터뷰 단계에서 학습-only 회귀로 ~3~4일 절감, 절감분은 surface 학습 깊이에 재투자.

## 결정 색인

| 영역 | 핵심 결정 | 상세 문서 |
|---|---|---|
| Graph 구조 | Router 감정 3분기 + 부정 confidence 분기, 노드 7~8개 | [`01`](./01-langgraph-architecture.md) |
| State 정의 | `TypedDict` + `Annotated[list, add]` 누적 필드 | [`01`](./01-langgraph-architecture.md) |
| 데이터 저장 | SQLite 다대다 (reviews + review_categories) + Memory Store `(place_id, kind)` | [`02`](./02-data-model.md) |
| 카테고리 처리 | 메타데이터로 SQL에만 저장, Drafter prompt parameter로 주입 (절충안) | [`02`](./02-data-model.md) |
| 입력 방식 | Mock JSON 파일 + Streamlit "fetch batch" 버튼 | [`03`](./03-input-and-runtime.md) |
| 실행 환경 | Streamlit 단일 프로세스 | [`03`](./03-input-and-runtime.md) |
| Multi-tenant | 코드 multi (namespace 학습), demo는 단일 매장 | [`03`](./03-input-and-runtime.md) |
| PII | 정규식 (전화·이메일·계좌), Classifier 이전 단계 | [`03`](./03-input-and-runtime.md) |
| Dashboard | Sidebar 매장 선택 + 메인 inbox | [`04`](./04-ux-and-streaming.md) |
| Streaming | node-level (`stream_mode='updates'`) | [`04`](./04-ux-and-streaming.md) |
| 답글 검토 | "복사" 버튼 (HITL 의도적 제외) | [`04`](./04-ux-and-streaming.md) |
| 매장 입력 | 첫 진입 강제 + seed 데이터 자동 로드 | [`05`](./05-personalization.md) |
| 피드백 학습 | 수정본 sample 추가 + Haiku diff hint | [`05`](./05-personalization.md) |
| 모델 | W1 Haiku 단일 → W2 D1 Drafter Sonnet 승격 결정 | [`06`](./06-models-and-evaluation.md) |
| 골든셋 | 자체 작성 50건 (5명×10건, cross-label, Cohen's kappa) | [`06`](./06-models-and-evaluation.md) |
| 팀 분담 | 사용자=skeleton, 4명=노드 1개씩 | [`07`](./07-team-and-demo.md) |
| Demo | 단일 매장 + mock 50건 사전 주입 | [`07`](./07-team-and-demo.md) |
| 의도적 제외 | HITL · FastAPI · cron · Google Places · speed-up · CSV · 단계적 입력 · AIHub | [`08`](./08-risks-and-deferrals.md) |

## 다음 단계 (W1 D1)

1. uv 환경 + pyproject.toml + Makefile (`make run` = `streamlit run app.py`)
2. SQLite 스키마 마이그레이션 (`migrations/001_init.sql`)
3. `data/seed_places.json` 매장 2개 (성숙 + 신규) 작성
4. `data/mock_reviews_<place_id>.json` 매장당 25~30건 (총 50~60건) 작성
5. LangGraph skeleton (`src/graph/build.py`): State + 노드 stub + Router 분기 함수 + compile

세부 실행 순서는 [`07-team-and-demo.md`](./07-team-and-demo.md).

## PROPOSAL.md 와의 차이

PROPOSAL.md는 v2 그대로 보존하되, 12개 항목이 학습-only 렌즈로 변경됨. 변경 사항 추적은 [`CHANGES-FROM-PROPOSAL.md`](./CHANGES-FROM-PROPOSAL.md).
