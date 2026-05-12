from app.services.github_client import GitHubClient


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | list) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict | list:
        return self._payload


class FakeSession:
    def get(self, url: str, headers: dict, timeout: int, params: dict | None = None) -> FakeResponse:
        if url.endswith("/users/example"):
            return FakeResponse(
                200,
                {
                    "login": "example",
                    "html_url": "https://github.com/example",
                    "name": "Example User",
                    "bio": "Builds backend systems",
                    "public_repos": 12,
                    "followers": 5,
                    "following": 2,
                },
            )
        if url.endswith("/users/example/repos"):
            return FakeResponse(
                200,
                [
                    {
                        "name": "backend-service",
                    "html_url": "https://github.com/example/backend-service",
                    "description": "Service API",
                    "language": "Python",
                    "stargazers_count": 7,
                    "forks_count": 1,
                    "open_issues_count": 2,
                    "topics": ["fastapi", "backend"],
                    "homepage": "https://example.com/backend-service",
                    "updated_at": "2026-05-04T12:00:00Z",
                },
                {
                    "name": "data-pipeline",
                    "html_url": "https://github.com/example/data-pipeline",
                    "description": "ETL work",
                    "language": "SQL",
                    "stargazers_count": 2,
                    "forks_count": 0,
                    "open_issues_count": 0,
                    "topics": ["sql", "etl"],
                    "homepage": None,
                    "updated_at": "2026-05-01T12:00:00Z",
                },
            ],
        )
        if url.endswith("/repos/example/backend-service/readme"):
            return FakeResponse(
                200,
                {
                    "content": "IyBCYWNrZW5kIFNlcnZpY2UKRmFzdEFQSSBiYXNlZCBzZXJ2aWNlIGZvciBvcmRlciBwcm9jZXNzaW5nLg==",
                    "encoding": "base64",
                },
            )
        if url.endswith("/repos/example/data-pipeline/readme"):
            return FakeResponse(
                200,
                {
                    "content": "IyBEYXRhIFBpcGVsaW5lClNRTCBhbmQgRVRMIHV0aWxpdHku",
                    "encoding": "base64",
                },
            )
        if url.endswith("/repos/example/backend-service/languages"):
            return FakeResponse(200, {"Python": 15000, "SQL": 4000})
        if url.endswith("/repos/example/data-pipeline/languages"):
            return FakeResponse(200, {"SQL": 12000, "Python": 2000})
        if url.endswith("/repos/example/backend-service/commits"):
            return FakeResponse(
                200,
                [
                    {"commit": {"message": "Add API tests\n\nMore body", "author": {"date": "2026-05-04T10:00:00Z"}}},
                    {"commit": {"message": "Refactor service layer", "author": {"date": "2026-05-03T10:00:00Z"}}},
                ],
            )
        if url.endswith("/repos/example/data-pipeline/commits"):
            return FakeResponse(
                200,
                [
                    {"commit": {"message": "Tune SQL aggregation", "author": {"date": "2026-05-01T10:00:00Z"}}},
                ],
            )
        if url.endswith("/repos/example/backend-service/contents"):
            return FakeResponse(
                200,
                [
                    {"name": "README.md"},
                    {"name": "tests"},
                    {"name": ".github"},
                    {"name": "Dockerfile"},
                    {"name": "src", "path": "src", "type": "dir"},
                ],
            )
        if url.endswith("/repos/example/data-pipeline/contents"):
            return FakeResponse(
                200,
                [
                    {"name": "README.md"},
                    {"name": "sql"},
                    {"name": "queries.sql", "path": "queries.sql", "type": "file"},
                ],
            )
        if url.endswith("/repos/example/backend-service/contents/src"):
            return FakeResponse(
                200,
                [
                    {"name": "main.py", "path": "src/main.py", "type": "file"},
                    {"name": "router.py", "path": "src/router.py", "type": "file"},
                ],
            )
        if url.endswith("/repos/example/backend-service/contents/src/main.py"):
            return FakeResponse(
                200,
                {
                    "content": "ZnJvbSBmYXN0YXBpIGltcG9ydCBGYXN0QVBJCmFwcCA9IEZhc3RBUEkoKQo=",
                    "encoding": "base64",
                },
            )
        if url.endswith("/repos/example/backend-service/contents/src/router.py"):
            return FakeResponse(
                200,
                {
                    "content": "ZnJvbSBmYXN0YXBpIGltcG9ydCBBUElSb3V0ZXIKcm91dGVyID0gQVBJUm91dGVyKCkKQHJvdXRlci5nZXQoJy9oZWFsdGgnKQpkZWYgaGVhbHRoKCk6CiAgICByZXR1cm4geydvayc6IFRydWV9Cg==",
                    "encoding": "base64",
                },
            )
        if url.endswith("/repos/example/data-pipeline/contents/queries.sql"):
            return FakeResponse(
                200,
                {
                    "content": "U0VMRUNUICogRlJPTSBldmVudHMgV0hFUkUgdHlwZSA9ICdjbGljayc7",
                    "encoding": "base64",
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")


def test_github_client_fetches_profile_snapshot() -> None:
    client = GitHubClient(session=FakeSession())
    result = client.fetch_profile("https://github.com/example")

    assert result.status == "fetched"
    assert result.profile is not None
    assert result.profile.username == "example"
    assert result.profile.top_languages == ["Python", "SQL"]
    assert len(result.profile.recent_repos) == 2
    assert result.profile.recent_commit_count == 3
    assert result.profile.recent_repos[0].topics == ["fastapi", "backend"]
    assert result.profile.recent_repos[0].readme_excerpt is not None
    assert result.profile.recent_repos[0].language_bytes["Python"] == 15000
    assert result.profile.recent_repos[0].recent_commit_headlines[0] == "Add API tests"
    assert result.profile.recent_repos[0].has_tests is True
    assert result.profile.recent_repos[0].has_ci is True
    assert result.profile.recent_repos[0].has_dockerfile is True
    assert result.profile.recent_repos[0].sample_code_paths == ["src/main.py", "src/router.py"]
    assert "FastAPI" in result.profile.recent_repos[0].detected_frameworks
    assert any("API route definitions" in item for item in result.profile.recent_repos[0].sample_code_signals)


def test_github_client_rejects_non_github_url() -> None:
    client = GitHubClient(session=FakeSession())
    result = client.fetch_profile("https://notgithub.com/example")

    assert result.status == "failed"
    assert result.failure_reason == "Could not parse a GitHub username from the URL."
