from typing import Literal, Optional

from pydantic import BaseModel, Field

SectionName = Literal["problem", "status", "cause", "result"]
SECTION_ORDER: list[SectionName] = ["problem", "status", "cause", "result"]
SECTION_TITLE = {
    "problem": "문제 인식",
    "status": "현황 파악",
    "cause": "원인 분석 및 해결책",
    "result": "결과 정리 및 성능 향상",
}


class Section(BaseModel):
    name: SectionName
    title: str
    content: str  # 마크다운
    sources: list[str] = Field(default_factory=list)


class SectionScore(BaseModel):
    name: SectionName
    score: int = Field(ge=0, le=100)
    rationale: str


class StoryDraft(BaseModel):
    problem: Optional[Section] = None
    status: Optional[Section] = None
    cause: Optional[Section] = None
    result: Optional[Section] = None

    # 다이어그램 (Mermaid 텍스트). diagram_node에서 채움.
    architecture: Optional[str] = None
    dataflow: Optional[str] = None

    # 머지 레이어 산출물 — 4섹션 + 다이어그램을 최종 한 덩어리로 정리한 마크다운
    merged: Optional[str] = None

    def get(self, name: SectionName) -> Optional[Section]:
        return getattr(self, name)

    def set(self, name: SectionName, section: Section) -> None:
        setattr(self, name, section)


class Verdict(BaseModel):
    scores: list[SectionScore]
    weakest: Optional[SectionName] = None
    overall_pass: bool = False
