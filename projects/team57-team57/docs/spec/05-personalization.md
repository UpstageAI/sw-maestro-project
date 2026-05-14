---
title: 05 — Personalization & Feedback Loop
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 02-data-model.md
  - 04-ux-and-streaming.md
last_updated: 2026-05-08
---

# Personalization & Feedback Loop

LangGraph Memory Store 학습 surface의 핵심. "쓸수록 우리 가게답게"라는 PROPOSAL F8의 원칙을 *최소 구현*으로 달성.

## 데이터 흐름

```
[seed_places.json] ─────► load on startup ─────► Memory Store
                                                  │
                                                  ▼
[graph.invoke(review)] ──► load_context (read) ──► Drafter ──► 답글 초안
                                                                 │
                                                                 ▼
                                                          [사장이 수정 + 복사]
                                                                 │
                                                                 ▼
                                            UI 호출: append_tone_sample()
                                                                 │
                                                                 ▼
                                                      Memory Store (write)
                                                                 │
                                                                 ▼
                                                  비동기 diff_hint_job (Haiku)
                                                                 │
                                                                 ▼
                                                      Memory Store (write feedback)
                                                                 │
                                                                 ▼
                                                  다음 graph.invoke 시 활용
```

## 매장 컨텍스트 (Memory Store metadata)

`(place_id, "metadata")` namespace, 단일 키 `"profile"`.

```python
{
    "display_name": "예시 카페 A",
    "category": "카페",
    "menus": [
        {"name": "아메리카노", "price": 4000},
        {"name": "라떼", "price": 4500},
        {"name": "치즈케이크", "price": 6500},
        ...
    ],
    "price_range": "₩₩",
    "tone_preference": "정중체" | "친근체" | "격식체",
    "address": "서울 ...",     # optional
    "completeness": 0.85,
}
```

`completeness`는 채워진 필수/권장 필드 비율. 진척도 표시(가벼운 gamification) 용도. 단계적 prompt UI는 의도적 제외 (아래 *Why* 절).

## 톤 샘플 (Memory Store tone_samples)

`(place_id, "tone_samples")` namespace, 키 = `sample_id` (uuid). append-only.

```python
{
    "sample_id": "sm_xxxx",
    "review_text": "주말에 자리가 너무 없어요. 30분 기다렸어요.",
    "ai_draft": "기다림으로 불편을 드려 죄송합니다. 피크타임 인력을 보강해...",
    "owner_final": "오래 기다리셔서 죄송해요. 평일 오후엔 비교적 한산하니 다음에 방문해주세요!",
    "drafter_used": "apology",
    "categories": ["대기시간"],
    "created_at": "2026-04-15T20:11:00Z"
}
```

### 쓰기 시점

- **사장이 답글 수정 + [복사]** 또는 **사장이 답글 [복사] (수정 없이)** 시 모두 append.
- 수정 없이 복사한 경우도 학습 데이터 (사장이 "이대로 OK" 라는 신호).
- 무시(다른 리뷰로 이동) / 거부(X 버튼)는 append 안 함.

### 읽기 시점 (Drafter few-shot)

```python
# load_context 노드
sample_items = store.search((place_id, "tone_samples"), limit=3)
tone_samples = [item.value for item in sample_items]
```

최근 3건만. Drafter prompt에 다음과 같이 주입:

```
[과거 사장 채택 답글 샘플 — 최근 3건, 톤 모방용]

[샘플 1]
리뷰: "..."
사장 최종 답글: "..."

[샘플 2]
리뷰: "..."
사장 최종 답글: "..."

[샘플 3]
리뷰: "..."
사장 최종 답글: "..."
```

샘플이 0건이면 (신규 매장) 이 섹션 통째로 prompt에서 제거 — fallback은 매장 메타의 `tone_preference` 만으로 답글 생성.

## 피드백 / diff hint (Memory Store feedback)

`(place_id, "feedback")` namespace, 키 = `feedback_id` (uuid). append-only.

### diff hint 생성 (비동기, Haiku)

답글 sample이 새로 append될 때마다 background job 트리거 (Streamlit `st.experimental_async` 또는 단순 `threading.Thread`):

```
[Haiku에게 보내는 prompt]

다음은 AI가 작성한 답글 초안과 사장이 수정한 최종 답글입니다.
사장의 톤·표현 선호를 한 줄(40자 이내)로 요약하세요.

AI 초안: "기다림으로 불편을 드려 죄송합니다. 피크타임 인력을 보강해..."
사장 최종: "오래 기다리셔서 죄송해요. 평일 오후엔 비교적 한산하니 다음에 방문해주세요!"

출력 형식: { "diff_hint": "..." }
```

Haiku 응답 예: `{"diff_hint": "더 짧고 친근한 종결어, 대안 제시 추가 경향"}`

### 읽기 시점 (Drafter prompt 추가 hint)

```python
feedback_items = store.search((place_id, "feedback"), limit=1)
feedback_hints = [item.value["diff_hint"] for item in feedback_items]
```

최근 1건만 prompt에 주입:

```
[사장의 톤 선호 hint]
{diff_hint}
```

### 비용

- diff hint 1회 = Haiku 호출 1회 ≈ input 200토큰 + output 50토큰 ≈ $0.0001 미만.
- 사장이 답글 수정할 때마다 1회. 무시 가능한 비용.

## Drafter prompt 구조 (3 + 1 노드 공통)

```
[System]
당신은 {매장 메타.category} "{매장 메타.display_name}"의 답글 비서입니다.
톤: {매장 메타.tone_preference}.
가격대: {매장 메타.price_range}.

대표 메뉴: {메뉴 5개 슬라이스}

[Few-shot — tone_samples 0~3건]
(샘플 0건이면 이 블록 생략)

[Tone hint — feedback 최근 1건]
{diff_hint}
(없으면 생략)

[지시]
다음 리뷰에 대한 답글 초안을 작성하세요.
- 한국어 존댓말 고정.
- 가격/할인 약속, 매장 정책 변경 표현 회피.
- 80~150자.
- {drafter별 추가 지시 — apology면 "사실 인정 → 사과 → 개선 약속" 3단 강제}

[Review]
원문: {masked_text}
감정: {sentiment}, 신뢰도: {confidence}
카테고리(메타데이터): {categories}
{risk_flag면 "주의: 안전성 risk_flag 감지 — 정책에 영향 줄 표현 회피"}

[Output]
답글 텍스트만 출력 (JSON 아님, 평문).
```

카테고리는 prompt parameter로 주입되어 *답글 내용*에 영향을 주지만 *노드 분기*에는 사용되지 않음 — [`02-data-model.md`](./02-data-model.md) 카테고리 처리 정책 참고.

## 매장 입력은 *첫 진입 강제*

PROPOSAL의 "Skip + 단계적" 또는 인터뷰 중 거론된 "답글마다 톤 샘플 추가 prompt 팔레트"는 **의도적으로 채택하지 않습니다**.

### Why

| 항목 | 단계적 prompt UI | 첫 진입 강제 (채택) |
|---|---|---|
| 학습 surface | 0 | 0 |
| Memory Store 동작 학습 | 동일 | 동일 |
| 구현 비용 | 답글 수정 후 dialog + completeness 추적 + dismissible 카드 | form 1개 |
| 시드 데이터 활용 | seed가 있어도 어차피 prompt 노출 → 일관성 X | seed 자동 로드 후 form skip |
| Drafter few-shot | 신규 매장은 sample 0개로 시작 → "AI가 generic" 인상 | seed 매장은 처음부터 sample 3건 |

학습-only 렌즈에서는 **시드 데이터가 미리 채워진 매장**이면 form 자체가 불필요. 새 매장 추가 시에만 강제 form. UX 학습 surface는 0이지만, 본 프로젝트에서 LangGraph 학습이 일어나는 surface는 *Memory Store API* 자체이며, 이는 어느 입력 방식이든 동일하게 학습됨.

## 후순위 / 시간 부족 시

| 항목 | 후순위 처리 |
|---|---|
| diff hint 생성 (비동기 Haiku) | 미구현, tone_samples만 append |
| feedback namespace 자체 | 미사용, prompt에서 hint 블록 제거 |
| 매장 등록 form | seed 매장 2개로만 시연, form 미구현 |
| `completeness` 진척도 표시 | 미구현 (UI 단순화) |
