from __future__ import annotations

from abc import ABC, abstractmethod
import json
from typing import Any, Callable

import requests
from pydantic import BaseModel, Field, ValidationError

from app.core.models import CandidateRecord, Criterion, EvaluationResult, Evidence, JobRecord


class BaseEvaluator(ABC):
    @abstractmethod
    def suggest_criteria(self, jd_text: str) -> list[Criterion]:
        raise NotImplementedError

    @abstractmethod
    def evaluate_candidate(self, job: JobRecord, candidate: CandidateRecord) -> EvaluationResult:
        raise NotImplementedError


class MockEvaluator(BaseEvaluator):
    DEFAULT_CRITERIA = [
        Criterion(name="Core Skill Match", description="JD keywords appear in the candidate material", weight=30),
        Criterion(name="Project Evidence", description="Observable output or portfolio evidence exists", weight=20),
        Criterion(name="Collaboration Signal", description="Teamwork, communication, and shared delivery signal", weight=15),
        Criterion(name="Learning Velocity", description="Growth signal, iteration, or self-driven learning", weight=10),
        Criterion(name="Problem Solving", description="Clear ownership of technical or product problems", weight=15),
        Criterion(name="Role Motivation", description="Role-specific interest or domain alignment", weight=10),
    ]

    def suggest_criteria(self, jd_text: str) -> list[Criterion]:
        lowered = jd_text.lower()
        criteria = list(self.DEFAULT_CRITERIA)
        if "backend" in lowered or "api" in lowered:
            criteria[0] = Criterion(
                name="Backend Fundamentals",
                description="API, database, server-side logic, and reliability fit",
                weight=30,
            )
        if "data" in lowered or "sql" in lowered:
            criteria[4] = Criterion(
                name="Data Reasoning",
                description="Database modeling, query quality, and data handling fit",
                weight=15,
            )
        return criteria

    def evaluate_candidate(self, job: JobRecord, candidate: CandidateRecord) -> EvaluationResult:
        jd_words = {word.strip(".,()[]").lower() for word in job.jd_text.split() if len(word) > 3}
        resume_words = {word.strip(".,()[]").lower() for word in candidate.masked_resume_text.split() if len(word) > 3}
        overlap = jd_words & resume_words
        overlap_ratio = min(len(overlap) / max(len(jd_words), 1), 1.0)

        has_github = candidate.github_status == "fetched"
        has_github_url = bool(candidate.github_url)
        language_bonus = 0
        recent_repo_bonus = 0
        if candidate.github_profile:
            github_words = {
                language.lower()
                for language in candidate.github_profile.top_languages
            }
            language_bonus = 5 if github_words & jd_words else 0
            recent_repo_bonus = min(len(candidate.github_profile.recent_repos), 3)

        jd_score = min(100, round(45 + overlap_ratio * 50 + (5 if has_github_url else 0) + language_bonus))
        alignment_score = min(
            100,
            round(
                35
                + overlap_ratio * 40
                + (15 if has_github else 0)
                + recent_repo_bonus
                + (5 if "project" in resume_words else 0)
            ),
        )
        summary = (
            "Candidate shows keyword overlap with the role description. "
            "This is a mock evaluation and should be replaced with the Upstage-backed scorer."
        )
        evidence = [
            Evidence(
                source_type="resume",
                source_ref=f"candidate:{candidate.id}",
                snippet=f"Keyword overlap count: {len(overlap)}",
                confidence=65,
            )
        ]
        if candidate.github_profile:
            evidence.append(
                Evidence(
                    source_type="github",
                    source_ref=candidate.github_profile.profile_url,
                    snippet=(
                        f"Public repos: {candidate.github_profile.public_repos}, "
                        f"top languages: {', '.join(candidate.github_profile.top_languages) or 'unknown'}, "
                        f"recent sampled commits: {candidate.github_profile.recent_commit_count}."
                    ),
                    confidence=70,
                )
            )
            for repo in candidate.github_profile.recent_repos[:2]:
                topic_text = f" Topics: {', '.join(repo.topics[:4])}." if repo.topics else ""
                readme_text = f" README: {repo.readme_excerpt}" if repo.readme_excerpt else ""
                commit_text = (
                    f" Recent commits: {' | '.join(repo.recent_commit_headlines[:2])}."
                    if repo.recent_commit_headlines
                    else ""
                )
                structure_bits = []
                if repo.has_tests:
                    structure_bits.append("tests present")
                if repo.has_ci:
                    structure_bits.append("CI config present")
                if repo.has_dockerfile:
                    structure_bits.append("Dockerfile present")
                structure_text = f" Structure: {', '.join(structure_bits)}." if structure_bits else ""
                framework_text = (
                    f" Frameworks/signals: {', '.join(repo.detected_frameworks[:5])}."
                    if repo.detected_frameworks
                    else ""
                )
                code_signal_text = (
                    f" Code sample: {' | '.join(repo.sample_code_signals[:2])}."
                    if repo.sample_code_signals
                    else ""
                )
                evidence.append(
                    Evidence(
                        source_type="github",
                        source_ref=repo.html_url,
                        snippet=(
                            f"Recent repo '{repo.name}'"
                            + (f" uses {repo.language}" if repo.language else "")
                            + (f" and has {repo.stargazers_count} stars." if repo.stargazers_count else ".")
                            + topic_text
                            + readme_text
                            + commit_text
                            + structure_text
                            + framework_text
                            + code_signal_text
                        ),
                        confidence=60,
                    )
                )
        elif candidate.github_url:
            evidence.append(
                Evidence(
                    source_type="github",
                    source_ref=candidate.github_url,
                    snippet=(
                        candidate.github_failure_reason
                        or "GitHub URL provided, but evidence fetch did not complete."
                    ),
                    confidence=30,
                )
            )

        return EvaluationResult(
            job_id=job.id,
            candidate_id=candidate.id,
            jd_score=jd_score,
            alignment_score=alignment_score,
            summary=summary,
            evidence=evidence,
        )


class UpstageEvaluator(BaseEvaluator):
    class CriteriaResponse(BaseModel):
        criteria: list[Criterion] = Field(min_length=3, max_length=8)

    class ScoreEvidence(BaseModel):
        source_type: str
        source_ref: str
        snippet: str
        confidence: int = Field(ge=0, le=100)

    class JDMatchResponse(BaseModel):
        jd_score: int = Field(ge=0, le=100)
        summary: str
        evidence: list[ScoreEvidence] = Field(default_factory=list, min_length=1)

    class AlignmentResponse(BaseModel):
        alignment_score: int = Field(ge=0, le=100)
        summary: str
        evidence: list[ScoreEvidence] = Field(default_factory=list, min_length=1)

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str = "https://api.upstage.ai/v1",
        session: requests.Session | None = None,
        max_retries: int = 2,
        timeout_seconds: int = 40,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.audit_hook: Callable[[str, dict[str, Any]], None] | None = None
        self.audit_context: dict[str, Any] = {}

    def suggest_criteria(self, jd_text: str) -> list[Criterion]:
        payload = self._chat_completion(
            system_prompt=(
                "You are a hiring criteria planner. "
                "Return strict JSON only. Do not wrap in markdown. "
                "Generate 6 evaluation criteria for a hiring team. "
                "Weights must sum to 100 and every weight must be an integer. "
                "Prefer a balanced set covering core skills, project evidence, collaboration, and problem solving."
            ),
            user_prompt=(
                "Analyze the following job description and return JSON with this schema:\n"
                '{ "criteria": [{"name": string, "description": string, "weight": integer}] }\n'
                "Focus only on job-relevant, skills-based hiring factors.\n"
                "Do not use age, gender, school prestige, appearance, or nationality.\n\n"
                "If the JD is written in Korean, write the criteria in Korean.\n"
                "If the JD is written in English, write the criteria in English.\n"
                "Avoid redundant criteria such as repeating the same skill in multiple rows.\n\n"
                f"JOB DESCRIPTION:\n{jd_text}"
            ),
            response_model=self.CriteriaResponse,
            call_name="criteria_suggestion",
        )
        criteria = payload.criteria
        total_weight = sum(item.weight for item in criteria)
        if total_weight != 100:
            normalized = []
            running_total = 0
            for index, item in enumerate(criteria):
                if index == len(criteria) - 1:
                    weight = 100 - running_total
                else:
                    weight = max(0, round(item.weight / total_weight * 100)) if total_weight else 0
                    running_total += weight
                normalized.append(Criterion(name=item.name, description=item.description, weight=weight))
            criteria = normalized
        return criteria

    def evaluate_candidate(self, job: JobRecord, candidate: CandidateRecord) -> EvaluationResult:
        jd_match = self._chat_completion(
            system_prompt=(
                "You are a hiring evaluator focused on JD fit. "
                "Return strict JSON only. "
                "Never infer protected traits. "
                "Use only provided evidence."
            ),
            user_prompt=(
                "Return JSON with this schema:\n"
                '{ "jd_score": integer, "summary": string, "evidence": [{"source_type": string, "source_ref": string, "snippet": string, "confidence": integer}] }\n'
                "Score 0-100 based on how well the candidate matches the confirmed role criteria.\n"
                "At least one evidence item must cite resume or github input.\n\n"
                f"ROLE CRITERIA:\n{json.dumps([item.model_dump() for item in job.criteria], ensure_ascii=False)}\n\n"
                f"JOB DESCRIPTION:\n{job.jd_text}\n\n"
                f"CANDIDATE RESUME (MASKED):\n{candidate.masked_resume_text}\n\n"
                f"CANDIDATE GITHUB SNAPSHOT:\n{self._github_context(candidate)}"
            ),
            response_model=self.JDMatchResponse,
            call_name="jd_match",
        )
        alignment = self._chat_completion(
            system_prompt=(
                "You are a hiring evaluator focused on claim-evidence alignment. "
                "Return strict JSON only. "
                "Measure whether the candidate's stated experience is supported by observable artifacts. "
                "Use calibration anchors: 0-20 = direct contradiction or almost no support, "
                "21-40 = weak or ambiguous support, 41-60 = partial support, "
                "61-80 = strong support, 81-100 = highly specific and repeated support."
            ),
            user_prompt=(
                "Return JSON with this schema:\n"
                '{ "alignment_score": integer, "summary": string, "evidence": [{"source_type": string, "source_ref": string, "snippet": string, "confidence": integer}] }\n'
                "Score 0-100 based on claim-to-evidence alignment. "
                "Higher means stronger consistency between resume claims and public artifacts.\n"
                "Do not use 0 unless the evidence clearly contradicts the claim or there is almost no relevant support.\n"
                "Because direct identity fields are masked, do not heavily penalize the candidate only because ownership cannot be proven from name matching alone.\n"
                "When artifacts are topically relevant but incomplete, prefer a middle score such as 35-65 rather than collapsing to zero.\n"
                "At least one evidence item must cite resume or github input.\n\n"
                f"CANDIDATE RESUME (MASKED):\n{candidate.masked_resume_text}\n\n"
                f"CANDIDATE GITHUB SNAPSHOT:\n{self._github_context(candidate)}"
            ),
            response_model=self.AlignmentResponse,
            call_name="alignment",
        )

        calibrated_alignment_score = self._calibrate_alignment_score(
            alignment.alignment_score,
            candidate,
            alignment.evidence,
        )

        combined_evidence = [
            self._to_evidence(item) for item in jd_match.evidence + alignment.evidence
        ]
        return EvaluationResult(
            job_id=job.id,
            candidate_id=candidate.id,
            jd_score=jd_match.jd_score,
            alignment_score=calibrated_alignment_score,
            summary=f"JD Fit: {jd_match.summary}\n\nAlignment: {alignment.summary}",
            evidence=combined_evidence,
        )

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        call_name: str,
    ) -> BaseModel:
        if not self.api_key:
            raise RuntimeError("HIREPROOF_UPSTAGE_API_KEY is required when evaluator mode is 'upstage'.")

        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                self._emit_audit(
                    "llm_request",
                    {
                        "call_name": call_name,
                        "model": self.model,
                        "system_prompt_preview": system_prompt[:400],
                        "user_prompt_preview": user_prompt[:700],
                        "system_prompt_length": len(system_prompt),
                        "user_prompt_length": len(user_prompt),
                    },
                )
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "stream": False,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                data = self._extract_json(content)
                validated = response_model.model_validate(data)
                self._emit_audit(
                    "llm_response",
                    {
                        "call_name": call_name,
                        "model": self.model,
                        "response_preview": content[:700],
                        "validated_keys": list(data.keys()),
                    },
                )
                return validated
            except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                self._emit_audit(
                    "llm_error",
                    {
                        "call_name": call_name,
                        "model": self.model,
                        "error": str(exc),
                    },
                )
                continue

        raise RuntimeError(f"Upstage evaluation failed after retries: {last_error}")

    def _extract_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON object found", cleaned, 0)
        return json.loads(cleaned[start : end + 1])

    def _github_context(self, candidate: CandidateRecord) -> str:
        if not candidate.github_profile:
            return json.dumps(
                {
                    "github_url": candidate.github_url,
                    "status": candidate.github_status,
                    "failure_reason": candidate.github_failure_reason,
                },
                ensure_ascii=False,
            )
        return json.dumps(candidate.github_profile.model_dump(mode="json"), ensure_ascii=False)

    def _to_evidence(self, item: ScoreEvidence) -> Evidence:
        source_type = self._normalize_source_type(item.source_type)
        return Evidence(
            source_type=source_type,
            source_ref=item.source_ref,
            snippet=item.snippet,
            confidence=item.confidence,
        )

    def _normalize_source_type(self, value: str) -> str:
        lowered = value.strip().lower()
        if "github" in lowered:
            return "github"
        if "blog" in lowered:
            return "blog"
        if "manual" in lowered:
            return "manual"
        if "system" in lowered:
            return "system"
        return "resume"

    def _calibrate_alignment_score(
        self,
        score: int,
        candidate: CandidateRecord,
        evidence: list[ScoreEvidence],
    ) -> int:
        has_github_evidence = any("github" in item.source_type.strip().lower() for item in evidence)
        has_artifact_context = candidate.github_status == "fetched" and candidate.github_profile is not None

        # Demo safeguard: if we have fetched public artifacts and the model still collapses
        # to a near-zero score, raise it into a "weak/partial support" band instead.
        if has_artifact_context and has_github_evidence and score == 0:
            return 35
        if has_artifact_context and has_github_evidence and score < 20:
            return 25
        return score

    def set_audit_hook(self, hook: Callable[[str, dict[str, Any]], None] | None) -> None:
        self.audit_hook = hook

    def set_audit_context(self, context: dict[str, Any]) -> None:
        self.audit_context = context

    def clear_audit_context(self) -> None:
        self.audit_context = {}

    def _emit_audit(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.audit_hook:
            return
        merged = dict(self.audit_context)
        merged.update(payload)
        self.audit_hook(event_type, merged)
