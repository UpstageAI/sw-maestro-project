from .chroma_patent_tool import (
    ChromaPatentDocument,
    ChromaPatentTool,
    getTools as getChromaTools,
)
from .kipris_tool import (
    KiprisPatentRecord,
    KiprisSearchResult,
    KiprisTool,
    getTools as getKiprisTools,
)

__all__ = [
    "ChromaPatentDocument",
    "ChromaPatentTool",
    "getChromaTools",
    "getKiprisTools",
    "getTools",
    "KiprisPatentRecord",
    "KiprisSearchResult",
    "KiprisTool",
]


def getTools(
    chroma_tool=None,
    kipris_tool=None,
    include_chroma: bool = True,
    include_kipris: bool = True,
) -> list:
    """LangChain agent에 넘길 backend 특허 검색 tool 전체 목록을 반환합니다."""
    tools = []
    if include_chroma:
        tools.extend(getChromaTools(chroma_tool))
    if include_kipris:
        tools.extend(getKiprisTools(kipris_tool))
    return tools
