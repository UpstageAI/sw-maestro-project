"""Code-level verification of every LangGraph workflow.

Imports each workflow class directly (no LangGraph dev server, no LangSmith
Studio), invokes the StateGraph with realistic inputs, and asserts the
expected node outputs are populated. Run with:

    python scripts/langgraph_codepath_verify.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.repositories.sqlite import SQLiteRepository
from app.services.llm import NoOpLLMClient
from app.workflows.qa import QAStudioContext, RetrievalQAWorkflow
from app.workflows.quality_review import QualityReviewWorkflow
from app.workflows.source_intake import SourceIntakeWorkflow
from app.workflows.storage import StorageWorkflow


SAMPLE_TEXT = (
    "결정: storage_preprocessing graph가 모든 노드를 정상 순회한다.\n\n"
    "근거: save_raw_document → chunk_document → extract_cards → finalize.\n\n"
    "리스크: chunk filter가 너무 강하면 카드가 0개로 떨어질 수 있다."
)


def banner(label: str) -> None:
    print()
    print(f"=== {label} ===")


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    repo = SQLiteRepository(tmp / "verify.sqlite3")
    repo.initialize()
    workspace = repo.create_workspace("LangGraph Codepath Verify")
    ws_id = workspace["id"]
    print(f"workspace_id={ws_id} db={repo.path}")

    # ----- 1. source_intake -----
    banner("1. source_intake")
    intake = SourceIntakeWorkflow(settings=_settings_with_no_token())
    print(f"   nodes: {list(intake.graph.nodes.keys())}")
    normalized = intake.normalize(
        workspace_id=ws_id,
        source_type="manual",
        source_url="",
        external_id="codepath-1",
        title="codepath.md",
        content=SAMPLE_TEXT,
    )
    print(
        "   result: filename={filename} type={document_type} src={source_type} fetched_via={fetched_via}".format(
            **{k: normalized[k] for k in ("filename", "document_type", "source_type", "fetched_via")}
        )
    )
    assert normalized["filename"] == "codepath.md"
    assert normalized["fetched_via"] == "pasted"
    assert normalized["source_type"] == "manual"
    print("   PASS")

    # ----- 2. storage_preprocessing -----
    banner("2. storage_preprocessing")
    storage = StorageWorkflow(repo)
    print(f"   nodes: {list(storage.graph.nodes.keys())}")
    storage_result = storage.ingest_text(
        workspace_id=ws_id,
        filename="codepath.md",
        content=SAMPLE_TEXT,
    )
    print(
        f"   result: doc={storage_result['document_id']} chunks={storage_result['chunk_count']} "
        f"cards={storage_result['card_count']} skipped={storage_result['skipped_chunk_count']} "
        f"needs_review={storage_result['needs_review_count']}"
    )
    assert storage_result["chunk_count"] == 3
    assert storage_result["card_count"] == 3
    cards = repo.list_cards(ws_id)
    types = sorted({c["card_type"] for c in cards})
    print(f"   card types extracted: {types}")
    assert types == ["decision", "evidence", "risk"]
    print("   PASS")

    # ----- 3. retrieval_qa (extractive mode, no Upstage) -----
    banner("3. retrieval_qa")
    qa = RetrievalQAWorkflow(repo, upstage_api_key="")  # extractive fallback
    print(f"   nodes: {list(qa.graph.nodes.keys())}")
    state = qa.graph.invoke(
        {"workspace_id": ws_id, "question": "GraphDB가 아닌 SQLite를 쓴 이유는?"},
        context=QAStudioContext(answer_mode="extractive", top_k=4),
    )
    print(f"   confidence={state.get('confidence')} cards={len(state.get('cards') or [])}")
    print(f"   evidence_cards={len(state.get('evidence_cards') or [])} chunks={len(state.get('evidence_chunks') or [])}")
    print(f"   answer (120c): {(state.get('answer') or '')[:120]}")
    assert state.get("confidence") in {"low", "medium", "high"}
    print("   PASS")

    # ----- 4. quality_review -----
    banner("4. quality_review")
    review = QualityReviewWorkflow(repo, llm_client=NoOpLLMClient())  # rule-based
    print(f"   nodes: {list(review.graph.nodes.keys())}")
    review_result = review.run(workspace_id=ws_id)
    print(
        f"   total_cards={review_result['total_cards']} reviewed={review_result['reviewed_count']} "
        f"summary={review_result['quality_summary']}"
    )
    for target in review_result["review_targets"][:3]:
        print(
            f"     - card #{target['card_id']} ({target['card_type']}, {target['priority']}): {target['issue'][:60]}"
        )
    assert isinstance(review_result["review_targets"], list)
    assert all("issue" in t and "suggestion" in t for t in review_result["review_targets"])
    print("   PASS")

    print()
    print("=== ALL 4 WORKFLOWS PASSED CODE-LEVEL VERIFICATION ===")


def _settings_with_no_token():
    """Return a Settings object with no provider tokens — exercises the manual path."""
    from app.core.config import Settings

    return Settings(_env_file=None)


if __name__ == "__main__":
    main()
