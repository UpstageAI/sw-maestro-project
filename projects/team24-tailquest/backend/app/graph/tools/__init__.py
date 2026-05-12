"""LLM-callable tools.

OpenAI-style tool specs + a single dispatch entry point. Currently only one
tool is exposed (web_search via Tavily). When the LLM emits a tool_call, the
dispatcher runs the tool and returns a string the LLM can read on its next
turn.
"""

from __future__ import annotations

from app.graph.tools.web_search import tavily_search


WEB_SEARCH_TOOL_SPEC: dict = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "인터넷에서 최신 기술 자료를 검색합니다. 면접 질문 토픽의 시의성을 보강하거나, "
            "사용자가 첨부한 자료에 없는 개념·구체적 사례를 확인하고 싶을 때 사용하세요. "
            "사실 확인이 필요 없는 일반 개념(예: 'TCP 3-way handshake')은 호출하지 마세요."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 질의어 — 한국어 또는 영어. 구체적일수록 좋음.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "최대 결과 수 (기본 3, 최대 5).",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}


async def dispatch_tool_call(name: str, args: dict) -> str:
    """Execute a tool by name. Always returns a string for the LLM to read."""
    if name == "web_search":
        query = str(args.get("query", "")).strip()
        if not query:
            return "검색 질의어가 비어있습니다."
        try:
            max_results = min(max(int(args.get("max_results", 3)), 1), 5)
        except (TypeError, ValueError):
            max_results = 3
        hits = await tavily_search(query, max_results=max_results)
        if not hits:
            return "검색 결과가 없습니다."
        return "\n\n".join(
            f"[{i}] {h.title}\nURL: {h.url}\n{h.snippet[:500]}"
            for i, h in enumerate(hits, 1)
        )
    return f"알 수 없는 도구: {name}"
