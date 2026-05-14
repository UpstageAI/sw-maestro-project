from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.db.connection import get_database_path
from src.db.repository import ReviewAgentRepository
from src.graph import run_review_agent
from src.llm.provider import get_provider
from src.state import ReviewAgentState


def ensure_demo_store(repo: ReviewAgentRepository) -> int:
    latest_store = repo.get_latest_store()
    if latest_store is not None:
        return latest_store.id

    return repo.upsert_store(
        store_id=None,
        name="모모카페 성수점",
        business_type="카페",
        menu_items=["아메리카노", "카페라떼", "크루아상", "디카페인 커피"],
        price_range="4,500원~8,500원",
        reply_tone="정중체",
        reply_samples=[
            "소중한 리뷰 남겨주셔서 감사합니다. 다음 방문에도 만족하실 수 있도록 정성껏 준비하겠습니다.",
            "방문해주셔서 감사합니다. 남겨주신 의견은 운영에 반영하겠습니다.",
        ],
    )


def load_scenario_reviews(name: str) -> str:
    payload = json.loads(Path("data/sample_reviews.json").read_text(encoding="utf-8"))
    scenarios = {item["name"]: item for item in payload["scenarios"]}
    if name not in scenarios:
        raise ValueError(f"Unknown scenario: {name}")
    return "\n".join(scenarios[name]["reviews"])


def print_state_result(title: str, state: ReviewAgentState) -> None:
    print(f"\n=== {title} ===")
    print(f"session_id: {state.session_id}")
    print(f"parsed_reviews: {len(state.parsed_reviews)}")
    print(f"saved_review_ids: {state.saved_review_ids}")
    print("execution_log:")
    for line in state.execution_log:
        print(f"- {line}")

    print("\nclassified_reviews:")
    for review in state.classified_reviews:
        print(
            f"- sentiment={review.get('sentiment')} categories={review.get('categories')} "
            f"menu_tags={review.get('menu_tags')} text={review.get('masked_text')}"
        )

    print("\ndrafted_replies:")
    for draft in state.drafted_replies:
        replies = draft.get("replies", [])
        print(f"- review_index={draft.get('review_index')} replies={replies[:1]}")

    print("\npattern_summary:")
    print(json.dumps(state.pattern_summary, ensure_ascii=False, indent=2))

    print("\nchecklist:")
    for item in state.checklist:
        print(f"- {item}")

    if state.warnings:
        print("\nwarnings:")
        for warning in state.warnings:
            print(f"- {warning}")

    if state.errors:
        print("\nerrors:")
        for error in state.errors:
            print(f"- {error}")


def run_scenario(repo: ReviewAgentRepository, scenario_name: str) -> ReviewAgentState:
    provider = get_provider()
    state = ReviewAgentState(
        store_id=ensure_demo_store(repo),
        raw_input_text=load_scenario_reviews(scenario_name),
    )
    return run_review_agent(repo=repo, provider=provider, state=state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LangGraph review-agent demo with mock provider.")
    parser.add_argument(
        "--scenario",
        choices=["scenario_a_daily_batch", "scenario_b_weekly_followup", "both"],
        default="both",
    )
    parser.add_argument("--reset-db", action="store_true")
    args = parser.parse_args()

    if args.reset_db:
        db_path = get_database_path()
        if db_path.exists():
            os.remove(db_path)

    repo = ReviewAgentRepository.from_env()
    repo.initialize()

    if args.scenario == "both":
        first = run_scenario(repo, "scenario_a_daily_batch")
        print_state_result("Scenario A", first)
        second = run_scenario(repo, "scenario_b_weekly_followup")
        print_state_result("Scenario B", second)
        return

    state = run_scenario(repo, args.scenario)
    print_state_result(args.scenario, state)


if __name__ == "__main__":
    main()
