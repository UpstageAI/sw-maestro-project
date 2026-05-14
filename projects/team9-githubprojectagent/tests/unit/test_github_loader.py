"""github_loader.py 단위 테스트 — 순수 함수 + 외부 의존 모킹."""
import io
import tarfile
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

from src.services.github_loader import parse_repo_url, _is_core_path, _fetch_tarball, fetch_repo
from src import config


# ──────────────────────────────────────────────
# parse_repo_url — 순수 함수
# ──────────────────────────────────────────────

class TestParseRepoUrl:
    def test_standard_https_url(self):
        owner, name = parse_repo_url("https://github.com/myuser/myrepo")
        assert owner == "myuser"
        assert name == "myrepo"

    def test_url_with_git_suffix(self):
        owner, name = parse_repo_url("https://github.com/myuser/myrepo.git")
        assert owner == "myuser"

    def test_url_with_trailing_slash(self):
        owner, name = parse_repo_url("https://github.com/myuser/myrepo/")
        assert owner == "myuser"
        assert name == "myrepo"

    def test_ssh_url(self):
        owner, name = parse_repo_url("git@github.com:myuser/myrepo")
        assert owner == "myuser"
        assert name == "myrepo"

    def test_url_with_whitespace(self):
        owner, name = parse_repo_url("  https://github.com/myuser/myrepo  ")
        assert owner == "myuser"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="파싱할 수 없습니다"):
            parse_repo_url("https://not-github.com/repo")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            parse_repo_url("")

    def test_org_repo(self):
        owner, name = parse_repo_url("https://github.com/some-org/some-repo")
        assert owner == "some-org"
        assert name == "some-repo"


# ──────────────────────────────────────────────
# _is_core_path — 순수 함수
# ──────────────────────────────────────────────

class TestIsCorePathFn:
    def test_readme_is_core(self):
        assert _is_core_path("README.md") is True

    def test_dockerfile_is_core(self):
        assert _is_core_path("Dockerfile") is True

    def test_requirements_txt_is_core(self):
        assert _is_core_path("requirements.txt") is True

    def test_src_dir_file_is_core(self):
        assert _is_core_path("src/main.py") is True

    def test_lib_dir_file_is_core(self):
        assert _is_core_path("lib/utils.go") is True

    def test_app_dir_file_is_core(self):
        assert _is_core_path("app/routes.py") is True

    def test_random_file_not_core(self):
        assert _is_core_path("random_file.txt") is False

    def test_test_dir_not_core(self):
        assert _is_core_path("tests/test_main.py") is False

    def test_package_json_is_core(self):
        assert _is_core_path("package.json") is True

    def test_go_mod_is_core(self):
        assert _is_core_path("go.mod") is True


# ──────────────────────────────────────────────
# _fetch_tarball — requests 모킹
# ──────────────────────────────────────────────

def _make_tarball_bytes(files: dict[str, str]) -> bytes:
    """테스트용 tarball 바이트 생성."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            encoded = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"owner-repo-abc1234/{path}")
            info.size = len(encoded)
            tar.addfile(info, io.BytesIO(encoded))
    return buf.getvalue()


class TestFetchTarball:
    def test_extracts_core_files(self):
        tarball = _make_tarball_bytes({"src/main.py": "print('hello')"})
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = tarball
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            core, docs = _fetch_tarball("owner", "repo", "main", None, lambda _: None)
        assert "src/main.py" in core

    def test_extracts_docs_files(self):
        tarball = _make_tarball_bytes({"docs/guide.md": "# 가이드"})
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = tarball
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            core, docs = _fetch_tarball("owner", "repo", "main", None, lambda _: None)
        assert "docs/guide.md" in docs

    def test_403_raises_value_error(self):
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.content = b""
            mock_get.return_value = mock_resp
            with pytest.raises(ValueError, match="403"):
                _fetch_tarball("owner", "repo", "main", None, lambda _: None)

    def test_404_raises_value_error(self):
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.content = b""
            mock_get.return_value = mock_resp
            with pytest.raises(ValueError, match="404"):
                _fetch_tarball("owner", "repo", "main", None, lambda _: None)

    def test_too_large_tarball_raises(self):
        huge = b"x" * (50 * 1024 * 1024 + 1)
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = huge
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            with pytest.raises(ValueError, match="너무 큼"):
                _fetch_tarball("owner", "repo", "main", None, lambda _: None)

    def test_request_exception_raises(self):
        import requests as req_lib
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_get.side_effect = req_lib.RequestException("연결 실패")
            with pytest.raises(ValueError, match="다운로드 실패"):
                _fetch_tarball("owner", "repo", "main", None, lambda _: None)

    def test_uses_token_in_header(self):
        tarball = _make_tarball_bytes({})
        with patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = tarball
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            _fetch_tarball("owner", "repo", "main", "mytoken", lambda _: None)
            headers = mock_get.call_args[1]["headers"]
            assert "mytoken" in headers.get("Authorization", "")


# ──────────────────────────────────────────────
# fetch_repo — Github 객체 완전 모킹
# ──────────────────────────────────────────────

def _make_mock_github(repo_name="testuser/testrepo"):
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_gh.get_repo.return_value = mock_repo
    mock_repo.description = "테스트 레포"
    mock_repo.language = "Python"
    mock_repo.stargazers_count = 10
    mock_repo.forks_count = 2
    mock_repo.private = False
    mock_repo.default_branch = "main"
    mock_repo.get_topics.return_value = ["python", "fastapi"]

    # README
    mock_readme = MagicMock()
    mock_readme.decoded_content = b"# Hello"
    mock_repo.get_readme.return_value = mock_readme

    # rate limit
    mock_rl = MagicMock()
    mock_rl.core.remaining = 100
    mock_rl.core.limit = 5000
    mock_rl.core.reset.strftime.return_value = "12:00:00"
    mock_gh.get_rate_limit.return_value = mock_rl

    # commits
    mock_commit = MagicMock()
    mock_commit.sha = "abc1234"
    mock_commit.commit.message = "feat: 테스트"
    mock_commit.commit.author.name = "작성자"
    mock_commit.commit.author.date = datetime(2024, 1, 1)
    mock_repo.get_commits.return_value.__getitem__ = MagicMock(return_value=[mock_commit])
    mock_repo.get_commits.return_value.__iter__ = MagicMock(return_value=iter([mock_commit]))

    return mock_gh, mock_repo


class TestFetchRepo:
    def test_fetch_repo_returns_repo_context(self):
        tarball = _make_tarball_bytes({"src/main.py": "code"})
        mock_gh, mock_repo = _make_mock_github()
        with patch("src.services.github_loader.Github", return_value=mock_gh), \
             patch("src.services.github_loader.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = tarball
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            from src.models.repo import RepoContext
            ctx = fetch_repo("https://github.com/testuser/testrepo", pat="mytoken")
        assert ctx.owner == "testuser"
        assert ctx.name == "testrepo"

    def test_fetch_repo_no_pat_uses_anonymous(self):
        tarball = _make_tarball_bytes({})
        mock_gh, mock_repo = _make_mock_github()
        with patch("src.services.github_loader.Github", return_value=mock_gh), \
             patch("src.services.github_loader.requests.get") as mock_get, \
             patch("src.services.github_loader.config") as mock_cfg:
            mock_cfg.GITHUB_PAT_DEFAULT = ""
            mock_cfg.MAX_COMMITS_FETCH = 10
            mock_cfg.MAX_FILES_FETCH = 30
            mock_cfg.MAX_FILE_SIZE_KB = 200
            mock_cfg.CORE_FILES = config.CORE_FILES
            mock_cfg.CORE_DIRS = config.CORE_DIRS
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = tarball
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            ctx = fetch_repo("https://github.com/testuser/testrepo")
        assert ctx.owner == "testuser"

    def test_fetch_repo_tarball_failure_continues(self):
        """tarball 실패 시 빈 파일 세트로 진행 (예외 전파 안 함)."""
        mock_gh, mock_repo = _make_mock_github()
        import requests as req_lib
        with patch("src.services.github_loader.Github", return_value=mock_gh), \
             patch("src.services.github_loader.requests.get") as mock_get:
            mock_get.side_effect = req_lib.RequestException("네트워크 오류")
            ctx = fetch_repo("https://github.com/testuser/testrepo", pat="mytoken")
        assert ctx.core_files == {}
        assert ctx.docs_files == {}
