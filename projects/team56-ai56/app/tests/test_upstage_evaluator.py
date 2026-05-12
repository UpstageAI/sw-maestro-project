from app.core.models import CandidateProfile, CandidateRecord, JobRecord
from app.services.evaluator import UpstageEvaluator


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls = []

    def post(self, url: str, headers: dict, json: dict, timeout: int) -> FakeResponse:
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(self.responses.pop(0))


def test_upstage_evaluator_suggests_criteria_and_scores_candidate() -> None:
    session = FakeSession(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": """```json
                            {
                              "criteria": [
                                {"name": "Python Fundamentals", "description": "Python backend skill", "weight": 30},
                                {"name": "SQL Skill", "description": "Database fluency", "weight": 20},
                                {"name": "API Design", "description": "REST and service design", "weight": 15},
                                {"name": "Project Evidence", "description": "Observable output", "weight": 15},
                                {"name": "Collaboration", "description": "Works with teams", "weight": 10},
                                {"name": "Growth", "description": "Learns quickly", "weight": 10}
                              ]
                            }
                            ```"""
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "jd_score": 82,
                              "summary": "Strong overlap with backend criteria.",
                              "evidence": [
                                {
                                  "source_type": "resume",
                                  "source_ref": "candidate:1",
                                  "snippet": "Python API project with SQL.",
                                  "confidence": 84
                                }
                              ]
                            }
                            """
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "alignment_score": 74,
                              "summary": "Claims are mostly supported by public GitHub evidence.",
                              "evidence": [
                                {
                                  "source_type": "GitHub profile",
                                  "source_ref": "https://github.com/example/project",
                                  "snippet": "Recent repo shows Python code and API work.",
                                  "confidence": 76
                                }
                              ]
                            }
                            """
                        }
                    }
                ]
            },
        ]
    )
    evaluator = UpstageEvaluator(
        api_key="test-key",
        model="solar-pro3",
        session=session,
    )
    criteria = evaluator.suggest_criteria("Backend role requiring Python and SQL.")

    assert len(criteria) == 6
    assert sum(item.weight for item in criteria) == 100

    job = JobRecord(title="Backend Engineer", jd_text="Backend role requiring Python and SQL.", criteria=criteria)
    candidate = CandidateRecord(
        job_id=job.id,
        name="Tester",
        resume_text="Python API project with SQL.",
        masked_resume_text="Python API project with SQL.",
        parsed_profile=CandidateProfile(skills=["python", "sql"]),
    )
    result = evaluator.evaluate_candidate(job, candidate)

    assert result.jd_score == 82
    assert result.alignment_score == 74
    assert len(result.evidence) == 2
    assert session.calls[0]["url"].endswith("/chat/completions")


def test_upstage_evaluator_calibrates_zero_alignment_when_github_evidence_exists() -> None:
    session = FakeSession(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "criteria": [
                                {"name": "Python Fundamentals", "description": "Python backend skill", "weight": 30},
                                {"name": "SQL Skill", "description": "Database fluency", "weight": 20},
                                {"name": "API Design", "description": "REST and service design", "weight": 15},
                                {"name": "Project Evidence", "description": "Observable output", "weight": 15},
                                {"name": "Collaboration", "description": "Works with teams", "weight": 10},
                                {"name": "Growth", "description": "Learns quickly", "weight": 10}
                              ]
                            }
                            """
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "jd_score": 75,
                              "summary": "Reasonable fit.",
                              "evidence": [
                                {
                                  "source_type": "resume",
                                  "source_ref": "candidate:1",
                                  "snippet": "Python API project with SQL.",
                                  "confidence": 80
                                }
                              ]
                            }
                            """
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                              "alignment_score": 0,
                              "summary": "Support is limited.",
                              "evidence": [
                                {
                                  "source_type": "github",
                                  "source_ref": "https://github.com/example/project",
                                  "snippet": "Repo shows backend-related code.",
                                  "confidence": 61
                                }
                              ]
                            }
                            """
                        }
                    }
                ]
            },
        ]
    )
    evaluator = UpstageEvaluator(api_key="test-key", model="solar-pro3", session=session)
    criteria = evaluator.suggest_criteria("Backend role requiring Python and SQL.")
    job = JobRecord(title="Backend Engineer", jd_text="Backend role requiring Python and SQL.", criteria=criteria)
    candidate = CandidateRecord(
        job_id=job.id,
        name="Tester",
        resume_text="Python API project with SQL.",
        masked_resume_text="Python API project with SQL.",
        github_url="https://github.com/example",
        github_status="fetched",
        github_profile={
            "username": "example",
            "profile_url": "https://github.com/example",
            "public_repos": 5,
            "followers": 1,
            "following": 1,
            "top_languages": ["Python"],
            "recent_repos": [
                {
                    "name": "backend-service",
                    "html_url": "https://github.com/example/backend-service",
                    "description": "Service API",
                    "language": "Python",
                    "stargazers_count": 0,
                    "updated_at": "2026-05-10T00:00:00Z",
                }
            ],
            "last_activity_at": "2026-05-10T00:00:00Z",
        },
        parsed_profile=CandidateProfile(skills=["python", "sql"]),
    )
    result = evaluator.evaluate_candidate(job, candidate)

    assert result.alignment_score == 35
