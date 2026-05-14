# ADR-0005: LangGraph 워크플로우 토폴로지 — 가벼운 그래프 + Reflection 보류

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0003에서 AI Gateway에 LangChain + LangGraph를 채택했다. 그러나 이 기획(펫 사진 + 키워드 → 1인칭 일기)의 흐름은 본질적으로 **선형 파이프라인**이고, "재생성"은 사용자 버튼 트리거이지 Agentic 동적 워크플로우가 아니다.

LangGraph가 진짜 가치를 발휘하는 패턴 중 본 기획에 자연스러운 것은:

- 안전성 검증 후 1회 자동 재시도 (state 루프)
- 사진 분석 실패 시 degraded mode 분기
- (도입한다면) 생성 결과의 자체 품질 평가 후 자동 개선 — **Reflection**

LangGraph 사용은 **학습 목적**이 핵심 동기로 명시됨.

## Decision

**길 1: 가벼운 그래프 + Reflection 보류.**

토폴로지 윤곽:
- 선형 메인 경로 + 두 곳의 조건 엣지
  - 안전성 검증 후 → pass / 자동 재시도(생성 노드로 1회) / fail
  - 사진 분석 후 → 성공 / degraded(텍스트만으로 진행)
- 외부 도구 호출 (ReAct), 멀티 에이전트, HITL pause는 사용하지 않음

> 노드 구체 책임 · State 정의는 본 ADR 후속 grill 단계에서 확정 후 부록으로 추가.

**Reflection(자체 critique 노드 + 자동 개선 루프)은 MVP에 도입하지 않는다.**

## Rationale

- **짧은 개발 기간 + 1인 사이드 프로젝트.** Reflection 도입 시 critique LLM의 한국어 톤·1인칭 유지 평가 정확도를 검증할 평가셋 구축이 추가로 필요하다.
- 길 1만으로도 `StateGraph`, `Conditional Edge`, state 루프, error 전파 등 LangGraph 기초의 80%는 학습된다.
- Reflection은 **그래프 토폴로지에 노드 1개 추가**로 후일 도입 가능 — 미래 확장 여지가 열려 있다.
- Reflection의 진짜 가치(자체 품질 가드)는 프롬프트 튜닝이 안정된 후에 평가하는 것이 합리적. 초기엔 critique이 잡음을 더할 위험.

## Alternatives Considered

### 길 2 — Reflection 처음부터 도입
- LangGraph 대표 패턴 진짜 학습. 사용자 재생성 클릭 전 자체 품질 가드(UX 가치).
- **탈락 이유**: 비용 +30~40%, critique LLM 정확도 검증 부담, 평가셋 부재.

### 길 3 — LangGraph 빼고 LangChain RunnableSequence만
- 본 기획의 선형성에 가장 정합.
- **탈락 이유**: 사용자 학습 목적이 명시됨 — "LangGraph도 써보는 것이 목적".

## Consequences

### Pros
- 학습 목적 부분 충족 (LangGraph 기초 패턴).
- 그래프 단순 → 디버깅·LangSmith trace 읽기 쉬움.
- Reflection 미래 도입 시 단일 노드 추가로 확장 가능.

### Cons
- LangGraph의 동적 가치(자율 분기, ReAct, Reflection) 일부만 활용.
- 코드 리뷰에서 "이 기획엔 LangChain만으로 충분하지 않나?" 의문이 반복 제기될 수 있음.

### 후속 조치
- 노드별 책임 / State 정의는 grill 진행에 따라 본 ADR 부록으로 갱신.
- **Reflection 재고려 트리거**: 프롬프트 튜닝 안정화 이후, 평가셋 5케이스 이상 확보 시.
- Reflection 도입 결정 시 별도 ADR로 본 ADR을 supersede.
- **호칭(honorific) 자유 입력 검증**(본문 등장·어미·PII)은 Reflection critique 노드의 항목으로 통합하거나 별도 Validation Agent ADR로 다룬다 — 본 ADR 단계에선 결정 보류.

---

## 부록 — 노드/State 구체화 (Q9 grill, 2026-05-03)

### 본문 vs 부록 정합

본문 가정한 "사진 분석 노드 → 성공/degraded 분기"는 **무산**. Q9-1에서 vision + 일기 + structured outputs를 **1회 LLM 호출**로 결정 → 별도 vision_analysis 노드 없음. 결과적으로 conditional edge는 safety_check 후 1곳만 남는다.

### 노드 토폴로지 (4 nodes + 1 conditional edge)

```
START
  ↓
prepare_context   (입력 정합, generate vs regenerate 모드 판별)
  ↓
call_llm          (OpenAI GPT-4o-mini Vision + structured outputs)
  ↓
safety_check      (호칭 substring + 길이 sanity)
  ↓ conditional
   ├─ violation && retry_count < 2 → call_llm  (state 루프)
   └─ otherwise → END
```

| 노드 | 책임 | LLM 호출 |
|---|---|---|
| prepare_context | 입력 sanity, 모드 판별, prompt 블록 조립 사전 준비 | 0 |
| call_llm | Vision API 호출. retry 시 같은 노드 재진입(`safety_retry_count += 1`). | 1 |
| safety_check | `honorific in diary_text` + 길이 (`50≤diary≤1000`, `1≤caption≤100`) | 0 |

### State schema

```python
class DiaryState(TypedDict):
    # 메타
    session_id: str
    seq: int                                      # 1~4

    # 입력 (BFF forward)
    pet_id: str
    honorific: str
    species: str
    gender: Literal['male', 'female', 'unknown']
    photo_signed_url: str
    keywords: str
    recent_diaries: list[str]                     # 최근 3개 diary_text

    # 재생성 (seq>=2)
    previous_diary_text: Optional[str]
    regen_feedback: Optional[str]                 # NULL 허용

    # 출력
    diary_text: Optional[str]
    short_caption: Optional[str]
    mood_tag: Optional[Literal[
        '행복','신남','평온','졸림','심심','슬픔','까칠']]

    # 안전 retry (state 내부, DB 영속 X)
    safety_retry_count: int                       # 0부터, max 2
    safety_violation: Optional[str]               # honorific_missing | diary_length | caption_length
```

### 재생성 처리 — 같은 graph, state 초기값 분기

Gateway endpoint `/diary/generate`와 `/diary/regenerate`는 **같은 LangGraph 인스턴스**를 호출. 차이는 state 초기화에서:
- generate: `previous_diary_text=None, regen_feedback=None, seq=1`
- regenerate: 위 두 필드 채움 + `seq=req.seq`

prompt template 분기 (user 메시지에 블록 조립):
| 모드 | 블록 |
|---|---|
| 첫 생성 | 키워드 / 펫 / 최근 일기 |
| 재생성 + 피드백 있음 | 위 + 이전 시도 + 사용자 피드백 + "피드백 반영해 다시" |
| 재생성 + 피드백 없음 | 위 + 이전 시도 + "다른 톤으로 시도" 안내 |

"이전 시도와 다르게" 강도는 **약하게** — 사용자 피드백을 진실로 두고 자연스러운 변형 유도 (Q9-4-feedback a).

### Vision 호출 파라미터 (Q9-1-img)
- `image_url.url = photo_signed_url` (Supabase Storage signed URL, TTL 1h)
- `image_url.detail = "low"` (클라이언트 1024px 리사이즈 + 비용 절약)
- structured outputs: `mood_tag` 7-enum + `short_caption` 동시 강제

### safety_check 의사코드

```python
def safety_check(state: DiaryState) -> dict:
    if state["honorific"] not in state["diary_text"]:
        return {"safety_violation": "honorific_missing"}
    if not 50 <= len(state["diary_text"]) <= 1000:
        return {"safety_violation": "diary_length"}
    if not 1 <= len(state["short_caption"]) <= 100:
        return {"safety_violation": "caption_length"}
    return {"safety_violation": None}

def should_retry(state: DiaryState) -> str:
    if state["safety_violation"] and state["safety_retry_count"] < 2:
        return "call_llm"
    return END
```

retry max 도달 후에도 violation이면 마지막 결과 그대로 END (Q9-3-D a). 카운트는 사용자 트리거 단위 차감(ADR-0008 정합) — 자동 retry 비용은 부담.

### 후속 조치
- `.claude/rules/tone-guide.md` 작성 (Q7-B-5 D + 3-layer 후속).
- prompt v1 (system + user template) 별도 작성 단계.
- `request_id` 추적은 LangSmith trace_id 자동 사용 (Q10 결정 후 정식 정합).

---

## 부록 — vision/diary 2-step 분리 + vision skip (2026-05-05)

이전 부록(2026-05-03)이 가정한 "1회 LLM 호출"은 구현 단계에서 두 차례 변경됨:

1. **vision/diary 분리** — 사진 사실 묘사(vision)와 1인칭 한국어 톤(diary)은 책임이 달라 모듈 분리. `agents/vision.py`, `agents/diary.py`로 캡슐화.
2. **vision skip 분기** — 같은 session 내 regenerate 시 photo 동일 → vision LLM 반복 호출 비용 절약 위해 conditional edge로 skip.

### 토폴로지 (실측 — `arch.md` §1 정합)

```
START → prepare_context
       ↓ conditional `_route_vision`
       ├─ vision_description == None → analyze_image → write_diary
       └─ vision_description != None  → write_diary (skip)
write_diary → safety_check
            ↓ conditional `should_retry`
            ├─ violation && retry<2 → write_diary
            └─ otherwise → END
```

노드 4개(`prepare_context`/`analyze_image`/`write_diary`/`safety_check`) + conditional 2곳. retry는 `write_diary`로만 회귀 — vision 토큰은 1회만 소비.

### State schema 변경

`vision_description: Optional[str]` 필드 추가. seq=1에서 `analyze_image`가 채우고 BFF가 `diary_generations.vision_description` 컬럼에 echo (ADR-0010). seq≥2 regenerate에선 BFF가 직전 row에서 SELECT → state 초기화 시 forward → `_route_vision`이 vision LLM skip.

legacy row(`vision_description IS NULL`)는 다음 regenerate에서 self-heal → migration backfill 불필요.

### 효과

regenerate 호출당 vision LLM 1회 절감, 응답 시간 약 6초 단축.

vision skip 시 `vision_done` SSE 미emit → BFF mediator는 NULL fallback으로 lastGen 값 echo (ADR-0008 부록 2026-05-05).
