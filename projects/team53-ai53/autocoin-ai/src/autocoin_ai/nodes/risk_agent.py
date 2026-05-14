"""Risk agent node — ReAct tool-calling loop (Phase 3c)."""

from __future__ import annotations

from autocoin_ai.constants import LIFECYCLE_FAILED, MAX_TOOL_CALLS
from autocoin_ai.llm import StepResult, gemini_step_with_tools
from autocoin_ai.models import AgentState, ensure_state_shape
from autocoin_ai.prompts.risk_agent_prompt import RISK_AGENT_SYSTEM_INSTRUCTION
from autocoin_ai.tools.registry import REGISTRY, dispatch


def risk_agent_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    if next_state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return next_state

    proposal = next_state.get("llm_proposal", {})
    intent = next_state.get("normalized_order_intent", {})
    bounds = next_state.get("policy_context", {}).get("persona_bounds", {})
    persona = next_state.get("inferred_persona", "MODERATE")
    existing_calls: list = list(next_state.get("risk_tool_calls", []))

    prompt = _build_prompt(intent, proposal, persona, bounds)
    tools = _build_gemini_tools()
    contents: list = [prompt]
    tool_calls: list = []
    total_calls = 0

    while total_calls < MAX_TOOL_CALLS:
        try:
            step: StepResult = gemini_step_with_tools(contents, tools, RISK_AGENT_SYSTEM_INSTRUCTION)
        except Exception:
            break

        if step.is_final or not step.function_calls:
            break

        func_responses: list = []
        for fc in step.function_calls:
            if total_calls >= MAX_TOOL_CALLS:
                break
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            try:
                result = dispatch(name, args)
            except KeyError:
                result = {"error": "unknown tool: %s" % name}

            tool_calls.append({
                "step": len(existing_calls) + total_calls + 1,
                "thought": step.text or "",
                "tool": name,
                "args": args,
                "result": result,
            })
            func_responses.append((name, result))
            total_calls += 1

        if not func_responses:
            break

        if step.candidate_content is not None:
            contents.append(step.candidate_content)
        _append_func_responses(contents, func_responses)

    next_state["risk_tool_calls"] = existing_calls + tool_calls
    return next_state


def _build_prompt(intent: dict, proposal: dict, persona: str, bounds: dict) -> str:
    return (
        "Assess risk for this trade:\n"
        "Symbol: %s  Side: %s  Size: %s USDT\n"
        "Proposed action: %s  Conviction: %s\n"
        "Persona: %s  max_order_usd: %s  min_conviction: %s\n"
        "Use tools to check balance and volatility, then stop."
    ) % (
        intent.get("symbol", ""),
        intent.get("side", ""),
        proposal.get("size_usd", intent.get("quoteOrderQty", "0")),
        proposal.get("action", ""),
        proposal.get("conviction", ""),
        persona,
        bounds.get("max_order_usd", 2000),
        bounds.get("min_conviction", 0.65),
    )


def _build_gemini_tools() -> list:
    from google.genai import types
    declarations = [
        types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.schema)
        for t in REGISTRY.values()
    ]
    return [types.Tool(function_declarations=declarations)]


def _append_func_responses(contents: list, responses: list) -> None:
    from google.genai import types
    parts = [
        types.Part(function_response=types.FunctionResponse(name=name, response=result))
        for name, result in responses
    ]
    contents.append(types.Content(role="user", parts=parts))
