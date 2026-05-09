# autocoin-ai AI 계층 명세

## 문서 목적

이 문서는 `autocoin-ai`의 중심 문서다. LangGraph 기반 AI 계층이 Coin Agent 안에서 어떤 상태 계약과 판단 규칙을 가져야 하는지 최소 범위로 정리한다.

## 관련 문서

- 진입점: `README.md`
- 범위와 요구사항: `SPEC.md`
- 책임 경계: `ARCHITECTURE.md`
- 이 문서: `AI.md`
- 필드와 상태 계약: `DATA.md`
- 테스트와 데모 기준: `TEST_AND_DEMO.md`

## 1. AI 계층의 역할

AI 계층은 주문 테스트 요청을 구조화하고, 정책과 시장 근거를 바탕으로 판단하며, 그 판단을 설명 가능한 형태로 남긴다. AI는 Binance를 직접 호출하지 않고, BE가 전달한 정규화 입력만 사용한다.

## 2. 고정 원칙

- 기본 범위는 Binance Spot Testnet 전용이다.
- 기본 실패 방향은 `NO_ORDER` 또는 `HOLD`다.
- `PASS`는 proposal 통과 의미일 뿐, 실행 승인 의미가 아니다.
- `READY_FOR_BE`는 lifecycle에서만 쓰는 AI-side handoff 상태다.
- 최종 실행 권한은 항상 BE에 있다.
- 같은 요청 흐름은 같은 `run_id`로 이어진다.
- 정책 artifact 기반 grounding 결과는 `policy_context`로 유지한다.
- 단계별 판단 근거는 `decision_trace`에 남긴다.

## 3. 최소 Agent 역할

| Agent | 책임 | 주요 산출물 |
|---|---|---|
| Intake | 자연어 `raw_text` → 구조화 주문 의도, trader_id / persona 결정 | `normalized_order_intent`, `trader_id`, `inferred_persona` |
| Policy / Planning | RAG retrieval, persona_bounds 설정, 정책 근거 선택 | `policy_context`, `trader_principles`, policy trace |
| Strategy | trader_principles + persona 기반 LLM proposal 생성 | `llm_proposal`, strategy trace |
| Market / Risk Gate | 결정론 7단계 검증, 도구 호출 | `risk_assessment`, `risk_tool_calls`, gate decision |
| Evaluator / Reflection | 사용자 리포트 + schema sanity check | `evaluator_review`, evaluator trace |
| Execution / Report | BE 결과 해석, 사용자 설명 정리 | execution trace, final report |

## 4. 최소 상태 계약

| 항목 | 의미 |
|---|---|
| `run_id` | 하나의 AI run 식별자 |
| `request_context` | 최초 요청의 immutable envelope |
| `policy_context` | 정책 artifact 기반 grounding 컨텍스트 |
| `trader_id` | 트레이더 스타일 식별자 (예: `wonyotti`, `livermore`) |
| `inferred_persona` | intake 결정 페르소나 (`CONSERVATIVE` / `MODERATE` / `AGGRESSIVE`) |
| `persona_override_reason` | 발화 명시 단어로 persona가 override된 사유 (선택) |
| `trader_principles` | RAG retrieval된 트레이더 원칙 목록 |
| `normalized_order_intent` | intake가 정규화한 주문 의도 |
| `llm_proposal` | strategy 노드의 LLM 제안 |
| `risk_assessment` | risk_gate 판정 결과 |
| `risk_tool_calls` | risk_gate가 호출한 도구 기록 (append-only) |
| `evaluator_review` | evaluator 최종 사용자 리포트 |
| `decision_trace` | 단계별 reason, evidence, final action 기록 |
| `verification_checks` | 단계별 검증 결과를 누적하는 공통 체크 목록 |
| `hold_reason` | `HOLD`의 세부 원인 |

`request_context`의 최소 필드는 `request_id`, `request_type`, `requested_at`, `user_input`다. Agentic MVP에서는 `user_input.raw_text`로 자연어를 전달한다. 기존 dict 형식은 회귀 호환으로 유지한다.

최소 종료 또는 핵심 상태는 다음 값을 유지한다.

- `READY_FOR_BE`
- `NO_ORDER`
- `BE_REJECTED`
- `FAILED`
- `REPORT_READY`
- `HOLD_REVIEW_REQUIRED`
- `HOLD_DATA_INSUFFICIENT`
- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

### 4.1 lifecycle 해석

| 값 | 의미 | 작성 주체 |
|---|---|---|
| `HOLD` | 사람 검토 또는 추가 데이터 대기 | AI 또는 BE |
| `READY_FOR_BE` | AI proposal이 BE deterministic revalidation으로 handoff 된 상태 | AI |
| `NO_ORDER` | 신규 주문 생성 없이 종료 | AI |
| `BE_REJECTED` | BE 재검증 차단 | BE |
| `FAILED` | schema mismatch 또는 복구 불가 기술 실패 | AI 또는 BE |
| `REPORT_READY` | 사용자용 최종 설명 준비 완료 | AI |

### 4.2 hold_reason 전체 집합

| 값 | 발생 조건 |
|---|---|
| `HOLD_INPUT_AMBIGUOUS` | `ambiguity_score > 0.5` (intake) |
| `HOLD_LOW_CONVICTION` | LLM proposal의 conviction < persona_bounds.min_conviction |
| `HOLD_RISK_AGENT_FLAGGED` | 변동성 또는 집중 리스크 임계 초과 |
| `HOLD_DATA_INSUFFICIENT` | 잔고 부족 또는 필수 데이터 누락 |
| `HOLD_REVIEW_REQUIRED` | 수동 운영 검토 필요 (BE or 정책) |

## 5. 판단 규칙

### 5.0 Intake

- `user_input.raw_text`가 있으면 Gemini structured output으로 LLM 파싱 모드를 실행한다.
- `raw_text`가 없으면 기존 dict 모드로 처리한다 (회귀 호환).
- `ambiguity_score > 0.5`이면 `HOLD` + `hold_reason=HOLD_INPUT_AMBIGUOUS`로 조기 종료한다.
- `trader_id`와 `inferred_persona`는 intake 종료 후 immutable이며, 이후 어떤 노드도 수정하지 않는다.
- `persona_override_reason`은 발화에서 명시 단어가 감지될 때만 기록하고 없으면 빈 문자열이다.

### 5.1 Policy / Planning

- 요청을 주문 테스트 의도로 정규화한다.
- `policy_context` 안에서 적용 정책 근거를 고른다.
- 누락 필드를 억지로 추정하지 않는다.
- 최초 `request_context`는 수정하지 않고, `normalized_order_intent`와 `decision_trace.policy`만 추가한다.

### 5.1-B Strategy

- `trader_principles`와 `persona_bounds`를 참고해 `action`, `size_usd`, `conviction`, `rationale`, `matched_principle_titles`를 포함한 `llm_proposal`을 생성한다.
- `matched_principle_titles`는 실제 `trader_principles`에 존재하는 title만 사용한다 (환각 차단은 evaluator가 검증).
- LLM 호출 실패 또는 schema 깨짐은 `FAILED` + reason `"STRATEGY_LLM_ERROR"`로 처리한다.

### 5.2 Market / Risk Gate

- `llm_proposal`을 받아 결정론 7단계 검증을 위→아래 단락 방식으로 수행한다.
- 잔고, 시장 변동성, 집중 리스크, persona_bounds를 순서대로 확인한다.
- 각 도구 호출 결과는 `risk_tool_calls`에 append한다.
- 검증 실패 시: `HOLD` + 해당 hold_reason, 또는 `NO_ORDER` + trace reason code.
- 모두 통과 시: `lifecycle_status = READY_FOR_BE`.
- LLM 호출을 하지 않는다 (결정론).

### 5.3 Evaluator / Reflection

- `FAILED`를 제외한 모든 lifecycle에서 항상 실행해 `evaluator_review.user_message`를 생성한다.
- `schema_warnings`에 4개 sanity check 결과를 기록한다: stage 완전성, strategy pass 여부, risk_tool_calls 일치, matched_principle_titles 환각 차단.
- `lifecycle_status`와 `hold_reason`을 echo만 하고 수정하지 않는다.
- LLM 호출 실패 시 결정론 폴백으로 `user_message`를 생성하며, `lifecycle_status`를 FAILED로 만들지 않는다.

`verification_checks`는 각 단계가 append 하는 최소 검증 목록으로 본다. Intake 파싱 검증, Policy grounding 검증, Strategy proposal 검증, Risk gate 판정 검증, Evaluator 완료 검증이 같은 run 안에서 누적되어야 한다.

최소 entry shape는 `name`, `stage`, `result`, `evidence_refs`를 가진다. stage는 `intake`, `policy`, `strategy`, `risk`, `evaluator`, `execution`, `be_revalidation` 중 하나로 제한한다.

`decision_trace`는 flat object가 아니라 stage-keyed container를 사용한다. 최소 키는 `policy`, `risk`, `evaluator`, `execution`, `run_summary`다. `intake`와 `strategy`는 선택적 키로 추가된다. 각 stage key의 값은 `reason_codes`, `evidence_refs`, `final_action`, 선택적 `notes`를 가진다.

### 5.4 Execution / Report

- BE가 준 실행 결과 또는 차단 결과를 해석한다.
- BE 차단은 `BE_REJECTED`로 구분해 설명한다.
- 사용자용 최종 요약은 `REPORT_READY` 기준으로 정리한다.
- schema mismatch나 필수 필드 결손처럼 설명 이전에 계약이 깨진 경우는 `FAILED`로 구분한다.

BE->AI completion payload는 두 축 중 하나를 포함해야 한다.

- 성공/실행 축: `execution_result`
- 재검증 차단 축: `be_rejection_evidence`

AI는 이 completion payload를 받아 `decision_trace.execution`과 `decision_trace.run_summary`를 완성한다. `NO_ORDER`와 `BE_REJECTED`도 설명 payload를 만들 수 있지만, lifecycle 종료 의미는 각각 유지하고 `REPORT_READY`는 "설명 준비 완료"라는 reporting 상태로만 해석한다.

## 6. resume 규칙

- resume는 같은 `run_id`에서만 허용한다.
- 초기 `policy_context`는 immutable grounding으로 유지한다.
- 보완 데이터, 승인 결과, execution result만 patch 대상으로 본다.
- resume 자체가 자동 승인 의미가 되면 안 된다.

### 6.1 immutable vs patchable

- immutable: `run_id`, 최초 `request_context`, 최초 `policy_context`, 이전 `decision_trace`, 이전 `verification_checks`
- patchable: 보완 입력, 최신 market snapshot, approval 결과, execution result, BE rejection evidence
- resume는 `HOLD` 또는 보완 가능한 상태에서만 허용되며, `FAILED` 종료 후에는 같은 run을 재사용하지 않는다.

## 7. 금지 사항

- AI가 Binance REST 또는 WebSocket을 직접 호출하는 구조
- AI가 서명, timestamp, API Key 처리를 담당하는 구조
- AI가 `PASS`를 최종 실행 상태처럼 설명하는 문구
- live trading, futures, margin, withdraw, leverage 문맥 추가

## 8. 다른 문서와의 연결

- 범위와 완료 기준은 `SPEC.md`
- 시스템 위치와 FE->BE->AI 경계는 `ARCHITECTURE.md`
- canonical 필드와 상태명은 `DATA.md`
- HOLD, `BE_REJECTED`, resume 검증 시나리오는 `TEST_AND_DEMO.md`
- human QA, `FAILED`, schema mismatch 검증 시나리오는 `TEST_AND_DEMO.md`
