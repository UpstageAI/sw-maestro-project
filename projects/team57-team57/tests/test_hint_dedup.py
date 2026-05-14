"""Wave 4: 톤 힌트 dedup/merge + CRUD 회귀 테스트.

검증 포인트:
- 첫 힌트는 dedup LLM 호출 없이 바로 append
- 중복 / 모순 / 독립 케이스 (mock 결정론적 의사결정)
- update_feedback / delete_feedback 동작
- list_feedback_with_meta 최신 순 정렬
- manual source 가 그대로 저장됨
- get_feedback_hints 가 최대 5건까지 반환
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

# 모든 테스트는 오프라인 mock 모드 — 모듈 import 전에 환경변수 셋업.
os.environ["REVIEW_OPS_LLM"] = "mock"
os.environ.pop("UPSTAGE_API_KEY", None)


@pytest.fixture(autouse=True)
def _fresh_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """매 테스트마다 임시 store dump 경로 + 메모리 reset."""
    dump = tmp_path / "store_dump.json"
    monkeypatch.setenv("STORE_DUMP_PATH", str(dump))

    # memory 모듈을 reload 해서 DUMP_PATH module-level 변수 새로 반영
    import importlib

    import src.store.memory as mem_mod

    mem_mod = importlib.reload(mem_mod)
    mem_mod.reset()
    yield mem_mod
    mem_mod.reset()


PLACE = "PLACE_HINT_TEST"


def _import_dedup():
    """hint_dedup 도 memory module reload 후 fresh import."""
    import importlib

    import src.graph.tools.hint_dedup as dedup_mod

    dedup_mod = importlib.reload(dedup_mod)
    return dedup_mod


# --- 첫 힌트 -----------------------------------------------------------------


def test_append_first_hint_skips_dedup_call(_fresh_store, monkeypatch):
    """기존 0건이면 dedup LLM 호출 없이 그대로 append."""
    memory = _fresh_store
    dedup = _import_dedup()

    calls = {"n": 0}

    def explode(*args, **kwargs):  # noqa: ARG001
        calls["n"] += 1
        raise RuntimeError("dedup LLM should not be called on first hint")

    # complete_json_with_meta 가 호출되면 raise 하도록 patch
    import src.llm.upstage as up_mod

    monkeypatch.setattr(up_mod, "complete_json_with_meta", explode)

    result = dedup.merge_or_append_hint(
        PLACE, "정중한 톤 강조", ["sm_xxx"], source="auto_diff"
    )
    assert result["action"] == "append"
    assert result["result_fid"]
    assert calls["n"] == 0

    items = memory.list_feedback_with_meta(PLACE)
    assert len(items) == 1
    assert items[0]["source"] == "auto_diff"
    assert items[0]["created_at"]
    assert items[0]["based_on_sample_ids"] == ["sm_xxx"]


# --- dedup 의사결정 ----------------------------------------------------------


def test_dedup_skip_when_duplicate(_fresh_store):
    memory = _fresh_store
    dedup = _import_dedup()

    memory.append_feedback(PLACE, "정중한 톤 강조", [], source="auto_diff")
    result = dedup.merge_or_append_hint(
        PLACE, "정중한 톤을 강조", [], source="auto_diff"
    )
    assert result["action"] == "skip"
    assert result["result_fid"] is None
    items = memory.list_feedback_with_meta(PLACE)
    assert len(items) == 1


def test_dedup_merge_on_contradiction(_fresh_store):
    memory = _fresh_store
    dedup = _import_dedup()

    old_fid = memory.append_feedback(
        PLACE, "친근체로 가볍게", [], source="auto_diff"
    )
    result = dedup.merge_or_append_hint(
        PLACE, "정중체로 격식 있게", [], source="auto_diff"
    )
    assert result["action"] == "merge"
    assert result["result_fid"]
    assert old_fid in result["merged_from"]

    items = memory.list_feedback_with_meta(PLACE)
    fids = {it["fid"] for it in items}
    assert old_fid not in fids  # 기존은 삭제됨
    assert result["result_fid"] in fids

    new_entry = next(it for it in items if it["fid"] == result["result_fid"])
    assert new_entry["source"] == "merged"
    assert old_fid in new_entry["merged_from"]


def test_dedup_append_when_independent(_fresh_store):
    memory = _fresh_store
    dedup = _import_dedup()

    memory.append_feedback(PLACE, "감사 표현 길게", [], source="auto_diff")
    result = dedup.merge_or_append_hint(
        PLACE, "이모티콘 자제", [], source="auto_diff"
    )
    assert result["action"] == "append"
    assert result["result_fid"]

    items = memory.list_feedback_with_meta(PLACE)
    assert len(items) == 2


# --- update / delete ---------------------------------------------------------


def test_update_feedback_changes_text_and_updated_at(_fresh_store):
    memory = _fresh_store

    fid = memory.append_feedback(PLACE, "원본", [], source="manual")
    items = memory.list_feedback_with_meta(PLACE)
    created_before = items[0]["created_at"]
    updated_before = items[0]["updated_at"]

    # updated_at 차이 보장 (ISO timestamp 가 ms 단위라 sleep)
    time.sleep(0.005)
    ok = memory.update_feedback(PLACE, fid, "수정됨")
    assert ok is True

    items = memory.list_feedback_with_meta(PLACE)
    assert items[0]["diff_hint"] == "수정됨"
    assert items[0]["created_at"] == created_before  # 변경 없음
    assert items[0]["updated_at"] >= updated_before  # 갱신 (>= 로 ts 동률 허용)


def test_delete_feedback(_fresh_store):
    memory = _fresh_store

    fid = memory.append_feedback(PLACE, "삭제 대상", [], source="auto_diff")
    assert memory.delete_feedback(PLACE, fid) is True
    assert memory.list_feedback_with_meta(PLACE) == []
    # 없는 fid 재삭제 — False
    assert memory.delete_feedback(PLACE, fid) is False


# --- 정렬 / 최신 순 ----------------------------------------------------------


def test_list_feedback_with_meta_orders_newest_first(_fresh_store):
    memory = _fresh_store

    memory.append_feedback(PLACE, "첫번째", [], source="auto_diff")
    time.sleep(0.005)
    memory.append_feedback(PLACE, "두번째", [], source="auto_diff")
    time.sleep(0.005)
    memory.append_feedback(PLACE, "세번째", [], source="auto_diff")

    items = memory.list_feedback_with_meta(PLACE)
    assert [it["diff_hint"] for it in items] == ["세번째", "두번째", "첫번째"]


# --- manual source ----------------------------------------------------------


def test_manual_source_passes_through(_fresh_store):
    memory = _fresh_store
    dedup = _import_dedup()

    result = dedup.merge_or_append_hint(
        PLACE, "친근한 어투로", [], source="manual"
    )
    assert result["action"] == "append"
    items = memory.list_feedback_with_meta(PLACE)
    assert len(items) == 1
    assert items[0]["source"] == "manual"


# --- load_context limit -----------------------------------------------------


def test_load_context_returns_up_to_5_hints(_fresh_store):
    memory = _fresh_store

    for i in range(7):
        memory.append_feedback(PLACE, f"힌트 {i}", [], source="auto_diff")
        time.sleep(0.002)

    hints = memory.get_feedback_hints(PLACE)
    assert len(hints) == 5
    # 최신 순이므로 가장 최근 추가된 "힌트 6" 가 첫번째
    assert hints[0] == "힌트 6"


# --- Wave 5: dimension 기반 sharp dedup ----------------------------------------


def test_dedup_merge_preferred_phrasing_same_dimension(_fresh_store):
    """같은 dimension(사과표현) + 다른 선호 표현(미안해요↔죄송합니다) → merge.

    BUG 회귀: 기존 '미안해요 선호' + 신규 '죄송합니다 선호' 가 append 되어 두 개
    누적되던 문제를 dimension-aware dedup 으로 해결.
    """
    memory = _fresh_store
    dedup = _import_dedup()

    fid1 = memory.append_feedback(
        PLACE, "미안해요 선호", [], source="auto_diff", dimension="사과표현"
    )
    result = dedup.merge_or_append_hint(
        PLACE, "죄송합니다 선호", [], source="auto_diff", dimension="사과표현"
    )
    assert result["action"] == "merge"
    assert result.get("merged_from") == [fid1]

    listed = memory.list_feedback_with_meta(PLACE, limit=10)
    fids = [e["fid"] for e in listed]
    assert fid1 not in fids  # 기존 삭제
    assert len(listed) == 1  # 신규 1건만 남음


def test_dedup_skip_same_preference_same_dimension(_fresh_store):
    """같은 dimension + 같은 선호 표현 → skip."""
    memory = _fresh_store
    dedup = _import_dedup()

    memory.append_feedback(
        PLACE, "미안해요 선호", [], source="auto_diff", dimension="사과표현"
    )
    result = dedup.merge_or_append_hint(
        PLACE, "미안해요 선호", [], source="auto_diff", dimension="사과표현"
    )
    assert result["action"] == "skip"


def test_dedup_append_when_different_dimension(_fresh_store):
    """서로 다른 dimension (사과표현 vs 길이) → append."""
    memory = _fresh_store
    dedup = _import_dedup()

    memory.append_feedback(
        PLACE, "죄송합니다 선호", [], source="auto_diff", dimension="사과표현"
    )
    result = dedup.merge_or_append_hint(
        PLACE, "짧게 선호", [], source="auto_diff", dimension="길이"
    )
    assert result["action"] == "append"
    listed = memory.list_feedback_with_meta(PLACE, limit=10)
    assert len(listed) == 2


def test_diff_hint_schema_mock_outputs_before_after(_fresh_store):
    """mock 모드에서 DIFF_HINT_SCHEMA 호출 시 before/after/dimension/hint 추출."""
    from src.graph.tools.hint_dedup import DIFF_HINT_SCHEMA, DIFF_HINT_SYSTEM
    from src.llm.upstage import complete_json_with_meta

    result, _ = complete_json_with_meta(
        prompt="AI 초안:\n불편을 드려 미안해요\n\n사장 최종:\n불편을 드려 죄송합니다",
        system=DIFF_HINT_SYSTEM,
        schema=DIFF_HINT_SCHEMA,
    )
    assert "미안" in result.get("before", "") or result.get("before") == "미안해요"
    assert "죄송" in result.get("after", "") or result.get("after") == "죄송합니다"
    assert result.get("dimension") == "사과표현"
    assert "보다" in result.get("hint", "") and "선호" in result.get("hint", "")
