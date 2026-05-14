from __future__ import annotations

import json
from pathlib import Path

from src.db.repository import ReviewAgentRepository
from src.graph import run_review_agent
from src.llm.mock_provider import MockProvider
from src.state import ReviewAgentState


def _ensure_store(repo: ReviewAgentRepository) -> int:
    return repo.upsert_store(
        store_id=None,
        name="테스트 카페",
        business_type="카페",
        menu_items=["아메리카노", "카페라떼", "크루아상"],
        price_range="5000~10000원",
        reply_tone="정중체",
        reply_samples=["리뷰 감사합니다. 더 좋은 경험을 드리겠습니다."],
    )


def _scenario_text(name: str) -> str:
    payload = json.loads(Path("data/sample_reviews.json").read_text(encoding="utf-8"))
    target = next(item for item in payload["scenarios"] if item["name"] == name)
    return "\n".join(target["reviews"])


def test_graph_flow_runs_end_to_end_with_mock_provider(tmp_path: Path) -> None:
    repo = ReviewAgentRepository(tmp_path / "graph.db")
    repo.initialize()
    store_id = _ensure_store(repo)

    first_state = run_review_agent(
        repo=repo,
        provider=MockProvider(),
        state=ReviewAgentState(store_id=store_id, raw_input_text=_scenario_text("scenario_a_daily_batch")),
    )
    second_state = run_review_agent(
        repo=repo,
        provider=MockProvider(),
        state=ReviewAgentState(store_id=store_id, raw_input_text=_scenario_text("scenario_b_weekly_followup")),
    )

    assert len(first_state.parsed_reviews) == 8
    assert len(first_state.saved_review_ids) == 8
    assert first_state.pattern_summary["enabled"] is False

    assert len(second_state.parsed_reviews) == 5
    assert len(second_state.saved_review_ids) == 5
    assert second_state.pattern_summary["enabled"] is True
    assert len(second_state.checklist) >= 1
    assert any("Node" in item for item in second_state.execution_log)

