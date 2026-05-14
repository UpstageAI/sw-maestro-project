"""LangGraph StateGraph 골격 + 진입점. 담당: C(이유준)."""
from __future__ import annotations

import asyncio
import datetime
import os
from collections.abc import AsyncIterator
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import END, StateGraph

from memory import checkpointer
from schemas.models import AgentResponse, ChatChunk, ScheduleProposal
from agent.nodes import (
    call_tool_node,
    compose_schedule_node,
    generate_proposal_summary,
    refine_node,
    think_node,
)


class AgentState(TypedDict):
    user_input: str
    thread_id: str | None
    mode: str                     # "schedule" | "refine"
    tools_called: list[str]       # 이미 호출된 Tool 이름 목록
    next_action: str              # think_node가 결정한 다음 동작
    calendar_data: list[dict]
    health_data: list[dict]
    workouts_data: list[dict]
    proposal: dict | None


def _route_after_think(state: AgentState) -> str:
    """think 노드 이후 분기: Tool 호출 / 스케줄 도출 / 재조정."""
    action = state["next_action"]
    if action == "compose":
        return "compose_schedule"
    if action == "refine":
        return "refine"
    return "call_tool"


# --- 그래프 조립 ---
_builder = StateGraph(AgentState)
_builder.add_node("think", think_node)
_builder.add_node("call_tool", call_tool_node)
_builder.add_node("compose_schedule", compose_schedule_node)
_builder.add_node("refine", refine_node)

_builder.set_entry_point("think")
_builder.add_conditional_edges(
    "think",
    _route_after_think,
    {"call_tool": "call_tool", "compose_schedule": "compose_schedule", "refine": "refine"},
)
_builder.add_edge("call_tool", "think")  # Tool 호출 후 다시 think
_builder.add_edge("compose_schedule", END)
_builder.add_edge("refine", END)

graph = _builder.compile(checkpointer=checkpointer)


# --- 진입점 ---

def run_agent(user_input: str, session_state: dict) -> AgentResponse:
    """비스트림 진입점 — 테스트·단순 호출용.

    compose_schedule_node/refine_node가 async이므로 ainvoke를 asyncio.run으로 실행.
    """
    config = {"configurable": {"thread_id": "test-sync"}}
    initial: AgentState = {
        "user_input": user_input,
        "thread_id": None,
        "mode": "schedule",
        "tools_called": [],
        "next_action": "",
        "calendar_data": [],
        "health_data": [],
        "workouts_data": [],
        "proposal": None,
    }
    result = asyncio.run(graph.ainvoke(initial, config))
    proposal_dict = result.get("proposal")
    proposal = ScheduleProposal.model_validate(proposal_dict) if proposal_dict else None
    return AgentResponse(
        message="스케줄 도출 완료",
        proposal=proposal,
        needs_approval=True,
    )


def _get_prior_proposal(config: dict) -> dict | None:
    """체크포인터에서 해당 thread의 이전 proposal을 가져온다. 없으면 None."""
    prev = checkpointer.get_tuple(config)
    if not prev:
        return None
    return prev.checkpoint.get("channel_values", {}).get("proposal") or None


async def run_agent_stream(
    user_input: str,
    thread_id: str | None = None,
) -> AsyncIterator[ChatChunk]:
    """SSE 스트림 진입점 — backend/api/chat.py가 호출.

    같은 thread_id로 이전 proposal이 있으면 refine 모드로 동작.
    ChatChunk(type ∈ text/tool_call/proposal/done/error)를 순차 yield.
    chunk별 payload 스키마는 schemas/CLAUDE.md 참고.
    """
    tid = thread_id or "default-thread"
    config = {"configurable": {"thread_id": tid}}

    prior_proposal = _get_prior_proposal(config)
    is_refine = prior_proposal is not None

    if is_refine:
        # 재조정: user_input·mode만 업데이트, 나머지(calendar/health/workouts/proposal)는 체크포인터에서 복원
        initial: dict = {
            "user_input": user_input,
            "mode": "refine",
            "tools_called": [],
            "next_action": "",
        }
    else:
        initial = {
            "user_input": user_input,
            "thread_id": tid,
            "mode": "schedule",
            "tools_called": [],
            "next_action": "",
            "calendar_data": [],
            "health_data": [],
            "workouts_data": [],
            "proposal": None,
        }

    final_proposal: dict | None = None

    try:
        async for update in graph.astream(initial, config, stream_mode="updates"):
            for node_name, node_update in update.items():
                if node_name == "think":
                    action = node_update.get("next_action", "")
                    if action and action not in ("compose", "refine"):
                        _today = datetime.date.today()
                        _week_start = _today - datetime.timedelta(days=_today.weekday())
                        _tool_args = {
                            "start": _week_start.isoformat(),
                            "end": (_week_start + datetime.timedelta(days=6)).isoformat(),
                        }
                        yield ChatChunk(
                            type="tool_call",
                            payload={"name": action, "args": _tool_args},
                        )
                elif node_name in ("compose_schedule", "refine"):
                    if proposal := node_update.get("proposal"):
                        final_proposal = proposal
    except Exception as exc:
        yield ChatChunk(type="error", payload={"message": str(exc)})
        return

    # 그래프 완료 후: LLM 텍스트 요약(토큰 단위) → proposal → done
    if final_proposal:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # agent/CLAUDE.md: "없으면 명확히 에러 — silent fallback 금지"
            yield ChatChunk(type="error", payload={"message": "OPENAI_API_KEY가 설정되지 않아 텍스트 요약을 생략합니다."})
        else:
            try:
                async for token in generate_proposal_summary(
                    final_proposal, user_input, api_key,
                    is_refine=is_refine,
                    prior_proposal=prior_proposal,
                ):
                    if token:
                        yield ChatChunk(type="text", payload={"delta": token})
            except Exception as exc:
                yield ChatChunk(type="error", payload={"message": str(exc)})
        yield ChatChunk(type="proposal", payload=final_proposal)

    yield ChatChunk(type="done", payload={"thread_id": tid})
