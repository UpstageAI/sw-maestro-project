from pathlib import Path

from app.config import get_settings
from app.core.models import CandidateCreate, GitHubProfileSnapshot, GitHubRepoSummary, JobCreate
from app.services.github_client import GitHubFetchResult
from app.services.pipeline import HireProofPipeline
from app.services.evaluator import BaseEvaluator


class FakeGitHubClient:
    def __init__(self, result: GitHubFetchResult | None = None) -> None:
        self.result = result or GitHubFetchResult(
            status="fetched",
            profile=GitHubProfileSnapshot(
                username="example",
                profile_url="https://github.com/example",
                public_repos=4,
                top_languages=["Python", "SQL"],
                recent_repos=[
                    GitHubRepoSummary(
                        name="resume-project",
                        html_url="https://github.com/example/resume-project",
                        language="Python",
                        stargazers_count=3,
                        updated_at="2026-05-05T00:00:00Z",
                    )
                ],
                last_activity_at="2026-05-05T00:00:00Z",
            ),
        )

    def fetch_profile(self, github_url: str | None) -> GitHubFetchResult:
        return self.result


class BrokenEvaluator(BaseEvaluator):
    def suggest_criteria(self, jd_text: str):
        raise RuntimeError("simulated llm failure")

    def evaluate_candidate(self, job, candidate):
        raise RuntimeError("simulated llm failure")


def build_pipeline(tmp_path, monkeypatch, github_result: GitHubFetchResult | None = None) -> HireProofPipeline:
    monkeypatch.setenv("HIREPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HIREPROOF_UPLOADS_DIR", str(tmp_path / "data" / "uploads"))
    monkeypatch.setenv("HIREPROOF_ARTIFACTS_DIR", str(tmp_path / "data" / "artifacts"))
    monkeypatch.setenv("HIREPROOF_SQLITE_PATH", str(tmp_path / "data" / "artifacts" / "hireproof.db"))
    monkeypatch.setenv("HIREPROOF_EVALUATOR_MODE", "mock")
    get_settings.cache_clear()
    return HireProofPipeline(github_client=FakeGitHubClient(github_result))


def test_pipeline_creates_job_and_evaluates_candidate() -> None:
    from _pytest.monkeypatch import MonkeyPatch
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmpdir:
        monkeypatch = MonkeyPatch()
        pipeline = build_pipeline(Path(tmpdir), monkeypatch)
        job = pipeline.create_job(
            JobCreate(
                title="Backend Engineer",
                jd_text="We need backend API, SQL, Python, and teamwork experience.",
            )
        )

        candidate = pipeline.add_candidate(
            job.id,
            CandidateCreate(
                name="Tester",
                resume_text="Python API project with SQL and team collaboration. GitHub: https://github.com/example/tester",
            ),
        )
        evaluations = pipeline.repository.list_evaluations(job.id)

        assert candidate.github_url == "https://github.com/example/tester"
        assert candidate.github_status == "fetched"
        assert candidate.github_profile is not None
        assert len(evaluations) >= 1
        assert evaluations[0].jd_score >= 45
        monkeypatch.undo()


def test_pipeline_upload_stores_token_mappings(tmp_path, monkeypatch) -> None:
    pipeline = build_pipeline(tmp_path, monkeypatch)
    job = pipeline.create_job(
        JobCreate(
            title="Backend Intern",
            jd_text="We need backend API, Python, SQL, and GitHub project evidence.",
        )
    )

    resume_path = tmp_path / "resume.txt"
    resume_path.write_text(
        "이름: 홍길동\n이메일: gildong@example.com\n연락처: 010-1234-5678\n"
        "Python API project with SQL and GitHub profile https://github.com/example/tester",
        encoding="utf-8",
    )

    candidate = pipeline.add_candidate_from_upload(
        job.id,
        candidate_name="홍길동",
        filename=resume_path.name,
        file_bytes=resume_path.read_bytes(),
    )
    mappings = pipeline.repository.list_token_mappings(candidate.id)

    assert candidate.source_filename == "resume.txt"
    assert candidate.github_url == "https://github.com/example/tester"
    assert candidate.github_status == "fetched"
    assert "[EMAIL_001]" in candidate.masked_resume_text
    assert any(item.kind == "email" for item in mappings)
    assert any(item.kind == "phone" for item in mappings)


def test_pipeline_records_github_failure_reason(tmp_path, monkeypatch) -> None:
    pipeline = build_pipeline(
        tmp_path,
        monkeypatch,
        GitHubFetchResult(status="failed", failure_reason="GitHub profile not found."),
    )
    job = pipeline.create_job(
        JobCreate(
            title="Backend Intern",
            jd_text="We need backend API, Python, SQL, and GitHub project evidence.",
        )
    )

    candidate = pipeline.add_candidate(
        job.id,
        CandidateCreate(
            name="Tester",
            resume_text="GitHub profile https://github.com/missing-user and Python API experience.",
        ),
    )
    evaluations = pipeline.repository.list_evaluations(job.id)

    assert candidate.github_status == "failed"
    assert candidate.github_failure_reason == "GitHub profile not found."
    assert any("GitHub profile not found." in evidence.snippet for evidence in evaluations[0].evidence)


def test_pipeline_falls_back_to_mock_on_llm_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HIREPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HIREPROOF_UPLOADS_DIR", str(tmp_path / "data" / "uploads"))
    monkeypatch.setenv("HIREPROOF_ARTIFACTS_DIR", str(tmp_path / "data" / "artifacts"))
    monkeypatch.setenv("HIREPROOF_SQLITE_PATH", str(tmp_path / "data" / "artifacts" / "hireproof.db"))
    monkeypatch.setenv("HIREPROOF_EVALUATOR_MODE", "upstage")
    monkeypatch.setenv("HIREPROOF_FALLBACK_TO_MOCK_ON_LLM_ERROR", "true")
    get_settings.cache_clear()

    pipeline = HireProofPipeline(
        github_client=FakeGitHubClient(),
        evaluator=BrokenEvaluator(),
    )
    job = pipeline.create_job(
        JobCreate(
            title="Backend Intern",
            jd_text="We need backend API, Python, SQL, and GitHub project evidence.",
        )
    )
    candidate = pipeline.add_candidate(
        job.id,
        CandidateCreate(
            name="Tester",
            resume_text="Python API project with SQL and GitHub profile https://github.com/example/tester",
        ),
    )
    logs = pipeline.repository.list_audit_logs(job_id=job.id)

    assert candidate.id is not None
    assert any(log.event_type == "llm_fallback_used" for log in logs)
