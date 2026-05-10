from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.db.repository import ReviewAgentRepository
from src.llm.provider import LLMProvider
from src.nodes.checklist import run_checklist_agent_node
from src.nodes.classifier import run_classifier_agent_node
from src.nodes.context_loader import run_context_loader_node
from src.nodes.input_parser import run_input_parser_node
from src.nodes.pattern import run_pattern_agent_node
from src.nodes.persistence import run_persistence_tool_node
from src.nodes.reply_drafter import run_reply_drafter_agent_node
from src.state import ReviewAgentState

try:
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except ModuleNotFoundError:  # pragma: no cover
    END = "__end__"
    START = "__start__"
    HAS_LANGGRAPH = False


def build_review_agent_graph(
    *,
    repo: ReviewAgentRepository,
    provider: LLMProvider,
):
    if not HAS_LANGGRAPH:
        return _FallbackCompiledGraph(repo=repo, provider=provider)

    graph = StateGraph(ReviewAgentState)

    graph.add_node("input_parser", lambda state: run_input_parser_node(_coerce_state(state)))
    graph.add_node("context_loader", lambda state: run_context_loader_node(_coerce_state(state), repo))
    graph.add_node("classifier", lambda state: run_classifier_agent_node(_coerce_state(state), provider))
    graph.add_node("reply_drafter", lambda state: run_reply_drafter_agent_node(_coerce_state(state), provider))
    graph.add_node("persistence", lambda state: run_persistence_tool_node(_coerce_state(state), repo))
    graph.add_node("pattern", lambda state: run_pattern_agent_node(_coerce_state(state), repo))
    graph.add_node("checklist", lambda state: run_checklist_agent_node(_coerce_state(state)))

    graph.add_edge(START, "input_parser")
    graph.add_conditional_edges(
        "input_parser",
        _route_after_input_parser,
        {
            "context_loader": "context_loader",
            "end": END,
        },
    )
    graph.add_edge("context_loader", "classifier")
    graph.add_edge("classifier", "reply_drafter")
    graph.add_edge("reply_drafter", "persistence")
    graph.add_edge("persistence", "pattern")
    graph.add_edge("pattern", "checklist")
    graph.add_edge("checklist", END)

    return graph.compile()


def run_review_agent(
    *,
    repo: ReviewAgentRepository,
    provider: LLMProvider,
    state: ReviewAgentState,
) -> ReviewAgentState:
    compiled = build_review_agent_graph(repo=repo, provider=provider)
    result = compiled.invoke(state)
    return _coerce_state(result)


def _route_after_input_parser(state: ReviewAgentState | dict[str, Any]) -> str:
    normalized = _coerce_state(state)
    return "context_loader" if normalized.parsed_reviews else "end"


def _coerce_state(state: ReviewAgentState | dict[str, Any]) -> ReviewAgentState:
    if isinstance(state, ReviewAgentState):
        return state
    return ReviewAgentState.from_dict(state)


class _FallbackCompiledGraph:
    def __init__(self, *, repo: ReviewAgentRepository, provider: LLMProvider) -> None:
        self.repo = repo
        self.provider = provider

    def invoke(self, state: ReviewAgentState | dict[str, Any]) -> dict[str, Any]:
        current = _coerce_state(state)
        current = run_input_parser_node(current)
        if not current.parsed_reviews:
            current.execution_log.append("FallbackGraph: finished early because no parsed reviews")
            return asdict(current)
        current = run_context_loader_node(current, self.repo)
        current = run_classifier_agent_node(current, self.provider)
        current = run_reply_drafter_agent_node(current, self.provider)
        current = run_persistence_tool_node(current, self.repo)
        current = run_pattern_agent_node(current, self.repo)
        current = run_checklist_agent_node(current)
        current.execution_log.append("FallbackGraph: executed sequentially without langgraph package")
        return asdict(current)
