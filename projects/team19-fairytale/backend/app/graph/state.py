from __future__ import annotations

from typing import TypedDict


class PersonDict(TypedDict, total=False):
    name: str
    relation: str
    kind: str          # 가족 / 친구 / 선생님 / 이웃 / 기타
    closeness: int     # 1(어색함) ~ 5(아주 가까움)
    role_today: str    # 오늘 일기 속 역할
    traits: list[str]  # 특징 키워드
    note: str


class Critique(TypedDict, total=False):
    scores: dict[str, int]   # fairy_tale / age_vocab / character_mapping / safety (1~5)
    average: float
    comment: str             # 어디를 어떻게 고쳐야 하는지 자유 코멘트
    passed: bool             # average >= 임계값 여부


class StoryOut(TypedDict, total=False):
    title: str
    body: str


class GraphState(TypedDict, total=False):
    # 입력
    diary_date: str
    diary: str
    people: list[PersonDict]

    # 작업 중간 산출물
    outline: str             # plan 노드 결과 (JSON 문자열)
    draft_title: str         # 가장 최근 write 결과
    draft_body: str
    critique: Critique
    revision_count: int      # 지금까지 write 가 몇 번 돌았는지

    # 최종 결과
    story: StoryOut
