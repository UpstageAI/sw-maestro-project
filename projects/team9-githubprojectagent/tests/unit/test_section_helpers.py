"""section_helpers.py 순수 함수 단위 테스트."""
import pytest
from datetime import datetime
from src.tools.section_helpers import (
    extract_repo_metadata,
    detect_tech_stack,
    summarize_directory_tree,
    _classify,
    summarize_commits_by_topic,
    find_bugfix_commits,
    find_perf_commits,
    parse_changelog,
    read_file,
    search_code,
    make_tools,
)
from src.models.repo import RepoContext, CommitInfo


def _commit(sha, msg, date_str="2024-01-01"):
    return CommitInfo(
        sha=sha,
        message=msg,
        author="테스터",
        date=datetime.fromisoformat(date_str),
    )


@pytest.fixture
def rich_ctx():
    return RepoContext(
        owner="myuser",
        name="myrepo",
        description="FastAPI 기반 AI 에이전트",
        topics=["fastapi", "llm", "python"],
        primary_language="Python",
        stars=42,
        forks=5,
        commits=[
            _commit("abc1234", "feat: 초기 구현", "2024-01-01"),
            _commit("def5678", "fix: 버그 수정", "2024-02-01"),
            _commit("ghi9012", "perf: 성능 개선", "2024-03-01"),
            _commit("jkl3456", "refactor: 리팩터링", "2024-04-01"),
            _commit("mno7890", "chore: 의존성 업데이트", "2024-05-01"),
        ],
        core_files={
            "requirements.txt": "fastapi==0.115.0\nuvicorn==0.34.0\nlangchain==0.3.0",
            "Dockerfile": "FROM python:3.11\nCOPY . .\nRUN pip install -r requirements.txt",
            "docker-compose.yml": "version: '3'\nservices:\n  app:\n    build: .",
            "src/main.py": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'ok': True}",
            "CHANGELOG.md": "# Changelog\n## v1.0.0\n- 초기 릴리즈",
        },
        docs_files={
            "docs/arch.md": "# 아키텍처\n설명",
        },
    )


@pytest.fixture
def empty_ctx():
    return RepoContext(owner="a", name="b")


# ──────────────────────────────────────────────
# extract_repo_metadata
# ──────────────────────────────────────────────

class TestExtractRepoMetadata:
    def test_contains_full_name(self, rich_ctx):
        result = extract_repo_metadata(rich_ctx)
        assert "myuser/myrepo" in result

    def test_contains_description(self, rich_ctx):
        assert "FastAPI 기반 AI 에이전트" in extract_repo_metadata(rich_ctx)

    def test_contains_topics(self, rich_ctx):
        result = extract_repo_metadata(rich_ctx)
        assert "fastapi" in result

    def test_contains_language(self, rich_ctx):
        assert "Python" in extract_repo_metadata(rich_ctx)

    def test_contains_stars_forks(self, rich_ctx):
        result = extract_repo_metadata(rich_ctx)
        assert "42" in result and "5" in result

    def test_contains_first_commit(self, rich_ctx):
        result = extract_repo_metadata(rich_ctx)
        assert "mno7890" in result  # commits[-1]

    def test_no_commits(self, empty_ctx):
        result = extract_repo_metadata(empty_ctx)
        assert "a/b" in result
        assert "(없음)" in result  # description 없음


# ──────────────────────────────────────────────
# detect_tech_stack
# ──────────────────────────────────────────────

class TestDetectTechStack:
    def test_detects_python_requirements(self, rich_ctx):
        result = detect_tech_stack(rich_ctx)
        assert "Python" in result
        assert "fastapi" in result

    def test_detects_dockerfile(self, rich_ctx):
        assert "Docker" in detect_tech_stack(rich_ctx)

    def test_detects_docker_compose(self, rich_ctx):
        assert "Docker Compose" in detect_tech_stack(rich_ctx)

    def test_no_manifest_fallback(self, empty_ctx):
        assert "감지된 manifest 없음" in detect_tech_stack(empty_ctx)

    def test_detects_package_json(self):
        ctx = RepoContext(owner="a", name="b", core_files={
            "package.json": '{"dependencies": {"express": "^4.18.0", "react": "^18.0.0"}}'
        })
        result = detect_tech_stack(ctx)
        assert "JavaScript" in result
        assert "express" in result

    def test_detects_go_mod(self):
        ctx = RepoContext(owner="a", name="b", core_files={"go.mod": "module example.com\ngo 1.21"})
        assert "Go" in detect_tech_stack(ctx)

    def test_detects_cargo_toml(self):
        ctx = RepoContext(owner="a", name="b", core_files={"Cargo.toml": '[package]\nname = "myapp"'})
        assert "Rust" in detect_tech_stack(ctx)

    def test_detects_pyproject_toml(self):
        ctx = RepoContext(owner="a", name="b", core_files={"pyproject.toml": "[tool.poetry]\nname = 'app'"})
        assert "pyproject.toml" in detect_tech_stack(ctx)

    def test_invalid_package_json_skipped(self):
        ctx = RepoContext(owner="a", name="b", core_files={"package.json": "not json!"})
        result = detect_tech_stack(ctx)
        assert "JavaScript" not in result  # JSON 파싱 실패 → 스킵


# ──────────────────────────────────────────────
# summarize_directory_tree
# ──────────────────────────────────────────────

class TestSummarizeDirectoryTree:
    def test_shows_directories(self, rich_ctx):
        result = summarize_directory_tree(rich_ctx)
        assert "src" in result

    def test_shows_root_files(self, rich_ctx):
        result = summarize_directory_tree(rich_ctx)
        assert "(root)" in result

    def test_empty_ctx_fallback(self, empty_ctx):
        assert "파일 없음" in summarize_directory_tree(empty_ctx)

    def test_limits_files_per_dir(self):
        # 디렉토리당 8개 초과 시 "... 외 N개" 표시
        files = {f"src/file{i}.py": "content" for i in range(12)}
        ctx = RepoContext(owner="a", name="b", core_files=files)
        result = summarize_directory_tree(ctx)
        assert "외" in result


# ──────────────────────────────────────────────
# _classify
# ──────────────────────────────────────────────

class TestClassify:
    def test_feat_prefix(self):
        assert _classify("feat: 새 기능 추가") == "feat"

    def test_fix_prefix(self):
        assert _classify("fix: 버그 수정") == "fix"

    def test_bugfix_maps_to_fix(self):
        assert _classify("bugfix: 로그인 오류 수정") == "fix"

    def test_hotfix_maps_to_fix(self):
        assert _classify("hotfix: 긴급 수정") == "fix"

    def test_perf_prefix(self):
        assert _classify("perf: 쿼리 최적화") == "perf"

    def test_refactor_prefix(self):
        assert _classify("refactor: 코드 정리") == "refactor"

    def test_korean_bug_keyword(self):
        assert _classify("버그 수정했습니다") == "fix"

    def test_korean_refactor_keyword(self):
        assert _classify("리팩터링 완료") == "refactor"

    def test_korean_perf_keyword(self):
        assert _classify("성능 개선") == "perf"

    def test_korean_feat_keyword(self):
        assert _classify("기능 추가") == "feat"

    def test_unknown_becomes_other(self):
        assert _classify("타입 미분류 커밋 메시지") == "other"

    def test_feat_with_scope(self):
        assert _classify("feat(auth): OAuth 추가") == "feat"


# ──────────────────────────────────────────────
# summarize_commits_by_topic
# ──────────────────────────────────────────────

class TestSummarizeCommitsByTopic:
    def test_returns_distribution(self, rich_ctx):
        result = summarize_commits_by_topic(rich_ctx)
        assert "전체 분포" in result

    def test_shows_feat_commits(self, rich_ctx):
        result = summarize_commits_by_topic(rich_ctx)
        assert "feat" in result

    def test_shows_fix_commits(self, rich_ctx):
        result = summarize_commits_by_topic(rich_ctx)
        assert "fix" in result

    def test_empty_commits(self, empty_ctx):
        result = summarize_commits_by_topic(empty_ctx)
        assert "전체 분포" in result


# ──────────────────────────────────────────────
# find_bugfix_commits / find_perf_commits
# ──────────────────────────────────────────────

class TestFindBugfixCommits:
    def test_finds_fix_commits(self, rich_ctx):
        result = find_bugfix_commits(rich_ctx)
        assert "def5678" in result

    def test_no_fix_commits(self, empty_ctx):
        assert "버그 픽스 커밋 없음" in find_bugfix_commits(empty_ctx)

    def test_limit_respected(self, rich_ctx):
        result = find_bugfix_commits(rich_ctx, limit=1)
        # limit=1 이면 최대 1개만
        assert result.count("def5678") <= 1


class TestFindPerfCommits:
    def test_finds_perf_commits(self, rich_ctx):
        result = find_perf_commits(rich_ctx)
        assert "ghi9012" in result

    def test_no_perf_commits(self, empty_ctx):
        assert "성능 관련 커밋 없음" in find_perf_commits(empty_ctx)


# ──────────────────────────────────────────────
# parse_changelog
# ──────────────────────────────────────────────

class TestParseChangelog:
    def test_finds_changelog(self, rich_ctx):
        result = parse_changelog(rich_ctx)
        assert result is not None
        assert "Changelog" in result

    def test_returns_none_when_missing(self, empty_ctx):
        assert parse_changelog(empty_ctx) is None

    def test_finds_releases_md(self):
        ctx = RepoContext(owner="a", name="b", core_files={
            "RELEASES.md": "# Releases\n## v2.0.0\n- 주요 변경"
        })
        assert "Releases" in parse_changelog(ctx)

    def test_truncates_to_3000_chars(self):
        ctx = RepoContext(owner="a", name="b", core_files={
            "CHANGELOG.md": "# " + "A" * 5000
        })
        result = parse_changelog(ctx)
        assert len(result) <= 3000


# ──────────────────────────────────────────────
# read_file / search_code
# ──────────────────────────────────────────────

class TestReadFile:
    def test_reads_core_file(self, rich_ctx):
        content = read_file(rich_ctx, "src/main.py")
        assert "FastAPI" in content

    def test_reads_docs_file(self, rich_ctx):
        content = read_file(rich_ctx, "docs/arch.md")
        assert "아키텍처" in content

    def test_missing_file_returns_placeholder(self, rich_ctx):
        assert "파일 없음" in read_file(rich_ctx, "nonexistent.py")


class TestSearchCode:
    def test_finds_pattern(self, rich_ctx):
        result = search_code(rich_ctx, "FastAPI")
        assert "src/main.py" in result

    def test_no_match_returns_placeholder(self, rich_ctx):
        result = search_code(rich_ctx, "XYZXYZXYZ_NOTFOUND")
        assert "매치 없음" in result

    def test_max_hits_respected(self, rich_ctx):
        # 모든 파일에서 매치되는 패턴
        result = search_code(rich_ctx, ".", max_hits=2)
        lines = [l for l in result.splitlines() if ":" in l]
        assert len(lines) <= 2

    def test_empty_ctx(self, empty_ctx):
        assert "매치 없음" in search_code(empty_ctx, "anything")


# ──────────────────────────────────────────────
# make_tools
# ──────────────────────────────────────────────

class TestMakeTools:
    def test_returns_list(self, rich_ctx):
        tools = make_tools(rich_ctx)
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_names_unique(self, rich_ctx):
        tools = make_tools(rich_ctx)
        names = [t.name for t in tools]
        assert len(names) == len(set(names))

    def test_has_extract_repo_metadata(self, rich_ctx):
        tools = make_tools(rich_ctx)
        names = [t.name for t in tools]
        assert "extract_repo_metadata" in names

    def test_has_search_code(self, rich_ctx):
        tools = make_tools(rich_ctx)
        names = [t.name for t in tools]
        assert "search_code" in names

    def test_extract_repo_metadata_tool_callable(self, rich_ctx):
        tools = make_tools(rich_ctx)
        tool = next(t for t in tools if t.name == "extract_repo_metadata")
        result = tool.invoke({})
        assert "myuser/myrepo" in result

    def test_read_file_tool_callable(self, rich_ctx):
        tools = make_tools(rich_ctx)
        tool = next(t for t in tools if t.name == "read_file")
        result = tool.invoke({"path": "src/main.py"})
        assert "FastAPI" in result

    def test_all_expected_tools_present(self, rich_ctx):
        tools = make_tools(rich_ctx)
        names = {t.name for t in tools}
        expected = {
            "extract_repo_metadata", "detect_tech_stack", "summarize_directory_tree",
            "summarize_commits_by_topic", "find_bugfix_commits", "find_perf_commits",
            "parse_changelog", "read_file", "search_code",
        }
        assert expected == names
