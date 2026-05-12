from __future__ import annotations

import os

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI 주식 리포트", layout="wide")
st.title("📊 AI 주식 리포트 생성 서비스")
st.caption("한국투자증권 API · LangGraph 멀티 에이전트 · Upstage Solar")

if "summary" not in st.session_state:
    st.session_state.summary = None
    st.session_state.report = ""
    st.session_state.symbol = ""
    st.session_state.data_source = "live"
    st.session_state.fetch_status = {}
    st.session_state.fallback_reason = ""
    st.session_state.history: list[dict] = []
    st.session_state.report_trace: list[dict] = []

if "chat_input_version" not in st.session_state:
    st.session_state.chat_input_version = 0

if "report_trace" not in st.session_state:
    st.session_state.report_trace = []

if st.session_state.history and isinstance(st.session_state.history[0], tuple):
    st.session_state.history = [
        {"role": r, "content": c} for r, c in st.session_state.history
    ]


def _request_json(method: str, path: str, **kwargs) -> dict:
    url = f"{API_BASE}{path}"
    try:
        resp = httpx.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text.strip()
        raise RuntimeError(
            f"{e.response.status_code} {e.response.reason_phrase}"
            + (f"\n{detail}" if detail else "")
        ) from e


def _chat_history_payload() -> list[dict[str, str]]:
    return [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.history[-12:]
        if m.get("role") in {"user", "assistant"} and m.get("content")
    ]


def _render_trace(events: list[dict]) -> None:
    if not events:
        st.caption("표시할 추적 이벤트가 없습니다.")
        return
    rows = []
    for ev in events:
        info = ev.get("info") or {}
        info_str = ", ".join(f"{k}={v}" for k, v in info.items() if v != "" and v != {})
        rows.append(
            {
                "step": ev.get("step", ""),
                "status": ev.get("status", ""),
                "elapsed_ms": ev.get("elapsed_ms", 0),
                "info": info_str,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

with st.sidebar:
    st.subheader("종목 선택")
    symbol = st.text_input("종목 코드", value="005930", help="예: 005930 (삼성전자)")
    if st.button("리포트 생성", use_container_width=True, type="primary"):
        with st.spinner("데이터 수집 및 리포트 생성 중..."):
            try:
                data = _request_json(
                    "POST",
                    "/report",
                    json={"symbol": symbol.strip()},
                    timeout=180.0,
                )
                st.session_state.symbol = symbol.strip()
                st.session_state.summary = data.get("summary", {})
                st.session_state.report = data.get("report", "")
                st.session_state.data_source = data.get("data_source", "live")
                st.session_state.fetch_status = data.get("fetch_status", {})
                st.session_state.fallback_reason = data.get("fallback_reason", "")
                st.session_state.report_trace = data.get("trace", [])
                st.session_state.history = []
                st.success("리포트 생성 완료")
            except Exception as e:
                st.error(f"리포트 생성 실패: {e}")

    st.divider()
    try:
        h = _request_json("GET", "/health", timeout=3.0)
        st.caption(
            f"Data: {h.get('data_mode', 'mock')} · "
            f"KIS: {'auth ready' if h.get('kis_auth_ready') else 'not required' if h.get('data_mode') == 'mock' else 'auth pending'} · "
            f"LLM: {'ready' if h.get('llm_ready') else 'stub'} ({h.get('model','')})"
        )
        if h.get("kis_auth_mode"):
            st.caption(f"KIS auth mode: {h.get('kis_auth_mode')}")
    except Exception:
        st.caption("⚠️ 백엔드 미연결: `uvicorn app.api:app` 실행 필요")

col_left, col_right = st.columns([3, 2])

with col_left:
    if st.session_state.summary:
        s = st.session_state.summary
        st.subheader(f"{s.get('name', '')} ({s.get('symbol', '')})")
        m1, m2, m3 = st.columns(3)
        m1.metric("현재가", f"{s.get('price', 0):,.0f}원")
        m2.metric("전일 대비", f"{s.get('change_rate', 0):+.2f}%")
        m3.metric("수집 청크", s.get("n_chunks", 0))
        data_source = st.session_state.get("data_source", s.get("data_source", "live"))
        fetch_status = st.session_state.get("fetch_status", s.get("fetch_status", {}))
        fallback_reason = st.session_state.get("fallback_reason", s.get("fallback_reason", ""))
        if data_source == "live":
            pass
        elif data_source == "mock":
            st.warning("mock 데모 데이터를 사용했습니다.")
        else:
            parts = []
            if fetch_status:
                parts.append(
                    ", ".join(
                        f"{k}:{v}" for k, v in fetch_status.items() if v
                    )
                )
            if fallback_reason:
                parts.append(fallback_reason)
            st.error(
                "시세 데이터를 확인할 수 없습니다."
                + (f" ({' | '.join(parts)})" if parts else "")
            )
        bars = s.get("bars", [])
        if bars:
            df = pd.DataFrame(bars)
            df["date"] = pd.to_datetime(df["date"])
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=df["date"],
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                    )
                ]
            )
            fig.update_layout(
                height=380,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("좌측 사이드바에서 종목 코드를 입력하고 '리포트 생성'을 누르세요.")

    if st.session_state.report:
        st.subheader("📄 투자 리포트")
        st.markdown(st.session_state.report)
        if st.session_state.report_trace:
            with st.expander("🔍 백엔드 파이프라인 추적 (LangGraph 노드)"):
                _render_trace(st.session_state.report_trace)

with col_right:
    st.subheader("💬 대화")
    with st.container(height=520, border=True):
        if st.session_state.history:
            for msg in st.session_state.history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and msg.get("trace"):
                        with st.expander("🔍 백엔드 동작"):
                            _render_trace(msg["trace"])
        else:
            st.info("리포트나 시세에 대해 질문해 보세요.")

    with st.form("chat_form", clear_on_submit=True):
        q = st.text_input(
            "질문",
            placeholder="리포트나 시세에 대해 질문하세요",
            label_visibility="collapsed",
            key=f"chat_question_{st.session_state.chat_input_version}",
        )
        submitted = st.form_submit_button("전송", use_container_width=True)

    if submitted and q:
        st.session_state.chat_input_version += 1
        history_payload = _chat_history_payload()
        st.session_state.history.append({"role": "user", "content": q})
        trace: list[dict] = []
        with st.spinner("답변 생성 중..."):
            try:
                data = _request_json(
                    "POST",
                    "/chat",
                    json={
                        "question": q,
                        "symbol": st.session_state.symbol or None,
                        "history": history_payload,
                    },
                    timeout=60.0,
                )
                ans = data.get("answer", "")
                trace = data.get("trace", []) or []
            except Exception as e:
                ans = f"오류: {e}"
        st.session_state.history.append(
            {"role": "assistant", "content": ans, "trace": trace}
        )
        st.rerun()
