from __future__ import annotations

import base64
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from app.core.models import GitHubProfileSnapshot, GitHubRepoSummary


@dataclass
class GitHubFetchResult:
    status: str
    profile: GitHubProfileSnapshot | None = None
    failure_reason: str | None = None


class GitHubClient:
    API_ROOT = "https://api.github.com"
    DEFAULT_HEADERS = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "HireProof-MVP",
    }
    CODE_FILE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".go", ".java", ".rs"}
    PREFERRED_DIRS = {"src", "app", "server", "api", "backend", "frontend", "sql", "lib"}

    def __init__(self, session: requests.Session | None = None, timeout_seconds: int = 10) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    def fetch_profile(self, github_url: str | None) -> GitHubFetchResult:
        if not github_url:
            return GitHubFetchResult(status="skipped", failure_reason="No GitHub URL provided.")

        username = self._extract_username(github_url)
        if not username:
            return GitHubFetchResult(status="failed", failure_reason="Could not parse a GitHub username from the URL.")

        try:
            user_response = self.session.get(
                f"{self.API_ROOT}/users/{username}",
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout_seconds,
            )
            if user_response.status_code == 404:
                return GitHubFetchResult(status="failed", failure_reason="GitHub profile not found.")
            if user_response.status_code == 403:
                return GitHubFetchResult(status="failed", failure_reason="GitHub rate limit or access restriction.")
            user_response.raise_for_status()

            repos_response = self.session.get(
                f"{self.API_ROOT}/users/{username}/repos",
                headers=self.DEFAULT_HEADERS,
                params={"sort": "updated", "per_page": 5, "type": "owner"},
                timeout=self.timeout_seconds,
            )
            if repos_response.status_code == 403:
                return GitHubFetchResult(status="failed", failure_reason="GitHub repository fetch hit a rate limit.")
            repos_response.raise_for_status()
        except requests.RequestException as exc:
            return GitHubFetchResult(status="failed", failure_reason=f"GitHub fetch failed: {exc}")

        user_payload = user_response.json()
        repos_payload = repos_response.json()
        repos: list[GitHubRepoSummary] = []
        for index, repo in enumerate(repos_payload):
            readme_excerpt = self._fetch_readme_excerpt(username, repo["name"]) if index < 2 else None
            language_bytes = self._fetch_repo_languages(username, repo["name"]) if index < 3 else {}
            recent_commits = self._fetch_recent_commits(username, repo["name"]) if index < 3 else []
            root_entries = self._fetch_root_entries(username, repo["name"]) if index < 3 else []
            code_samples = self._fetch_code_samples(username, repo["name"], root_entries) if index < 2 else []
            lowered_entries = {entry.lower() for entry in root_entries}
            repos.append(
                GitHubRepoSummary(
                    name=repo["name"],
                    html_url=repo["html_url"],
                    description=repo.get("description"),
                    language=repo.get("language"),
                    stargazers_count=repo.get("stargazers_count", 0),
                    forks_count=repo.get("forks_count", 0),
                    open_issues_count=repo.get("open_issues_count", 0),
                    topics=repo.get("topics", []) or [],
                    homepage=repo.get("homepage"),
                    readme_excerpt=readme_excerpt,
                    language_bytes=language_bytes,
                    recent_commit_headlines=[item["headline"] for item in recent_commits],
                    recent_commit_timestamps=[item["timestamp"] for item in recent_commits],
                    root_entries=root_entries,
                    sample_code_paths=[item["path"] for item in code_samples],
                    sample_code_signals=[item["signal"] for item in code_samples],
                    detected_frameworks=self._detect_frameworks(
                        [item["content"] for item in code_samples],
                        lowered_entries,
                    ),
                    has_tests=self._has_test_signal(lowered_entries),
                    has_ci=self._has_ci_signal(lowered_entries),
                    has_dockerfile="dockerfile" in lowered_entries,
                    updated_at=repo.get("updated_at"),
                )
            )
        language_counter: Counter[str] = Counter()
        for repo in repos:
            if repo.language_bytes:
                language_counter.update(repo.language_bytes)
            elif repo.language:
                language_counter.update({repo.language: 1})
        top_languages = [language for language, _ in language_counter.most_common(5)]
        last_activity = repos[0].updated_at if repos else user_payload.get("updated_at")
        recent_commit_count = sum(len(repo.recent_commit_headlines) for repo in repos)

        profile = GitHubProfileSnapshot(
            username=user_payload["login"],
            profile_url=user_payload["html_url"],
            display_name=user_payload.get("name"),
            bio=user_payload.get("bio"),
            company=user_payload.get("company"),
            blog=user_payload.get("blog"),
            location=user_payload.get("location"),
            public_repos=user_payload.get("public_repos", 0),
            followers=user_payload.get("followers", 0),
            following=user_payload.get("following", 0),
            top_languages=top_languages,
            recent_repos=repos,
            recent_commit_count=recent_commit_count,
            last_activity_at=last_activity,
        )
        return GitHubFetchResult(status="fetched", profile=profile)

    def _fetch_readme_excerpt(self, owner: str, repo: str) -> str | None:
        try:
            response = self.session.get(
                f"{self.API_ROOT}/repos/{owner}/{repo}/readme",
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return None
            payload = response.json()
            content = payload.get("content")
            encoding = payload.get("encoding")
            if not content or encoding != "base64":
                return None
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            normalized = " ".join(decoded.split())
            return normalized[:240] if normalized else None
        except (requests.RequestException, ValueError, TypeError):
            return None

    def _fetch_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        try:
            response = self.session.get(
                f"{self.API_ROOT}/repos/{owner}/{repo}/languages",
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return {}
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except (requests.RequestException, ValueError, TypeError):
            return {}

    def _fetch_recent_commits(self, owner: str, repo: str) -> list[dict[str, str]]:
        try:
            response = self.session.get(
                f"{self.API_ROOT}/repos/{owner}/{repo}/commits",
                headers=self.DEFAULT_HEADERS,
                params={"per_page": 5},
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return []
            payload = response.json()
            if not isinstance(payload, list):
                return []
            commits: list[dict[str, str]] = []
            for item in payload[:5]:
                commit = item.get("commit", {})
                headline = (commit.get("message") or "").splitlines()[0].strip()
                timestamp = ((commit.get("author") or {}).get("date")) or ""
                if headline:
                    commits.append({"headline": headline, "timestamp": timestamp})
            return commits
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return []

    def _fetch_root_entries(self, owner: str, repo: str) -> list[str]:
        payload = self._fetch_contents(owner, repo)
        if not isinstance(payload, list):
            return []
        return [item.get("name", "") for item in payload if item.get("name")]

    def _fetch_code_samples(self, owner: str, repo: str, root_entries: list[str]) -> list[dict[str, str]]:
        candidates: list[tuple[str, str]] = []
        root_payload = self._fetch_contents(owner, repo)
        if isinstance(root_payload, list):
            candidates.extend(self._collect_file_candidates(root_payload))
            for item in root_payload:
                if item.get("type") == "dir" and item.get("name", "").lower() in self.PREFERRED_DIRS:
                    nested_payload = self._fetch_contents(owner, repo, item.get("path", ""))
                    if isinstance(nested_payload, list):
                        candidates.extend(self._collect_file_candidates(nested_payload))

        seen_paths: set[str] = set()
        samples: list[dict[str, str]] = []
        for path, download_target in candidates:
            if path in seen_paths:
                continue
            seen_paths.add(path)
            content = self._fetch_file_text(owner, repo, download_target)
            if not content:
                continue
            signal = self._summarize_code_signal(path, content)
            samples.append({"path": path, "signal": signal, "content": content})
            if len(samples) >= 3:
                break
        return samples

    def _fetch_contents(self, owner: str, repo: str, path: str = "") -> dict | list | None:
        try:
            url = f"{self.API_ROOT}/repos/{owner}/{repo}/contents"
            if path:
                url += f"/{path}"
            response = self.session.get(
                url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return None
            return response.json()
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return None

    def _collect_file_candidates(self, payload: list[dict]) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        for item in payload:
            if item.get("type") != "file":
                continue
            path = item.get("path", "")
            name = item.get("name", "")
            if not path or not name:
                continue
            if self._is_code_file(name):
                candidates.append((path, path))
        return candidates

    def _fetch_file_text(self, owner: str, repo: str, path: str) -> str | None:
        try:
            response = self.session.get(
                f"{self.API_ROOT}/repos/{owner}/{repo}/contents/{path}",
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout_seconds,
            )
            if response.status_code >= 400:
                return None
            payload = response.json()
            content = payload.get("content")
            encoding = payload.get("encoding")
            if not content or encoding != "base64":
                return None
            decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
            return decoded[:2000]
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            return None

    def _is_code_file(self, name: str) -> bool:
        lowered = name.lower()
        return any(lowered.endswith(ext) for ext in self.CODE_FILE_EXTENSIONS)

    def _detect_frameworks(self, code_texts: list[str], lowered_entries: set[str]) -> list[str]:
        joined = "\n".join(code_texts).lower()
        signals: list[tuple[str, bool]] = [
            ("FastAPI", "fastapi" in joined),
            ("Flask", "flask" in joined),
            ("Django", "django" in joined),
            ("React", "react" in joined or "tsx" in joined),
            ("Express", "express" in joined),
            ("GraphQL", "graphql" in joined),
            ("Pytest", "pytest" in joined or "tests" in lowered_entries),
            ("Docker", "docker" in joined or "dockerfile" in lowered_entries),
            ("SQL", "select " in joined or "insert " in joined or "update " in joined),
        ]
        return [label for label, present in signals if present]

    def _summarize_code_signal(self, path: str, content: str) -> str:
        lowered = content.lower()
        signal_bits: list[str] = [path]
        if "fastapi" in lowered:
            signal_bits.append("FastAPI usage")
        if "router" in lowered or "@app." in lowered:
            signal_bits.append("API route definitions")
        if "pytest" in lowered or "assert " in lowered:
            signal_bits.append("test/assert patterns")
        if "graphql" in lowered:
            signal_bits.append("GraphQL references")
        if "select " in lowered or "insert " in lowered or "update " in lowered:
            signal_bits.append("SQL query patterns")
        if "docker" in lowered:
            signal_bits.append("containerization signal")
        if len(signal_bits) == 1:
            signal_bits.append("general source code present")
        return " | ".join(signal_bits)

    def _has_test_signal(self, lowered_entries: set[str]) -> bool:
        return any(
            entry in lowered_entries
            for entry in {"tests", "test", "__tests__", "pytest.ini", "conftest.py"}
        )

    def _has_ci_signal(self, lowered_entries: set[str]) -> bool:
        return any(
            entry in lowered_entries
            for entry in {".github", ".circleci", ".gitlab-ci.yml"}
        )

    def _extract_username(self, github_url: str) -> str | None:
        parsed = urlparse(github_url)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            return None
        segments = [segment for segment in parsed.path.split("/") if segment]
        if not segments:
            return None
        return segments[0]
