from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.modules.mentor_candidate.schemas import Mentor


def test_mentors_endpoint_returns_mentor_list(monkeypatch):
    mentors = [
        Mentor(
            mentor_id=1,
            name="테스트멘토",
            stacks=["Python"],
            hobbie="",
            target="기술",
            is_overseas=False,
            is_new_mentor=False,
            can_plan=True,
            meeting_mode_preference="온라인",
            domains=["AI"],
            is_certificated=False,
            career=[("테스트회사", 5)],
        )
    ]

    monkeypatch.setattr("app.modules.mentor.router.get_all_mentors", lambda: mentors)

    response = TestClient(app).get("/api/mentors")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "테스트멘토"
