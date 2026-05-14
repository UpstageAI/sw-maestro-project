"""LangGraph workflow assembly.

Phase 2 graph (RAG + HITL integrated):

  START
    │
    ├──▶ analyzer ────────┐
    └──▶ term_extractor ──┤  (parallel fan-out)
                          ▼
                knowledge_retriever   [RAG join point]
                          │
                          ▼
                question_generator
                          │
                          ▼
                      evaluator
                          │
                ◆ _route_after_eval
                ├──"regenerate"──▶ question_generator
                └──"done"────────▶ human_review  [interrupt_before]
                                        │
                                ◆ _route_after_feedback
                                ├──"regenerate"────▶ question_generator
                                ├──"refine_easier"─▶ question_generator
                                ├──"refine_harder"─▶ question_generator
                                └──"accept"────────▶ END

Parallel fan-out of analyzer + term_extractor cuts wall-clock latency by ~40%
since the two nodes are independent. LangGraph merges their partial-state dicts
before knowledge_retriever runs (join point).

HITL notes:
- MemorySaver is used for dev/MVP (single-process, in-memory). v1.1: SqliteSaver.
- BE calls graph.ainvoke(initial, config={"configurable": {"thread_id": <uuid>}})
  → graph pauses before human_review → BE returns partial state with
  status="awaiting_feedback".
- BE receives feedback → graph.aupdate_state(config, {"feedback": UserFeedback(...)})
  → graph.ainvoke(None, config) resumes from human_review.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analyzer_node,
    evaluator_node,
    human_review_node,
    knowledge_retriever_node,
    question_generator_node,
    term_extractor_node,
)
from app.graph.schema import GraphState

_MAX_RETRIES = 3
_MAX_FEEDBACK = 4  # user feedback action limit (accept excluded); matches FE MAX_FEEDBACK_COUNT

# Single MemorySaver instance shared across all invocations.
# v1.1: replace with AsyncSqliteSaver + aiosqlite for persistence across restarts.
_checkpointer = MemorySaver()


def _route_after_eval(state: GraphState) -> str:
    """Conditional edge after evaluator: regenerate or move to human_review."""
    eval_result = state.get("evaluation")
    iteration = state.get("iteration_count", 0)
    if eval_result and not eval_result.pass_threshold and iteration < _MAX_RETRIES:
        return "regenerate"
    return "done"


def _route_after_feedback(state: GraphState) -> str:
    """Conditional edge after human_review: route based on user feedback action.

    Falls back to "accept" when:
    - no feedback is present (graph resumed without update_state)
    - feedback_count has hit the ceiling (_MAX_FEEDBACK)
    """
    if state.get("feedback_count", 0) >= _MAX_FEEDBACK:
        return "accept"  # hard ceiling — prevent infinite feedback loops
    fb = state.get("feedback")
    if fb is None:
        return "accept"
    return fb.action  # "regenerate" | "refine_easier" | "refine_harder" | "accept"


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("analyzer", analyzer_node)
    g.add_node("term_extractor", term_extractor_node)
    g.add_node("knowledge_retriever", knowledge_retriever_node)
    g.add_node("question_generator", question_generator_node)
    g.add_node("evaluator", evaluator_node)
    g.add_node("human_review", human_review_node)

    # Fan out from START to both analyzer and term_extractor in parallel.
    g.add_edge(START, "analyzer")
    g.add_edge(START, "term_extractor")

    # Both must complete (join) before knowledge_retriever runs.
    g.add_edge("analyzer", "knowledge_retriever")
    g.add_edge("term_extractor", "knowledge_retriever")

    # knowledge_retriever feeds into question_generator with RAG context.
    g.add_edge("knowledge_retriever", "question_generator")

    g.add_edge("question_generator", "evaluator")

    # After evaluation: either regenerate (quality too low) or go to human_review.
    g.add_conditional_edges(
        "evaluator",
        _route_after_eval,
        {"regenerate": "question_generator", "done": "human_review"},
    )

    # After human_review (interrupt resumes here):
    # accept → END, all refine variants → question_generator.
    g.add_conditional_edges(
        "human_review",
        _route_after_feedback,
        {
            "regenerate": "question_generator",
            "refine_easier": "question_generator",
            "refine_harder": "question_generator",
            "accept": END,
        },
    )

    return g.compile(
        checkpointer=_checkpointer,
        interrupt_before=["human_review"],
    )


_compiled = None


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
