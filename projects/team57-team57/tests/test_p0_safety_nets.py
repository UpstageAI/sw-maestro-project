"""P0-2 / P0-3 / P0-5 — safety net 통합 회귀 테스트.

검증 포인트:
- P0-2: classifier 실패 시 1회 재시도 → 그래도 실패하면 classification_failed=True
- P0-3: 비한국어 리뷰는 LLM 호출 0회, lang_skip=True
- P0-5: 드래프터 출력에 위험 표현이 섞이면 후처리에서 치환 + safety_notes 기록
- 통합: build.graph 가 한국어 1건 mock 모드에서 raise 없이 완주
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

# 모든 테스트는 오프라인 mock 모드 강제 — 모듈 로드 전에 세팅.
os.environ["REVIEW_OPS_LLM"] = "mock"
os.environ.pop("UPSTAGE_API_KEY", None)


# --- P0-5 safety_filter 단위 -----------------------------------------------


def test_safety_filter_replaces_refund() -> None:
    from src.graph.tools.safety_filter import filter_risky_phrases

    out, notes = filter_risky_phrases("환불해드릴게요")
    assert "환불" not in out
    assert "별도 안내" in out
    assert any("환불" in n for n in notes)


def test_safety_filter_passthrough() -> None:
    from src.graph.tools.safety_filter import filter_risky_phrases

    out, notes = filter_risky_phrases("좋은 리뷰 감사합니다")
    assert out == "좋은 리뷰 감사합니다"
    assert notes == []


def test_safety_filter_multi_phrase() -> None:
    from src.graph.tools.safety_filter import filter_risky_phrases

    out, notes = filter_risky_phrases("환불 또는 할인을 제공해드리겠습니다")
    assert "환불" not in out
    assert "할인" not in out
    assert len(notes) >= 2


# --- P0-3 pii_mask 한국어 필터 ---------------------------------------------


def test_pii_mask_korean_passes() -> None:
    from src.graph.nodes.pii_mask import pii_mask_node

    out = pii_mask_node({"raw_text": "맛있는 카페였어요 또 가고 싶어요"})
    assert out["lang_skip"] is False
    assert out["lang_skip_reason"] == ""


def test_pii_mask_english_skips() -> None:
    from src.graph.nodes.pii_mask import pii_mask_node

    out = pii_mask_node({"raw_text": "Great coffee, friendly staff!"})
    assert out["lang_skip"] is True
    assert "ko_ratio" in out["lang_skip_reason"]


def test_pii_mask_mixed_short() -> None:
    """알파벳 < MIN_ALPHABETIC_CHARS 이면 한국어 없어도 skip 트리거하지 않음."""
    from src.graph.nodes.pii_mask import pii_mask_node

    out = pii_mask_node({"raw_text": "Hi!"})
    assert out["lang_skip"] is False


def test_pii_mask_mixed_majority_korean() -> None:
    """한국어 비율이 임계 이상이면 통과 (영어 단어가 섞여 있어도)."""
    from src.graph.nodes.pii_mask import pii_mask_node

    out = pii_mask_node({"raw_text": "정말 맛있어요 cafe 분위기도 좋고 친절했어요"})
    assert out["lang_skip"] is False


# --- P0-2/P0-3 route_by_sentiment 분기 -------------------------------------


def test_route_lang_skip_to_noop() -> None:
    from src.graph.routes.sentiment import route_by_sentiment

    assert route_by_sentiment({"lang_skip": True}) == "noop_drafter"


def test_route_classification_failed_to_noop() -> None:
    """classification_failed 가 sentiment 보다 우선."""
    from src.graph.routes.sentiment import route_by_sentiment

    out = route_by_sentiment(
        {"classification_failed": True, "sentiment": "negative", "confidence": 0.9}
    )
    assert out == "noop_drafter"


def test_route_normal_paths_unchanged() -> None:
    """기존 4분기 회귀 — 안전망이 끼어들지 않는다."""
    from src.graph.routes.sentiment import route_by_sentiment

    assert route_by_sentiment({"sentiment": "positive"}) == "thanks_drafter"
    assert route_by_sentiment({"sentiment": "neutral"}) == "neutral_drafter"
    assert (
        route_by_sentiment({"sentiment": "negative", "confidence": 0.9})
        == "apology_drafter"
    )
    assert (
        route_by_sentiment({"sentiment": "negative", "confidence": 0.3})
        == "apology_drafter_lowconf"
    )


# --- P0-3 classifier short-circuit -----------------------------------------


def test_classifier_node_short_circuits_on_lang_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lang_skip=True 면 classify() 가 raise 해도 classifier_node 는 raise 하지 않는다."""
    import src.graph.nodes.classifier as clf_mod

    def explode(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("classify should not be called when lang_skip=True")

    monkeypatch.setattr(clf_mod, "classify", explode)

    out = clf_mod.classifier_node(
        {"masked_text": "Great coffee", "lang_skip": True, "lang_skip_reason": "non-Korean (ko_ratio=0.00)"}
    )
    assert out["sentiment"] == "neutral"
    assert out["confidence"] == 0.0
    assert out["categories"] == []
    assert "classification_failed" not in out or out.get("classification_failed") is not True


# --- P0-2 classifier retry --------------------------------------------------


def test_classifier_retry_then_succeed(monkeypatch: pytest.MonkeyPatch) -> None:
    """첫 호출은 실패, 두 번째 호출은 성공 → classification_failed 안 뜸."""
    import src.graph.nodes.classifier as clf_mod

    calls = {"n": 0}

    def flaky(_text: str):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient 5xx (test)")
        return (
            {
                "sentiment": "negative",
                "categories": [{"category": "맛", "confidence": 0.8}],
                "confidence": 0.85,
                "risk_flag": False,
                "risk_reason": None,
            },
            {
                "model": "solar-pro2",
                "duration_ms": 1,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )

    monkeypatch.setattr(clf_mod, "classify", flaky)

    out = clf_mod.classifier_node({"masked_text": "줄이 너무 길어요"})
    assert calls["n"] == 2
    assert out.get("classification_failed") is not True
    assert out["sentiment"] == "negative"


def test_classifier_double_failure_sets_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """1회 + 1회 재시도 모두 실패 → classification_failed=True + 안전 기본값."""
    import src.graph.nodes.classifier as clf_mod

    calls = {"n": 0}

    def always_fail(_text: str):
        calls["n"] += 1
        raise RuntimeError("permanent failure (test)")

    monkeypatch.setattr(clf_mod, "classify", always_fail)

    out = clf_mod.classifier_node({"masked_text": "리뷰 본문"})
    assert calls["n"] == clf_mod.MAX_RETRIES + 1
    assert out["classification_failed"] is True
    assert "permanent failure" in out["classification_error"]
    assert out["sentiment"] == "neutral"
    assert out["confidence"] == 0.0
    assert out["categories"] == []
    # Router log → noop_drafter 분기
    router_log = next(
        e for e in out["node_log"] if e["node"] == "route_by_sentiment"
    )
    assert router_log["details"]["next_node"] == "noop_drafter"


# --- P0-5 drafter safety propagation ---------------------------------------


def test_drafter_safety_notes_propagated(monkeypatch: pytest.MonkeyPatch) -> None:
    """drafter 가 받은 LLM 텍스트에 '환불' 이 있으면 reply_draft 에서 제거 + notes 기록."""
    import src.graph.nodes.drafters as drafters_mod

    def fake_complete(prompt: str, *, system: str, model: str | None = None):  # noqa: ARG001
        return (
            "감사합니다 환불해드리겠습니다 다음에도 와주세요.",
            {"model": "solar-pro2", "duration_ms": 1, "input_tokens": 0, "output_tokens": 0},
        )

    monkeypatch.setattr(drafters_mod, "complete_text_with_meta", fake_complete)

    state = {
        "masked_text": "좋아요",
        "sentiment": "positive",
        "confidence": 0.9,
        "categories": [],
        "place_metadata": {},
    }
    out = drafters_mod.thanks_drafter(state)
    assert "환불" not in out["reply_draft"]
    assert out["safety_notes"]
    assert any("환불" in n for n in out["safety_notes"])
    assert out["drafter_used"] == "thanks"


def test_noop_drafter_produces_placeholder() -> None:
    from src.graph.nodes.drafters import noop_drafter

    out = noop_drafter({"classification_failed": True, "classification_error": "boom"})
    assert "(자동 답글 생성 안 됨)" in out["reply_draft"]
    assert out["drafter_used"] == "noop"
    assert out["safety_notes"] == []


def test_noop_drafter_handles_lang_skip() -> None:
    from src.graph.nodes.drafters import noop_drafter

    out = noop_drafter({"lang_skip": True, "lang_skip_reason": "non-Korean (ko_ratio=0.00)"})
    assert out["reply_draft"]
    assert out["drafter_used"] == "noop"


# --- 통합: build.graph end-to-end (mock 모드) ------------------------------


def test_end_to_end_main_graph_mock_no_break(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Korean review 1건 → graph.invoke 가 raise 없이 reply_draft 채워서 완주."""
    # 임시 DB
    db_file = tmp_path / "test_graph.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setenv("REVIEW_OPS_LLM", "mock")
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)

    # sqlite 모듈을 reload 해서 DB_PATH 새로 반영
    import src.store.sqlite as sqlite_mod

    sqlite_mod = importlib.reload(sqlite_mod)
    sqlite_mod.run_migrations()
    sqlite_mod.upsert_place("PLACE_E2E", "테스트 매장")
    sqlite_mod.insert_raw_review(
        "REV_E2E", "PLACE_E2E", "정말 맛있고 친절했어요", "2026-05-01T00:00:00Z"
    )

    # memory_save → sqlite 가 module-level DB_PATH 를 쓰므로
    # build 모듈 import 전 환경변수 셋업이 끝나야 한다.
    import src.graph.nodes.memory_save as memsave_mod

    memsave_mod.db = sqlite_mod  # 새 DB 핸들 주입

    import src.graph.build as build_mod

    build_mod = importlib.reload(build_mod)

    final_state = build_mod.graph.invoke(
        {
            "place_id": "PLACE_E2E",
            "review_id": "REV_E2E",
            "raw_text": "정말 맛있고 친절했어요",
            "review_created_at": "2026-05-01T00:00:00Z",
        }
    )
    assert final_state["reply_draft"]
    assert final_state.get("drafter_used") in {
        "thanks",
        "apology",
        "apology_lowconf",
        "neutral",
        "noop",
    }
    # reply 가 DB 에 적재됨
    reply = sqlite_mod.get_reply_for_review("REV_E2E")
    assert reply is not None
