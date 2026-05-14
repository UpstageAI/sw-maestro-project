"""context_builder.py 단위 테스트 — LLM 호출 모킹."""
import pytest
from unittest.mock import patch
from datetime import datetime
from src.services.context_builder import compress_context, sanitize_files, _format_commits
from src.models.repo import RepoContext, CommitInfo


def _make_commit(sha, msg):
    return CommitInfo(sha=sha, message=msg, author="작성자", date=datetime(2024, 1, 1))


@pytest.fixture
def ctx_with_commits():
    return RepoContext(
        owner="testuser",
        name="testrepo",
        readme="# 테스트 레포\n\nFastAPI 기반 프로젝트입니다.",
        commits=[
            _make_commit("abc1234", "feat: 초기 구현"),
            _make_commit("def5678", "fix: 버그 수정"),
            _make_commit("ghi9012", "refactor: 리팩터링"),
        ],
    )


@pytest.fixture
def ctx_no_data():
    return RepoContext(owner="a", name="b")


class TestFormatCommits:
    def test_formats_commits(self, ctx_with_commits):
        result = _format_commits(ctx_with_commits)
        assert "abc1234" in result
        assert "feat: 초기 구현" in result

    def test_respects_limit(self, ctx_with_commits):
        result = _format_commits(ctx_with_commits, limit=1)
        assert "abc1234" in result
        assert "def5678" not in result

    def test_empty_commits(self, ctx_no_data):
        result = _format_commits(ctx_no_data)
        assert result == ""

    def test_truncates_long_message(self):
        ctx = RepoContext(owner="a", name="b", commits=[
            _make_commit("abc1234", "feat: " + "A" * 200)
        ])
        result = _format_commits(ctx)
        # 포맷: "- sha (date) msg" → maxsplit=3으로 msg 부분만 추출
        lines = result.splitlines()
        msg_part = lines[0].split(" ", 3)[-1]  # "feat: AAA..." 부분
        assert len(msg_part) <= 120


class TestCompressContext:
    def test_no_commits_no_readme(self, ctx_no_data):
        result = compress_context(ctx_no_data)
        assert result.commit_summary == "(커밋/README 없음)"

    @patch("src.services.context_builder.invoke")
    def test_compress_calls_invoke(self, mock_invoke, ctx_with_commits):
        mock_invoke.return_value = "압축된 요약 결과"
        result = compress_context(ctx_with_commits)
        mock_invoke.assert_called_once()
        assert result.commit_summary == "압축된 요약 결과"

    @patch("src.services.context_builder.invoke")
    def test_readme_is_redacted_before_invoke(self, mock_invoke, ctx_with_commits):
        # README에 시크릿이 있으면 redact 후 invoke
        ctx_with_commits.readme = 'api_key = "' + "A" * 20 + '"'
        mock_invoke.return_value = "요약"
        compress_context(ctx_with_commits)
        call_args = mock_invoke.call_args[0][0]
        assert "A" * 20 not in call_args  # redact됨

    @patch("src.services.context_builder.invoke")
    def test_returns_modified_context(self, mock_invoke, ctx_with_commits):
        mock_invoke.return_value = "요약 결과"
        result = compress_context(ctx_with_commits)
        assert result is ctx_with_commits  # 같은 객체 반환

    def test_ctx_with_readme_only(self):
        ctx = RepoContext(owner="a", name="b", readme="# README만 있는 경우")
        with patch("src.services.context_builder.invoke") as mock:
            mock.return_value = "요약"
            result = compress_context(ctx)
        assert result.commit_summary == "요약"


class TestSanitizeFiles:
    def test_redacts_secrets_in_core_files(self):
        ctx = RepoContext(
            owner="a",
            name="b",
            core_files={"config.py": 'api_key = "' + "A" * 20 + '"'},
        )
        result = sanitize_files(ctx)
        assert "A" * 20 not in result.core_files["config.py"]

    def test_redacts_secrets_in_docs_files(self):
        ctx = RepoContext(
            owner="a",
            name="b",
            docs_files={"docs/setup.md": 'token = "' + "B" * 20 + '"'},
        )
        result = sanitize_files(ctx)
        assert "B" * 20 not in result.docs_files["docs/setup.md"]

    def test_redacts_secrets_in_readme(self):
        ctx = RepoContext(
            owner="a",
            name="b",
            readme='secret = "' + "C" * 20 + '"',
        )
        result = sanitize_files(ctx)
        assert "C" * 20 not in result.readme

    def test_no_readme_skipped(self):
        ctx = RepoContext(owner="a", name="b")
        result = sanitize_files(ctx)
        assert result.readme is None

    def test_normal_content_unchanged(self):
        ctx = RepoContext(
            owner="a",
            name="b",
            core_files={"main.py": "def hello():\n    return 'world'"},
        )
        result = sanitize_files(ctx)
        assert result.core_files["main.py"] == "def hello():\n    return 'world'"

    def test_returns_same_context_object(self):
        ctx = RepoContext(owner="a", name="b")
        result = sanitize_files(ctx)
        assert result is ctx
