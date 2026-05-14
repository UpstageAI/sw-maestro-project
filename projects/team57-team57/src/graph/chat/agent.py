"""Chat agent — `langgraph.prebuilt.create_react_agent` + Solar Pro 2 + 5 tools.

매장별로 별도 agent 를 만들어 closure 로 place_id 주입. tool 호출/응답 루프는
LangGraph 의 prebuilt ReAct 패턴이 자동 처리.
"""

from __future__ import annotations

import os

from src.graph.chat.tools import make_chat_tools
from src.llm.upstage import _is_mock_mode
from src.llm.upstage_chat import _MockChatAgent


_SYSTEM = (
    "당신은 소상공인 사장님의 매장 운영을 돕는 한국어 비서입니다. 친근체 존댓말. "
    "사장님 요청에 맞게 다음 5개 tool 중 적절한 것을 호출하세요:\n"
    "- analyze_new_reviews(n): 미처리 리뷰 N건을 LangGraph main graph 로 분석\n"
    "- get_top_complaints(): 최근 4주 부정 카테고리 TOP 3 + 점검 체크리스트\n"
    "- query_reviews(sentiment, limit): 저장된 리뷰 감정별 조회\n"
    "- get_store_info(): 매장 메뉴·톤·통계 조회\n"
    "- add_owner_reply(review_text, owner_reply, drafter_kind): 톤 샘플 추가\n\n"
    "규칙:\n"
    "1) tool 호출이 자명하면 망설이지 말고 호출. 결과를 받으면 한국어로 보기 좋게 정리해 답.\n"
    "2) 단순 인사·안부는 tool 없이 직접 응답.\n"
    "3) 매장 정보가 필요한데 사장님이 모호하게 물으면 get_store_info 먼저 호출.\n"
    "4) 모르는 정보는 추측 금지 — 'tool 로 확인해보겠습니다' 라 말하고 호출.\n"
    "5) 매장 운영·리뷰 응대 외 정치·종교 등 무관한 주제는 정중히 거절."
)


def build_chat_agent(place_id: str):
    """매장별 chat agent. place_id 가 tool closure 로 주입됨.

    mock 모드(`REVIEW_OPS_LLM=mock` 또는 `UPSTAGE_API_KEY` 미설정)에서는 stub agent
    를 반환 — `create_react_agent` 내부 루프를 흉내내는 비용이 너무 커서 단일 응답
    만 돌려주는 _MockChatAgent 로 우회한다. 채팅 UI 가 mock 모드라는 안내 메시지를
    바로 받게 된다.
    """
    if _is_mock_mode():
        return _MockChatAgent()

    # 실제 경로 — lazy import 로 mock 모드에서는 langchain-upstage 의 무거운 의존성을 피한다.
    from langchain_upstage import ChatUpstage
    from langgraph.prebuilt import create_react_agent

    llm = ChatUpstage(
        model=os.getenv("MODEL_CHAT", "solar-pro2"),
        temperature=0.3,
        streaming=True,  # token-level streaming 활성화 — UI 의 stream_mode='messages' 와 짝
    )
    tools = make_chat_tools(place_id)
    return create_react_agent(llm, tools=tools, prompt=_SYSTEM)
