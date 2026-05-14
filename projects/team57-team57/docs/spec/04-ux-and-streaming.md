---
title: 04 — UX & Streaming
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 03-input-and-runtime.md
  - 05-personalization.md
  - 07-team-and-demo.md
last_updated: 2026-05-08
---

# UX & Streaming

## 화면 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  review-ops-agent                                           │
├──────────┬──────────────────────────────────────────────────┤
│ Sidebar  │ Main                                             │
│          │                                                  │
│ 매장 목록 │ ┌─ 새 리뷰 ─────────────────────────────────────┐ │
│ ━━━━━━━ │ │ "원두향이 정말 좋아요. 라떼 추천합니다 :)"     │ │
│ ▶ 카페 A │ │ ★★★★★  · 2026-04-12 18:34                      │ │
│   식당 B │ ├─ 분류 (Classifier) ──────────────────────────┤ │
│          │ │ 감정: 긍정  conf 0.92                         │ │
│ ━━━━━━━ │ │ 카테고리: [맛, 가격]                          │ │
│ Graph     │ ├─ 답글 초안 (thanks_drafter) ─────────────────┤ │
│ 진행      │ │ "라떼 칭찬 감사드립니다! 원두는 ..."         │ │
│ ━━━━━━━ │ │  [복사] [수정]                                │ │
│ ✓ load   │ ├─ TOP 3 반복 불만 (4주 누적) ────────────────┤ │
│ ✓ pii    │ │ 1. 대기시간 (12회)                           │ │
│ ✓ class  │ │ 2. 위생 (5회)                                │ │
│ ⏳ drafter│ │ 3. 가격 (3회)                                │ │
│   memory │ ├─ 이번 주 점검 ──────────────────────────────┤ │
│          │ │ • 피크타임 인력 1명 추가 검토                │ │
│ ━━━━━━━ │ │ • 빨대 제공 동선 점검                         │ │
│ 새 리뷰  │ │ • ...                                         │ │
│ 가져오기  │ └────────────────────────────────────────────────┘ │
│ [버튼]   │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

### Sidebar 구성

1. **매장 목록** — `seed_places.json` 에서 자동 로드. 클릭 시 메인 영역 매장 컨텍스트 전환.
2. **Graph 진행 (live)** — 현재 처리 중인 리뷰의 노드 흐름. `stream_mode='updates'` 로 받은 노드명을 ✓/⏳/⏸ 아이콘과 함께 표시.
3. **새 리뷰 가져오기 버튼** — 현재 매장의 `mock_reviews_<place_id>.json` 에서 다음 N건 (기본 5건) 처리.
4. **TOP 3 새로고침 버튼** — batch graph (pattern + checklist) 수동 트리거.

### Main 구성 (선택된 리뷰별 카드)

1. **새 리뷰 카드** — 원문, 별점, timestamp.
2. **분류 카드** — sentiment, confidence, categories (정렬: confidence desc), risk_flag (있을 때만).
3. **답글 초안 카드** — Drafter 출력 + `[복사]` `[수정]` 버튼.
4. **TOP 3 카드 + 체크리스트 카드** — 매장 단위. `pattern_aggregator` 결과.

## Streaming 정책

### Node-level (필수 — Streaming surface 학습)

```python
status_box = st.sidebar.container()  # Graph 진행 panel
node_log = []

for chunk in graph.stream(input, config, stream_mode="updates"):
    # chunk = {"node_name": {state_delta_dict}}
    for node_name, _state_delta in chunk.items():
        node_log.append({"node": node_name, "ended_at": now_iso()})
        with status_box:
            st.write(f"✓ {node_name}")
```

`stream_mode='updates'`는 *노드 단위 변경분*만 emit하므로 사이드바 체크리스트 갱신에 최적.

### Token-level (옵션 — W2 D4 여유 시)

Drafter 노드만 token-level로 추가:

```python
async for chunk in graph.astream_events(input, config, version="v2"):
    if chunk["event"] == "on_chat_model_stream" and chunk["metadata"]["langgraph_node"].endswith("drafter"):
        token = chunk["data"]["chunk"].content
        st.session_state["drafter_buffer"] += token
        # st.write_stream으로 답글 카드 업데이트
```

token-level은 **시간 부족 시 첫 후순위** — Streaming surface는 node-level만으로도 학습 충분.

## 답글 검토 UX — "복사" 버튼 (HITL 폐기)

PROPOSAL의 "사람 개입 필수 / 자동 발행 금지"는 graph 차원의 HITL(`interrupt`/`resume`) 없이 **UI 차원의 단순 복사 버튼**으로 만족합니다.

### 흐름

1. graph 실행 종료 → 답글 초안이 main 카드에 표시.
2. 사장 액션 4가지:
   - `[복사]` 클릭 → `replies.copied_at` 기록. (`final_text`는 `draft_text` 그대로).
   - `[수정]` 클릭 → 텍스트 영역으로 변환, 사장 편집 후 `[저장]`. → `replies.final_text`, `replies.edited_at` 기록.
   - 무시 (다른 리뷰로 이동) → 아무것도 기록 안 됨.
   - 답글 거부 (X 버튼) → `replies.copied_at` 미기록 + dismiss 플래그.
3. 수정 시 비동기로 diff hint 생성 ([`05-personalization.md`](./05-personalization.md)).

### Why not HITL?

LangGraph `interrupt`/`resume`은 강력하지만 **Streamlit re-run 모델과 충돌**합니다. Streamlit은 모든 입력 변경 시 스크립트 전체 재실행 → graph thread 상태 복원에 Checkpointer 필수 → 학습 surface 1개 추가 필요. 학습-only 렌즈에서 의도적 제외.

대신 graph는 Drafter까지 끝까지 돌려 *초안만 남기고 종료*. 사장 액션은 graph 외부의 단순 DB write. PROPOSAL의 "발행은 사람이" 정신은 *결과적으로 보존* (graph가 자동 발행 안 함).

## 매장 컨텍스트 입력 form (첫 진입 시)

매장 시드가 이미 있으면 skip. 없는 경우 (사용자가 새 매장 추가 시):

```
┌─ 새 매장 등록 ──────────────────────┐
│ 매장 ID:    [PLACE_003   ]          │
│ 매장 이름:  [           ] *         │
│ 업종:       [카페 ▼]   *            │
│ 메뉴 (5~10): [+ 메뉴 추가]          │
│   [라떼      ] [4500원]  [삭제]     │
│   [           ] [      원]          │
│ 답글 톤:    (○) 정중체  (●) 친근체  │
│ 가격대:     [₩₩    ]                │
│                                      │
│              [등록]                  │
└──────────────────────────────────────┘
```

- 강제 필수: 매장 ID, 매장 이름, 업종, 답글 톤. (메뉴는 0건도 허용 — 시간이 지남에 따라 채워질 수 있음).
- 등록 시 Memory Store `(place_id, "metadata")` 에 put.
- "Skip + 단계적" UI는 **의도적으로 채택하지 않음** ([`05-personalization.md`](./05-personalization.md) Why 절 참조).

## 데모 시연 흐름

세부 흐름(시간·비트)은 **TBD** — W2 D3에 결정. 현재 spec에 명시할 수 있는 것:

- 단일 매장 (PLACE_001 — 성숙) 위주.
- mock 50건 사전 주입 상태에서 시작.
- 핵심 시연 비트 후보 (시간 배분은 W2 D3에 확정):
  1. sidebar 매장 전환 → multi-tenant + Memory Store namespace 시연.
  2. "새 리뷰 5건 가져오기" → graph stream + 노드 사이드바 진행.
  3. 부정 리뷰 답글 수정 → tone_samples append + diff hint 생성 비동기 호출 시연 (Memory Store mutation 보임).
  4. "TOP 3 + 체크리스트" 버튼 → batch graph + SQL tool 호출 (Tool use surface).

세부 시나리오는 [`07-team-and-demo.md`](./07-team-and-demo.md) 의 Demo 절.

## 후순위 / 시간 부족 시

| 항목 | 후순위 처리 |
|---|---|
| token-level streaming | 빼고 node-level만 |
| TOP 3 + 체크리스트 카드 | hardcoded 통계로 대체 (batch graph 미구현) |
| 매장 등록 form | seed 매장 2개로만 시연, form 미구현 |
| 답글 수정 후 diff hint | 수정본만 append, diff 생성 생략 |
