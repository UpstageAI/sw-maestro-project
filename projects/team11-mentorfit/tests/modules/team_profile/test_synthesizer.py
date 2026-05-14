from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.core.schemas import MentoringDomain
from app.modules.team_profile.schemas import MemberProfile
from app.modules.team_profile.synthesizer import (
    TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT,
    VALID_DOMAIN_VALUES,
    _build_user_prompt,
    synthesize_team_profile,
)


SAMPLE_MEMBERS = [
    MemberProfile(
        name="테스터",
        skills=["Python"],
        role="BE",
        goals="취업",
        mentoring_needs="코드 리뷰",
        background="컴공 4학년",
        project_experience="해커톤 우승",
    ),
]


def test_build_user_prompt_includes_all_fields():
    prompt = _build_user_prompt(SAMPLE_MEMBERS, "테스트 기획", "시니어 멘토")

    assert "테스터" in prompt
    assert "BE" in prompt
    assert "Python" in prompt
    assert "취업" in prompt
    assert "컴공 4학년" in prompt
    assert "해커톤 우승" in prompt
    assert "테스트 기획" in prompt
    assert "시니어 멘토" in prompt


def test_build_user_prompt_without_optional_fields():
    members = [MemberProfile(name="간단멤버")]
    prompt = _build_user_prompt(members, "프로젝트", "")

    assert "간단멤버" in prompt
    assert "미정" in prompt
    assert "없음" in prompt
    assert "선호 멘토 조건" not in prompt


@pytest.mark.asyncio
async def test_synthesize_team_profile_uses_structured_response_format(monkeypatch):
    async def _complete(*, messages, model, response_format, **kwargs):
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert model
        assert response_format == TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT
        assert "temperature" in kwargs
        assert "max_tokens" in kwargs
        return json.dumps(
            {
                "members_r_and_r": "테스터가 BE 역할을 맡습니다.",
                "program_goals": "취업, 인증",
                "mentoring_needs": "코드 리뷰와 아키텍처 피드백이 필요합니다.",
                "mentoring_domains": ["기술_깊이", "아키텍처_설계"],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "app.modules.team_profile.synthesizer.upstage_client.get_chat_completion",
        _complete,
    )

    result = await synthesize_team_profile(
        SAMPLE_MEMBERS,
        project_plan="FastAPI 기반 서비스",
        fit_conditions="실무 경험이 많은 멘토",
    )

    assert result.members_r_and_r == "테스터가 BE 역할을 맡습니다."
    assert result.program_goals == "취업, 인증"
    assert result.mentoring_needs == "코드 리뷰와 아키텍처 피드백이 필요합니다."
    assert result.mentoring_domains == [
        MentoringDomain.TECH_DEPTH,
        MentoringDomain.ARCHITECTURE,
    ]


@pytest.mark.asyncio
async def test_synthesize_team_profile_rejects_missing_structured_fields(monkeypatch):
    async def _complete(*, response_format, **kwargs):
        assert response_format == TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT
        return json.dumps(
            {
                "members_r_and_r": "테스터가 BE 역할을 맡습니다.",
                "program_goals": "취업",
                "mentoring_domains": ["기술_깊이"],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "app.modules.team_profile.synthesizer.upstage_client.get_chat_completion",
        _complete,
    )

    with pytest.raises(ValidationError):
        await synthesize_team_profile(
            SAMPLE_MEMBERS,
            project_plan="FastAPI 기반 서비스",
            fit_conditions="실무 경험이 많은 멘토",
        )


@pytest.mark.asyncio
async def test_synthesize_team_profile_rejects_missing_mentoring_domains(monkeypatch):
    async def _complete(*, response_format, **kwargs):
        assert response_format == TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT
        return json.dumps(
            {
                "members_r_and_r": "테스터가 BE 역할을 맡습니다.",
                "program_goals": "취업",
                "mentoring_needs": "코드 리뷰가 필요합니다.",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "app.modules.team_profile.synthesizer.upstage_client.get_chat_completion",
        _complete,
    )

    with pytest.raises(ValidationError):
        await synthesize_team_profile(
            SAMPLE_MEMBERS,
            project_plan="FastAPI 기반 서비스",
            fit_conditions="실무 경험이 많은 멘토",
        )


@pytest.mark.asyncio
async def test_synthesize_team_profile_rejects_empty_mentoring_domains(monkeypatch):
    async def _complete(*, response_format, **kwargs):
        assert response_format == TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT
        return json.dumps(
            {
                "members_r_and_r": "테스터가 BE 역할을 맡습니다.",
                "program_goals": "취업",
                "mentoring_needs": "코드 리뷰가 필요합니다.",
                "mentoring_domains": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "app.modules.team_profile.synthesizer.upstage_client.get_chat_completion",
        _complete,
    )

    with pytest.raises(ValidationError):
        await synthesize_team_profile(
            SAMPLE_MEMBERS,
            project_plan="FastAPI 기반 서비스",
            fit_conditions="실무 경험이 많은 멘토",
        )


def test_synthesis_response_format_requires_complete_program_goal_names():
    description = TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT["json_schema"]["schema"][
        "properties"
    ]["program_goals"]["description"]

    assert "완성된 목표명" in description
    assert "한 글자 축약 금지" in description
    assert "인증" in description
    assert "취업" in description
    assert "인, 취, 창" in description


def test_synthesis_response_format_does_not_allow_one_character_contract_values():
    properties = TEAM_PROFILE_SYNTHESIS_RESPONSE_FORMAT["json_schema"]["schema"][
        "properties"
    ]

    assert properties["members_r_and_r"]["minLength"] > 1
    assert properties["mentoring_needs"]["minLength"] > 1
    assert properties["program_goals"]["minLength"] == 2
    assert "완결된 한국어 문구" in properties["members_r_and_r"]["description"]
    assert "완결된 한국어 문구" in properties["mentoring_needs"]["description"]


def test_valid_domain_values():
    assert "기술_깊이" in VALID_DOMAIN_VALUES
    assert "아키텍처_설계" in VALID_DOMAIN_VALUES
    assert "창업_BM" in VALID_DOMAIN_VALUES
    assert "취업_커리어" in VALID_DOMAIN_VALUES
    assert "인증_발표" in VALID_DOMAIN_VALUES
    assert "협업_기획" in VALID_DOMAIN_VALUES
    assert "존재하지않는도메인" not in VALID_DOMAIN_VALUES
