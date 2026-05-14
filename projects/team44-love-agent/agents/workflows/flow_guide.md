# 상담 플로우 가이드

사용자가 고민을 입력한 순간부터 최종 답변을 받기까지 데이터가 어떻게 흐르는지 **단계별 입력/처리/출력**을 예시와 함께 보여주는 문서입니다.

- 정확한 타입 정의와 모든 enum 값은 [message_schema.md](message_schema.md)
- 슈퍼바이저 동작 규칙과 분기 조건은 [supervisor_protocol.md](supervisor_protocol.md)
- 이 문서는 위 두 문서의 **읽기 쉬운 워크스루** 버전입니다.

> 본 문서의 모든 예시는 다음 한 가지 시나리오로 통일합니다.
> **"요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어."**

---

## 전체 흐름 한눈에

```text
사용자 질문 입력
        │
        ▼
[0] 백엔드 접수 ─────────────── POST /consultations
        │
        ▼
[1] 슈퍼바이저 · 질문 분석 ───── analyze_question
        │
        ▼
[2] 1라운드 · 독립 의견 ──────── 6개 에이전트 병렬
        │
        ▼
[3] 슈퍼바이저 · 쟁점 정리 ───── summarize_round_1
        │
        ▼
[4] 2라운드 · 토론 ───────────── 6개 에이전트 순차
        │
        ▼
[5] 슈퍼바이저 · 충돌 분류 ───── classify_round_2
        │
        ▼
   ┌─── 합의율 ≥ 0.7 ─── 예 ───┐
   │                            ▼
   아니오                    [7] 슈퍼바이저 · 최종 통합
        │                       │
        ▼                       │
[6] 3라운드 · 최종 입장 ─────── │
        │                       │
        └────────────▶ [7] 슈퍼바이저 · 최종 통합
                                │
                                ▼
                         [8] 프론트 응답 반환
```

---

## 단계 요약표

| # | 단계 | 호출 주체 | 동시성 | 평균 소요 | 다음 단계 결정 |
| --- | --- | --- | --- | --- | --- |
| 0 | 백엔드 접수 | 백엔드 | — | 즉시 | 항상 [1] |
| 1 | 질문 분석 | 슈퍼바이저 | 단일 | ~3초 | 정상이면 [2], 안전 차단이면 종료 |
| 2 | 1라운드 의견 | 6 에이전트 | **병렬** | ~5초 | 4개 이상 성공 시 [3] |
| 3 | 1라운드 요약 | 슈퍼바이저 | 단일 | ~3초 | 항상 [4] |
| 4 | 2라운드 토론 | 6 에이전트 | **순차** | ~30초 | 4개 이상 성공 시 [5] |
| 5 | 충돌 분류 | 슈퍼바이저 | 단일 | ~3초 | 합의율로 [6] 또는 [7] 분기 |
| 6 | 3라운드 입장 | 6 에이전트 | **순차** | ~30초 | 항상 [7] |
| 7 | 최종 통합 | 슈퍼바이저 | 단일 | ~5초 | [8] |
| 8 | 응답 반환 | 백엔드 | — | 즉시 | 종료 |

> 전체 워크플로우 권장 타임아웃: **5분**.

---

# [0] 백엔드 접수

## 언제 일어나나
사용자가 화면에서 "상담 시작" 버튼을 누른 순간.

## 무엇이 들어오나 — `POST /consultations`

```json
{
  "consultation_id": "c8f4a8e2-9c3a-4f6b-8e7d-1a2b3c4d5e6f",
  "user_question": "요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어.",
  "language": "ko-KR",
  "client_meta": {
    "user_agent": "Mozilla/5.0 ...",
    "submitted_at": "2026-05-06T12:00:00.000Z"
  }
}
```

| 필드 | 누가 채우나 | 비고 |
| --- | --- | --- |
| `consultation_id` | 프론트 | UUID v4. 같은 ID 재요청 시 기존 결과 반환 |
| `user_question` | 사용자 | 1~4000자, 트리밍 후 빈 문자열이면 400 |
| `language` | 프론트 | PoC는 `"ko-KR"` 고정 |

## 무슨 일이 벌어지나
1. 입력 검증 (길이, 언어, UUID 형식)
2. `ConsultationState` 초기화
3. LangGraph 워크플로우 트리거
4. 클라이언트에는 즉시 `consultation_id`와 `status: "pending"`만 응답 (비동기). 클라이언트는 이후 폴링 또는 SSE로 진행 상황 수신

## 무엇이 나가나 — 즉시 응답

```json
{
  "consultation_id": "c8f4a8e2-9c3a-4f6b-8e7d-1a2b3c4d5e6f",
  "status": "pending",
  "started_at": "2026-05-06T12:00:00.123Z"
}
```

## 다음 단계
[1] 슈퍼바이저 질문 분석.

---

# [1] 슈퍼바이저 · 질문 분석

## 언제 일어나나
워크플로우 시작 직후.

## 무엇이 들어오나
슈퍼바이저 LLM에 다음 컨텍스트만 전달:

```text
사용자 질문: "요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어."
언어: ko-KR
```

## 무슨 일이 벌어지나
슈퍼바이저는 질문에서 **관계 상태·갈등 유형·핵심 이슈·사용자 감정·토론 목표** 5가지를 추출합니다. 이건 이후 6개 에이전트가 모두 공유할 "토론의 출발점"이 됩니다.

## 무엇이 나가나 — `QuestionAnalysis`

```json
{
  "id": "msg_01H...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:03.456Z",
  "language": "ko-KR",
  "relationship_state": "crush",
  "conflict_type": "communication_frequency",
  "key_issues": [
    "답장 텀이 점점 길어짐",
    "상대 의도가 모호함 (밀당 vs 관심 감소)",
    "사용자가 다음 행동을 결정하지 못함"
  ],
  "user_emotion": "anxious",
  "debate_goal": "답장 패턴의 의미를 해석하고 사용자가 취할 수 있는 다음 행동을 제시한다."
}
```

## 다음 단계
- 정상 → [2] 1라운드 시작
- `SAFETY_BLOCKED` → 안전 가드 응답으로 즉시 종료 ([supervisor_protocol.md §6.5](supervisor_protocol.md))

---

# [2] 1라운드 · 6개 에이전트 독립 의견

## 언제 일어나나
질문 분석이 끝난 직후.

## 무엇이 들어오나
6개 에이전트가 **동시에** 호출됩니다. 각 에이전트가 받는 컨텍스트:

```text
[시스템 프롬프트: 페르소나]
당신은 "현실주의자"입니다. (페르소나 상세 — 임지빈 정의)

[입력: QuestionAnalysis]
- 관계 상태: 썸 (crush)
- 갈등 유형: 연락 빈도
- 핵심 이슈: ["답장 텀이 길어짐", "상대 의도 모호", "다음 행동 미결정"]
- 사용자 감정: 불안 (anxious)
- 토론 목표: ...

[지시: 라운드 1 — 독립 의견]
다른 에이전트의 의견은 아직 보지 못한 상태에서, 당신의 페르소나에 따라
독립적인 조언을 생성하세요.

[출력 형식]
{
  "advice": ...,
  "rationale": ...,
  "stance": "proceed" | "pause" | "withdraw" | "clarify" | "mixed",
  "confidence": 0.0~1.0,
  "key_points": [...]
}
```

## 무슨 일이 벌어지나
6개 에이전트가 병렬로 LLM을 호출해 각자 의견을 만듭니다. 서로의 의견은 보지 않습니다.

## 무엇이 나가나 — `AgentOpinion[]` (6개)

예시(2개만 발췌):

```json
[
  {
    "id": "msg_02A...",
    "consultation_id": "c8f4a8e2-...",
    "created_at": "2026-05-06T12:00:08.123Z",
    "language": "ko-KR",
    "round": "round_1",
    "agent_id": "realist",
    "agent_name": "현실주의자",
    "advice": "답장 텀이 점점 늘어나는 패턴 자체가 신호입니다. 모호한 채로 두지 말고 관계의 온도를 직접 확인해야 합니다.",
    "rationale": "텍스트 빈도는 상대의 우선순위를 비교적 정직하게 반영합니다. 더 길게 끌면 결정 비용만 커집니다.",
    "stance": "clarify",
    "confidence": 0.78,
    "key_points": ["텍스트 빈도는 우선순위 신호", "결정 지연의 비용"]
  },
  {
    "id": "msg_02B...",
    "consultation_id": "c8f4a8e2-...",
    "created_at": "2026-05-06T12:00:08.789Z",
    "language": "ko-KR",
    "round": "round_1",
    "agent_id": "empath",
    "agent_name": "공감형 감성론자",
    "advice": "지금 가장 힘든 건 '모르겠다'는 그 상태 자체일 거예요. 답을 재촉하기 전에 본인 마음을 먼저 정리해 보는 것도 한 방법이에요.",
    "rationale": "불안한 상태에서 내린 결정은 보통 후회가 따라붙습니다. 행동 전에 감정 정리가 먼저입니다.",
    "stance": "pause",
    "confidence": 0.62,
    "key_points": ["모호함이 주는 피로", "감정 정리 우선"]
  }
  // ... analyst, actor, mediator, friend 4개 더
]
```

## 다음 단계
- 4개 이상 성공 → [3] 슈퍼바이저 1라운드 요약
- 4개 미만 → 워크플로우 실패 종료 ([supervisor_protocol.md §5.2](supervisor_protocol.md))

---

# [3] 슈퍼바이저 · 1라운드 요약

## 언제 일어나나
6개 에이전트의 의견이 모두(또는 4개 이상) 모인 직후.

## 무엇이 들어오나
- `QuestionAnalysis` (1단계 결과)
- `AgentOpinion[]` 전문 6개

## 무슨 일이 벌어지나
슈퍼바이저는 의견들의 **수렴 지점**과 **발산 지점**을 짚어내고, 다음 라운드에서 다뤄야 할 **열린 질문**을 만듭니다. 이건 2라운드 에이전트들이 공통으로 보게 될 "토론의 안내판"입니다.

## 무엇이 나가나 — `SupervisorNote (mode = "summary_1")`

```json
{
  "id": "msg_03...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:11.000Z",
  "language": "ko-KR",
  "mode": "summary_1",
  "payload": {
    "headline": "사용자는 답장 패턴 해석과 다음 행동 결정 사이에서 멈춰 있다.",
    "converging_points": [
      "현 상태를 그대로 두면 결정 비용이 커진다는 데에는 다수가 동의",
      "텍스트 빈도가 의미 있는 신호라는 점에 대체로 합의"
    ],
    "diverging_points": [
      "당장 직접 확인할 것인가 vs 감정 정리가 먼저인가",
      "행동 권유의 강도 (적극적 제안 vs 가벼운 신호)"
    ],
    "open_questions": [
      "답장 텀이 길어진 시점에 사용자가 한 행동은 무엇인가",
      "직접 확인이 부담스러우면 어떤 우회 방법이 가능한가"
    ]
  }
}
```

## 다음 단계
[4] 2라운드 토론.

---

# [4] 2라운드 · 6개 에이전트 토론 (순차)

## 언제 일어나나
1라운드 요약이 끝난 직후.

## 무엇이 들어오나
6개 에이전트가 **정해진 순서**로 호출됩니다.

```text
realist → analyst → mediator → empath → actor → friend
```

각 에이전트가 받는 컨텍스트:

```text
[시스템 프롬프트: 자기 페르소나 + 라운드 2 지시문]

[배경 정보]
- QuestionAnalysis
- summary_1 (직전 슈퍼바이저 요약)
- 자기의 1라운드 의견 (전문)
- 다른 5개 에이전트의 1라운드 의견 (id, agent_id, advice, stance, key_points)
- (자기보다 앞서 발언한 동료의 2라운드 발언이 있다면 함께)

[지시: 라운드 2 — 반박 또는 보완]
1~3개 의견을 골라 동의/부분동의/반박/추가관점 중 하나로 응답하세요.
새로운 근거나 입장 변화가 있으면 명시하세요.

[출력 형식]
{
  "targets": [{"target_message_id": ..., "target_agent_id": ..., "agreement": ...}],
  "statement": ...,
  "rationale": ...,
  "updated_position": "..." | null,
  "new_evidence": [...]
}
```

## 무슨 일이 벌어지나
각 에이전트가 차례대로 다른 에이전트의 의견을 명시적으로 가리키며 반박·동의·보완합니다. **참조는 반드시 메시지 `id`로**.

## 무엇이 나가나 — `AgentRebuttal[]` (6개)

예시 1개:

```json
{
  "id": "msg_04C...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:14.000Z",
  "language": "ko-KR",
  "round": "round_2",
  "agent_id": "analyst",
  "agent_name": "신중한 분석가",
  "targets": [
    {
      "target_message_id": "msg_02A...",
      "target_agent_id": "realist",
      "agreement": "partial"
    },
    {
      "target_message_id": "msg_02B...",
      "target_agent_id": "empath",
      "agreement": "extend"
    }
  ],
  "statement": "현실주의자의 '신호 해석' 관점은 타당하지만, 단일 변수(텍스트 빈도)만으로 결론짓는 건 위험합니다. 빈도 변화의 시점, 답장 길이, 새 화제 제안 여부까지 함께 보면 더 정확합니다.",
  "rationale": "관계 신호는 다변량입니다. 빈도만 보면 일시적 외부 사정(시험·프로젝트)을 잘못 해석할 수 있습니다.",
  "updated_position": "clarify",
  "new_evidence": [
    "빈도 외에도 답장 길이·새 화제 제안 여부를 함께 봐야 함",
    "외부 사정으로 인한 일시적 변화 가능성"
  ]
}
```

## 다음 단계
- 4개 이상 성공 → [5] 충돌 분류
- 4개 미만 → 실패 종료

---

# [5] 슈퍼바이저 · 충돌 분류

## 언제 일어나나
2라운드 6개 발언이 모두(또는 4개 이상) 끝난 직후.

## 무엇이 들어오나
- `summary_1` (요약본)
- `AgentRebuttal[]` 6개 전문

## 무슨 일이 벌어지나
슈퍼바이저는 토론 결과를 **합의 / 충돌 / 보류** 3분류로 정리하고, 합의율(`consensus_ratio`)을 계산해 **3라운드를 진행할지 바로 최종 통합으로 갈지**를 결정합니다.

| 분류 | 기준 |
| --- | --- |
| `consensus` | 5개 이상 에이전트가 동일·호환 입장 |
| `conflict` | `agree`/`disagree` 양 진영이 각각 2개 이상 |
| `pending` | 위 둘 모두 아닌 경우 |

```text
consensus_ratio = consensus / (consensus + conflict + pending)

consensus_ratio ≥ 0.7  AND  conflict 0개  → next_action = "skip_to_final"
그 외                                    → next_action = "proceed_to_round_3"
```

## 무엇이 나가나 — `SupervisorNote (mode = "classify_2")`

```json
{
  "id": "msg_05...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:32.000Z",
  "language": "ko-KR",
  "mode": "classify_2",
  "payload": {
    "consensus": [
      {
        "topic": "현 상태 방치는 결정 비용을 키운다",
        "supporting_message_ids": ["msg_02A...", "msg_04C...", "msg_04D..."]
      }
    ],
    "conflict": [
      {
        "topic": "직접 확인 vs 감정 정리 우선",
        "supporting_message_ids": ["msg_02A...", "msg_02B...", "msg_04E..."]
      }
    ],
    "pending": [
      {
        "topic": "구체적인 다음 행동의 강도",
        "supporting_message_ids": ["msg_04F..."]
      }
    ],
    "consensus_ratio": 0.33,
    "next_action": "proceed_to_round_3"
  }
}
```

## 다음 단계
- `next_action == "skip_to_final"` → [7] 최종 통합 (3라운드 생략, `Termination.reason = "consensus_reached"` 기록)
- `next_action == "proceed_to_round_3"` → [6] 3라운드

---

# [6] 3라운드 · 6개 에이전트 최종 입장 (조건부)

## 언제 일어나나
[5]에서 `proceed_to_round_3`로 결정된 경우에만.

## 무엇이 들어오나
각 에이전트가 받는 컨텍스트:

```text
- QuestionAnalysis
- summary_1, classify_2 (슈퍼바이저 요약본 둘)
- 자기의 1라운드 의견과 2라운드 발언
- 합의·충돌·보류 항목

[지시: 라운드 3 — 최종 입장]
토론 전체를 통과한 자기 입장을 정리하세요. 1라운드와 비교해 입장이 변했다면
이유를 명시하고, 사용자가 취할 수 있는 행동을 0~3개 제시하세요.
```

## 무엇이 나가나 — `AgentFinalPosition[]` (6개)

예시 1개:

```json
{
  "id": "msg_06A...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:50.000Z",
  "language": "ko-KR",
  "round": "round_3",
  "agent_id": "realist",
  "agent_name": "현실주의자",
  "final_stance": "clarify",
  "final_advice": "빈도 외 다른 신호도 함께 보되, 일주일 안에 가벼운 만남을 직접 제안해 관계 온도를 확인하세요.",
  "changed_from_round_1": false,
  "action_items": [
    "최근 2주 답장 패턴을 빈도/길이/주제 3축으로 메모",
    "주말 가벼운 약속 한 건 직접 제안",
    "제안 후 24시간 답장 패턴 관찰"
  ]
}
```

## 다음 단계
[7] 최종 통합.

---

# [7] 슈퍼바이저 · 최종 통합

## 언제 일어나나
- 3라운드 종료 후 (정상 경로)
- 또는 [5]에서 합의 도달로 점프해온 경우 (3라운드 생략)

## 무엇이 들어오나
- `QuestionAnalysis`
- `summary_1`
- `classify_2`
- `AgentFinalPosition[]` (3라운드 진행했을 경우)

> 1·2라운드 발언 원문은 들어오지 않습니다. 슈퍼바이저 요약본만으로 통합 (토큰 절약).

## 무슨 일이 벌어지나
슈퍼바이저는 **상황 요약 + 의견 대립점 + 최종 조언 + 실행 항목 + 주의사항** 5블록 구조로 사용자에게 줄 답변을 완성합니다.

## 무엇이 나가나 — `SupervisorNote (mode = "final")`

```json
{
  "id": "msg_07...",
  "consultation_id": "c8f4a8e2-...",
  "created_at": "2026-05-06T12:00:55.000Z",
  "language": "ko-KR",
  "mode": "final",
  "payload": {
    "situation": "썸 단계에서 상대의 답장 빈도가 줄어들면서 사용자가 관계의 온도를 판단하지 못하고 있는 상황입니다. 텍스트 신호만으로는 의도를 단정짓기 어렵고, 결정을 미루는 것 자체가 사용자의 불안을 키우고 있습니다.",
    "disagreements": [
      "직접 확인을 먼저 할 것인가, 본인 감정 정리가 먼저인가",
      "관찰 기간을 더 둘 것인가, 즉시 행동할 것인가"
    ],
    "final_advice": "먼저 1주일 정도 답장 패턴을 빈도·길이·주제 3축으로 가볍게 관찰한 뒤, 그 사이에 큰 변화가 없으면 주말 가벼운 약속 한 건을 먼저 제안해 관계의 온도를 직접 확인하세요. 동시에 본인이 정말 원하는 관계 형태가 무엇인지도 정리해 두는 게 좋습니다.",
    "action_items": [
      {
        "title": "답장 패턴 메모",
        "detail": "최근 2주 답장 빈도·길이·주제를 간단히 기록한다",
        "timing": "immediate"
      },
      {
        "title": "본인 감정 정리",
        "detail": "이 관계에서 본인이 원하는 형태를 한 문장으로 적어 본다",
        "timing": "short_term"
      },
      {
        "title": "가벼운 만남 제안",
        "detail": "주말에 부담 없는 활동 한 건을 직접 제안한다",
        "timing": "short_term"
      }
    ],
    "caveats": [
      "이 조언은 일반적 패턴 해석이며 개별 상황마다 차이가 있을 수 있습니다."
    ]
  }
}
```

## 다음 단계
[8] 응답 반환.

---

# [8] 프론트 응답 반환

## 무엇이 나가나 — `ConsultationResponse`

프론트가 화면을 그릴 때 필요한 모든 정보가 담긴 최종 응답입니다.

```json
{
  "consultation_id": "c8f4a8e2-...",
  "status": "completed",
  "started_at": "2026-05-06T12:00:00.123Z",
  "completed_at": "2026-05-06T12:00:55.456Z",
  "user_question": "요즘 썸남이 답장이 늦는데 밀당인지 관심이 식은 건지 모르겠어.",
  "language": "ko-KR",

  "analysis": {
    "relationship_state": "crush",
    "conflict_type": "communication_frequency",
    "key_issues": [...],
    "user_emotion": "anxious",
    "debate_goal": "..."
  },

  "rounds": [
    {
      "round": "round_1",
      "started_at": "...",
      "completed_at": "...",
      "messages": [ /* AgentOpinion 6개 */ ],
      "supervisor_note": { /* summary_1 */ }
    },
    {
      "round": "round_2",
      "messages": [ /* AgentRebuttal 6개 */ ],
      "supervisor_note": { /* classify_2 */ }
    },
    {
      "round": "round_3",
      "messages": [ /* AgentFinalPosition 6개 */ ]
    }
  ],

  "final": {
    "situation": "...",
    "disagreements": [...],
    "final_advice": "...",
    "action_items": [...],
    "caveats": [...],
    "contributing_agents": ["realist", "empath", "analyst", "actor", "mediator", "friend"]
  },

  "errors": []
}
```

## 화면 매핑 — 어떤 필드가 어떤 화면 요소를 그리나

| 화면 요소 | 응답 필드 |
| --- | --- |
| 진행 단계 표시 | `status` |
| 상담 시작 화면 (사용자 입력 에코) | `user_question` |
| 슈퍼바이저 분석 카드 | `analysis` |
| 6개 에이전트 의견 카드 | `rounds[round_1].messages` |
| 1라운드 쟁점 정리 | `rounds[round_1].supervisor_note` |
| 토론 로그 (말풍선 + 화살표) | `rounds[round_2].messages` (`targets`로 화살표) |
| 충돌·합의 시각화 | `rounds[round_2].supervisor_note.payload.{consensus, conflict, pending}` |
| 3라운드 최종 입장 카드 | `rounds[round_3].messages` |
| 최종 결과 — 상황 요약 | `final.situation` |
| 최종 결과 — 대립점 | `final.disagreements` |
| 최종 결과 — 조언 본문 | `final.final_advice` |
| 최종 결과 — 액션 카드 | `final.action_items` |
| 최종 결과 — 주의사항 | `final.caveats` |
| 오류·종료 안내 문구 | `errors[*].user_message_key`, `termination.user_message_key` |

---

# 예외 흐름

## 안전 필터 차단
[1]에서 부적절한 입력 감지 시:

```json
{
  "consultation_id": "...",
  "status": "terminated",
  "termination": {
    "reason": "safety_filter",
    "user_message_key": "termination.safety_refused"
  },
  "final": {
    "situation": "",
    "final_advice": "",
    "action_items": [],
    "caveats": ["safety.refused"]
  }
}
```

## 합의 조기 도달 ([5]에서 분기)
3라운드를 생략하고 [7]로 점프. 응답에서 `rounds`에 `round_3`이 없고 `termination.reason = "consensus_reached"`.

## 에이전트 부분 실패
일부 에이전트가 LLM 오류로 스킵되면 해당 라운드 메시지가 6개 미만이 됩니다. `errors` 배열에 사유 기록, `final.contributing_agents`에서 제외.

## 워크플로우 타임아웃 (5분 초과)
가능한 마지막 자료로 [7] 최종 통합을 강행. 불가능하면 `status = "failed"`.

> 모든 예외 처리 상세는 [supervisor_protocol.md §6, §7](supervisor_protocol.md) 참조.

---

# 자주 묻는 질문

## Q. 1라운드는 왜 병렬, 2·3라운드는 왜 순차인가?
1라운드는 "독립 의견" 수집이라 서로 영향을 주면 안 됩니다. 2·3라운드는 토론이라 앞 발언을 보고 반응해야 하므로 순차입니다.

## Q. 메시지끼리 어떻게 연결하나?
모든 메시지에는 UUID `id`가 있고, 반박은 `targets[*].target_message_id`로 그 ID를 가리킵니다. 인덱스나 이름 비교 금지.

## Q. 페르소나 이름이 바뀌면 코드가 깨지나?
안 깨집니다. `agent_id`(불변, 영문)와 `agent_name`(표시용, 한글)이 분리돼 있습니다.

## Q. 사용자에게 보이는 한국어 문구는 누가 정하나?
백엔드는 한국어 평문을 만들지 않습니다. `*_user_message_key`라는 키만 응답에 담고, 프론트가 박준혁님이 정의한 문구 사전에서 키로 조회해 표시합니다.

## Q. 이 문서랑 [message_schema.md](message_schema.md)·[supervisor_protocol.md](supervisor_protocol.md)는 어떤 관계?
- 이 문서: **사람이 흐름을 이해하기 위한 워크스루**
- `message_schema.md`: 모든 데이터 타입의 정확한 정의
- `supervisor_protocol.md`: 슈퍼바이저 동작과 분기 규칙

> 세 문서가 충돌하면 `message_schema.md`와 `supervisor_protocol.md`가 우선합니다 (이 문서는 설명용).
