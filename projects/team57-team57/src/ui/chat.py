"""채팅 UI — 사이드바 버튼 + dialog 모달 (자체 스크롤) + invoke 기반 응답.

설계
- 버튼 위치: 사이드바 (안정적) — CSS floating 회피.
- 메시지 영역: `st.container(height=N)` 자체 세로 스크롤.
- 응답: `agent.invoke()` 로 보장된 응답. 마지막 *content 가 있는* `AIMessage` 를
  안전하게 추출. token streaming 은 simulated typing 효과로 대체 (안정성 우선).
- agent 입력: welcome assistant 메시지는 *제외* — 첫 사용자 입력부터 컨텍스트 시작.
"""

from __future__ import annotations

import time

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.chat.agent import build_chat_agent
from src.store import memory


# ---------------------------------------------------------------------------
# Welcome
# ---------------------------------------------------------------------------


def _greet(place_id: str) -> str:
    meta = memory.get_metadata(place_id)
    name = meta.get("display_name", place_id)
    return (
        f"안녕하세요, **{name}** 사장님! 🌱\n\n"
        f"매장 운영을 도와드리는 비서예요. 다음을 자연어로 요청하실 수 있어요:\n\n"
        f"- 🔁 *오늘 새 리뷰 5건 분석해줘*\n"
        f"- 📊 *이번 주 반복 불만 알려줘*\n"
        f"- 🔍 *최근 부정 리뷰 3건 보여줘*\n"
        f"- 🍽️ *내 매장 메뉴랑 톤 샘플 알려줘*\n"
        f"- ✍️ *이 답글 톤 샘플로 추가해줘 — 리뷰: ... / 답글: ...*\n\n"
        f"어떤 일을 도와드릴까요?"
    )


# ---------------------------------------------------------------------------
# Message conversion (welcome 제외, user/assistant 만 LangChain 형식으로)
# ---------------------------------------------------------------------------


def _to_langchain_messages(history: list[dict]) -> list:
    """welcome 등 사용자 입력 *전* 의 assistant 메시지는 제외.
    create_react_agent 가 첫 user 메시지로 시작해야 자연스러움.
    """
    out: list = []
    seen_user = False
    for m in history:
        if not seen_user and m["role"] != "user":
            continue
        seen_user = True
        if m["role"] == "user":
            out.append(HumanMessage(content=m["content"]))
        else:
            out.append(AIMessage(content=m["content"]))
    return out


# ---------------------------------------------------------------------------
# Agent invoke + 안전한 응답 추출
# ---------------------------------------------------------------------------


def _extract_final_text(result_messages: list) -> str:
    """result['messages'] 에서 *content 가 있는 마지막 AIMessage* 를 찾아 텍스트 반환.
    create_react_agent 는 종종 (tool_calls만 있는 AIMessage → ToolMessage → 최종 AIMessage)
    순으로 누적하므로 단순 [-1] 만 보면 안 됨.
    """
    for msg in reversed(result_messages):
        cls = type(msg).__name__
        if cls in {"AIMessage", "AIMessageChunk"}:
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                content = "".join(
                    c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                )
            if isinstance(content, str) and content.strip():
                return content
    # AIMessage 가 모두 비어있으면 마지막 ToolMessage content 라도
    for msg in reversed(result_messages):
        if type(msg).__name__ == "ToolMessage":
            content = getattr(msg, "content", "")
            if isinstance(content, str) and content.strip():
                return f"(tool 결과)\n\n{content}"
    return ""


def _run_agent(place_id: str, history_msgs: list, placeholder, *, simulate_typing: bool = True) -> str:
    """agent.invoke 로 안전하게 응답 받기. typing 효과는 placeholder 갱신으로 시뮬."""
    try:
        agent = build_chat_agent(place_id)
        result = agent.invoke({"messages": history_msgs})
    except Exception as e:  # noqa: BLE001
        msg = f"오류: {e}"
        placeholder.error(msg)
        return msg

    msgs = result.get("messages", [])
    full = _extract_final_text(msgs)

    if not full:
        # 디버깅 정보 노출
        types = [type(m).__name__ for m in msgs]
        full = (
            "응답을 추출하지 못했습니다.\n\n"
            f"agent 가 반환한 메시지 타입: {types}\n"
            "tool 호출만 하고 최종 응답을 안 만든 케이스일 수 있어요. "
            "다시 시도하시거나 더 구체적으로 질문해주세요."
        )
        placeholder.warning(full)
        return full

    if simulate_typing:
        # 글자 단위로 점진 표시 (UX 보강)
        displayed = ""
        for char in full:
            displayed += char
            placeholder.markdown(displayed + "▌")
            time.sleep(0.005)  # ~5ms/char — 200 char/sec
        placeholder.markdown(full)
    else:
        placeholder.markdown(full)

    return full


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


@st.dialog("🤖 매장 비서", width="large")
def chat_dialog(place_id: str) -> None:
    """대화 모달 — 메시지 히스토리 (자체 스크롤) + 사용자 입력 + agent 응답."""
    history_key = f"chat_messages_{place_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {"role": "assistant", "content": _greet(place_id)}
        ]

    # 헤더: 매장 이름 + 새 대화 버튼
    meta = memory.get_metadata(place_id)
    header_cols = st.columns([5, 1])
    with header_cols[0]:
        st.caption(f"💼 {meta.get('display_name', place_id)} · 톤 학습 누적 활용")
    with header_cols[1]:
        if st.button("🔄 새 대화", key=f"chat_clear_{place_id}", use_container_width=True):
            st.session_state[history_key] = [
                {"role": "assistant", "content": _greet(place_id)}
            ]
            st.rerun()

    # 메시지 영역 — 고정 높이 + 자체 세로 스크롤
    msg_area = st.container(height=420)
    with msg_area:
        for msg in st.session_state[history_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 사용자 입력
    user_input = st.chat_input("무엇을 도와드릴까요?")
    if not user_input:
        return

    # 사용자 메시지 즉시 표시
    st.session_state[history_key].append({"role": "user", "content": user_input})
    with msg_area:
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            ph = st.empty()
            history_msgs = _to_langchain_messages(st.session_state[history_key])
            full = _run_agent(place_id, history_msgs, ph, simulate_typing=True)

    st.session_state[history_key].append({"role": "assistant", "content": full})
