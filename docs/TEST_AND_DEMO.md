# autocoin-ai 테스트 및 데모 기준

## 문서 목적

이 문서는 `autocoin-ai` 서브프로젝트에서 꼭 검증해야 하는 AI 중심 테스트와 데모 기준을 정리한다. 전체 FE나 BE 테스트를 다시 쓰지 않고, 책임 경계와 상태 계약이 유지되는지 확인하는 데 초점을 둔다.

## 관련 문서

- 진입점: `README.md`
- 범위와 완료 기준: `SPEC.md`
- 구조와 cadence: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- AI 계층 규칙: `AI.md`
- 데이터와 상태 계약: `DATA.md`
- 이 문서: `TEST_AND_DEMO.md`

## 1. 테스트 원칙

- 모든 시나리오는 Binance Spot Testnet 전용이다.
- FE->BE->AI 경계가 깨지면 실패로 본다.
- `PASS`와 최종 실행 승인을 같은 의미로 보면 안 된다.
- `PASS`와 `READY_FOR_BE`는 같은 값이 아니며, 전자는 trace/gate 의미, 후자는 lifecycle handoff 의미다.
- 보류와 차단은 `run_id`, `hold_reason`, `decision_trace` 기준으로 설명 가능해야 한다.
- schema mismatch와 기술 실패는 `FAILED`로 따로 구분되어야 한다.
- 정책별 workflow 차이와 비정상 흐름은 human QA rehearsal로 반복 검증 가능해야 한다.

## 2. 필수 검증 항목

| ID | 검증 항목 | 기대 결과 |
|---|---|---|
| AIT-01 | 정책 grounding | `policy_context`가 trace와 함께 남는다. |
| AIT-01A | initial request contract | 최초 요청이 `request_context` 최소 shape를 가진다. |
| AIT-02 | risk gate 판단 | `decision_trace`에 근거와 `final_action`이 남는다. |
| AIT-02A | proposal / lifecycle 분리 | `PASS`와 `READY_FOR_BE`가 서로 다른 의미로 유지된다. |
| AIT-02B | trace container shape | `decision_trace`가 stage-keyed canonical container를 유지한다. |
| AIT-03 | review hold | `HOLD_REVIEW_REQUIRED`가 구분된다. |
| AIT-04 | data hold | `HOLD_DATA_INSUFFICIENT`가 구분된다. |
| AIT-05 | BE 재검증 차단 | `BE_REJECTED`가 일반 실패와 구분된다. |
| AIT-06 | schema mismatch / 기술 실패 | 계약 위반이나 복구 불가 실패는 `FAILED`로 구분된다. |
| AIT-07 | final report | 최종 설명이 `REPORT_READY` 기준으로 정리된다. |
| AIT-08 | same run resume | 같은 `run_id` 기준 resume가 유지된다. |
| AIT-08A | completion payload contract | BE가 `execution_result` 또는 `be_rejection_evidence`를 되돌려 줄 수 있다. |
| AIT-09 | boundary check | FE는 Binance 직접 호출을 하지 않고, BE만 최종 제출 권한을 가진다. |
| AIT-10 | human QA rehearsal | 정책별 workflow 차이와 비정상 상태가 반복 검증 가능하다. |
| AIT-11 | 자연어 intake 파싱 | `user_input.raw_text`가 `normalized_order_intent`, `trader_id`, `inferred_persona`로 변환된다. |
| AIT-12 | ambiguity HOLD | 모호한 입력은 `HOLD` + `hold_reason=HOLD_INPUT_AMBIGUOUS`로 조기 종료된다. |
| AIT-13 | persona override | "공격적으로" 발화가 `inferred_persona=AGGRESSIVE` + `persona_override_reason` 기록으로 이어진다. |
| AIT-14 | trader_id 결정 | 디폴트 `wonyotti`, 발화 또는 명시 시 `livermore`로 전환된다. |
| AIT-15 | RAG retrieval | `policy` 노드가 `trader_principles`를 retrieval하고 적어도 1개 이상 반환한다. |
| AIT-16 | strategy proposal | `llm_proposal`이 `action`, `conviction`, `matched_principle_titles`를 포함한다. |
| AIT-17 | risk_gate 결정론 | 7단계 검증 결과가 `risk_assessment.verdict`와 `risk_tool_calls`로 추적 가능하다. |
| AIT-18 | evaluator user_message | `evaluator_review.user_message`가 항상 생성되고 FE에 표시 가능하다. |
| AIT-19 | dict 모드 회귀 | `raw_text` 없는 기존 입력에서 기존 24개 테스트가 통과한다. |

## 3. 최소 시나리오

### 시나리오 1. 정책 허용 흐름

1. FE가 주문 테스트 요청을 BE에 전달한다.
2. BE가 `policy_context`를 구성해 AI run을 시작한다.
3. AI가 proposal을 만들고 lifecycle은 `READY_FOR_BE`로 정리된다.
4. `decision_trace` 또는 gate 의미의 `PASS`가 lifecycle 값과 혼동되지 않는지 확인한다.
5. BE가 `execution_result`를 돌려주고 AI가 reporting payload를 완성하는지 확인한다.
6. 결과는 최종적으로 `REPORT_READY`로 정리될 수 있다.

### 시나리오 2. `HOLD_REVIEW_REQUIRED`

1. 정책상 자동 진행이 허용되지 않는 요청을 사용한다.
2. AI는 `HOLD`와 `hold_reason=HOLD_REVIEW_REQUIRED`를 남긴다.
3. 승인 전에는 주문이 제출되지 않는다.

### 시나리오 3. `HOLD_DATA_INSUFFICIENT`

1. 시장 데이터 또는 필수 입력이 부족한 요청을 사용한다.
2. AI는 `HOLD`와 `hold_reason=HOLD_DATA_INSUFFICIENT`를 남긴다.
3. 보완 후 같은 `run_id`로 resume 한다.

### 시나리오 4. `BE_REJECTED`

1. AI proposal은 통과했지만 BE 재검증에서 차단되는 조건을 준비한다.
2. BE가 `be_rejection_evidence`를 AI에 되돌려 주는지 확인한다.
3. 최종 구분 값은 `BE_REJECTED`로 남아야 한다.
4. 이 결과는 일반 기술 실패와 분리되어 설명되어야 한다.

### 시나리오 5. `FAILED`

1. schema mismatch 또는 필수 필드 결손 상황을 준비한다.
2. 상태는 `BE_REJECTED`나 `HOLD`와 섞이지 않고 `FAILED`로 남아야 한다.
3. 실패 원인과 재시도 불가 또는 추가 수정 필요성이 설명되어야 한다.

### 시나리오 6. same `run_id` resume

1. `HOLD_REVIEW_REQUIRED` 또는 `HOLD_DATA_INSUFFICIENT` 상태를 만든다.
2. 같은 `run_id`로 patchable 필드만 보완해 resume 한다.
3. 이전 `decision_trace`와 `verification_checks`가 보존되고, 보완된 stage entry만 추가되는지 확인한다.

### 시나리오 8. 자연어 매수 → 정상 통과 (Agentic MVP)

1. `user_input.raw_text = "공격적으로 비트코인 5만원어치 사줘"` 입력을 사용한다.
2. intake가 `BTCUSDT BUY`, `inferred_persona=AGGRESSIVE`, `persona_override_reason` 기록, `ambiguity_score ≤ 0.5`로 파싱한다.
3. policy가 `livermore` 또는 `wonyotti` 원칙을 retrieval한다.
4. strategy가 `action=BUY`, `conviction ≥ 0.5`, `matched_principle_titles` 1개 이상을 포함한 `llm_proposal`을 생성한다.
5. risk_gate가 7단계를 통과해 `lifecycle_status=READY_FOR_BE`가 된다.
6. evaluator가 `evaluator_review.user_message`를 생성한다.

### 시나리오 9. 모호한 입력 → `HOLD_INPUT_AMBIGUOUS`

1. `user_input.raw_text = "비트코인 좀 사봐"` 처럼 모호한 입력을 사용한다.
2. intake의 `ambiguity_score > 0.5`로 판단된다.
3. `lifecycle_status=HOLD`, `hold_reason=HOLD_INPUT_AMBIGUOUS`로 종료된다.
4. evaluator가 `user_message`를 생성해 추가 정보 요청 안내를 한다.

### 시나리오 10. conviction 미달 → `HOLD_LOW_CONVICTION`

1. 심볼, 방향, 금액은 명확하나 `llm_proposal.conviction < persona_bounds.min_conviction`인 상황을 사용한다.
2. risk_gate가 `lifecycle_status=HOLD`, `hold_reason=HOLD_LOW_CONVICTION`으로 판정한다.

### 시나리오 11. `NO_ORDER` reporting

1. 명백한 금지 요청 또는 필수 입력 누락 요청을 준비한다.
2. lifecycle은 `NO_ORDER`로 종료되어야 한다.
3. 사용자 설명 payload는 별도로 생성될 수 있지만, lifecycle 값이 `REPORT_READY`로 덮어써지지 않는지 확인한다.

## 4. human QA rehearsal

- 최소 2명 이상이 정책 허용 흐름, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, `FAILED`를 같은 용어로 읽고 같은 기대 결과로 검증해야 한다.
- policy preset 또는 동등한 시나리오 분기를 바꿔도 FE->BE->AI 책임 경계 설명이 흔들리지 않아야 한다.
- rehearsal은 happy path 1회가 아니라 비정상 흐름까지 반복 가능해야 한다.

## 5. 데모 체크포인트

- Testnet 전용 host만 노출되는지 확인
- `run_id`가 같은 흐름으로 이어지는지 확인
- `policy_context`와 `decision_trace`가 결과 설명에 반영되는지 확인
- `decision_trace`가 `policy`, `risk`, `evaluator`, `execution`, `run_summary` key를 유지하는지 확인
- `READY_FOR_BE`가 lifecycle handoff로만 쓰이는지 확인
- `hold_reason`이 5가지 subtype(`HOLD_INPUT_AMBIGUOUS`, `HOLD_LOW_CONVICTION`, `HOLD_RISK_AGENT_FLAGGED`, `HOLD_DATA_INSUFFICIENT`, `HOLD_REVIEW_REQUIRED`)으로 구분되는지 확인
- `FAILED`가 `BE_REJECTED`나 `HOLD`와 다른 축으로 설명되는지 확인
- FE가 실행 주체처럼 보이지 않는지 확인
- BE가 최종 제출 권한자임이 드러나는지 확인
- `user_input.raw_text` 자연어 입력이 `normalized_order_intent`로 파싱되는지 확인
- `trader_id`와 `inferred_persona`가 intake 이후 변경되지 않는지 확인
- `trader_principles`가 1개 이상 retrieval되는지 확인
- `evaluator_review.user_message`가 FE 표시용으로 생성되는지 확인
- dict 모드 입력(기존 24개 테스트)이 회귀 없이 통과하는지 확인

## 6. 완료 판단

이 서브프로젝트 문서는 다음 조건을 만족할 때 일관된 것으로 본다.

- `README.md`, `SPEC.md`, `ARCHITECTURE.md`, `AI.md`, `DATA.md`와 용어가 맞는다.
- `run_id`, `policy_context`, `decision_trace`, `hold_reason`가 같은 의미로 유지된다.
- `verification_checks`가 단계별 검증 목록으로 같은 의미를 가진다.
- `request_context`, `execution_result`, `be_rejection_evidence`의 최소 shape가 유지된다.
- `decision_trace`가 stage-keyed canonical container로 유지된다.
- `PASS`와 `READY_FOR_BE`가 서로 다른 의미로 유지된다.
- `HOLD_INPUT_AMBIGUOUS`, `HOLD_LOW_CONVICTION`, `HOLD_RISK_AGENT_FLAGGED`, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`가 빠지지 않는다.
- `trader_id`, `inferred_persona`, `trader_principles`, `llm_proposal`, `evaluator_review`가 같은 의미로 유지된다.
- `user_input.raw_text` 모드와 dict 모드가 회귀 호환을 유지하며 공존한다.
- Testnet-only 범위와 FE->BE->AI 경계가 데모 설명에도 유지된다.
- human QA rehearsal이 정책별 분기와 비정상 흐름까지 반복 가능하다.
