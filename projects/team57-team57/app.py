from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.db.connection import get_database_path
from src.db.repository import ReviewAgentRepository
from src.graph import run_review_agent
from src.llm.provider import get_provider
from src.state import ReviewAgentState
from src.tools.db_tools import DEMO_STORE_NAME, initialize_demo_store_tool


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return

    load_dotenv()


def _get_repo() -> ReviewAgentRepository:
    repo = ReviewAgentRepository.from_env()
    repo.initialize()
    return repo


def _load_sample_reviews() -> dict[str, dict[str, Any]]:
    sample_path = Path("data/sample_reviews.json")
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    return {item["name"]: item for item in payload["scenarios"]}


def _get_active_store(repo: ReviewAgentRepository):
    active_store_id = st.session_state.get("active_store_id")
    if active_store_id:
        store = repo.get_store(active_store_id)
        if store is not None:
            return store
    latest_store = repo.get_latest_store()
    if latest_store is not None:
        st.session_state["active_store_id"] = latest_store.id
    return latest_store


def _parse_multiline(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _format_top_category(classified_reviews: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for review in classified_reviews:
        for category in review.get("categories", []):
            counts[category] = counts.get(category, 0) + 1
    if not counts:
        return "-"
    return max(counts.items(), key=lambda item: item[1])[0]


def _render_sidebar(repo: ReviewAgentRepository) -> None:
    store = _get_active_store(repo)

    with st.sidebar:
        st.header("매장 컨텍스트")
        if st.button("데모 모드 초기화", use_container_width=True, type="secondary"):
            demo_info = initialize_demo_store_tool(repo)
            st.session_state["active_store_id"] = demo_info["store_id"]
            st.session_state["raw_input_text"] = ""
            st.session_state.pop("last_result", None)
            st.success(
                f"{demo_info['store_name']} 매장과 과거 리뷰 {demo_info['seeded_review_count']}건을 초기화했습니다."
            )
            st.rerun()

        with st.form("store_context_form", clear_on_submit=False):
            name = st.text_input("가게명", value=store.name if store else "")
            business_type = st.text_input("업종", value=store.business_type if store else "")
            menu_items_text = st.text_area(
                "대표 메뉴 목록",
                value="\n".join(store.menu_items) if store else "",
                help="한 줄에 하나씩 입력하세요.",
                height=120,
            )
            price_range = st.text_input("가격대", value=store.price_range if store else "")
            reply_tone = st.selectbox(
                "답글 톤",
                options=["정중체", "친근체", "격식체"],
                index=["정중체", "친근체", "격식체"].index(store.reply_tone) if store else 0,
            )
            reply_samples_text = st.text_area(
                "평소 답글 샘플",
                value="\n".join(store.reply_samples) if store else "",
                help="한 줄에 하나씩 입력하세요.",
                height=160,
            )
            submitted = st.form_submit_button("매장 컨텍스트 저장", use_container_width=True)

        if submitted:
            if not name.strip() or not business_type.strip():
                st.error("가게명과 업종은 필수입니다.")
            else:
                store_id = repo.upsert_store(
                    store_id=store.id if store else None,
                    name=name.strip(),
                    business_type=business_type.strip(),
                    menu_items=_parse_multiline(menu_items_text),
                    price_range=price_range.strip(),
                    reply_tone=reply_tone,
                    reply_samples=_parse_multiline(reply_samples_text),
                )
                st.session_state["active_store_id"] = store_id
                st.session_state.pop("last_result", None)
                st.success("매장 컨텍스트를 저장했습니다.")
                st.rerun()

        if store:
            st.caption(f"현재 매장 ID: {store.id}")
            st.caption(f"DB 경로: {get_database_path()}")
            if store.name == DEMO_STORE_NAME:
                st.caption("현재 데모 매장이 활성화되어 있습니다.")

        _render_db_debug_panel(repo, store)


def _render_input_area(sample_reviews: dict[str, dict[str, Any]]) -> bool:
    st.subheader("리뷰 입력")
    if "raw_input_text" not in st.session_state:
        st.session_state["raw_input_text"] = ""

    col1, col2, col3 = st.columns([1, 1, 1.2])
    if col1.button("샘플 리뷰 A 불러오기", use_container_width=True):
        st.session_state["raw_input_text"] = "\n".join(sample_reviews["scenario_a_daily_batch"]["reviews"])
        st.rerun()
    if col2.button("샘플 리뷰 B 불러오기", use_container_width=True):
        st.session_state["raw_input_text"] = "\n".join(sample_reviews["scenario_b_weekly_followup"]["reviews"])
        st.rerun()
    analyze_clicked = col3.button("분석 시작", type="primary", use_container_width=True)

    st.text_area(
        "리뷰 여러 건을 붙여넣으세요",
        key="raw_input_text",
        height=220,
        placeholder="빈 줄 또는 줄바꿈 기준으로 여러 리뷰를 붙여넣을 수 있습니다.",
    )

    st.caption("전화번호, 이메일, 긴 숫자열은 저장 전에 자동으로 마스킹됩니다.")
    return analyze_clicked


def _run_analysis(repo: ReviewAgentRepository) -> None:
    store = _get_active_store(repo)
    raw_input_text = st.session_state.get("raw_input_text", "")

    if store is None:
        st.error("먼저 사이드바에서 매장 컨텍스트를 저장해 주세요.")
        return
    if not raw_input_text.strip():
        st.error("분석할 리뷰를 입력해 주세요.")
        return

    provider = get_provider()
    state = ReviewAgentState(
        store_id=store.id,
        raw_input_text=raw_input_text,
    )
    result = run_review_agent(repo=repo, provider=provider, state=state)
    st.session_state["last_result"] = result
    st.session_state["last_provider_name"] = provider.provider_name


def _render_summary(result: ReviewAgentState) -> None:
    sentiments = [review.get("sentiment") for review in result.classified_reviews]
    total_count = len(result.classified_reviews)
    positive_count = sum(sentiment == "긍정" for sentiment in sentiments)
    neutral_count = sum(sentiment == "중립" for sentiment in sentiments)
    negative_count = sum(sentiment == "부정" for sentiment in sentiments)
    top_category = _format_top_category(result.classified_reviews)

    st.subheader("요약")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 리뷰 수", total_count)
    c2.metric("긍정 / 중립 / 부정", f"{positive_count} / {neutral_count} / {negative_count}")
    c3.metric("최다 카테고리", top_category)
    c4.metric("저장된 리뷰", len(result.saved_review_ids))


def _extract_node_name(log_line: str) -> str:
    return log_line.split(":", 1)[0]


def _render_execution_flow(result: ReviewAgentState) -> None:
    st.subheader("Agent 실행 흐름")
    node_logs = [line for line in result.execution_log if "Node" in line or "Graph" in line]
    if node_logs:
        flow = " → ".join(_extract_node_name(line) for line in node_logs)
        st.markdown(f"**Node Flow**  \n`{flow}`")
        columns = st.columns(len(node_logs))
        for column, line in zip(columns, node_logs):
            column.success(_extract_node_name(line))
            column.caption(line)

    for index, line in enumerate(result.execution_log, start=1):
        st.write(f"{index}. {line}")


def _save_reply_feedback(repo: ReviewAgentRepository, review_id: int, edited_reply: str, selected_reply: str | None) -> None:
    review = repo.get_review(review_id)
    before_reply = review.edited_reply if review and review.edited_reply else (review.selected_reply if review else "")
    repo.update_review_feedback(
        review_id=review_id,
        edited_reply=edited_reply,
        selected_reply=selected_reply,
        status="feedback_saved",
    )
    repo.create_feedback_event(
        store_id=st.session_state["active_store_id"],
        review_id=review_id,
        feedback_type="edited_reply",
        before_value=before_reply,
        after_value=edited_reply,
    )


def _render_db_debug_panel(repo: ReviewAgentRepository, store: Any | None) -> None:
    with st.expander("개발자 확인용 DB 상태", expanded=False):
        st.markdown("**현재 활성 매장 기준**")
        if store is None:
            st.caption("현재 활성화된 매장이 없습니다.")
        else:
            st.caption(f"매장: {store.name} (store_id={store.id})")
            c1, c2, c3 = st.columns(3)
            c1.metric("이 매장 reviews", repo.count_reviews_by_store(store.id))
            c2.metric("이 매장 feedback", repo.count_feedback_events_by_store(store.id))
            c3.metric("전체 stores", repo.count_stores())

        st.markdown("**최근 저장된 리뷰 5건 - 현재 매장 기준**")
        recent_reviews = repo.list_recent_reviews_by_store(store.id, limit=5) if store else []
        if not recent_reviews:
            st.caption("현재 매장 기준 저장된 리뷰가 없습니다.")
        for review in recent_reviews:
            st.write(
                f"- review_id={review.id} sentiment={review.sentiment} "
                f"categories={', '.join(review.categories) or '-'} text={review.masked_text[:50]}"
            )

        st.markdown("**최근 feedback 5건 - 현재 매장 기준**")
        recent_feedback = repo.list_recent_feedback_events_by_store(store.id, limit=5) if store else []
        if not recent_feedback:
            st.caption("현재 매장 기준 저장된 feedback이 없습니다.")
        for event in recent_feedback:
            st.write(
                f"- feedback_id={event.id} review_id={event.review_id} type={event.feedback_type} "
                f"after={event.after_value[:50] if event.after_value else '-'}"
            )

        st.markdown("**전체 DB 참고 수치**")
        g1, g2 = st.columns(2)
        g1.metric("전체 reviews", repo.count_reviews())
        g2.metric("전체 feedback_events", repo.count_feedback_events())


def _render_review_results(repo: ReviewAgentRepository, result: ReviewAgentState) -> None:
    st.subheader("리뷰별 결과")

    for index, review in enumerate(result.classified_reviews):
        review_id = result.saved_review_ids[index] if index < len(result.saved_review_ids) else None
        drafted = result.drafted_replies[index] if index < len(result.drafted_replies) else {"replies": []}
        persisted = repo.get_review(review_id) if review_id else None
        selected_reply = persisted.selected_reply if persisted else None
        default_reply = (
            persisted.edited_reply
            if persisted and persisted.edited_reply
            else selected_reply
            or (drafted.get("replies") or [""])[0]
        )

        with st.container(border=True):
            st.markdown(f"**리뷰 {index + 1}**")
            st.write(review.get("original_text", ""))

            meta1, meta2, meta3 = st.columns([1, 2, 2])
            meta1.write(f"감정: {review.get('sentiment') or '-'}")
            meta2.write(f"카테고리: {', '.join(review.get('categories', [])) or '-'}")
            meta3.write(f"메뉴 태그: {', '.join(review.get('menu_tags', [])) or '-'}")

            replies = drafted.get("replies", []) or [""]
            radio_key = f"selected_reply_{review_id}_{index}"
            textarea_key = f"edited_reply_{review_id}_{index}"

            default_radio_index = 0
            if selected_reply and selected_reply in replies:
                default_radio_index = replies.index(selected_reply)

            selected_candidate = st.radio(
                "답글 초안 선택",
                options=replies,
                index=default_radio_index,
                key=radio_key,
                format_func=lambda value: value if value else "(초안 없음)",
            )
            edited_reply = st.text_area(
                "수정 답글",
                value=default_reply,
                key=textarea_key,
                height=120,
            )

            save_clicked = st.button("수정 답글 저장", key=f"save_feedback_{review_id}_{index}")
            if save_clicked and review_id:
                if not edited_reply.strip():
                    st.warning("수정 답글이 비어 있습니다.")
                else:
                    _save_reply_feedback(repo, review_id, edited_reply.strip(), selected_candidate)
                    st.session_state["feedback_saved_notice"] = (
                        "수정 답글이 저장되었습니다. 다음 분석 시 최근 수정 답글 샘플로 반영됩니다."
                    )
                    st.rerun()


def _render_patterns_and_checklist(result: ReviewAgentState) -> None:
    left, right = st.columns(2)

    with left:
        st.subheader("반복 불만 TOP 3")
        pattern_summary = result.pattern_summary or {}
        if not pattern_summary.get("enabled"):
            st.info(pattern_summary.get("message", "누적 데이터가 부족합니다"))
        else:
            for item in pattern_summary.get("top_categories", [])[:3]:
                st.write(f"- {item['name']}: {item['count']}건")
            top_keywords = pattern_summary.get("top_keywords", [])
            if top_keywords:
                st.caption(
                    "키워드: " + ", ".join(f"{item['name']}({item['count']})" for item in top_keywords[:5])
                )

    with right:
        st.subheader("개선 체크리스트")
        for item in result.checklist:
            st.write(f"- {item}")


def _render_warnings_and_errors(result: ReviewAgentState) -> None:
    if result.warnings:
        with st.expander("Warnings", expanded=False):
            for warning in result.warnings:
                st.write(f"- {warning}")
    if result.errors:
        with st.expander("Errors", expanded=True):
            for error in result.errors:
                st.write(f"- {error}")


def _render_backend_log_panel(result: ReviewAgentState) -> None:
    st.subheader("백엔드 실행 로그")
    if not result.backend_logs:
        st.info("표시할 백엔드 실행 로그가 없습니다.")
        return

    for item in result.backend_logs:
        status_bits = []
        status_bits.append("DB 저장" if item["db_saved"] else "DB 저장 없음")
        if item["has_warning"]:
            status_bits.append("경고 있음")
        if item["has_error"]:
            status_bits.append("에러 있음")

        with st.container(border=True):
            st.markdown(f"**{item['node_name']}**  ")
            st.caption(f"실행 시간: {item['executed_at']} | {' | '.join(status_bits)}")
            st.write(f"입력 요약: {item['input_summary']}")
            st.write(f"출력 요약: {item['output_summary']}")


def main() -> None:
    _load_env()
    st.set_page_config(
        page_title="리뷰 응대 및 반복 불만 분석 AI Agent",
        page_icon="📝",
        layout="wide",
    )
    st.title("소상공인 리뷰 응대 및 반복 불만 분석 AI Agent")
    st.caption("Mock LLM 기반으로 API 키 없이도 전체 Agent 플로우를 데모할 수 있습니다.")

    repo = _get_repo()
    sample_reviews = _load_sample_reviews()
    _render_sidebar(repo)

    analyze_clicked = _render_input_area(sample_reviews)
    if analyze_clicked:
        _run_analysis(repo)

    result: ReviewAgentState | None = st.session_state.get("last_result")
    if result is None:
        st.info("사이드바에서 매장 정보를 저장한 뒤 샘플 리뷰를 불러오거나 직접 입력해서 분석을 시작해 주세요.")
        return

    provider_name = st.session_state.get("last_provider_name", "mock")
    st.caption(f"최근 실행 Provider: {provider_name}")
    store = _get_active_store(repo)
    if store is not None:
        recent_feedback_count = len(repo.list_recent_edited_replies(store.id, limit=5))
        st.caption(f"최근 수정 답글 샘플 반영 수: {recent_feedback_count}")
    if st.session_state.get("feedback_saved_notice"):
        st.info(st.session_state["feedback_saved_notice"])
    _render_summary(result)
    _render_patterns_and_checklist(result)
    _render_review_results(repo, result)
    _render_execution_flow(result)
    _render_backend_log_panel(result)
    _render_warnings_and_errors(result)


if __name__ == "__main__":
    main()
