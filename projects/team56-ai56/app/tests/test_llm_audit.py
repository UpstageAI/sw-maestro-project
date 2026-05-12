from pathlib import Path

from app.config import get_settings
from app.core.models import CandidateCreate, JobCreate
from app.services.evaluator import UpstageEvaluator
from app.services.pipeline import HireProofPipeline


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

    def post(self, url: str, headers: dict, json: dict, timeout: int) -> FakeResponse:
        return FakeResponse(self.responses.pop(0))


def test_pipeline_records_llm_request_and_response_logs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HIREPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HIREPROOF_UPLOADS_DIR", str(tmp_path / "data" / "uploads"))
    monkeypatch.setenv("HIREPROOF_ARTIFACTS_DIR", str(tmp_path / "data" / "artifacts"))
    monkeypatch.setenv("HIREPROOF_SQLITE_PATH", str(tmp_path / "data" / "artifacts" / "hireproof.db"))
    monkeypatch.setenv("HIREPROOF_EVALUATOR_MODE", "upstage")
    get_settings.cache_clear()

    session = FakeSession(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"criteria":[{"name":"Python","description":"Python skill","weight":30},{"name":"SQL","description":"SQL skill","weight":20},{"name":"API","description":"API design","weight":15},{"name":"Projects","description":"Project proof","weight":15},{"name":"Collaboration","description":"Teamwork","weight":10},{"name":"Growth","description":"Learning","weight":10}]}'
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"jd_score":80,"summary":"Strong fit.","evidence":[{"source_type":"resume","source_ref":"candidate:1","snippet":"Python API project","confidence":80}]}'
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"alignment_score":60,"summary":"Supported by artifacts.","evidence":[{"source_type":"github","source_ref":"https://github.com/example/project","snippet":"Relevant repo found","confidence":72}]}'
                        }
                    }
                ]
            },
        ]
    )
    evaluator = UpstageEvaluator(api_key="test-key", model="solar-pro3", session=session)
    pipeline = HireProofPipeline(evaluator=evaluator)

    job = pipeline.create_job(JobCreate(title="Backend", jd_text="Python SQL API backend role"))
    pipeline.add_candidate(
        job.id,
        CandidateCreate(
            name="Tester",
            resume_text="Python API project with SQL and GitHub profile https://github.com/example/tester",
        ),
    )
    logs = pipeline.repository.list_audit_logs(job_id=job.id)
    event_types = [log.event_type for log in logs]

    assert "llm_request" in event_types
    assert "llm_response" in event_types
