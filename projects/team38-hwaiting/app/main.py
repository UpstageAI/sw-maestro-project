"""Streamlit 챗봇 엔트리 (PRD US-007 / US-014~US-016 / FR-21~FR-26)."""
from __future__ import annotations

import sys
from pathlib import Path

# Windows 한국어 환경의 기본 stdout 인코딩(cp949) 이 em-dash 등 일부 BMP 문자를
# 인코딩하지 못해 print() 가 UnicodeEncodeError 를 내는 문제 보정.
# Python 3.7+ TextIOWrapper.reconfigure 사용. import 직후 실행돼야 langchain/
# langgraph 내부 print 까지 커버한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from app.ui_components import render_results, render_sidebar  # noqa: E402
from graph.build import build_graph  # noqa: E402
from graph.state import initial_state  # noqa: E402

st.set_page_config(page_title="노트북 추천 챗봇", layout="wide")
st.title("💻 노트북 추천 챗봇")
st.caption("9가지 조건을 자연스럽게 알려주시면 다나와 데이터에서 5개까지 추천해드려요.")


@st.cache_resource(show_spinner=False)
def _get_graph():
    return build_graph()


def _reset_session() -> None:
    st.session_state.clear()
    st.rerun()


def _ensure_state() -> None:
    if "chat_state" not in st.session_state:
        st.session_state["chat_state"] = initial_state()


def _render_messages(state) -> None:
    for m in state.get("messages") or []:
        if isinstance(m, HumanMessage):
            role = "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        else:
            continue
        with st.chat_message(role):
            st.markdown(str(m.content))


def main() -> None:
    _ensure_state()
    state = st.session_state["chat_state"]

    render_sidebar(state, on_reset=_reset_session)
    _render_messages(state)

    if state.get("candidates"):
        render_results(state["candidates"])

    prompt = st.chat_input("어떤 노트북을 찾으세요?")
    if not prompt:
        return

    state["messages"] = (state.get("messages") or []) + [HumanMessage(content=prompt)]
    state["candidates"] = []
    state["sql_clause"] = None
    state["final_answer"] = None

    graph = _get_graph()
    with st.spinner("생각 중..."):
        try:
            new_state = graph.invoke(state)
        except Exception as e:  # noqa: BLE001
            st.error(f"그래프 실행 중 오류: {e}")
            return

    st.session_state["chat_state"] = new_state
    st.rerun()


main()
