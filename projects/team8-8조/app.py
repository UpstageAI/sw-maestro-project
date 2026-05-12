from __future__ import annotations

import streamlit as st

from daily_news_agent.ai_client import DemoAIClient, UpstageAIClient
from daily_news_agent.config import Settings
from daily_news_agent.mail_sender import SMTPMailClient, build_briefing_email_payload
from daily_news_agent.models import BriefingResult
from daily_news_agent.naver_news import NaverNewsClient
from daily_news_agent.news_source import GoogleNewsRssClient, NewsRouter
from daily_news_agent.vector_store import ChromaArticleStore
from daily_news_agent.workflow import DailyNewsWorkflow


def create_ai_client(settings: Settings) -> DemoAIClient | UpstageAIClient:
    if not settings.upstage_api_key:
        return DemoAIClient()
    return UpstageAIClient(
        api_key=settings.upstage_api_key,
        base_url=settings.upstage_base_url,
        chat_model=settings.upstage_chat_model,
        document_embedding_model=settings.upstage_document_embedding_model,
        query_embedding_model=settings.upstage_query_embedding_model,
    )


def create_naver_client(settings: Settings) -> NaverNewsClient | None:
    if not settings.naver_client_id or not settings.naver_client_secret:
        return None
    return NaverNewsClient(
        client_id=settings.naver_client_id,
        client_secret=settings.naver_client_secret,
        timeout_seconds=settings.request_timeout_seconds,
    )


def create_news_router(settings: Settings) -> NewsRouter:
    return NewsRouter(
        google_client=GoogleNewsRssClient(timeout_seconds=settings.request_timeout_seconds),
        naver_client=create_naver_client(settings),
    )


def create_workflow(settings: Settings) -> DailyNewsWorkflow:
    return DailyNewsWorkflow(
        news_router=create_news_router(settings),
        vector_store=ChromaArticleStore(
            path=settings.chroma_path,
            collection_name=settings.chroma_collection_name,
        ),
        ai_client=create_ai_client(settings),
    )


def create_mail_client(settings: Settings) -> SMTPMailClient:
    return SMTPMailClient(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        use_ssl=settings.smtp_use_ssl,
        timeout_seconds=settings.request_timeout_seconds,
    )


def send_briefing_email(settings: Settings, briefing_result: BriefingResult, recipient: str) -> None:
    settings.validate_mail_settings()
    payload = build_briefing_email_payload(
        briefing_result=briefing_result,
        sender=settings.email_from,
        recipient=recipient,
    )
    create_mail_client(settings).send(payload)


def render_briefing_result(result: BriefingResult) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("검색 키워드", len(result.keywords))
    col2.metric("정제된 기사", result.collected_count)
    col3.metric("새로 저장", result.stored_count)
    col4.metric("이미 저장됨", result.skipped_existing_count)

    if result.errors:
        st.warning("\n".join(result.errors))

    st.subheader("생성된 브리핑")
    st.markdown(result.briefing_markdown)

    st.subheader("선별된 기사")
    for article in result.selected_articles:
        with st.expander(article.title):
            st.write(article.summary or "요약 없음")
            st.write(f"출처: {article.source}")
            st.write(f"발행일: {article.published_at or '알 수 없음'}")
            st.write(f"키워드: {article.keyword}")
            if article.tags:
                st.write("태그: " + "  ".join(f"`#{tag}`" for tag in article.tags))
            st.link_button("원문 열기", article.link)


def render_collection_ready_state() -> None:
    result = st.session_state["collection_result"]
    st.success("뉴스 수집 및 저장이 완료되었습니다. 브리핑 생성 버튼을 누를 수 있습니다.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("검색 키워드", len(result.keywords))
    col2.metric("정제된 기사", result.collected_count)
    col3.metric("새로 저장", result.stored_count)
    col4.metric("이미 저장됨", result.skipped_existing_count)

    st.caption(f"수집 키워드: {', '.join(result.keywords)}")
    if result.errors:
        st.warning("\n".join(result.errors))


def render_subscription_section(settings: Settings) -> None:
    st.divider()
    st.subheader("메일로 뉴스 받기")
    st.caption("현재 화면에서 생성한 브리핑 결과를 메일로 전송합니다.")

    default_recipient = st.session_state.get("subscription_email", settings.email_to_default)
    recipient = st.text_input(
        "수신자 이메일",
        value=default_recipient,
        key="subscription_email",
        placeholder="recipient@example.com",
    )
    has_briefing = "briefing_result" in st.session_state

    if st.button(
        "전송하기",
        use_container_width=True,
        disabled=not has_briefing,
        help=None if has_briefing else "브리핑을 먼저 생성해 주세요.",
    ):
        try:
            if not recipient.strip():
                raise ValueError("수신자 이메일을 입력해 주세요.")
            send_briefing_email(settings, st.session_state["briefing_result"], recipient.strip())
            st.success(f"{recipient.strip()} 주소로 브리핑 메일을 보냈습니다.")
        except Exception as exc:
            st.error(str(exc))


def main() -> None:
    settings = Settings.from_env()

    st.set_page_config(page_title="Daily News Agent", layout="wide")
    st.title("Daily News Agent")
    st.caption("관심 분야를 입력하면 Google News RSS에서 하루치 뉴스를 모아 로컬 Vector DB에 저장하고 브리핑을 생성합니다.")

    with st.sidebar:
        st.subheader("실행 설정")
        st.write(f"AI 모드: {'Upstage' if settings.upstage_api_key else 'Demo'}")
        naver_enabled = bool(settings.naver_client_id and settings.naver_client_secret)
        st.write(f"뉴스 소스: {'Naver(한글) + Google' if naver_enabled else 'Google only'}")
        st.write(f"Vector DB: `{settings.chroma_path}`")
        st.write(f"Collection: `{settings.chroma_collection_name}`")
        per_keyword_limit = st.number_input(
            "키워드별 수집 기사 수",
            min_value=3,
            max_value=20,
            value=settings.per_keyword_limit,
            step=1,
        )
        top_k = st.number_input("요약에 사용할 기사 수", min_value=3, max_value=12, value=settings.top_k, step=1)

    interest = st.text_input("관심 분야", value="AI 산업 동향")
    keyword_text = st.text_input("검색 키워드 3개", value="AI, 반도체, 스타트업")
    input_signature = (interest, keyword_text)

    collect_col, briefing_col = st.columns(2)
    with collect_col:
        collect_clicked = st.button("뉴스 수집 및 저장", type="primary", use_container_width=True)
    with briefing_col:
        has_collection = (
            "collection_result" in st.session_state
            and st.session_state.get("collection_signature") == input_signature
        )
        briefing_button_label = "브리핑 생성 가능" if has_collection else "브리핑 생성"
        briefing_clicked = st.button(
            briefing_button_label,
            disabled=not has_collection,
            use_container_width=True,
            help=None if has_collection else "뉴스 수집 및 저장을 먼저 완료해야 합니다.",
        )

    if has_collection and "briefing_result" not in st.session_state:
        render_collection_ready_state()
    elif not has_collection:
        if "collection_result" in st.session_state:
            st.warning("입력값이 바뀌었습니다. 현재 관심 분야와 키워드로 다시 수집해야 브리핑을 생성할 수 있습니다.")
        else:
            st.info("먼저 뉴스를 수집하고 Vector DB에 저장한 뒤 브리핑을 생성할 수 있습니다.")

    if collect_clicked:
        try:
            workflow = create_workflow(settings)
            with st.status("뉴스 수집 및 저장", expanded=True) as status:
                result = workflow.collect_and_store(
                    interest=interest,
                    keyword_text=keyword_text,
                    per_keyword_limit=int(per_keyword_limit),
                    progress=status.write,
                )
                status.update(label="뉴스 수집 및 저장 완료", state="complete")

            st.session_state["collection_result"] = result
            st.session_state["collection_signature"] = input_signature
            st.session_state.pop("briefing_result", None)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if briefing_clicked:
        try:
            workflow = create_workflow(settings)
            collection_result = st.session_state["collection_result"]
            with st.status("브리핑 생성", expanded=True) as status:
                briefing_result = workflow.generate_briefing(
                    interest=collection_result.interest,
                    keywords=collection_result.keywords,
                    top_k=int(top_k),
                    fallback_articles=collection_result.collected_articles,
                    collected_count=collection_result.collected_count,
                    stored_count=collection_result.stored_count,
                    skipped_existing_count=collection_result.skipped_existing_count,
                    errors=collection_result.errors,
                    progress=status.write,
                )
                status.update(label="브리핑 생성 완료", state="complete")
            st.session_state["briefing_result"] = briefing_result
        except Exception as exc:
            st.error(str(exc))

    if "briefing_result" in st.session_state:
        render_briefing_result(st.session_state["briefing_result"])

    render_subscription_section(settings)


if __name__ == "__main__":
    main()
