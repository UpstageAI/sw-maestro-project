"""LangGraph orchestration for the two text-LLM flows:

- ``generate_missions``    — 5 missions from a curated candidate pool
- ``regenerate_mission_for_place`` — 1 fresh mission for an existing place

Each flow is a small StateGraph: prepare → call_llm → validate → (retry | finalize).
The verify_photo (vision) call stays in agent.py because wrapping a single
call in a graph adds no value.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from prompts import AGENT_SYSTEM_EN, AGENT_SYSTEM_KO, SYSTEM_EN, SYSTEM_KO
from schemas import (
    AgentMessageRequest,
    AgentMessageResponse,
    Context,
    Mission,
    MissionBundle,
)


logger = logging.getLogger("duribeon")

#: Max number of *additional* LLM calls after the first attempt.
MAX_RETRIES = 2


# ──────────────────────────────────────────────────────────────────
#  Shared LLM client (Upstage Solar via OpenAI-compatible endpoint)
# ──────────────────────────────────────────────────────────────────


def _chat_model(temperature: float = 0.8) -> ChatOpenAI:
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "UPSTAGE_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    base_url = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
    model = os.getenv("UPSTAGE_TEXT_MODEL", "solar-pro2")
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _resp_text(resp) -> str:
    content = getattr(resp, "content", "")
    if isinstance(content, str):
        return content or "{}"
    # langchain occasionally returns a list of content blocks; flatten.
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and "text" in c:
                parts.append(c["text"])
            elif isinstance(c, str):
                parts.append(c)
        return "".join(parts) or "{}"
    return "{}"


def _log_usage(resp) -> None:
    usage = getattr(resp, "usage_metadata", None)
    if usage:
        logger.info(
            "  usage: input=%s output=%s total=%s",
            usage.get("input_tokens", "?"),
            usage.get("output_tokens", "?"),
            usage.get("total_tokens", "?"),
        )


# ══════════════════════════════════════════════════════════════════
#  GENERATE MISSIONS graph (5 missions from candidate pool)
# ══════════════════════════════════════════════════════════════════


class GenerateState(TypedDict, total=False):
    ctx: Context
    candidates: list[dict]
    rejected_place_ids: list[str]
    attempt: int  # number of LLM calls completed so far
    raw: str
    cleaned: list[Mission]
    validation_error: str
    result: list[Mission]


def _g_prepare(state: GenerateState) -> dict:
    # Lazy import to avoid a circular load with agent.py.
    from agent import query_curation_db
    from seed import load_places

    ctx: Context = state["ctx"]
    rejected = state.get("rejected_place_ids") or []

    candidates = query_curation_db(ctx.area, ctx.avoid)
    candidates = [p for p in candidates if p["id"] not in rejected]

    # Fallback 1: full-area pool (still respecting rejected_place_ids).
    if len(candidates) < 5:
        backup = [
            p for p in load_places()
            if p["area"] == ctx.area and p["id"] not in rejected
        ]
        for p in backup:
            if p not in candidates:
                candidates.append(p)
            if len(candidates) >= 8:
                break

    # Fallback 2: recycle rejected places when the seed is exhausted.
    if len(candidates) < 5:
        full_area = [p for p in load_places() if p["area"] == ctx.area]
        for p in full_area:
            if p not in candidates:
                candidates.append(p)
            if len(candidates) >= 5:
                break

    logger.info("=" * 70)
    logger.info("→ LangGraph generate_missions (Upstage)")
    logger.info(
        "  prepare: area=%s group=%s time=%s mood=%s avoid=%s lang=%s",
        ctx.area, ctx.group, ctx.time_budget, ctx.mood, ctx.avoid, ctx.language,
    )
    logger.info(
        "  rejected=%d candidates=%d (%s)",
        len(rejected),
        len(candidates),
        ", ".join(c["id"] for c in candidates),
    )
    return {"candidates": candidates, "attempt": 0}


def _g_build_payload(ctx: Context, candidates: list[dict], rejected: list[str]) -> tuple[str, str]:
    is_ko = ctx.language == "ko"
    name_key = "name_ko" if is_ko else "name_en"
    desc_key = "desc_ko" if is_ko else "desc_en"
    candidate_lines = [
        {
            "place_id": p["id"],
            "name": p[name_key],
            "category": p["category"],
            "tags": p["tags"],
            "desc": p[desc_key],
        }
        for p in candidates
    ]
    user_payload = {
        "context": {
            "area": ctx.area,
            "group": ctx.group,
            "time_budget": ctx.time_budget,
            "mood": ctx.mood,
            "avoid": ctx.avoid,
        },
        "rejected_place_ids": rejected,
        "candidates": candidate_lines,
        "instruction": (
            "위 CANDIDATES의 place_id 중에서만 골라 정확히 5개의 미션을 JSON으로 출력하라. "
            "사용자의 time_budget(시간 여유)에 맞춰 각 미션의 estimated_minutes를 합리적으로 잡아라. "
            "(예: '30분 정도'면 모두 ≤30분, '반나절'이면 60~120분 OK, '하루 종일'이면 자유롭게)"
            if is_ko
            else "Pick from CANDIDATES place_ids only and output exactly 5 missions as JSON. "
                 "Respect the user's time_budget when sizing each mission's estimated_minutes "
                 "(e.g., '~30 min' → all ≤30, 'half day' → 60-120 OK, 'all day' → free)."
        ),
    }
    system = SYSTEM_KO if is_ko else SYSTEM_EN
    return system, json.dumps(user_payload, ensure_ascii=False)


def _g_call_llm(state: GenerateState) -> dict:
    ctx: Context = state["ctx"]
    candidates = state["candidates"]
    rejected = state.get("rejected_place_ids") or []
    attempt = state.get("attempt", 0) + 1
    is_ko = ctx.language == "ko"

    system, user_text = _g_build_payload(ctx, candidates, rejected)

    if attempt > 1:
        prev_err = state.get("validation_error", "")
        if is_ko:
            system += (
                f"\n\n[재시도 #{attempt - 1}] 이전 시도 실패 사유: {prev_err}\n"
                "규칙을 더 엄격히 지켜라:\n"
                "- 정확히 5개 미션\n"
                "- place_id는 CANDIDATES 목록에서만, 5개 모두 unique\n"
                "- 같은 place_id 두 번 사용 금지"
            )
        else:
            system += (
                f"\n\n[Retry #{attempt - 1}] Previous attempt failed: {prev_err}\n"
                "Follow rules more strictly:\n"
                "- Exactly 5 missions\n"
                "- place_id MUST come from CANDIDATES, all 5 unique\n"
                "- No duplicate place_id"
            )

    model_name = os.getenv("UPSTAGE_TEXT_MODEL", "solar-pro2")
    logger.info(
        "  call_llm: model=%s attempt=%d/%d payload=%d chars",
        model_name, attempt, MAX_RETRIES + 1, len(user_text),
    )
    if attempt == 1:
        for line in json.dumps(json.loads(user_text), ensure_ascii=False, indent=2).splitlines():
            logger.info("    %s", line)

    chat = _chat_model(temperature=0.8 if attempt == 1 else 0.95)
    t0 = time.perf_counter()
    resp = chat.invoke([SystemMessage(content=system), HumanMessage(content=user_text)])
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = _resp_text(resp)

    logger.info("  ← raw response (%d chars, %d ms)", len(raw), elapsed_ms)
    for line in raw.splitlines():
        logger.info("    %s", line)
    _log_usage(resp)

    return {"raw": raw, "attempt": attempt}


def _g_validate(state: GenerateState) -> dict:
    candidates = state["candidates"]
    raw = state.get("raw", "{}")
    cleaned: list[Mission] = []
    err = ""

    try:
        data = json.loads(raw)
        bundle = MissionBundle.model_validate(data)
        valid_ids = {p["id"] for p in candidates}
        seen: set[str] = set()
        for m in bundle.missions:
            if m.place_id not in valid_ids:
                continue
            if m.place_id in seen:
                continue
            seen.add(m.place_id)
            cleaned.append(m)
        if len(cleaned) < 5:
            err = f"only {len(cleaned)} unique valid missions (need 5)"
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"

    logger.info(
        "  validate: cleaned=%d/5 error=%s",
        len(cleaned),
        repr(err) if err else "none",
    )
    return {"cleaned": cleaned, "validation_error": err}


def _g_finalize(state: GenerateState) -> dict:
    from agent import _fallback_mission

    ctx: Context = state["ctx"]
    candidates = state["candidates"]
    cleaned = list(state.get("cleaned") or [])
    llm_count = len(cleaned)

    fallback_filled = 0
    if len(cleaned) < 5:
        used = {m.place_id for m in cleaned}
        idx = 0
        for cand in candidates:
            if cand["id"] in used:
                continue
            cleaned.append(_fallback_mission(cand, ctx, idx))
            used.add(cand["id"])
            idx += 1
            fallback_filled += 1
            if len(cleaned) >= 5:
                break

    logger.info(
        "  finalize: result=%d (LLM=%d, fallback=%d)",
        len(cleaned), llm_count, fallback_filled,
    )
    for i, m in enumerate(cleaned[:5], 1):
        logger.info("    [%d] %s — %s (%s)", i, m.place_id, m.title, m.category)

    if len(cleaned) < 5:
        raise RuntimeError(
            f"only {len(cleaned)} missions producible; check curation seed for area '{ctx.area}'"
        )
    return {"result": cleaned[:5]}


def _g_route_after_validate(state: GenerateState) -> str:
    if len(state.get("cleaned") or []) >= 5:
        return "finalize"
    if state.get("attempt", 0) < MAX_RETRIES + 1:
        logger.info("  retry → call_llm")
        return "call_llm"
    return "finalize"


def _build_generate_graph():
    g = StateGraph(GenerateState)
    g.add_node("prepare", _g_prepare)
    g.add_node("call_llm", _g_call_llm)
    g.add_node("validate", _g_validate)
    g.add_node("finalize", _g_finalize)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "call_llm")
    g.add_edge("call_llm", "validate")
    g.add_conditional_edges(
        "validate",
        _g_route_after_validate,
        {"call_llm": "call_llm", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)
    return g.compile()


GENERATE_GRAPH = _build_generate_graph()


def generate_missions(
    ctx: Context,
    rejected_place_ids: list[str] | None = None,
) -> tuple[list[Mission], list[dict]]:
    final = GENERATE_GRAPH.invoke({
        "ctx": ctx,
        "rejected_place_ids": rejected_place_ids or [],
        "attempt": 0,
    })
    return final["result"], final["candidates"]


# ══════════════════════════════════════════════════════════════════
#  REGENERATE graph (1 mission for an existing place)
# ══════════════════════════════════════════════════════════════════


class RegenerateState(TypedDict, total=False):
    ctx: Context
    place_id: str
    place: dict
    previous_title: str | None
    attempt: int
    raw: str
    parsed: Mission | None
    validation_error: str
    result: Mission


def _r_prepare(state: RegenerateState) -> dict:
    from seed import load_places

    ctx: Context = state["ctx"]
    place_id = state["place_id"]
    places = load_places()
    place = next((p for p in places if p["id"] == place_id), None)
    if place is None:
        raise RuntimeError(f"unknown place_id: {place_id!r}")

    logger.info("=" * 70)
    logger.info("→ LangGraph regenerate_mission_for_place (Upstage)")
    logger.info(
        "  prepare: place_id=%s lang=%s prev_title=%s",
        place_id, ctx.language, state.get("previous_title") or "-",
    )
    return {"place": place, "attempt": 0}


def _r_build_payload(ctx: Context, place: dict, previous_title: str | None) -> tuple[str, str]:
    is_ko = ctx.language == "ko"
    name = place["name_ko" if is_ko else "name_en"]
    desc = place["desc_ko" if is_ko else "desc_en"]

    instruction_ko = (
        "위 PLACE에 대해 새로운 미션 1개를 JSON으로 출력하라. 같은 장소지만 "
        "이전 미션과 다른 각도(다른 감각·다른 액션·다른 시간대·다른 사회적 상호작용)로 접근하라. "
        "사용자의 time_budget에 맞춰 estimated_minutes를 잡아라. "
        "출력 형식: {\"mission\": {Mission 스키마 모든 필드}}"
    )
    instruction_en = (
        "Generate ONE new mission for the PLACE above. Same place but a different "
        "angle from the previous one (different sense / action / time-of-day / social "
        "interaction). Size estimated_minutes to fit the user's time_budget. "
        "Output format: {\"mission\": {all Mission schema fields}}"
    )

    user_payload: dict = {
        "context": {
            "area": ctx.area,
            "group": ctx.group,
            "time_budget": ctx.time_budget,
            "mood": ctx.mood,
            "avoid": ctx.avoid,
        },
        "place": {
            "place_id": place["id"],
            "name": name,
            "category": place["category"],
            "tags": place["tags"],
            "desc": desc,
        },
        "instruction": instruction_ko if is_ko else instruction_en,
    }
    if previous_title:
        user_payload["previous_title"] = previous_title

    system = SYSTEM_KO if is_ko else SYSTEM_EN
    return system, json.dumps(user_payload, ensure_ascii=False)


def _r_call_llm(state: RegenerateState) -> dict:
    ctx: Context = state["ctx"]
    place = state["place"]
    previous_title = state.get("previous_title")
    attempt = state.get("attempt", 0) + 1
    is_ko = ctx.language == "ko"

    system, user_text = _r_build_payload(ctx, place, previous_title)

    if attempt > 1:
        prev_err = state.get("validation_error", "")
        if is_ko:
            system += (
                f"\n\n[재시도 #{attempt - 1}] 이전 시도 실패 사유: {prev_err}\n"
                f"PLACE의 place_id ({place['id']})를 그대로 사용하고, "
                "이전 제목과 충분히 다른 미션을 만들어라."
            )
        else:
            system += (
                f"\n\n[Retry #{attempt - 1}] Previous attempt failed: {prev_err}\n"
                f"Use the exact place_id ({place['id']}) and produce a clearly different mission."
            )

    model_name = os.getenv("UPSTAGE_TEXT_MODEL", "solar-pro2")
    logger.info(
        "  call_llm: model=%s attempt=%d/%d payload=%d chars",
        model_name, attempt, MAX_RETRIES + 1, len(user_text),
    )
    if attempt == 1:
        for line in json.dumps(json.loads(user_text), ensure_ascii=False, indent=2).splitlines():
            logger.info("    %s", line)

    chat = _chat_model(temperature=0.95 if attempt == 1 else 1.0)
    t0 = time.perf_counter()
    resp = chat.invoke([SystemMessage(content=system), HumanMessage(content=user_text)])
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = _resp_text(resp)

    logger.info("  ← raw response (%d chars, %d ms)", len(raw), elapsed_ms)
    for line in raw.splitlines():
        logger.info("    %s", line)
    _log_usage(resp)

    return {"raw": raw, "attempt": attempt}


def _r_validate(state: RegenerateState) -> dict:
    raw = state.get("raw", "{}")
    place = state["place"]
    parsed: Mission | None = None
    err = ""

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("response is not a JSON object")
        if "mission" in data and isinstance(data["mission"], dict):
            m_data = data["mission"]
        elif "missions" in data and isinstance(data["missions"], list) and data["missions"]:
            m_data = data["missions"][0]
        else:
            m_data = data
        parsed = Mission.model_validate(m_data)
        if parsed.place_id != place["id"]:
            err = f"place_id mismatch: got {parsed.place_id!r}, want {place['id']!r}"
            parsed = None
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
        parsed = None

    logger.info(
        "  validate: parsed=%s error=%s",
        "ok" if parsed else "no",
        repr(err) if err else "none",
    )
    return {"parsed": parsed, "validation_error": err}


def _r_finalize(state: RegenerateState) -> dict:
    from agent import _fallback_mission

    ctx: Context = state["ctx"]
    place = state["place"]
    parsed = state.get("parsed")

    if parsed is None:
        logger.info("  finalize: deterministic fallback")
        mission = _fallback_mission(place, ctx, int(time.time()) % 1000)
    else:
        is_ko = ctx.language == "ko"
        name = place["name_ko" if is_ko else "name_en"]
        if parsed.place_name != name:
            mission = Mission(**{**parsed.model_dump(), "place_name": name})
        else:
            mission = parsed

    logger.info("  finalize: result=%s — %s (%s)", mission.place_id, mission.title, mission.category)
    return {"result": mission}


def _r_route_after_validate(state: RegenerateState) -> str:
    if state.get("parsed") is not None:
        return "finalize"
    if state.get("attempt", 0) < MAX_RETRIES + 1:
        logger.info("  retry → call_llm")
        return "call_llm"
    return "finalize"


def _build_regenerate_graph():
    g = StateGraph(RegenerateState)
    g.add_node("prepare", _r_prepare)
    g.add_node("call_llm", _r_call_llm)
    g.add_node("validate", _r_validate)
    g.add_node("finalize", _r_finalize)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "call_llm")
    g.add_edge("call_llm", "validate")
    g.add_conditional_edges(
        "validate",
        _r_route_after_validate,
        {"call_llm": "call_llm", "finalize": "finalize"},
    )
    g.add_edge("finalize", END)
    return g.compile()


REGENERATE_GRAPH = _build_regenerate_graph()


def regenerate_mission_for_place(
    ctx: Context,
    place_id: str,
    previous_title: str | None = None,
) -> Mission:
    final = REGENERATE_GRAPH.invoke({
        "ctx": ctx,
        "place_id": place_id,
        "previous_title": previous_title,
        "attempt": 0,
    })
    return final["result"]


# ══════════════════════════════════════════════════════════════════
#  AGENT graph — classify free-text intent into action list
# ══════════════════════════════════════════════════════════════════


_ALLOWED_ACTION_TYPES = {
    "set_context_area",
    "set_context_group",
    "set_context_time_budget",
    "set_context_mood",
    "set_context_avoid",
    "proceed_to_generate",
    "regenerate_mission",
    "reject_mission",
    "pick_mission",
    "reroll_all",
    "generate_more",
    "reset_chat",
}


class AgentState(TypedDict, total=False):
    req: AgentMessageRequest
    raw: str
    bot_response: str
    actions: list[dict]
    result: AgentMessageResponse


def _agent_build_user_payload(req: AgentMessageRequest) -> str:
    # Lazy import to keep module load light.
    from seed import load_areas

    areas = load_areas()
    return json.dumps(
        {
            "step": req.step,
            "language": req.language,
            "context": req.context,
            "available_areas": [
                {
                    "id": a["id"],
                    "name_ko": a["name_ko"],
                    "name_en": a["name_en"],
                    "match_ko": a.get("match_ko", []),
                    "match_en": a.get("match_en", []),
                }
                for a in areas
            ],
            "panel_pool": [
                {"index": i + 1, "id": p.id, "place_id": p.place_id, "title": p.title, "category": p.category}
                for i, p in enumerate([pm for pm in req.panel if pm.state == "pool"])
            ],
            "panel_active": [
                {"id": p.id, "place_id": p.place_id, "title": p.title}
                for p in req.panel if p.state == "active"
            ],
            "panel_history": [
                {"id": p.id, "place_id": p.place_id, "title": p.title, "state": p.state}
                for p in req.panel if p.state in ("passed", "failed", "rejected")
            ],
            "active_mission_id": req.active_mission_id,
            "chat_history": [
                {"role": t.role, "text": t.text} for t in req.chat_history[-20:]
            ],
            "user_text": req.text,
        },
        ensure_ascii=False,
    )


def _agent_call_llm(state: AgentState) -> dict:
    req: AgentMessageRequest = state["req"]
    is_ko = req.language == "ko"
    system = AGENT_SYSTEM_KO if is_ko else AGENT_SYSTEM_EN
    user_text = _agent_build_user_payload(req)

    logger.info("=" * 70)
    logger.info("→ LangGraph agent (Upstage)")
    logger.info(
        "  step=%s lang=%s pool=%d active=%s user=%r",
        req.step, req.language,
        sum(1 for p in req.panel if p.state == "pool"),
        req.active_mission_id or "-",
        req.text[:80],
    )
    logger.info("  user payload (%d chars)", len(user_text))

    chat = _chat_model(temperature=0.3)
    t0 = time.perf_counter()
    resp = chat.invoke([SystemMessage(content=system), HumanMessage(content=user_text)])
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = _resp_text(resp)

    logger.info("  ← raw (%d chars, %d ms)", len(raw), elapsed_ms)
    for line in raw.splitlines():
        logger.info("    %s", line)
    _log_usage(resp)

    return {"raw": raw}


def _agent_validate(state: AgentState) -> dict:
    raw = state.get("raw", "{}")
    bot_response = ""
    actions: list[dict] = []

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            bot_response = str(data.get("bot_response") or "").strip()
            raw_actions = data.get("actions")
            if isinstance(raw_actions, list):
                for a in raw_actions:
                    if not isinstance(a, dict):
                        continue
                    a_type = a.get("type")
                    if a_type not in _ALLOWED_ACTION_TYPES:
                        logger.info("  drop unknown action type: %r", a_type)
                        continue
                    payload = a.get("payload") or {}
                    if not isinstance(payload, dict):
                        payload = {}
                    actions.append({"type": a_type, "payload": payload})
    except Exception as e:  # noqa: BLE001
        logger.info("  agent JSON parse failed: %s", e)

    if not bot_response:
        bot_response = (
            "음... 무슨 말인지 잘 모르겠어. 다시 말해줘."
            if state["req"].language == "ko"
            else "Hmm, didn't quite catch that. Could you say it again?"
        )

    logger.info("  validate: actions=%d (%s) reply=%r",
                len(actions), ",".join(a["type"] for a in actions), bot_response[:80])

    result = AgentMessageResponse(
        bot_response=bot_response,
        actions=[{"type": a["type"], "payload": a["payload"]} for a in actions],  # type: ignore[arg-type]
    )
    return {"bot_response": bot_response, "actions": actions, "result": result}


def _build_agent_graph():
    g = StateGraph(AgentState)
    g.add_node("call_llm", _agent_call_llm)
    g.add_node("validate", _agent_validate)
    g.add_edge(START, "call_llm")
    g.add_edge("call_llm", "validate")
    g.add_edge("validate", END)
    return g.compile()


AGENT_GRAPH = _build_agent_graph()


def run_agent(req: AgentMessageRequest) -> AgentMessageResponse:
    final = AGENT_GRAPH.invoke({"req": req})
    return final["result"]
