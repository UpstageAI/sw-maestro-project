"""High-level pipeline runners shared by the JSON and SSE handlers.

``run_pipeline_buffered`` collects events into a list and returns
``(result, events)`` for the JSON endpoint.

``stream_pipeline_events`` is an async generator that yields events one by
one — suitable for SSE.

Both runners apply the same input validation step before invoking the graph,
emitting ``agent_start`` / ``agent_done`` / ``error`` events for the
``input-validation`` agent to match the original TS contract.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from _lib.agents.input_validation import validate_input
from _lib.graph import get_compiled_graph
from _lib.state import AgentState, make_event


def _make_validation_failure_events(errors: List[str]) -> List[Dict[str, Any]]:
    return [
        make_event("agent_start", agent="input-validation", index=0, total=6),
        make_event(
            "error",
            agent="input-validation",
            message=" / ".join(errors),
        ),
    ]


def _initial_state(api_key: str, user_input: Dict[str, Any], model: Optional[str]) -> AgentState:
    state: AgentState = {
        "apiKey": api_key,
        "userInput": user_input,  # type: ignore[typeddict-item]
        "model": model,
    }
    return state


async def stream_pipeline_events(
    api_key: Any,
    raw_input: Any,
    model: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Yield ``AgentEvent`` dicts one by one as the pipeline executes."""
    # 1) Input validation runs synchronously, before the graph.
    yield make_event("agent_start", agent="input-validation", index=0, total=6)
    validation = validate_input(api_key, raw_input)
    if not validation.ok or validation.normalized is None:
        yield make_event(
            "error",
            agent="input-validation",
            message=" / ".join(validation.errors),
        )
        return
    yield make_event(
        "agent_done", agent="input-validation", index=0, total=6,
        payload={"ok": True},
    )

    # 2-6) Run the LangGraph; nodes emit their own events via stream writer.
    graph = get_compiled_graph()
    state = _initial_state(api_key, dict(validation.normalized), model)
    try:
        async for chunk in graph.astream(state, stream_mode="custom"):
            # Each chunk is a dict written by a node via get_stream_writer().
            yield chunk
    except Exception as err:  # noqa: BLE001 — surface the error to the client
        yield make_event("error", message=str(err) or "알 수 없는 오류가 발생했어요.")


async def run_pipeline_buffered(
    api_key: Any,
    raw_input: Any,
    model: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run the pipeline and collect all events; return ``(result, events)``."""
    events: List[Dict[str, Any]] = []
    result: Optional[Dict[str, Any]] = None
    async for event in stream_pipeline_events(api_key, raw_input, model):
        events.append(event)
        if event.get("type") == "pipeline_done" and isinstance(event.get("payload"), dict):
            result = event["payload"]
    return result, events
