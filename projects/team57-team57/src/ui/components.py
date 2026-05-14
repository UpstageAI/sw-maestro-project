"""UI 보조 컴포넌트 — 진행 패널 / 노드 트레이스 / 리뷰 결과 카드."""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from collections import deque

import pandas as pd
import streamlit as st

_SENTIMENT_LABELS = {"positive": "😊 긍정", "neutral": "😐 중립", "negative": "😟 부정"}
_SENTIMENT_ORDER = ["positive", "neutral", "negative"]

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx
except ImportError:  # 구버전 호환
    add_script_run_ctx = None  # type: ignore[assignment]

from src.store import memory
from src.store import sqlite as db


# ============================================================================
# 통계·인사이트·필터
# ============================================================================


def render_review_filters(stats: dict, *, key_prefix: str = "") -> tuple[set, set]:
    """sentiment + category multi-select pill toggles. (selected_sents, selected_cats) 반환.

    빈 set = 필터 해제 (모두 표시). 그룹 내 OR, 그룹 간 AND.
    """
    sent_counts = stats.get("by_sentiment", {})
    cat_counts = stats.get("by_category", {})

    cols = st.columns([3, 5])

    with cols[0]:
        sent_options = [s for s in _SENTIMENT_ORDER if sent_counts.get(s, 0) > 0]
        if sent_options:
            sent_labels = {
                s: f"{_SENTIMENT_LABELS[s]} {sent_counts.get(s, 0)}"
                for s in sent_options
            }
            selected_sents = st.pills(
                "감정 필터",
                options=sent_options,
                format_func=lambda s: sent_labels[s],
                selection_mode="multi",
                default=[],
                key=f"{key_prefix}filter_sent",
                label_visibility="visible",
            )
        else:
            selected_sents = []
            st.caption("감정 필터 — 데이터 없음")

    with cols[1]:
        cat_options = sorted(cat_counts.keys(), key=lambda c: -cat_counts[c])
        if cat_options:
            cat_labels = {c: f"{c} {cat_counts[c]}" for c in cat_options}
            selected_cats = st.pills(
                "카테고리 필터 (멀티라벨)",
                options=cat_options,
                format_func=lambda c: cat_labels[c],
                selection_mode="multi",
                default=[],
                key=f"{key_prefix}filter_cat",
                label_visibility="visible",
            )
        else:
            selected_cats = []
            st.caption("카테고리 필터 — 데이터 없음")

    return set(selected_sents or []), set(selected_cats or [])


def filter_reviews(rows: list, selected_sents: set, selected_cats: set) -> list:
    """리뷰 목록 필터링. 그룹 내 OR, 그룹 간 AND. 빈 그룹 = 필터 없음.

    `categories` 는 SQLite GROUP_CONCAT 결과 (콤마 구분) 라 split 후 비교.
    멀티라벨 리뷰가 선택된 카테고리 *하나라도* 가지면 매치.
    """
    out = []
    for r in rows:
        if selected_sents and r["sentiment"] not in selected_sents:
            continue
        if selected_cats:
            review_cats_raw = r["categories"] or ""
            review_cats = {c.strip() for c in review_cats_raw.split(",") if c.strip()}
            if not (review_cats & selected_cats):
                continue
        out.append(r)
    return out


# ============================================================================
# ETA history (moving window average, maxlen=5 per action)
# ============================================================================

ETA_DEFAULTS_SEC = {
    "fetch_5_reviews": 25.0,    # per review (1 main graph run)
    "top3_refresh": 25.0,        # per batch graph run
    "save_tone_learn": 10.0,     # per diff hint LLM call
    "manual_tone_add": 0.5,      # 사용자 수동 추가 (사실상 즉시)
}


def _eta_history() -> dict[str, deque]:
    if "eta_history" not in st.session_state:
        st.session_state.eta_history = {}
    return st.session_state.eta_history


def get_eta(action: str) -> tuple[float, str]:
    """평균 ETA + 라벨. 관측 없으면 ETA_DEFAULTS_SEC 사용."""
    hist = _eta_history()
    deq = hist.get(action)
    if not deq:
        return ETA_DEFAULTS_SEC.get(action, 10.0), "(초기 추정)"
    avg = sum(deq) / len(deq)
    return avg, f"(직전 {len(deq)} 회 평균)"


def record_eta(action: str, observed_seconds: float) -> None:
    hist = _eta_history()
    if action not in hist:
        hist[action] = deque(maxlen=5)
    hist[action].append(observed_seconds)


def format_eta(seconds: float) -> str:
    seconds = max(0, seconds)
    if seconds < 60:
        return f"{int(seconds)}초"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# ============================================================================
# Progress panel — 액션 트리거 시 상단에 표시
# ============================================================================


class ProgressPanel:
    """3개 액션(fetch_5/top3/save_tone)에서 공통으로 사용하는 진행 패널.

    Usage:
        panel = ProgressPanel("새 리뷰 5건 처리", action="fetch_5_reviews", total_steps=5)
        panel.start()
        for i, item in enumerate(items, 1):
            panel.set_status(f"REV_{item['id']} · classifier 중")
            # ... do work ...
            panel.advance(i)  # i 단계 완료
        panel.finish()
    """

    def __init__(self, action_name: str, *, action: str, total_steps: int):
        self.action_name = action_name
        self.action = action
        self.total_steps = max(total_steps, 1)
        self.eta_per_step, self.eta_label = get_eta(action)
        self.total_eta = self.eta_per_step * self.total_steps
        self.t0: float = 0.0
        self._done = False
        self._step_lines: list[str] = []
        self._last_step = 0
        self._stop_event = threading.Event()
        self._ticker: threading.Thread | None = None

    def start(self) -> "ProgressPanel":
        self.t0 = time.time()
        self._container = st.container(border=True)
        # 단계 로그는 expander(default open)에 배치 → 사용자가 클릭 한 번으로 접을 수 있음.
        # 개별 placeholder 들은 expander 밖에 (시각성 유지).
        with self._container:
            self._header = st.empty()
            self._progress = st.empty()
            self._status = st.empty()
            log_exp = st.expander("📋 노드 단계 로그", expanded=True)
            with log_exp:
                self._steps_box = st.empty()

        self._render_header(initial=True)
        self._render_progress(0)
        self._steps_box.code("(아직 시작 안 함)", language="text")

        # 1초마다 진행률·헤더 갱신하는 daemon thread (long-running LLM 호출 중에도 시간 흘러감 표시)
        self._ticker = threading.Thread(target=self._tick_loop, daemon=True)
        if add_script_run_ctx is not None:
            try:
                add_script_run_ctx(self._ticker)
            except Exception:
                pass
        self._ticker.start()
        return self

    def _tick_loop(self) -> None:
        """1초마다 경과시간 기반으로 progress + header 업데이트 (다른 chunk 안 와도 진행률 보임)."""
        while not self._stop_event.wait(timeout=1.0):
            if self._done:
                return
            try:
                self._render_progress(self._last_step)
                self._render_header()
            except Exception:
                # placeholder 가 폐기됐거나 컨텍스트 끝남 → 종료
                return

    def _render_header(self, *, initial: bool = False) -> None:
        eta_str = format_eta(self.total_eta)
        if initial:
            self._header.markdown(
                f"⏱ **{self.action_name}** — 예상 ~{eta_str} {self.eta_label}"
            )
        else:
            elapsed_str = format_eta(time.time() - self.t0)
            self._header.markdown(
                f"⏱ **{self.action_name}** — {elapsed_str} / ~{eta_str} {self.eta_label}"
            )

    def _render_progress(self, step_completed: int) -> None:
        """진행률 = 경과시간 / 예상시간 (smooth fill). step 비율이 더 크면 그걸로 보정 (역행 방지)."""
        elapsed = time.time() - self.t0
        if step_completed >= self.total_steps:
            ratio = 1.0
        else:
            time_ratio = elapsed / max(self.total_eta, 0.1)
            step_ratio = step_completed / self.total_steps
            if time_ratio >= 1.0:
                # 예상보다 오래 걸리는 중 — 95% 에서 멈춤 (오해 방지)
                ratio = max(0.95, step_ratio)
            else:
                ratio = max(time_ratio, step_ratio)
        remain = max(self.total_eta - elapsed, 0)
        text = (
            f"{step_completed}/{self.total_steps} · "
            f"경과 {format_eta(elapsed)} · 남은 ~{format_eta(remain)}"
        )
        self._progress.progress(ratio, text=text)

    def set_status(self, label: str) -> None:
        if self._done:
            return
        self._status.caption(f"⏳ {label}")
        self._render_header()
        # 경과시간 반영해 진행률도 같이 업데이트 (마지막 step 번호 유지)
        self._render_progress(self._last_step)

    def advance(self, step_completed: int) -> None:
        if self._done:
            return
        self._last_step = step_completed
        self._render_progress(step_completed)
        self._render_header()

    def add_step_line(self, line: str) -> None:
        """단계별 로그 누적 (항상 보이는 code 블록)."""
        if self._done:
            return
        self._step_lines.append(line)
        # 마지막 30줄만 — 너무 길면 잘림
        recent = "\n".join(self._step_lines[-30:])
        self._steps_box.code(recent, language="text")

    def finish(self) -> None:
        if self._done:
            return
        self._done = True
        self._stop_event.set()  # 1초 ticker 종료 신호
        elapsed = time.time() - self.t0
        record_eta(self.action, elapsed / self.total_steps)
        self._header.markdown(
            f"✅ **{self.action_name}** — 총 {format_eta(elapsed)} 소요 "
            f"(평균 {format_eta(elapsed / self.total_steps)}/스텝)"
        )
        # 진행률 바: 100% 로 채우고 그대로 표시 (사라지지 않게)
        self._progress.progress(1.0, text=f"완료 · 총 {format_eta(elapsed)}")
        self._status.empty()
        # 단계 로그는 그대로 둠 (사용자가 사후에 expander 접거나 펼쳐 확인 가능)


# ============================================================================
# Node trace — 카드 안 expander
# ============================================================================


_KIND_ICON = {
    "memory_read": "📖",
    "memory_write": "💾",
    "transform": "🔧",
    "llm": "🧠",
    "router": "🔀",
    "sql_read": "🗃️",
    "sql_write": "🗃️",
}


def _format_duration(ms: int) -> str:
    if ms >= 1000:
        return f"{ms / 1000:.2f}s"
    return f"{ms}ms"


def render_node_trace(node_log: list[dict], *, key_prefix: str = "") -> None:
    """그래프 1회 실행 trace를 st.dataframe + 토글로 노출.

    nested expander 제약 회피를 위해 부속 디테일은 st.toggle 로 전환됨.
    """
    if not node_log:
        st.caption("(트레이스 없음)")
        return

    # 1) st.dataframe — 정렬·반응형·column_config
    df = pd.DataFrame(
        [
            {
                "#": i,
                "노드": entry.get("node", "?"),
                "시간": _format_duration(entry.get("duration_ms", 0)),
                "종류": f"{_KIND_ICON.get(entry.get('kind', ''), '•')} {entry.get('kind', '')}",
                "요약": entry.get("summary") or "",
            }
            for i, entry in enumerate(node_log, 1)
        ]
    )
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn("#", width="small", format="%d"),
            "노드": st.column_config.TextColumn("노드", width="medium"),
            "시간": st.column_config.TextColumn("⏱ 시간", width="small"),
            "종류": st.column_config.TextColumn("종류", width="small"),
            "요약": st.column_config.TextColumn("요약", width="large"),
        },
        height=min(45 + 35 * len(node_log), 420),
    )

    # 디테일 — 각 행 별로 토글 (nested expander 회피)
    for i, entry in enumerate(node_log, 1):
        kind = entry.get("kind")
        details = entry.get("details") or {}
        node = entry.get("node", "?")

        if kind == "llm":
            label = f"📜 #{i} `{node}` — prompt/응답 미리보기"
        elif kind == "router":
            label = f"🔀 #{i} `{node}` — 분기 결정"
        elif kind in ("sql_read", "sql_write"):
            label = f"🗃️ #{i} `{node}` — SQL 호출"
        elif kind in ("memory_read", "memory_write"):
            label = f"📖 #{i} `{node}` — Memory Store 접근"
        else:
            continue  # transform 등은 디테일 없음

        toggle_key = f"{key_prefix}_detail_{i}"
        if st.toggle(label, key=toggle_key, value=False):
            with st.container(border=True):
                if kind == "llm":
                    model = details.get("model", "?")
                    in_tok = details.get("input_tokens", 0)
                    out_tok = details.get("output_tokens", 0)
                    cache_read = details.get("cache_read_tokens", 0)
                    api_ms = details.get("duration_api_ms", 0)
                    st.caption(
                        f"model: `{model}` · API {api_ms}ms · "
                        f"tokens {in_tok}→{out_tok} (cache read {cache_read})"
                    )
                    if details.get("system_preview"):
                        st.markdown("**system prompt** (앞 200자)")
                        st.code(details["system_preview"], language="text")
                    if details.get("prompt_preview"):
                        st.markdown("**user prompt** (앞 200자)")
                        st.code(details["prompt_preview"], language="text")
                    if details.get("response_preview"):
                        st.markdown("**응답** (앞 200자)")
                        st.code(details["response_preview"], language="text")
                elif kind == "router":
                    inputs = details.get("decision_inputs", {})
                    st.markdown(f"- 다음 노드: `{details.get('next_node', '?')}`")
                    st.markdown(f"- 임계값: `{details.get('threshold', '?')}`")
                    st.markdown(f"- 입력: `{inputs}`")
                elif kind in ("sql_read", "sql_write"):
                    if details.get("tool"):
                        st.markdown(f"- tool: `{details['tool']}`")
                    if details.get("args"):
                        st.markdown(f"- args: `{details['args']}`")
                    if details.get("result") is not None:
                        st.markdown("- result:")
                        st.json(details["result"])
                    if details.get("review_id"):
                        st.markdown(f"- review_id: `{details['review_id']}`")
                    if details.get("reply_id"):
                        st.markdown(f"- reply_id: `{details['reply_id']}`")
                elif kind in ("memory_read", "memory_write"):
                    if details.get("namespaces_read"):
                        st.markdown("- 읽은 namespace:")
                        for ns in details["namespaces_read"]:
                            st.markdown(f"  - `{ns}`")
                    for k in (
                        "tone_samples_count",
                        "feedback_hints_count",
                        "menus_count",
                        "tone_preference",
                    ):
                        if k in details:
                            st.markdown(f"- {k}: `{details[k]}`")


# ============================================================================
# 답글 수정 후 diff hint (claude CLI 1회)
# ============================================================================


def _diff_hint(place_id: str, ai_draft: str, owner_final: str, sample_id: str) -> None:
    """답글 초안↔최종본 차이를 Solar 로 구조화 추출 후 dedup pipeline 으로 저장.

    Wave 5: complete_text 의 자유서술 → complete_json_with_meta 의 구조화 출력
    (dimension/before/after/hint) 로 전환. 같은 dimension 내 모순 (예: 미안해요 →
    죄송합니다) 을 dedup 에서 sharp 하게 감지 가능.
    """
    if ai_draft.strip() == owner_final.strip():
        return
    try:
        import os

        from src.graph.tools.hint_dedup import (
            DIFF_HINT_SCHEMA,
            DIFF_HINT_SYSTEM,
            merge_or_append_hint,
        )
        from src.llm.upstage import complete_json_with_meta

        result, _ = complete_json_with_meta(
            prompt=f"AI 초안:\n{ai_draft}\n\n사장 최종:\n{owner_final}",
            system=DIFF_HINT_SYSTEM,
            schema=DIFF_HINT_SCHEMA,
            model=os.getenv("MODEL_DIFF_HINT", "solar-pro2"),
        )
        hint_text = (result.get("hint") or "").strip()
        if not hint_text:
            return
        dimension = result.get("dimension") or "기타"
        merge_result = merge_or_append_hint(
            place_id,
            hint_text,
            [sample_id],
            source="auto_diff",
            dimension=dimension,
        )
        action = merge_result.get("action", "append")
        reason = merge_result.get("reason", "")
        if action == "skip":
            st.caption(f"💡 힌트 중복으로 통합 안 함 ({reason})")
        elif action == "merge":
            st.caption(f"✍️ 기존 힌트와 통합됨 ({reason})")
        else:
            st.caption("💡 새 톤 힌트 추가됨")
    except Exception as e:  # noqa: BLE001
        st.caption(f"(diff hint 생성 실패: {e})")


# ============================================================================
# 리뷰 결과 카드 (기존 — trace expander 추가)
# ============================================================================


def _extract_safety_notes(node_log: list[dict] | None) -> list[str]:
    """drafter 노드 log 의 details.safety_notes 를 모아 반환. Wave 2 산출."""
    if not node_log:
        return []
    notes: list[str] = []
    for entry in node_log:
        if entry.get("kind") != "llm":
            continue
        details = entry.get("details") or {}
        for n in details.get("safety_notes") or []:
            if n and n not in notes:
                notes.append(n)
    return notes


def render_review_result(
    row: sqlite3.Row,
    reply: sqlite3.Row | None,
    *,
    node_log: list[dict] | None = None,
    trace_expanded: bool = False,
    with_trace_expander: bool = True,
    key_prefix: str = "",
) -> None:
    """리뷰 1건 카드 렌더링: 분류 + 답글 + 복사/수정 버튼 + 트레이스.

    Args:
        trace_expanded: 트레이스 기본 펼침 여부 (인라인 카드는 True 권장).
        with_trace_expander: False면 outer expander 대신 toggle 사용 (이미 outer expander 안인 경우).
        key_prefix: widget key 충돌 방지용 prefix. 같은 review를 여러 위치에서
            렌더할 때 'inline_'/'bottom_' 등으로 구분.

    Wave 3: lang_skip / classification_failed 분기 카드는 다른 비주얼로 렌더 —
    placeholder 답글을 흐리게 + 사장이 직접 답글을 작성하도록 text_area 노출.
    """
    pfx = key_prefix

    # Wave 3: 실패/스킵 카드 분기 — sentiment NULL 또는 drafter=noop
    is_failure_card = (
        row["sentiment"] is None
        or (reply is not None and reply["drafter_used"] == "noop")
    )

    # --- 분류 카드 ---
    with st.container(border=True):
        st.markdown("**🔍 분류 결과**")
        if is_failure_card:
            st.warning(
                "⚠️ 분류 실패 또는 비한국어 — 직접 답글을 작성해주세요"
            )
        cols = st.columns([1, 1, 2, 1])
        sentiment_emoji = {"positive": "😊 긍정", "negative": "😟 부정", "neutral": "😐 중립"}
        cols[0].metric("감정", sentiment_emoji.get(row["sentiment"], row["sentiment"] or "—"))
        cols[1].metric("신뢰도", f"{(row['confidence'] or 0):.2f}")
        cats = row["categories"] or "(없음)"
        cols[2].metric("카테고리", cats)
        if row["risk_flag"]:
            cols[3].warning(f"⚠️ risk: {row['risk_reason'] or 'flagged'}")

    # --- 답글 카드 ---
    if not reply:
        st.warning("답글 draft를 찾을 수 없습니다.")
        return

    # Wave 3: 실패 카드는 placeholder + 사장 직접 입력 텍스트에어리어로 분기
    if is_failure_card:
        with st.container(border=True):
            st.markdown(f"**✍️ 사장님이 직접 작성** (drafter: `{reply['drafter_used']}`)")
            st.caption("자동 생성된 placeholder — 아래에 직접 답글을 적고 저장하세요.")
            st.markdown(f":gray[{reply['draft_text']}]")

            owner_key = f"{pfx}owner_write_{reply['reply_id']}"
            owner_text = st.text_area(
                "직접 답글",
                value=reply["final_text"] or "",
                key=owner_key,
                height=120,
                label_visibility="collapsed",
                placeholder="이 리뷰에 대한 답글을 직접 작성해주세요.",
            )
            cb1, _ = st.columns([1, 5])
            if cb1.button(
                "💾 직접 답글 저장",
                key=f"{pfx}owner_save_{reply['reply_id']}",
                type="primary",
            ):
                if not (owner_text or "").strip():
                    st.error("답글을 입력해주세요.")
                else:
                    db.mark_reply_edited(reply["reply_id"], owner_text.strip())
                    st.toast("직접 답글 저장 + audit 기록")
                    st.rerun()

            if reply["copied_at"] or reply["edited_at"]:
                st.caption(
                    f"copied={reply['copied_at']}  ·  edited={reply['edited_at']}"
                )

        # trace 는 정상 카드와 동일하게 노출 (lang_skip / noop 흐름 확인용)
        if node_log is None:
            node_log = (st.session_state.get("traces") or {}).get(row["review_id"])
        if node_log:
            if with_trace_expander:
                with st.expander(
                    f"🔍 graph trace ({len(node_log)} steps)", expanded=trace_expanded
                ):
                    render_node_trace(node_log, key_prefix=f"{pfx}trace_{row['review_id']}")
            else:
                show_trace = st.toggle(
                    f"🔍 graph trace ({len(node_log)} steps)",
                    key=f"{pfx}trace_toggle_{row['review_id']}",
                    value=trace_expanded,
                )
                if show_trace:
                    render_node_trace(
                        node_log, key_prefix=f"{pfx}trace_inner_{row['review_id']}"
                    )
        return

    with st.container(border=True):
        st.markdown(f"**💬 답글 초안** (drafter: `{reply['drafter_used']}`)")

        edit_key = f"{pfx}edit_mode_{reply['reply_id']}"
        text_key = f"{pfx}edit_text_{reply['reply_id']}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False
            st.session_state[text_key] = reply["final_text"] or reply["draft_text"]

        if st.session_state[edit_key]:
            edited = st.text_area(
                "답글 수정",
                value=st.session_state[text_key],
                key=f"{pfx}textarea_{reply['reply_id']}",
                label_visibility="collapsed",
                height=120,
            )
            cb1, cb2, _ = st.columns([1, 1, 5])
            if cb1.button("💾 저장 + 톤 학습", key=f"{pfx}save_{reply['reply_id']}", type="primary"):
                # 저장 + 톤 학습 진행 패널
                panel = ProgressPanel(
                    "톤 학습 (diff hint)", action="save_tone_learn", total_steps=1
                ).start()
                panel.set_status("SQLite reply 업데이트")
                db.mark_reply_edited(reply["reply_id"], edited)
                panel.set_status("Memory Store에 톤 샘플 append")
                sid = memory.append_tone_sample(
                    row["place_id"],
                    {
                        "review_text": row["raw_text"],
                        "ai_draft": reply["draft_text"],
                        "owner_final": edited,
                        "drafter_used": reply["drafter_used"],
                        "categories": (row["categories"] or "").split(","),
                        "created_at": row["created_at"],
                        "source": "edited",
                    },
                )
                panel.set_status("Haiku 호출 — diff hint 생성 중 (~10초)")
                _diff_hint(row["place_id"], reply["draft_text"], edited, sid)
                panel.advance(1)
                panel.finish()
                st.session_state[edit_key] = False
                st.toast("답글 저장 + 톤 학습 완료 (Memory Store에 반영)")
                st.rerun()
            if cb2.button("취소", key=f"{pfx}cancel_{reply['reply_id']}"):
                st.session_state[edit_key] = False
                st.rerun()
        else:
            current = reply["final_text"] or reply["draft_text"]
            st.text_area(
                "답글",
                value=current,
                key=f"{pfx}display_{reply['reply_id']}",
                disabled=True,
                label_visibility="collapsed",
                height=120,
            )
            # Wave 3: safety_notes 가시화 — drafter 노드 log 의 details.safety_notes 에서 모음
            _safety_notes = _extract_safety_notes(
                node_log
                if node_log is not None
                else (st.session_state.get("traces") or {}).get(row["review_id"])
            )
            if _safety_notes:
                st.markdown(":orange[⚠️ 안전 필터 적용:]")
                for _note in _safety_notes:
                    st.markdown(f":orange[  · {_note}]")
            cb1, cb2, _ = st.columns([1, 1, 5])
            if cb1.button("📋 복사", key=f"{pfx}copy_{reply['reply_id']}"):
                db.mark_reply_copied(reply["reply_id"])
                memory.append_tone_sample(
                    row["place_id"],
                    {
                        "review_text": row["raw_text"],
                        "ai_draft": reply["draft_text"],
                        "owner_final": reply["draft_text"],
                        "drafter_used": reply["drafter_used"],
                        "categories": (row["categories"] or "").split(","),
                        "created_at": row["created_at"],
                        "source": "copied",
                    },
                )
                st.toast("복사됨 + 톤 샘플로 추가")
            if cb2.button("✏️ 수정", key=f"{pfx}edit_{reply['reply_id']}"):
                st.session_state[edit_key] = True
                st.rerun()

        if reply["copied_at"] or reply["edited_at"]:
            st.caption(
                f"copied={reply['copied_at']}  ·  edited={reply['edited_at']}"
            )

    # --- 트레이스 ---
    if node_log is None:
        node_log = (st.session_state.get("traces") or {}).get(row["review_id"])
    if node_log:
        if with_trace_expander:
            # 인라인 카드 — outer expander 사용 (nested 아님)
            with st.expander(
                f"🔍 graph trace ({len(node_log)} steps)", expanded=trace_expanded
            ):
                render_node_trace(node_log, key_prefix=f"{pfx}trace_{row['review_id']}")
        else:
            # 바닥 목록 — 이미 outer expander 안이라 trace 는 toggle 로 노출
            show_trace = st.toggle(
                f"🔍 graph trace ({len(node_log)} steps)",
                key=f"{pfx}trace_toggle_{row['review_id']}",
                value=trace_expanded,
            )
            if show_trace:
                render_node_trace(node_log, key_prefix=f"{pfx}trace_inner_{row['review_id']}")


# ============================================================================
# 사이드바 — 매장 메뉴 / 톤 샘플 / 사장 답글 추가 form
# ============================================================================


_SOURCE_LABELS = {
    "seed": "🌱 시드",
    "copied": "📋 복사",
    "edited": "✏️ 수정",
    "manual": "✍️ 수동 추가",
}


def render_sidebar_place_info(place_id: str) -> None:
    """사이드바에 매장 메뉴 / 톤 샘플 & 활동 통합 expander 노출.

    위치: app.py의 sidebar 안에서 호출.

    구성:
      - 🍽️ 메뉴 N개 (별도 expander)
      - 🎭 톤 샘플 & 활동 (통합 expander 안에 4 탭: 목록 / 단일 추가 / 일괄 추가 / 이력)
    """
    meta = memory.get_metadata(place_id)
    menus = meta.get("menus") or []
    samples = memory.get_tone_samples(place_id, limit=20)

    # 메뉴
    with st.expander(f"🍽️ 메뉴 {len(menus)}개", expanded=False):
        if not menus:
            st.caption("(메뉴 미입력 — Drafter 가 generic 답글 생성)")
        else:
            for m in menus:
                price = m.get("price", "?")
                price_str = f"{price:,}원" if isinstance(price, int) else str(price)
                st.markdown(f"- **{m.get('name', '?')}** · {price_str}")

    # 톤 샘플 & 활동 통합 — 3 탭 (단일/일괄 은 radio 로 통합)
    with st.expander(f"🎭 톤 샘플 & 활동 ({len(samples)})", expanded=False):
        tab_list, tab_add, tab_log = st.tabs(
            ["목록", "➕ 샘플 추가", "📜 이력"]
        )

        with tab_list:
            _render_tone_sample_list(place_id, samples)
        with tab_add:
            mode = st.radio(
                "입력 모드",
                options=["단일", "일괄"],
                horizontal=True,
                key=f"tsample_add_mode_{place_id}",
                label_visibility="collapsed",
            )
            if mode == "단일":
                _render_tone_sample_single_form(place_id)
            else:
                _render_tone_sample_batch_form(place_id)
        with tab_log:
            _render_activity_log(place_id)


def _render_tone_sample_list(place_id: str, samples: list[dict]) -> None:
    """톤 샘플 목록 — 기존 '톤 샘플 N개' expander 내용 보존."""
    if not samples:
        st.caption("(톤 샘플 없음 — '단일 추가' 또는 '일괄 추가' 탭으로 시드)")
        return
    for i, s in enumerate(samples, 1):
        src = s.get("source", "seed")
        src_label = _SOURCE_LABELS.get(src, src)
        drafter = s.get("drafter_used", "?")
        cats = ", ".join(s.get("categories") or []) or "—"
        with st.container(border=True):
            st.markdown(f"**샘플 {i}** · {src_label} · `{drafter}` · {cats}")
            review = s.get("review_text", "")
            if review:
                st.caption(f"리뷰: {review[:80]}{'…' if len(review) > 80 else ''}")
            final = s.get("owner_final") or s.get("ai_draft", "")
            if final:
                st.caption(f"답글: {final[:80]}{'…' if len(final) > 80 else ''}")


def _render_tone_sample_single_form(place_id: str) -> None:
    """단일 톤 샘플 추가 — 기존 render_add_tone_sample_form 내용을 탭 안으로 이동."""
    st.caption("과거 직접 작성하셨던 답글을 톤 샘플로 추가하면 Drafter 가 그 톤을 모방합니다.")

    with st.form(f"tsample_single_form_{place_id}", clear_on_submit=True):
        review_text = st.text_area(
            "리뷰 원문",
            key=f"tsample_single_review_{place_id}",
            height=80,
            placeholder="예: 주말에 1시간 대기는 너무하네요.",
        )
        owner_reply = st.text_area(
            "사장님 답글",
            key=f"tsample_single_reply_{place_id}",
            height=100,
            placeholder="예: 주말엔 정말 붐벼서 오래 기다리셨네요…",
        )
        cats = st.multiselect(
            "카테고리 (선택)",
            options=["맛", "서비스", "가격", "대기시간", "위생"],
            key=f"tsample_single_cats_{place_id}",
        )
        drafter_kind = st.radio(
            "답글 종류",
            options=["thanks", "apology", "neutral", "(미지정)"],
            horizontal=True,
            key=f"tsample_single_drafter_{place_id}",
            index=3,
        )
        submitted = st.form_submit_button("➕ 톤 샘플 추가", use_container_width=True)
        if submitted:
            if not review_text.strip() or not owner_reply.strip():
                st.error("리뷰와 답글을 모두 입력해주세요")
            else:
                from datetime import datetime, timezone

                sample = {
                    "review_text": review_text.strip(),
                    "ai_draft": "",  # 수동 추가 = AI 초안 없음
                    "owner_final": owner_reply.strip(),
                    "drafter_used": drafter_kind if drafter_kind != "(미지정)" else "",
                    "categories": cats,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "manual",
                }
                memory.append_tone_sample(place_id, sample)
                st.success("톤 샘플 추가됨")
                st.rerun()


# --- 일괄 입력 파서 (Excel/CSV/블록) ---------------------------------------


_MIN_LEN = 3
_MAX_LEN = 800


def _parse_block(text: str) -> list[tuple[str, str]]:
    """리뷰:/답글: 블록. 빈 줄로 블록 구분, multi-line 본문 지원."""
    blocks = re.split(r'\n\s*\n', text.strip())
    out: list[tuple[str, str]] = []
    for block in blocks:
        m_review = re.search(
            r'리뷰\s*:\s*(.+?)(?=\n\s*답글\s*:|$)',
            block, re.DOTALL,
        )
        m_reply = re.search(r'답글\s*:\s*(.+)$', block, re.DOTALL)
        if m_review and m_reply:
            r = m_review.group(1).strip()
            p = m_reply.group(1).strip()
            if r and p:
                out.append((r, p))
    return out


def _parse_tabular(text: str, delim: str) -> list[tuple[str, str]]:
    """줄 단위 delim split (첫 occurrence 만 — 답글에 delim 포함 가능)."""
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        # 헤더 추정 행 스킵
        if line.strip().lower() in ("리뷰,답글", "review,reply", "리뷰\t답글", "review\treply"):
            continue
        parts = line.split(delim, 1)
        if len(parts) == 2:
            r, p = parts[0].strip(), parts[1].strip()
            if r and p:
                out.append((r, p))
    return out


def _parse_tone_sample_batch(text: str, fmt: str) -> list[tuple[str, str]]:
    """일괄 입력 파서. 길이 필터(_MIN_LEN ≤ len ≤ _MAX_LEN) 적용.

    auto-detect 우선순위:
      1. '리뷰:' 또는 '리뷰 :' 포함 → 블록
      2. TAB 문자 포함 → TSV
      3. fallback → CSV
    """
    text = (text or "").strip()
    if not text:
        return []
    if fmt == "블록":
        pairs = _parse_block(text)
    elif fmt == "TSV":
        pairs = _parse_tabular(text, "\t")
    elif fmt == "CSV":
        pairs = _parse_tabular(text, ",")
    else:
        # 자동 감지
        if "리뷰:" in text or "리뷰 :" in text:
            pairs = _parse_block(text)
        elif "\t" in text:
            pairs = _parse_tabular(text, "\t")
        else:
            pairs = _parse_tabular(text, ",")

    # 길이 필터
    return [
        (r, p) for r, p in pairs
        if _MIN_LEN <= len(r) <= _MAX_LEN and _MIN_LEN <= len(p) <= _MAX_LEN
    ]


def _count_raw_pairs(text: str, fmt: str) -> int:
    """필터 전 raw pair 수 — '몇 건 제외됨' 계산용."""
    text = (text or "").strip()
    if not text:
        return 0
    if fmt == "블록":
        return len(_parse_block(text))
    if fmt == "TSV":
        return len(_parse_tabular(text, "\t"))
    if fmt == "CSV":
        return len(_parse_tabular(text, ","))
    # auto
    if "리뷰:" in text or "리뷰 :" in text:
        return len(_parse_block(text))
    if "\t" in text:
        return len(_parse_tabular(text, "\t"))
    return len(_parse_tabular(text, ","))


def _render_tone_sample_batch_form(place_id: str) -> None:
    """일괄 톤 샘플 추가 — Excel 복사·블록·CSV 형식 paste 지원."""
    st.caption(
        "Excel/메모장에서 복사한 리뷰·답글 묶음을 한 번에 추가합니다."
    )

    selected_format = st.selectbox(
        "형식",
        ["자동 감지", "블록", "TSV", "CSV"],
        key=f"tsample_batch_format_{place_id}",
    )
    drafter_kind = st.selectbox(
        "답글 종류 (전체 적용)",
        ["neutral", "thanks", "apology", "(미지정)"],
        key=f"tsample_batch_drafter_{place_id}",
    )

    placeholder = (
        "예 (블록):\n"
        "리뷰: 음식이 정말 맛있었어요\n"
        "답글: 감사합니다 또 들러주세요!\n"
        "\n"
        "리뷰: 너무 짰어요\n"
        "답글: 죄송합니다, 간을 다시 점검하겠습니다.\n"
    )
    raw_text = st.text_area(
        "일괄 입력",
        height=240,
        placeholder=placeholder,
        key=f"tsample_batch_text_{place_id}",
    )

    with st.container(border=True):
        st.caption(
            "**형식 도움말**  \n"
            "• 블록: '리뷰: …\\n답글: …' 블록을 빈 줄로 구분 (multi-line 가능)  \n"
            "• TSV: 한 줄에 '리뷰<TAB>답글' (Excel 2열 복사 그대로)  \n"
            "• CSV: '리뷰,답글' — 첫 쉼표만 split (답글에 쉼표 포함 가능)"
        )

    pairs = _parse_tone_sample_batch(raw_text, selected_format)
    raw_count = _count_raw_pairs(raw_text, selected_format)
    skipped = raw_count - len(pairs)

    if pairs:
        st.caption(f"✓ {len(pairs)}건 인식됨")
        if skipped > 0:
            st.caption(f"⚠️ 너무 짧거나 긴 {skipped}건 제외됨")
        with st.container(border=True):
            for review, reply in pairs[:3]:
                st.caption(f"리뷰: {review[:50]}{'…' if len(review) > 50 else ''}")
                st.caption(f"답글: {reply[:50]}{'…' if len(reply) > 50 else ''}")
                st.divider()
            if len(pairs) > 3:
                st.caption(f"… 외 {len(pairs) - 3}건")
    elif raw_text.strip():
        st.warning("형식을 인식하지 못했습니다. 도움말 참고.")

    submit_label = f"➕ {len(pairs)}건 일괄 추가" if pairs else "➕ 일괄 추가"
    if st.button(
        submit_label,
        key=f"tsample_batch_submit_{place_id}",
        disabled=not pairs,
        use_container_width=True,
    ):
        from datetime import datetime, timezone

        n = 0
        for review, reply in pairs:
            sample = {
                "review_text": review,
                "ai_draft": "",
                "owner_final": reply,
                "drafter_used": drafter_kind if drafter_kind != "(미지정)" else "",
                "categories": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "manual",
            }
            memory.append_tone_sample(place_id, sample)
            n += 1
        st.success(f"{n}건 톤 샘플 추가됨")
        st.rerun()


def _render_activity_log(place_id: str) -> None:
    """사장 수정 활동 audit log — pill 필터 + 최근 20건."""
    selected_types = st.pills(
        "이벤트 필터",
        options=["copy", "edit", "manual_add", "diff_hint_generated"],
        selection_mode="multi",
        default=[],
        key=f"activity_filter_{place_id}",
    )
    events = db.list_feedback_events(place_id, limit=20)
    if selected_types:
        events = [ev for ev in events if ev["event_type"] in selected_types]

    if not events:
        st.caption("아직 기록된 수정 이력이 없습니다.")
        return

    _icons = {
        "copy": "📋",
        "edit": "✏️",
        "manual_add": "➕",
        "diff_hint_generated": "💡",
    }
    for ev in events:
        icon = _icons.get(ev["event_type"], "•")
        st.caption(f"{icon} `{ev['event_type']}` — {ev['created_at']}")
        if ev["before_text"]:
            st.caption(f"  before: {ev['before_text'][:60]}…")
        if ev["after_text"]:
            st.caption(f"  after: {ev['after_text'][:60]}…")


# ============================================================================
# 톤 힌트 CRUD (Wave 4) — 사이드바 expander
# ============================================================================


_HINT_SOURCE_BADGES = {
    "auto_diff": ":blue[📌 auto_diff]",
    "manual": ":green[📌 manual]",
    "merged": ":orange[📌 merged]",
}


def render_tone_hints_crud(place_id: str, *, key_prefix: str = "hint_crud_") -> None:
    """톤 힌트 CRUD — 목록 + 편집/삭제/직접 추가. 모두 dedup pipeline 경유.

    Args:
        key_prefix: Streamlit widget key 충돌 방지용 prefix.
    """
    with st.expander("🎨 톤 힌트 관리", expanded=False):
        hints = memory.list_feedback_with_meta(place_id, limit=20)

        if not hints:
            st.caption("아직 톤 힌트가 없습니다.")
        else:
            for i, h in enumerate(hints):
                fid = h["fid"]
                source = h.get("source", "auto_diff")
                badge = _HINT_SOURCE_BADGES.get(source, f":gray[📌 {source}]")
                created = (h.get("created_at") or "")[:10] or "-"

                edit_key = f"{key_prefix}edit_{fid}"
                text_key = f"{key_prefix}text_{fid}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False

                with st.container(border=True):
                    st.markdown(f"{badge} · {created}")
                    if st.session_state[edit_key]:
                        new_val = st.text_area(
                            "톤 힌트 편집",
                            value=st.session_state.get(text_key, h["diff_hint"]),
                            key=f"{key_prefix}area_{fid}",
                            height=70,
                            label_visibility="collapsed",
                        )
                        cb1, cb2 = st.columns(2)
                        if cb1.button(
                            "💾 저장",
                            key=f"{key_prefix}save_{fid}",
                            use_container_width=True,
                            type="primary",
                        ):
                            if (new_val or "").strip():
                                memory.update_feedback(place_id, fid, new_val.strip())
                                st.session_state[edit_key] = False
                                st.toast("힌트 갱신 완료")
                                st.rerun()
                            else:
                                st.error("빈 힌트는 저장할 수 없습니다.")
                        if cb2.button(
                            "취소",
                            key=f"{key_prefix}cancel_{fid}",
                            use_container_width=True,
                        ):
                            st.session_state[edit_key] = False
                            st.rerun()
                    else:
                        st.markdown(f"- {h['diff_hint']}")
                        cb1, cb2 = st.columns(2)
                        if cb1.button(
                            "📝 편집",
                            key=f"{key_prefix}edit_btn_{fid}",
                            use_container_width=True,
                        ):
                            st.session_state[edit_key] = True
                            st.session_state[text_key] = h["diff_hint"]
                            st.rerun()
                        if cb2.button(
                            "🗑️ 삭제",
                            key=f"{key_prefix}del_{fid}",
                            use_container_width=True,
                        ):
                            memory.delete_feedback(place_id, fid)
                            st.toast("힌트 삭제됨")
                            st.rerun()

        st.divider()
        # 직접 추가 form
        add_key = f"{key_prefix}new_text_{place_id}"
        new_text = st.text_input(
            "새 톤 힌트 직접 추가",
            placeholder="예: 더 친근하고 가벼운 어투",
            max_chars=80,
            key=add_key,
        )
        if st.button(
            "➕ 추가", key=f"{key_prefix}add_btn_{place_id}", use_container_width=True
        ):
            if not (new_text or "").strip():
                st.error("힌트를 입력해주세요.")
            else:
                from src.graph.tools.hint_dedup import merge_or_append_hint

                result = merge_or_append_hint(
                    place_id, new_text.strip(), [], source="manual"
                )
                action = result.get("action")
                reason = result.get("reason", "")
                if action == "skip":
                    st.caption(f"💡 힌트 중복으로 통합 안 함 ({reason})")
                elif action == "merge":
                    st.caption(f"✍️ 기존 힌트와 통합됨 ({reason})")
                else:
                    st.caption("💡 새 톤 힌트 추가됨")
                st.rerun()
