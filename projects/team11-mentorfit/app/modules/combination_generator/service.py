from __future__ import annotations

import json

from app.core.config import settings
from app.core.upstage import upstage_client
from app.data.mentors import get_all_mentors
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile


class CombinationGeneratorService:
    def __init__(self, mentors: list[Mentor] | None = None):
        self._mentors = mentors or get_all_mentors()
        self._mentor_by_id = {mentor.mentor_id: mentor for mentor in self._mentors}

    async def generate(
        self,
        team_profile: TeamProfile,
        candidates: list[CandidateResult],
    ) -> list[CombCandidateResult]:
        results: list[CombCandidateResult] = []
        for candidate in candidates:
            result = await self._generate_single(team_profile, candidate, candidates)
            results.append(result)
        return results

    async def _generate_single(
        self,
        team_profile: TeamProfile,
        candidate: CandidateResult,
        candidates: list[CandidateResult],
    ) -> CombCandidateResult:
        if settings.mock_mode or not settings.upstage_api_key:
            return self._fallback_combination(candidate, candidates)

        mentor = self._mentor_by_id.get(candidate.mentor_id)
        if mentor is None:
            return self._fallback_combination(candidate, candidates)

        messages = self._build_prompt(team_profile, candidate, mentor)
        raw = await upstage_client.chat_completion(messages, model=settings.combination_model)
        return self._parse_llm_response(raw, candidate, candidates)

    def _build_prompt(
        self,
        team_profile: TeamProfile,
        candidate: CandidateResult,
        mentor: Mentor,
    ) -> list[dict]:
        other_mentors = [m for m in self._mentors if m.mentor_id != candidate.mentor_id]
        mentor_list = "\n".join(self._mentor_line(m) for m in other_mentors)
        return [
            {
                "role": "system",
                "content": (
                    "당신은 멘토 조합 전문가입니다. 주어진 팀 프로필과 기준 멘토의 약점을 바탕으로 "
                    "전체 멘토 풀에서 최적의 보완 멘토 2명을 선정하고 조합을 평가합니다. "
                    "반드시 JSON으로만 응답하세요."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"팀 프로필:\n"
                    f"- 기술 스택: {team_profile.skills}\n"
                    f"- 팀원 구성: {team_profile.members_rnr}\n"
                    f"- 프로젝트: {team_profile.project_plan_tech_goals}\n"
                    f"- 프로그램 목표: {team_profile.maestro_program_goals}\n"
                    f"- 멘토링 니즈: {team_profile.mentoring_needs}\n\n"
                    f"기준 멘토: {self._mentor_line(mentor)}\n"
                    f"- 추천 이유: {candidate.reason}\n"
                    f"- 약점: {candidate.weak_point}\n\n"
                    f"전체 멘토 풀 (기준 멘토 제외):\n{mentor_list}\n\n"
                    "아래 JSON 형식으로만 응답하세요:\n"
                    "{\n"
                    '  "second_mentor_id": 2,\n'
                    '  "third_mentor_id": 3,\n'
                    '  "strengths": ["...", "...", "..."],\n'
                    '  "weak_points": ["...", "...", "..."],\n'
                    '  "reason": "..."\n'
                    "}"
                ),
            },
        ]

    def _parse_llm_response(
        self,
        raw: str,
        candidate: CandidateResult,
        candidates: list[CandidateResult],
    ) -> CombCandidateResult:
        try:
            data = json.loads(raw)
            candidate_ids = [
                mentor_id
                for mentor_id in [data.get("second_mentor_id"), data.get("third_mentor_id")]
                if isinstance(mentor_id, int)
                and mentor_id in self._mentor_by_id
                and mentor_id != candidate.mentor_id
            ][:2]
            return CombCandidateResult(
                mentor_id=candidate.mentor_id,
                candidate_ids=candidate_ids,
                strengths=data.get("strengths", [])[:3],
                weak_points=data.get("weak_points", [])[:3],
                rank=candidate.rank,
                reason=data.get("reason", candidate.reason),
                weak_point=candidate.weak_point,
            )
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            return self._fallback_combination(candidate, candidates)

    def _fallback_combination(
        self,
        candidate: CandidateResult,
        candidates: list[CandidateResult],
    ) -> CombCandidateResult:
        candidate_ids = [
            other.mentor_id
            for other in candidates
            if other.mentor_id != candidate.mentor_id and other.mentor_id in self._mentor_by_id
        ][:2]
        return CombCandidateResult(
            mentor_id=candidate.mentor_id,
            candidate_ids=candidate_ids,
            strengths=[],
            weak_points=[],
            rank=candidate.rank,
            reason=candidate.reason,
            weak_point=candidate.weak_point,
        )

    @staticmethod
    def _mentor_line(mentor: Mentor) -> str:
        career = ", ".join(f"{company}({years}년)" for company, years in mentor.career)
        return (
            f"- {mentor.mentor_id}: {mentor.name} | "
            f"기술: {', '.join(mentor.stacks)} | "
            f"도메인: {', '.join(mentor.domains)} | "
            f"목표: {mentor.target} | "
            f"경력: {career}"
        )
