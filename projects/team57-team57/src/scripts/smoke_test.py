"""End-to-end smoke test — main graph 1회 + batch graph 1회 실행.

Usage: `uv run python -m src.scripts.smoke_test`
사전 조건: `.env` 의 UPSTAGE_API_KEY 가 설정되어 있어야 합니다.
(https://console.upstage.ai 에서 발급)
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Windows console: 한글·유니코드 출력 안전화
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass

load_dotenv()

if not os.getenv("UPSTAGE_API_KEY"):
    sys.exit(
        "UPSTAGE_API_KEY 가 설정되지 않았습니다.\n"
        "  1) cp .env.example .env\n"
        "  2) https://console.upstage.ai 에서 API 키 발급 후 .env 에 입력"
    )

from src.graph.build import graph
from src.graph.build_batch import batch_graph
from src.store import sqlite as db


def _print_chunk(prefix: str, chunk: dict) -> None:
    for node, delta in chunk.items():
        if node in ("__start__", "__end__"):
            continue
        keys = ", ".join((delta or {}).keys())
        print(f"{prefix} ✓ {node:<30} → {{{keys}}}")


def main() -> None:
    print("=" * 70)
    print("Smoke test — main graph (1 review)")
    print("=" * 70)

    place_id = "PLACE_001"
    unprocessed = db.get_unprocessed_reviews(place_id, limit=1)
    if not unprocessed:
        sys.exit(f"처리할 리뷰가 없습니다. `make seed`를 먼저 실행하세요.")

    review = unprocessed[0]
    print(f"\n[리뷰] {review['review_id']}")
    print(f"  > {review['raw_text']}")
    print(f"  > timestamp: {review['created_at']}")
    print()

    final_state = {}
    for chunk in graph.stream(
        {
            "place_id": place_id,
            "review_id": review["review_id"],
            "raw_text": review["raw_text"],
            "review_created_at": review["created_at"],
        },
        stream_mode="updates",
    ):
        _print_chunk("  ", chunk)
        for _node, delta in chunk.items():
            if delta:
                final_state.update(delta)

    print()
    print("[최종 state]")
    print(f"  sentiment:    {final_state.get('sentiment')}  (conf {final_state.get('confidence', 0):.2f})")
    print(f"  categories:   {[c['category'] for c in final_state.get('categories', [])]}")
    print(f"  risk_flag:    {final_state.get('risk_flag')}")
    print(f"  drafter_used: {final_state.get('drafter_used')}")
    print(f"  reply_draft:  {final_state.get('reply_draft', '')[:100]}...")

    print()
    print("=" * 70)
    print("Smoke test — batch graph (TOP 3 + checklist)")
    print("=" * 70)

    # 다른 리뷰도 몇 개 처리해서 batch에 데이터 만들어두기
    print("\n  (선)main graph 추가 4건 처리...")
    more = db.get_unprocessed_reviews(place_id, limit=4)
    for r in more:
        for _ in graph.stream(
            {
                "place_id": place_id,
                "review_id": r["review_id"],
                "raw_text": r["raw_text"],
                "review_created_at": r["created_at"],
            },
            stream_mode="updates",
        ):
            pass
        print(f"    ✓ processed {r['review_id']}")

    print("\n  batch graph 시작...")
    batch_state: dict = {}
    for chunk in batch_graph.stream({"place_id": place_id}, stream_mode="updates"):
        _print_chunk("  ", chunk)
        for _node, delta in chunk.items():
            if delta:
                batch_state.update(delta)

    print()
    print("[batch 최종 state]")
    print(f"  top3_data:  {batch_state.get('top3_data')}")
    print(f"  top3_summary:")
    for line in (batch_state.get("top3_summary") or "").split("\n"):
        print(f"    {line}")
    print(f"  checklist:")
    for item in batch_state.get("checklist", []):
        print(f"    - {item}")

    print("\nSmoke test 완료. `make run` 으로 Streamlit UI 확인하세요.")


if __name__ == "__main__":
    main()
