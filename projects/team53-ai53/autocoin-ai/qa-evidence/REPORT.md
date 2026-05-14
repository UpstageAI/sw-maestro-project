# autocoin-ai 시나리오 B QA 보고서

| 항목 | 값 |
|---|---|
| 검수자 | 검수자 B (jbh010204) |
| 범위 | 시나리오 B (QA-B-01 ~ QA-B-05) |
| 검수일 | 2026-05-08 |
| 대상 커밋 | `autocoin-ai` clone, main HEAD |
| 검수 환경 | Python 3.14.3, langgraph 0.2.76, pytest 8.4.2 (`.venv` editable install) |
| baseline pytest | 12 / 12 PASS |
| QA-B harness | 5 / 5 PASS (`qa-evidence/qa_b_runner.py`) |

## 1. 시나리오별 pass/fail 표

| ID | 검증 항목 | 핵심 입력 | 관찰된 lifecycle / hold_reason | pass/fail | 증빙 |
|---|---|---|---|---|---|
| QA-B-01 | `HOLD_DATA_INSUFFICIENT` 분리 | `user_input.market_snapshot_fresh = false` | `HOLD` / `HOLD_DATA_INSUFFICIENT`, risk reason `STALE_MARKET_SNAPSHOT` | PASS | `scenarios/QA-B-01.json` |
| QA-B-02 | evaluator/reflection 차단 | 합성 state(`READY_FOR_BE` + 빈 `verification_checks`)를 `evaluator_node`에 직접 주입 | `HOLD` / `HOLD_DATA_INSUFFICIENT`, evaluator reason `EVIDENCE_INSUFFICIENT` | PASS | `scenarios/QA-B-02.json` |
| QA-B-03 | `verification_checks` append-only | B-01의 HOLD → 정상 데이터로 resume → 전/후 diff | 이전 entry 보존, 새 stage entry append, stage 값 모두 canonical | PASS | `scenarios/QA-B-03.json` |
| QA-B-04 | same `run_id` resume | B-01의 HOLD → `supplemental_user_input.market_snapshot_fresh = true`로 resume | `run_id`, `request_id`, `policy_refs` 모두 보존, lifecycle `READY_FOR_BE`로 전진, `resume_history`에 1건 기록 | PASS *(주석 1)* | `scenarios/QA-B-04.json` |
| QA-B-05 | resume ≠ 자동 승인 | `requires_review=true` HOLD → (1) 빈 patch resume, (2) `approval.approved=true` resume | (1) `HOLD/HOLD_REVIEW_REQUIRED` 유지, (2) `READY_FOR_BE`로 전진 | PASS | `scenarios/QA-B-05.json` |

> *주석 1 (QA-B-04)*: lifecycle / `run_id` / `request_id` / `policy_refs` / `resume_history` 5개 immutable 항목은 보존되었으나, `docs/AI.md` §6.1이 immutable로 명시한 *"이전 `decision_trace`"*는 보존되지 않았다 (resume 후 risk stage entry가 `STALE_MARKET_SNAPSHOT/HOLD` → `ALL_CHECKS_PASSED/PASS`로 덮어써짐). 본 PASS 판정은 lenient 해석이며, 이 spec/impl divergence는 §2 대표 발견 사례로 escalate한다. 증빙: `scenarios/QA-B-04.json` 의 `spec_divergence_decision_trace_immutability` 블록.

## 2. 대표 발견 사례 — `decision_trace` immutability spec/impl divergence (QA-B-04)

`docs/qa.md` §8은 "대표 실패 사례 1개 이상"을 산출물로 요구한다. 시나리오 5개는 산출물 표 기준 모두 PASS지만, QA-B-04 증빙 안에서 명확한 spec/impl divergence를 발견했다. 시나리오 자체 PASS 판정과 별개로 escalate한다.

- **spec 명문**: `docs/AI.md` §6.1 — *"immutable: `run_id`, 최초 `request_context`, 최초 `policy_context`, **이전 `decision_trace`**, 이전 `verification_checks`"* 그리고 §6 — *"초기 `policy_context`는 immutable grounding으로 유지한다."*
- **impl 동작**: `src/autocoin_ai/app.py:31-50` `AutocoinAgentApp.resume()`는 `deepcopy(prev)` 후 `self.start(previous)`를 호출 → graph가 `policy` 노드부터 다시 실행 → `policy_node` / `risk_node` / `evaluator_node`가 모두 `set_trace()` (`src/autocoin_ai/models.py:80-97`)로 자신의 stage entry를 *덮어쓴다* (`state.setdefault("decision_trace", canonical_trace())[stage] = entry`).
- **관찰 증빙** (`scenarios/QA-B-04.json`):
  - `pre_resume_risk_trace`: `{reason_codes: ["STALE_MARKET_SNAPSHOT"], final_action: "HOLD"}`
  - `post_resume_risk_trace`: `{reason_codes: ["ALL_CHECKS_PASSED"], final_action: "PASS"}`
  - `spec_divergence_decision_trace_immutability.previous_decision_trace_risk_preserved = false`
- **영향 평가**: 시나리오 B 범위에서 lifecycle 진행은 `READY_FOR_BE`로 정확히 안내되므로 행동 결과는 일관된다. 그러나 spec이 명문으로 "이전 `decision_trace`는 immutable"을 약속했다면 (a) 이전 trace를 별도 슬롯(예: `decision_trace_history` / per-attempt array)에 보존하거나 (b) spec 문구를 "재집계 가능"으로 수정해야 정합한다. 둘 중 어느 쪽도 본 검수 단독으로 결정할 수 없으므로 spec/impl 오너에게 escalate한다.
- **권고 결정 항목** (BE 통합 라운드 전에 결정 필요):
  1. 이전 `decision_trace`를 보존할 것인가, spec 문구를 변경할 것인가?
  2. 보존한다면 슬롯 이름과 history shape (예: `decision_trace_history: List[Dict[stage, TraceEntry]]`) 합의 필요.
  3. `evidence_refs`가 list 인덱스를 가리키는 경우, history 도입 시 인덱스 의미가 바뀌는지 재점검 필요 (`docs/DATA.md` §6 trace shape에 영향).

(부속 발견 — QA-B-02 그래프 routing 구조적 관찰은 §5로 이동.)

## 3. canonical 용어 일치 체크리스트

`docs/qa.md` §7 "canonical 상태/필드명이 틀리면 실패다" 기준에 따라 각 증빙 JSON에서 다음 용어가 임의 변형 없이 그대로 등장하는지 확인했다.

| 카테고리 | 항목 | 확인 |
|---|---|---|
| 식별자 | `run_id` | OK (`airun_test_001` 그대로 유지, B-04 immutable 확인) |
| 컨텍스트 | `request_context`, `policy_context` | OK (B-04 pre/post diff에서 보존) |
| trace | `decision_trace`(stage-keyed: `policy`/`risk`/`evaluator`/`execution`/`run_summary`) | OK (B-01~B-05 모두 stage-keyed container 유지) |
| 검증 | `verification_checks` (`stage` ∈ {policy, risk, evaluator, execution, be_revalidation}) | OK (B-03에서 `all_stages_canonical=true`로 검증) |
| HOLD | `hold_reason` ∈ {`HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`} | OK (B-01: DATA, B-05: REVIEW로 분리 확인) |
| lifecycle | `HOLD`, `READY_FOR_BE`, `NO_ORDER`, `BE_REJECTED`, `FAILED`, `REPORT_READY` | OK (시나리오 B 범위에서 사용된 `HOLD`, `READY_FOR_BE`가 임의 변형 없음) |
| gate vs lifecycle 분리 | `PASS` ≠ `READY_FOR_BE` | OK (B-04에서 risk trace `final_action=PASS`이고 lifecycle만 `READY_FOR_BE`) |
| resume 계약 | `resume_history`, `resume_reason`, `patch_fields` | OK (B-04, B-05 증빙에 그대로 등장) |

## 4. 공통 판정 규칙(`docs/qa.md` §7) 점검

| 규칙 | 결과 | 메모 |
|---|---|---|
| canonical 상태/필드명 정합 | PASS | 위 §3 표 |
| `PASS`를 최종 승인처럼 설명하지 않음 | PASS | `decision_trace.risk.final_action=PASS`은 gate 의미만, lifecycle은 별도 `READY_FOR_BE`(B-04) |
| `READY_FOR_BE`는 lifecycle handoff 의미만 | PASS | 시나리오 B 범위에서 BE 호출/체결 의미로 쓰이지 않음 |
| HOLD 두 subtype 분리 | PASS | B-01 `HOLD_DATA_INSUFFICIENT`, B-05 `HOLD_REVIEW_REQUIRED` 둘 다 명확히 분리 |
| same `run_id` resume에서 immutable 필드 보존 | PASS | B-04 `run_id_preserved`, `request_id_preserved`, `policy_refs_preserved` 모두 true |

## 5. 검수자 B 메모 (부속 관찰)

1. **`app.resume`는 graph를 재실행한다** (`src/autocoin_ai/app.py:31-50`). 시나리오 B 범위에서 두 가지 부수 효과가 관찰된다:
   - **`verification_checks` 중복 누적**: 동일 `(stage, name)` 쌍이 list 끝에 다시 append된다 (B-03 증빙: `initial_checks_count=3` → `resumed_checks_count=7`, `duplicate_stage_name_pairs_count=2`). 이전 entry는 *원형 그대로* 살아있고 (`initial_entry_values_intact=true`) list가 잘리지 않으므로 strict 'append-only'에는 부합하지만, `evidence_refs`가 list 인덱스를 가리킬 경우 인덱스 의미가 바뀐다.
   - **`decision_trace` stage entry 덮어쓰기**: 위 §2 대표 발견 사례 참조. spec/impl divergence로 escalate 됨.
2. **QA-B-02 그래프 routing 한계**: `src/autocoin_ai/graph.py:24-27` `route_after_risk`는 `lifecycle == LIFECYCLE_READY_FOR_BE`일 때만 `evaluator`로 보낸다. 그런데 risk_node가 `READY_FOR_BE`를 셋팅하는 시점에는 `policy_node`가 이미 `policy.initial_request_contract` / `policy.policy_context_available` pass를 append했고 risk_node 자신도 `risk.risk_gate_rules` pass를 append한 상태다. 따라서 `evaluator_node`(`src/autocoin_ai/nodes/evaluator.py:22-27`)의 `EVIDENCE_INSUFFICIENT` branch는 정상 그래프 흐름의 어떤 입력으로도 트리거되지 않는다. 본 보고서는 `qa_b_runner.py:run_b02`가 합성 state를 evaluator_node에 직접 주입해 차단 책임을 검증했다 — 이 단위 harness를 향후 회귀 가드로 보존할 것을 권고한다. 평가자 차단 책임이 실제 그래프 안에서 의미를 가지려면 (a) BE deterministic revalidation 후 evaluator 재호출 또는 (b) reflection edge 추가가 필요하다.
3. **`FAILED` resume 금지는 코드에 강제되어 있다** (`app.py:35-36`). 시나리오 B 범위 외이지만 같은 `run_id` 안전 계약의 핵심 보호 장치로서 확인.
4. **빈 `patch_fields` resume은 정책상 허용**된다. `app.py:39-46`은 `supplemental_user_input`/`approval`이 없어도 `setdefault`만 호출하고 그래프를 재실행한다. QA-B-05의 안전 동작은 graph 재실행 시 같은 `requires_review=True`가 그대로 남아 다시 `HOLD_REVIEW_REQUIRED`로 떨어지는 `risk_node`의 멱등성에 기반한다 — 즉 *resume이 자동 승인을 하지 않는다*는 보장은 graph 재실행 + risk_node 룰의 결합으로만 성립하며, evaluator/별도 approval gate에 의한 보장이 아님을 명시.
5. **시나리오 B 범위에서 Binance 직접 호출 / 서명 / API key 처리 시도는 0건**이다 (B-04, B-05의 `verification_checks`에 `be_revalidation` stage entry는 발생하지 않음 — 시나리오 B 단독 범위에서는 BE 통합이 빠진 상태). `tests/test_boundaries.py::test_ai_application_does_not_contain_binance_execution_calls`도 PASS로 베이스라인에서 확인.

## 6. 최종 결론

> **시나리오 B 범위(QA-B-01 ~ QA-B-05)는 `autocoin-ai` 단독 검수 기준을 *조건부* 통과한다 (5/5 PASS + 1건 spec/impl divergence escalate).**

- 모든 시나리오에서 canonical 용어가 유지되었고, HOLD subtype과 lifecycle handoff (`READY_FOR_BE`)가 의도대로 분리된다.
- same `run_id` resume에서 `run_id` / `request_context` / `policy_context.policy_refs` / `verification_checks` (값 보존) / `resume_history`는 보존되며, resume 자체가 자동 승인 의미를 가지지 않는다.
- 다만 §2 발견 (이전 `decision_trace`가 `docs/AI.md` §6.1의 immutable 명문에 반해 resume 시 stage entry가 덮어써지는 점)은 본 검수 단독으로 PASS/FAIL 판정을 확정할 수 없다. **BE 통합 라운드 진입 전에 spec/impl 오너가 (a) 보존 슬롯 도입 또는 (b) spec 문구 수정 중 한 쪽으로 결정해야 한다.**
- evaluator의 차단 책임 검증은 그래프 routing 구조상 단위 harness로만 가능한 한계가 있으므로 (§5-2), 본 보고서의 `qa_b_runner.py:run_b02`를 향후 회귀 가드로 보존할 것을 권고한다.
- 위 결정 항목 외에는 시나리오 B 범위에서 회귀나 lifecycle 의미 충돌이 관찰되지 않았다.

## 7. 산출물 위치

- 본 보고서: `qa-evidence/REPORT.md`
- 시나리오별 JSON 증빙: `qa-evidence/scenarios/QA-B-0{1..5}.json`
- 5개 시나리오 통합 결과: `qa-evidence/rollup.json`
- 재현 가능한 harness: `qa-evidence/qa_b_runner.py` (실행: `.venv/bin/python qa-evidence/qa_b_runner.py`)
- 베이스라인 pytest: `pytest tests/ -v` (12 PASS)
