from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.data import mentors as mentor_data
from app.modules.mentor_candidate import llm_selector, retriever, service
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile


def _team_profile() -> TeamProfile:
    return TeamProfile(
        members_rnr="리더는 백엔드와 인프라, 팀원은 프론트엔드와 ML을 담당합니다.",
        project_plan_tech_goals="LLM 기반 멘토 추천 서비스를 FastAPI와 RAG로 구현합니다.",
        mentoring_needs="LLM 서비스 설계와 배포 구조에 대한 피드백이 필요합니다.",
        fit_conditions="AI 서비스 운영 경험이 있는 멘토를 선호합니다.",
        maestro_program_goals="소마 인증과 실제 서비스 출시를 목표로 합니다.",
        skills="Python, FastAPI, LLM, RAG",
    )


def _mentor(
    mentor_id: int,
    *,
    name: str | None = None,
    stacks: list[str] | None = None,
    domains: list[str] | None = None,
) -> Mentor:
    return Mentor(
        mentor_id=mentor_id,
        name=name or f"테스트멘토{mentor_id}",
        stacks=stacks or ["Python"],
        hobbie="테스트",
        target="기술",
        is_overseas=False,
        is_new_mentor=False,
        can_plan=False,
        meeting_mode_preference="온·오프라인",
        domains=domains or ["AI"],
        is_certificated=False,
        career=[["TestCorp", 3]],
    )


def _llm_candidate(mentor_id: int, rank: int = 1) -> dict:
    return {
        "mentor_id": mentor_id,
        "rank": rank,
        "extracted_facts": f"멘토 {mentor_id}의 실제 데이터입니다.",
        "reasoning_process": f"현재 분석 중인 멘토: [ID: {mentor_id}, 이름: 테스트멘토{mentor_id}]",
        "reason": f"테스트멘토{mentor_id} 멘토님은 팀의 기술 목표에 적합합니다.",
        "weak_point": "일부 세부 도메인 경험은 추가 확인이 필요합니다.",
    }


def test_get_all_mentors_loads_from_configured_path_and_reuses_cache(tmp_path, monkeypatch):
    mentor_file = tmp_path / "mentors.json"
    mentor_file.write_text(
        json.dumps([_mentor(1).model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings, "mentor_data_path", str(mentor_file))
    mentor_data.reload_mentors()

    loaded = mentor_data.get_all_mentors()
    assert [mentor.mentor_id for mentor in loaded] == [1]

    mentor_file.write_text(
        json.dumps([_mentor(2).model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )
    assert [mentor.mentor_id for mentor in mentor_data.get_all_mentors()] == [1]

    mentor_data.reload_mentors()
    assert [mentor.mentor_id for mentor in mentor_data.get_all_mentors()] == [2]


@pytest.mark.asyncio
async def test_filter_mentors_falls_back_to_input_order_when_embedding_unavailable(monkeypatch):
    async def fake_get_embedding(text: str, cache_key: str | None = None):
        return None

    monkeypatch.setattr(retriever, "_get_embedding", fake_get_embedding)

    mentors = [_mentor(1), _mentor(2), _mentor(3)]
    result = await retriever.filter_mentors(_team_profile(), mentors, top_n=2)

    assert [mentor.mentor_id for mentor in result] == [1, 2]


@pytest.mark.asyncio
async def test_filter_mentors_sorts_by_cosine_similarity(monkeypatch):
    async def fake_get_embedding(text: str, cache_key: str | None = None):
        if cache_key == "1":
            return [1.0, 0.0]
        if cache_key == "2":
            return [0.0, 1.0]
        return [0.0, 1.0]

    monkeypatch.setattr(retriever, "_get_embedding", fake_get_embedding)

    mentors = [_mentor(1), _mentor(2)]
    result = await retriever.filter_mentors(_team_profile(), mentors, top_n=2)

    assert [mentor.mentor_id for mentor in result] == [2, 1]


@pytest.mark.asyncio
async def test_select_candidates_deduplicates_invalid_ids_and_fills_missing_slots(monkeypatch):
    async def fake_chat_completion(*args, **kwargs):
        return json.dumps(
            {
                "candidates": [
                    _llm_candidate(1, rank=1),
                    _llm_candidate(1, rank=2),
                    _llm_candidate(999, rank=3),
                ]
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        llm_selector.upstage_client,
        "get_chat_completion",
        fake_chat_completion,
    )

    mentors = [_mentor(1), _mentor(2), _mentor(3)]
    result = await llm_selector.select_candidates(_team_profile(), mentors, top_k=3)

    assert [candidate.mentor_id for candidate in result] == [1, 2, 3]
    assert [candidate.rank for candidate in result] == [1, 2, 3]
    assert all(isinstance(candidate, CandidateResult) for candidate in result)


@pytest.mark.asyncio
async def test_get_mentor_candidates_orchestrates_retriever_and_llm_selector(monkeypatch):
    all_mentors = [_mentor(1), _mentor(2), _mentor(3)]
    calls: list[tuple[str, int]] = []

    def fake_get_all_mentors():
        calls.append(("load", len(all_mentors)))
        return all_mentors

    async def fake_filter_mentors(team_profile, mentors, top_n):
        assert team_profile == _team_profile()
        assert mentors == all_mentors
        calls.append(("filter", top_n))
        return mentors[:2]

    async def fake_select_candidates(team_profile, mentors, top_k):
        assert team_profile == _team_profile()
        assert [mentor.mentor_id for mentor in mentors] == [1, 2]
        calls.append(("select", top_k))
        return [
            CandidateResult(
                mentor_id=1,
                rank=1,
                reason="테스트멘토1 멘토님은 팀 목표에 적합합니다.",
                weak_point="추가 확인이 필요한 영역이 있습니다.",
            )
        ]

    monkeypatch.setattr(settings, "prefilter_top_n", 2)
    monkeypatch.setattr(service, "get_all_mentors", fake_get_all_mentors)
    monkeypatch.setattr(service, "filter_mentors", fake_filter_mentors)
    monkeypatch.setattr(service, "select_candidates", fake_select_candidates)

    result = await service.get_mentor_candidates(_team_profile(), top_k=1)

    assert [candidate.mentor_id for candidate in result] == [1]
    assert calls == [("load", 3), ("filter", 2), ("select", 1)]
