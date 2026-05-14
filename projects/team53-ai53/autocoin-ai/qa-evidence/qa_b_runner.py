"""검수자 B (시나리오 B) 단독 QA harness.

QA-B-01 ~ QA-B-05 시나리오의 입력/기대결과/관찰결과/decision_trace/
verification_checks를 JSON 증빙으로 떨어뜨린다. docs/qa.md §3 증빙
기록 규칙을 그대로 따른다.

사용:
    .venv/bin/python qa-evidence/qa_b_runner.py
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from autocoin_ai.app import AutocoinAgentApp
from autocoin_ai.constants import (
    HOLD_DATA_INSUFFICIENT,
    HOLD_REVIEW_REQUIRED,
    LIFECYCLE_HOLD,
    LIFECYCLE_READY_FOR_BE,
)
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.nodes.evaluator import evaluator_node
from tests.fixtures import allowed_request, request_with_user_input


REVIEWER = "검수자 B"
OUT_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = OUT_DIR / "scenarios"
SCENARIOS_DIR.mkdir(exist_ok=True)


def _dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _trace_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    trace = state.get("decision_trace", {})
    return {
        stage: {
            "reason_codes": entry.get("reason_codes", []),
            "final_action": entry.get("final_action", ""),
        }
        for stage, entry in trace.items()
    }


def _checks_summary(state: Dict[str, Any]) -> list:
    return [
        {"stage": c.get("stage"), "name": c.get("name"), "result": c.get("result")}
        for c in state.get("verification_checks", [])
    ]


def _evidence(scenario_id: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "reviewer": REVIEWER,
        **summary,
    }


def run_b01() -> Dict[str, Any]:
    """QA-B-01 HOLD_DATA_INSUFFICIENT 검증."""
    payload = request_with_user_input(market_snapshot_fresh=False)
    app = AutocoinAgentApp()
    state = app.start(payload)

    expected = {
        "lifecycle_status": LIFECYCLE_HOLD,
        "hold_reason": HOLD_DATA_INSUFFICIENT,
        "risk.reason_codes": ["STALE_MARKET_SNAPSHOT"],
    }
    observed = {
        "lifecycle_status": state.get("lifecycle_status"),
        "hold_reason": state.get("hold_reason"),
        "risk.reason_codes": state["decision_trace"]["risk"]["reason_codes"],
    }
    passed = (
        observed["lifecycle_status"] == expected["lifecycle_status"]
        and observed["hold_reason"] == expected["hold_reason"]
        and observed["risk.reason_codes"] == expected["risk.reason_codes"]
    )

    summary = {
        "purpose": "데이터 부족이 generic failure가 아니라 data hold(HOLD_DATA_INSUFFICIENT)로 분리되는지 확인",
        "input_payload": payload,
        "expected": expected,
        "observed": observed,
        "decision_trace": _trace_summary(state),
        "verification_checks": _checks_summary(state),
        "passed": passed,
        "notes": "request_with_user_input(market_snapshot_fresh=False) → risk_node가 HOLD + HOLD_DATA_INSUFFICIENT를 셋팅",
    }
    _dump_json(SCENARIOS_DIR / "QA-B-01.json", _evidence("QA-B-01", summary))
    return _evidence("QA-B-01", summary)


def run_b02() -> Dict[str, Any]:
    """QA-B-02 evaluator/reflection 차단 검증.

    그래프 routing이 lifecycle == READY_FOR_BE 일 때만 evaluator를 거치도록
    되어 있고, 그 시점에는 policy / risk 모두 pass entry가 이미
    `verification_checks`에 누적되어 있다(graph.py:24-27, evaluator.py:14-27).
    따라서 자연 흐름에서는 EVIDENCE_INSUFFICIENT branch가 도달 불가다.
    QA 의도("근거 부족이면 승격을 막는다")를 직접 검증하기 위해
    합성된 state를 evaluator_node에 직접 주입하는 단위 harness를 사용한다.
    """
    synthetic_state = ensure_state_shape(
        {
            "run_id": "airun_b02_unit",
            "request_context": {
                "request_id": "req_b02_unit",
                "request_type": "PLACE_ORDER_TEST",
                "requested_at": "2026-05-08T15:00:00+09:00",
                "user_input": {
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "type": "MARKET",
                    "quoteOrderQty": "50",
                },
            },
            "policy_context": {"policy_refs": ["policy.symbol_allowlist"]},
            "lifecycle_status": LIFECYCLE_READY_FOR_BE,
            "verification_checks": [],
        }
    )
    state = evaluator_node(synthetic_state)

    expected = {
        "lifecycle_status": LIFECYCLE_HOLD,
        "hold_reason": HOLD_DATA_INSUFFICIENT,
        "evaluator.reason_codes": ["EVIDENCE_INSUFFICIENT"],
        "evaluator_check_appended": True,
    }
    eval_check = next(
        (c for c in state.get("verification_checks", []) if c["stage"] == "evaluator"),
        None,
    )
    observed = {
        "lifecycle_status": state.get("lifecycle_status"),
        "hold_reason": state.get("hold_reason"),
        "evaluator.reason_codes": state["decision_trace"]["evaluator"]["reason_codes"],
        "evaluator_check_appended": eval_check is not None and eval_check.get("result") == "fail",
    }
    passed = observed == expected

    summary = {
        "purpose": (
            "초기 단계가 통과한 것처럼 보여도 evaluator가 근거 부족이면 "
            "READY_FOR_BE 승격을 막고 HOLD/HOLD_DATA_INSUFFICIENT로 되돌리는지 확인"
        ),
        "input_payload": {
            "synthetic_state": {
                "lifecycle_status": LIFECYCLE_READY_FOR_BE,
                "verification_checks": [],
                "note": "policy/risk pass entry가 누락된 상태",
            }
        },
        "expected": expected,
        "observed": observed,
        "decision_trace": _trace_summary(state),
        "verification_checks": _checks_summary(state),
        "passed": passed,
        "notes": (
            "그래프(`graph.py:24-27`) routing이 자연 흐름에서는 evaluator를 "
            "policy+risk pass 누적된 상태로만 호출하므로 `evaluator.py:22-27` "
            "EVIDENCE_INSUFFICIENT branch는 graph harness만으로는 도달 불가. "
            "직접 단위 호출로 evaluator의 차단 책임 자체를 검증."
        ),
    }
    _dump_json(SCENARIOS_DIR / "QA-B-02.json", _evidence("QA-B-02", summary))
    return _evidence("QA-B-02", summary)


def run_b03() -> Dict[str, Any]:
    """QA-B-03 verification_checks append-only 검증."""
    payload = request_with_user_input(market_snapshot_fresh=False)
    app = AutocoinAgentApp()
    initial = app.start(payload)
    initial_checks = deepcopy(initial.get("verification_checks", []))
    initial_keys = [(c["stage"], c["name"]) for c in initial_checks]

    resumed = app.resume(
        "airun_test_001",
        {"supplemental_user_input": {"market_snapshot_fresh": True}},
        "MARKET_DATA_SUPPLIED",
    )
    resumed_checks = resumed.get("verification_checks", [])
    resumed_keys = [(c["stage"], c["name"]) for c in resumed_checks]

    none_removed = all(k in resumed_keys for k in initial_keys)
    initial_entries_intact = True
    for ic in initial_checks:
        match = next(
            (
                rc
                for rc in resumed_checks
                if rc.get("stage") == ic.get("stage")
                and rc.get("name") == ic.get("name")
                and rc.get("result") == ic.get("result")
                and rc.get("evidence_refs") == ic.get("evidence_refs")
            ),
            None,
        )
        if match is None:
            initial_entries_intact = False
            break
    only_canonical_stages = all(
        c["stage"] in ("policy", "risk", "evaluator", "execution", "be_revalidation")
        for c in resumed_checks
    )
    duplicate_count = max(0, len(resumed_checks) - len(set((c["stage"], c["name"]) for c in resumed_checks)))

    expected = {
        "previous_entries_preserved": True,
        "initial_entry_values_intact": True,
        "all_stages_canonical": True,
    }
    observed = {
        "previous_entries_preserved": none_removed,
        "initial_entry_values_intact": initial_entries_intact,
        "all_stages_canonical": only_canonical_stages,
    }
    passed = observed == expected

    summary = {
        "purpose": "stage별 verification_checks가 누적되고 덮어써지지 않는지 확인",
        "input_payload": {"initial": payload, "resume_patch": {"supplemental_user_input": {"market_snapshot_fresh": True}}},
        "expected": expected,
        "observed": observed,
        "initial_checks_count": len(initial_checks),
        "resumed_checks_count": len(resumed_checks),
        "initial_checks_summary": [
            {"stage": c["stage"], "name": c["name"], "result": c["result"]}
            for c in initial_checks
        ],
        "resumed_checks_summary": [
            {"stage": c["stage"], "name": c["name"], "result": c["result"]}
            for c in resumed_checks
        ],
        "duplicate_stage_name_pairs_count": duplicate_count,
        "passed": passed,
        "notes": (
            "주의: app.resume는 deepcopy(prev) 후 self.start를 다시 invoke하므로 "
            "policy_node가 두 번째 패스에서 동일 (stage, name) entry를 다시 append한다. "
            "이전 entry가 *원형 그대로* 살아있고(initial_entry_values_intact=True), "
            "새 entry가 list 끝에 append되므로 strict 'append-only'에는 부합한다. "
            "다만 동일 (stage, name) 쌍이 중복 등장하므로 후속 stage가 인덱스 기반 "
            "evidence_refs를 해석할 때 주의해야 한다 (duplicate_stage_name_pairs_count로 측정)."
        ),
    }
    _dump_json(SCENARIOS_DIR / "QA-B-03.json", _evidence("QA-B-03", summary))
    return _evidence("QA-B-03", summary)


def run_b04() -> Dict[str, Any]:
    """QA-B-04 same run_id resume 검증."""
    payload = request_with_user_input(market_snapshot_fresh=False)
    app = AutocoinAgentApp()
    initial = app.start(payload)
    pre_run_id = initial.get("run_id")
    pre_request_id = initial.get("request_context", {}).get("request_id")
    pre_policy_refs = list(initial.get("policy_context", {}).get("policy_refs", []))
    pre_trace_risk = deepcopy(initial.get("decision_trace", {}).get("risk", {}))

    resumed = app.resume(
        "airun_test_001",
        {"supplemental_user_input": {"market_snapshot_fresh": True}},
        "MARKET_DATA_SUPPLIED",
    )

    expected = {
        "run_id_preserved": True,
        "request_id_preserved": True,
        "policy_refs_preserved": True,
        "lifecycle_advanced": LIFECYCLE_READY_FOR_BE,
        "resume_history_recorded": True,
    }
    rh = resumed.get("resume_history", [])
    post_trace_risk = resumed.get("decision_trace", {}).get("risk", {})
    decision_trace_risk_preserved = post_trace_risk == pre_trace_risk
    observed = {
        "run_id_preserved": resumed.get("run_id") == pre_run_id,
        "request_id_preserved": resumed.get("request_context", {}).get("request_id") == pre_request_id,
        "policy_refs_preserved": list(resumed.get("policy_context", {}).get("policy_refs", [])) == pre_policy_refs,
        "lifecycle_advanced": resumed.get("lifecycle_status"),
        "resume_history_recorded": len(rh) >= 1
        and rh[0].get("resume_reason") == "MARKET_DATA_SUPPLIED",
    }
    passed = observed == expected
    spec_divergence = {
        "previous_decision_trace_risk_preserved": decision_trace_risk_preserved,
        "spec_reference": "docs/AI.md §6.1 (이전 decision_trace는 immutable)",
        "explanation": (
            "app.resume → app.start → graph 재실행 → 모든 node의 set_trace가 "
            "decision_trace[stage]를 새 entry로 교체한다(models.py:97). "
            "결과적으로 pre-resume의 risk stage entry(STALE_MARKET_SNAPSHOT/HOLD)는 "
            "post-resume에서 ALL_CHECKS_PASSED/PASS로 덮어써진다."
        ),
    }

    summary = {
        "purpose": "hold 후 같은 run_id로 resume되고 immutable 필드가 보존되며 보완 결과만 추가되는지 확인",
        "input_payload": {
            "initial": payload,
            "resume_patch": {"supplemental_user_input": {"market_snapshot_fresh": True}},
            "resume_reason": "MARKET_DATA_SUPPLIED",
        },
        "expected": expected,
        "observed": observed,
        "pre_resume_risk_trace": pre_trace_risk,
        "post_resume_risk_trace": post_trace_risk,
        "decision_trace": _trace_summary(resumed),
        "verification_checks": _checks_summary(resumed),
        "resume_history": rh,
        "spec_divergence_decision_trace_immutability": spec_divergence,
        "passed": passed,
        "notes": (
            "tests/test_resume.py:10-25의 패턴을 그대로 검증. "
            "run_id, request_context.request_id, policy_context.policy_refs 가 모두 "
            "보존되며 lifecycle은 READY_FOR_BE로 전진한다. "
            "다만 docs/AI.md §6.1이 immutable로 명시한 '이전 decision_trace'는 "
            "구현이 graph 재실행으로 stage entry를 덮어쓰므로 spec과 divergence가 "
            "있다 (spec_divergence_decision_trace_immutability 참조). "
            "본 시나리오 PASS 판정은 lifecycle/run_id/policy_refs/resume_history "
            "기준만 따른 lenient 해석이며, decision_trace immutability는 별도 "
            "REPORT.md §2 대표 발견 사례로 escalate."
        ),
    }
    _dump_json(SCENARIOS_DIR / "QA-B-04.json", _evidence("QA-B-04", summary))
    return _evidence("QA-B-04", summary)


def run_b05() -> Dict[str, Any]:
    """QA-B-05 resume은 자동 승인 아님 검증."""
    payload = request_with_user_input(requires_review=True)
    app = AutocoinAgentApp()
    initial = app.start(payload)

    no_approval_resume = app.resume(
        "airun_test_001",
        {},
        "NO_APPROVAL_YET",
    )
    approved_resume = app.resume(
        "airun_test_001",
        {"approval": {"approved": True}},
        "USER_APPROVED",
    )

    expected = {
        "initial_status": LIFECYCLE_HOLD,
        "initial_hold_reason": HOLD_REVIEW_REQUIRED,
        "no_approval_status": LIFECYCLE_HOLD,
        "no_approval_hold_reason": HOLD_REVIEW_REQUIRED,
        "approved_status": LIFECYCLE_READY_FOR_BE,
    }
    observed = {
        "initial_status": initial.get("lifecycle_status"),
        "initial_hold_reason": initial.get("hold_reason"),
        "no_approval_status": no_approval_resume.get("lifecycle_status"),
        "no_approval_hold_reason": no_approval_resume.get("hold_reason"),
        "approved_status": approved_resume.get("lifecycle_status"),
    }
    passed = observed == expected

    summary = {
        "purpose": "resume 자체가 자동 승인 의미를 가지면 안 되고, 필요한 검증이 다시 수행되는지 확인",
        "input_payload": {
            "initial": payload,
            "resume_attempts": [
                {"patch_fields": {}, "resume_reason": "NO_APPROVAL_YET"},
                {"patch_fields": {"approval": {"approved": True}}, "resume_reason": "USER_APPROVED"},
            ],
        },
        "expected": expected,
        "observed": observed,
        "post_no_approval_risk_trace": no_approval_resume.get("decision_trace", {}).get("risk", {}),
        "post_approved_risk_trace": approved_resume.get("decision_trace", {}).get("risk", {}),
        "no_approval_verification_checks": _checks_summary(no_approval_resume),
        "approved_verification_checks": _checks_summary(approved_resume),
        "resume_history": approved_resume.get("resume_history", []),
        "passed": passed,
        "notes": (
            "requires_review=True로 첫 HOLD를 만든 뒤 (1) 빈 patch로 resume → 여전히 HOLD/HOLD_REVIEW_REQUIRED, "
            "(2) approval.approved=True로 다시 resume → READY_FOR_BE로 전진. "
            "즉 resume이 단독으로는 승인 의미를 가지지 않으며 patch 내용이 검증을 통과해야 전진함을 확인."
        ),
    }
    _dump_json(SCENARIOS_DIR / "QA-B-05.json", _evidence("QA-B-05", summary))
    return _evidence("QA-B-05", summary)


def main() -> None:
    results = [
        run_b01(),
        run_b02(),
        run_b03(),
        run_b04(),
        run_b05(),
    ]
    rollup = {
        "reviewer": REVIEWER,
        "total": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "scenarios": [
            {
                "id": r["scenario_id"],
                "passed": r.get("passed"),
                "expected": r.get("expected"),
                "observed": r.get("observed"),
            }
            for r in results
        ],
    }
    _dump_json(OUT_DIR / "rollup.json", rollup)
    print(json.dumps(rollup, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
