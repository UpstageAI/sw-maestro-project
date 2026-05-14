"""Streamlit UI — sidebar 매장 선택 + 메인 inbox + 진행 패널 + graph trace."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.graph.build import graph
from src.graph.build_batch import batch_graph
from src.store import memory
from src.store import sqlite as db
from src.ui.chat import chat_dialog
from src.ui.components import (
    ProgressPanel,
    filter_reviews,
    render_node_trace,
    render_review_filters,
    render_review_result,
    render_sidebar_place_info,
    render_tone_hints_crud,
)

load_dotenv()

st.set_page_config(page_title="review-ops-agent", layout="wide")

# 폰트 크기만 살짝 줄이기 (Streamlit default 가 사장님 도구로 쓰기엔 큼)
st.html(
    """
    <style>
    .stApp h1 { font-size: 1.6rem !important; }
    .stApp h2 { font-size: 1.2rem !important; }
    .stApp h3 { font-size: 1.05rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.78rem !important; }
    </style>
    """
)

# ----------------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------------

if not os.path.exists(os.getenv("DB_PATH", "data/review_ops.db")):
    st.error(
        "DB가 초기화되지 않았습니다. 먼저 `make seed` 또는 "
        "`uv run python -m src.scripts.seed` 를 실행하세요."
    )
    st.stop()

place_ids = memory.list_place_ids()
if not place_ids:
    st.error("Memory Store에 시드된 매장이 없습니다. `make seed` 다시 실행하세요.")
    st.stop()

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------

if "selected_place" not in st.session_state:
    st.session_state.selected_place = place_ids[0]

if "batch_result" not in st.session_state:
    st.session_state.batch_result = {}  # {place_id: {top3_summary, top3_data, checklist, trace}}

if "traces" not in st.session_state:
    st.session_state.traces = {}  # {review_id: list[NodeLogEntry]}

# ----------------------------------------------------------------------------
# Sidebar — 매장 선택 + 액션
# ----------------------------------------------------------------------------

with st.sidebar:
    st.title("review-ops-agent")
    st.caption("LangGraph multi-tenant + Router + Memory + Tool")

    # Wave 3: 오프라인/CI 모드 가시화 — UPSTAGE_API_KEY 미설정 시 자동 mock
    from src.llm.upstage import _is_mock_mode
    if _is_mock_mode():
        st.warning("🟡 MOCK 모드 — LLM 호출 없이 동작 중")

    st.divider()
    st.markdown("**매장 목록**")
    metas = {pid: memory.get_metadata(pid) for pid in place_ids}
    selected = st.radio(
        "매장 선택",
        options=place_ids,
        index=place_ids.index(st.session_state.selected_place),
        format_func=lambda pid: f"{metas[pid].get('display_name', pid)} ({pid})",
        label_visibility="collapsed",
    )
    st.session_state.selected_place = selected

    meta = metas[selected]
    st.caption(
        f"업종: {meta.get('category', '?')} · 가격대 {meta.get('price_range', '?')} · "
        f"톤 선호: {meta.get('tone_preference', '미입력')}"
    )

    st.divider()
    # 🍽️ 메뉴 + 🎭 톤 샘플 & 활동 (목록 / 단일 추가 / 일괄 추가 / 이력 탭) 통합 expander
    render_sidebar_place_info(selected)

    # Wave 4: 톤 힌트 CRUD — 목록/편집/삭제/직접 추가 (모두 dedup pipeline 경유)
    render_tone_hints_crud(selected)

    st.divider()
    chat_btn = st.button("💬 매장 비서와 대화", type="primary", use_container_width=True)
    fetch_btn = st.button("🔁 새 리뷰 5건 가져오기", type="primary", use_container_width=True)
    pattern_btn = st.button("📊 TOP 3 + 체크리스트 새로고침", use_container_width=True)

    st.divider()
    # Wave 3 UX-1: 원클릭 데모 리셋 — db.reset_database + seed_all + st.rerun
    # 2단계 confirm 으로 실수 방지.
    if st.button("⚠️ 데모 리셋 (DB + 시드)", use_container_width=True):
        st.session_state["confirm_reset"] = True

    if st.session_state.get("confirm_reset"):
        st.warning("정말 모든 데이터를 초기화하시겠습니까?")
        col_a, col_b = st.columns(2)
        if col_a.button("✅ 확정", use_container_width=True, type="primary"):
            from src.scripts.seed import seed_all
            summary = seed_all(reset=True)
            st.session_state["confirm_reset"] = False
            st.session_state["traces"] = {}
            st.session_state["batch_result"] = {}
            st.toast(
                f"리셋 완료 — 매장 {summary['places']}, 리뷰 {summary['reviews_inserted']}",
            )
            st.rerun()
        if col_b.button("취소", use_container_width=True):
            st.session_state["confirm_reset"] = False
            st.rerun()

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

st.title(f"📝 {meta.get('display_name', selected)}")
st.caption(f"{meta.get('category', '매장')} · 가격대 {meta.get('price_range', '?')}")


def _process_one_review(review_row, panel: ProgressPanel) -> list[dict]:
    """1 review를 main graph 1회 실행. node_log 모아서 반환."""
    review_id = review_row["review_id"]
    node_log: list[dict] = []
    panel.set_status(f"`{review_id}` 처리 시작")

    for chunk in graph.stream(
        {
            "place_id": selected,
            "review_id": review_id,
            "raw_text": review_row["raw_text"],
            "review_created_at": review_row["created_at"],
        },
        stream_mode="updates",
    ):
        for node_name, delta in chunk.items():
            if node_name in ("__start__", "__end__"):
                continue
            entries = (delta or {}).get("node_log") or []
            node_log.extend(entries)
            # 진행 패널 단계 라인
            for entry in entries:
                summary = entry.get("summary", "")
                ms = entry.get("duration_ms", 0)
                panel.add_step_line(
                    f"  [{review_id}] ✓ {entry.get('node')} ({ms}ms) — {summary}"
                )
            panel.set_status(f"`{review_id}` · 노드 `{node_name}` 완료")

    return node_log


# --- TOP 3 + 체크리스트 (batch graph) ---------------------------------------

if pattern_btn:
    panel = ProgressPanel(
        "TOP 3 + 체크리스트", action="top3_refresh", total_steps=1
    ).start()

    result_state: dict = {}
    batch_log: list[dict] = []
    for chunk in batch_graph.stream({"place_id": selected}, stream_mode="updates"):
        for node_name, delta in chunk.items():
            if node_name in ("__start__", "__end__"):
                continue
            entries = (delta or {}).get("node_log") or []
            batch_log.extend(entries)
            for entry in entries:
                ms = entry.get("duration_ms", 0)
                panel.add_step_line(
                    f"  ✓ {entry.get('node')} ({ms}ms) — {entry.get('summary', '')}"
                )
            panel.set_status(f"노드 `{node_name}` 완료")
            for k, v in (delta or {}).items():
                if k != "node_log":
                    result_state[k] = v

    st.session_state.batch_result[selected] = {
        "top3_summary": result_state.get("top3_summary", ""),
        "top3_data": result_state.get("top3_data", []),
        "checklist": result_state.get("checklist", []),
        "trace": batch_log,
    }
    panel.advance(1)
    panel.finish()
    st.toast("batch 분석 완료")

batch = st.session_state.batch_result.get(selected, {})
if batch:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔝 TOP 3 반복 불만 (최근 4주)")
        if batch.get("top3_data"):
            for i, t in enumerate(batch["top3_data"], 1):
                st.markdown(f"**{i}. {t['category']}** — {t['freq']}회")
        else:
            st.info(batch.get("top3_summary", "데이터가 부족합니다."))
    with col2:
        st.subheader("✅ 이번 주 점검 체크리스트")
        for item in batch.get("checklist", []):
            st.markdown(f"- {item}")
    if batch.get("trace"):
        with st.expander(f"🔍 batch graph trace ({len(batch['trace'])} steps)", expanded=False):
            render_node_trace(batch["trace"], key_prefix="batch")

st.divider()

# --- 새 리뷰 처리 --------------------------------------------------------------

if fetch_btn:
    unprocessed = db.get_unprocessed_reviews(selected, limit=5)
    if not unprocessed:
        st.warning("처리할 새 리뷰가 없습니다. (모든 리뷰가 이미 처리됨)")
    else:
        panel = ProgressPanel(
            "새 리뷰 5건 처리", action="fetch_5_reviews", total_steps=len(unprocessed)
        ).start()

        for i, review in enumerate(unprocessed, 1):
            review_id = review["review_id"]
            node_log = _process_one_review(review, panel)
            st.session_state.traces[review_id] = node_log
            panel.advance(i)

            # 카드 즉시 표시 — 인라인 카드는 trace 기본 펼침 (사용자에게 graph 동작 보이도록)
            rows = db.list_reviews(selected, limit=1000)
            row = next((r for r in rows if r["review_id"] == review_id), None)
            reply = db.get_reply_for_review(review_id)
            if row and reply:
                st.markdown(f"### 📨 `{review_id}`")
                st.write(review["raw_text"])
                st.caption(f"리뷰 작성: {review['created_at']}")
                render_review_result(
                    row,
                    reply,
                    node_log=node_log,
                    trace_expanded=True,  # ← 방금 처리된 카드는 trace 펼쳐서 graph 동작 노출
                    with_trace_expander=True,
                    key_prefix="inline_",
                )
                st.divider()
            else:
                st.error(f"{review_id}: graph 완료 후 결과를 찾을 수 없습니다.")

        panel.finish()
        st.toast(f"{len(unprocessed)}건 처리 완료")

# --- 이미 처리된 리뷰 목록 ---------------------------------------------------

# --- 인사이트 + 처리된 리뷰 (필터 가능) -------------------------------------

stats = db.get_review_stats(selected)

# 필터 + 리뷰 목록
all_processed = db.list_reviews(selected, limit=200)
if not all_processed:
    st.caption("아직 처리된 리뷰가 없습니다. 사이드바에서 '새 리뷰 가져오기'를 눌러보세요.")
else:
    selected_sents, selected_cats = render_review_filters(stats, key_prefix="bottom_")
    filtered = filter_reviews(all_processed, selected_sents, selected_cats)

    filter_active = bool(selected_sents or selected_cats)
    visible = filtered[:30]
    header_count = (
        f"{len(visible)} / {len(all_processed)}건 표시"
        if filter_active
        else f"최근 {len(visible)}건"
    )

    st.subheader(f"📂 처리된 리뷰 — {header_count}")

    if not visible:
        st.info("필터 조건에 맞는 리뷰가 없습니다. 필터를 해제해보세요.")
    else:
        for row in visible:
            reply = db.get_reply_for_review(row["review_id"])
            with st.expander(
                f"[{row['sentiment'] or '?'}] {row['raw_text'][:50]}...",
                expanded=False,
            ):
                render_review_result(
                    row,
                    reply,
                    with_trace_expander=False,
                    trace_expanded=False,
                    key_prefix="bottom_",
                )

# ----------------------------------------------------------------------------
# 채팅 비서 — 사이드바 버튼으로 dialog 트리거
# ----------------------------------------------------------------------------

if chat_btn:
    chat_dialog(selected)
