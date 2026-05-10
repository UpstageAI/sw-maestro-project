"""Evaluator / reflection node — final user report + sanity checks."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, LIFECYCLE_HOLD, LIFECYCLE_READY_FOR_BE, PASS_ACTION
from autocoin_ai.llm import gemini_generate
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace
from autocoin_ai.prompts.evaluator_prompt import EVALUATOR_SCHEMA, EVALUATOR_SYSTEM_INSTRUCTION


def evaluator_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    lifecycle = next_state.get("lifecycle_status")
    if lifecycle == LIFECYCLE_FAILED:
        return next_state

    is_agentic = bool(next_state.get("trader_id"))
    proposal = next_state.get("llm_proposal", {})
    risk_assessment = next_state.get("risk_assessment", {})
    trader_principles = next_state.get("trader_principles", [])
    decision_trace = next_state.get("decision_trace", {})
    checks = next_state.get("verification_checks", [])
    risk_tool_calls = next_state.get("risk_tool_calls", [])
    intent = next_state.get("normalized_order_intent", {})

    action = str(proposal.get("action") or intent.get("side", ""))
    symbol = str(intent.get("symbol", ""))
    size_usd = str(proposal.get("size_usd", intent.get("quoteOrderQty", "0")))
    verdict = str(risk_assessment.get("verdict", ""))
    fail_reason = risk_assessment.get("fail_reason")

    # 4 sanity checks (§8.5)
    pre_warnings: list[str] = []

    # Check 1: decision_trace stages filled (except run_summary)
    required_stages = ("intake", "policy", "strategy", "risk") if is_agentic else ("policy", "risk")
    for stage in required_stages:
        if stage not in decision_trace or not decision_trace[stage]:
            pre_warnings.append("decision_trace missing stage: %s" % stage)

    # Check 2: verification_checks has required stage passes.
    if is_agentic:
        has_strategy_pass = any(
            c.get("stage") == "strategy" and c.get("result") == "pass" for c in checks
        )
        if not has_strategy_pass:
            pre_warnings.append("verification_checks missing strategy pass")
    else:
        has_policy_pass = any(c.get("stage") == "policy" and c.get("result") == "pass" for c in checks)
        if not has_policy_pass:
            pre_warnings.append("verification_checks missing policy pass")

    # Check 3: risk_tool_calls matches risk_assessment.tools_called
    tools_from_calls = [t["tool"] for t in risk_tool_calls]
    tools_from_assessment = list(risk_assessment.get("tools_called", []))
    if tools_from_calls != tools_from_assessment:
        pre_warnings.append(
            "risk_tool_calls/tools_called mismatch: %s vs %s" % (tools_from_calls, tools_from_assessment)
        )

    # Check 4: matched_principle_titles are real
    valid_titles = {p["title"] for p in trader_principles if isinstance(p, dict) and "title" in p}
    matched = proposal.get("matched_principle_titles", [])
    hallucinated = [t for t in matched if t not in valid_titles]
    if hallucinated:
        pre_warnings.append("hallucinated principle titles: %s" % hallucinated)

    prompt_proposal = dict(proposal)
    prompt_proposal.setdefault("action", action)
    prompt_proposal.setdefault("size_usd", size_usd)
    prompt = _build_prompt(lifecycle, hold_reason=next_state.get("hold_reason"), proposal=prompt_proposal,
                             risk_assessment=risk_assessment, decision_trace=decision_trace,
                             pre_warnings=pre_warnings)

    try:
        review = gemini_generate(prompt, EVALUATOR_SCHEMA, EVALUATOR_SYSTEM_INSTRUCTION)
        if pre_warnings:
            existing = list(review.get("schema_warnings", []))
            existing.extend(pre_warnings)
            review = dict(review)
            review["schema_warnings"] = existing
    except Exception:
        review = {
            "summary": "%s %s %s USDT 평가 완료. 결과: %s" % (action, symbol, size_usd, lifecycle),
            "user_message": "%s로 판단되었습니다. 사유: %s" % (verdict, fail_reason or "PASSED"),
            "reason_codes": ["EVALUATOR_LLM_FALLBACK"],
            "schema_warnings": ["LLM call failed; deterministic summary used"] + pre_warnings,
        }

    next_state["evaluator_review"] = review

    eval_result = "pass" if review.get("reason_codes") != ["EVALUATOR_LLM_FALLBACK"] else "fail"
    append_check(next_state, "evaluator_summary_complete", "evaluator", eval_result, ["evaluator_review"])
    trace_action = PASS_ACTION if lifecycle == LIFECYCLE_READY_FOR_BE else lifecycle or LIFECYCLE_HOLD
    set_trace(
        next_state,
        "evaluator",
        list(review.get("reason_codes", [])),
        ["evaluator_review"],
        trace_action,
    )
    set_trace(
        next_state,
        "run_summary",
        ["RUN_COMPLETE"],
        ["evaluator_review", "decision_trace"],
        lifecycle or LIFECYCLE_HOLD,
    )
    return next_state


def _build_prompt(lifecycle: str | None, hold_reason: str | None, proposal: dict,
                  risk_assessment: dict, decision_trace: dict, pre_warnings: list) -> str:
    return (
        "lifecycle_status: %s\n"
        "hold_reason: %s\n"
        "action: %s  conviction: %s  size_usd: %s\n"
        "risk verdict: %s  fail_reason: %s\n"
        "matched_principles: %s\n"
        "trace stages present: %s\n"
        "pre-check warnings: %s\n"
        "Generate the evaluator report."
    ) % (
        lifecycle,
        hold_reason or "None",
        proposal.get("action", ""),
        proposal.get("conviction", ""),
        proposal.get("size_usd", ""),
        risk_assessment.get("verdict", ""),
        risk_assessment.get("fail_reason", "None"),
        proposal.get("matched_principle_titles", []),
        list(decision_trace.keys()),
        pre_warnings or "none",
    )
