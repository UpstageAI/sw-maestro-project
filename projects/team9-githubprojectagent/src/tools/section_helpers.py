"""섹션별 deterministic 헬퍼 + LangChain Tool 래퍼.

두 가지 인터페이스를 동시에 제공:
1. **순수 함수** (`extract_repo_metadata(ctx)` 등) — orchestrator/agent에서 직접 호출
2. **`@tool` 래퍼** (`make_tools(ctx)`) — LangGraph/LLM이 tool calling으로 호출 가능
   각 도구는 Pydantic args_schema로 *파라미터별* 상세 description 포함.

모든 함수는 *이미 in-memory에 적재된* RepoContext 위에서만 동작 — GitHub API 재호출 X.
"""
import json
import re
from collections import Counter, defaultdict
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.models.repo import CommitInfo, RepoContext


# ============================================================
# 순수 함수 (deterministic)
# ============================================================

# === 문제 인식 ===

def extract_repo_metadata(ctx: RepoContext) -> str:
    first = ctx.commits[-1] if ctx.commits else None
    parts = [
        f"- 레포: {ctx.full_name}",
        f"- 설명: {ctx.description or '(없음)'}",
        f"- 토픽: {', '.join(ctx.topics) if ctx.topics else '(없음)'}",
        f"- 주 언어: {ctx.primary_language or '(없음)'}",
        f"- 스타/포크: {ctx.stars}/{ctx.forks}",
    ]
    if first:
        parts.append(
            f"- 첫 커밋: {first.sha} ({first.date.date()}) "
            f"{first.message.splitlines()[0][:120]}"
        )
    return "\n".join(parts)


# === 현황 파악 ===

def detect_tech_stack(ctx: RepoContext) -> str:
    out: list[str] = []
    pj = ctx.core_files.get("package.json")
    if pj:
        try:
            data = json.loads(pj)
            deps = list(data.get("dependencies", {}).keys()) + list(
                data.get("devDependencies", {}).keys()
            )
            out.append(f"**JavaScript/TypeScript** — {', '.join(deps[:25]) or '(없음)'}")
        except json.JSONDecodeError:
            pass
    if "requirements.txt" in ctx.core_files:
        reqs = [
            line.split("==")[0].split(">=")[0].strip()
            for line in ctx.core_files["requirements.txt"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        out.append(f"**Python (requirements.txt)** — {', '.join(reqs[:25])}")
    if "pyproject.toml" in ctx.core_files:
        out.append("**Python (pyproject.toml)** 존재")
    if "go.mod" in ctx.core_files:
        out.append("**Go** — go.mod 존재")
    if "Cargo.toml" in ctx.core_files:
        out.append("**Rust** — Cargo.toml 존재")
    if "Dockerfile" in ctx.core_files:
        out.append("**Docker** — Dockerfile 존재")
    if "docker-compose.yml" in ctx.core_files:
        out.append("**Docker Compose** 존재")
    return "\n".join(f"- {x}" for x in out) if out else "- (감지된 manifest 없음)"


def summarize_directory_tree(ctx: RepoContext) -> str:
    paths = list(ctx.core_files.keys()) + list(ctx.docs_files.keys())
    by_top = defaultdict(list)
    for p in paths:
        top = p.split("/")[0] if "/" in p else "(root)"
        by_top[top].append(p)
    lines = []
    for top, files in sorted(by_top.items()):
        lines.append(f"- **{top}/** ({len(files)}개)")
        for f in files[:8]:
            lines.append(f"  - {f}")
        if len(files) > 8:
            lines.append(f"  - ... 외 {len(files) - 8}개")
    return "\n".join(lines) if lines else "- (파일 없음)"


# === 원인 분석 및 해결책 ===

CONVENTIONAL = re.compile(
    r"^(?P<type>feat|fix|bugfix|hotfix|perf|refactor|chore|docs|test|build|ci|style|revert)"
    r"(?:\([^)]+\))?!?:\s*(?P<msg>.+)",
    re.IGNORECASE,
)


def _classify(msg: str) -> str:
    m = CONVENTIONAL.match(msg.strip())
    if m:
        t = m.group("type").lower()
        return {"bugfix": "fix", "hotfix": "fix"}.get(t, t)
    low = msg.lower()
    if any(k in low for k in ["fix ", "버그", "오류", "에러"]):
        return "fix"
    if any(k in low for k in ["refactor", "리팩"]):
        return "refactor"
    if any(k in low for k in ["perf", "optimize", "성능"]):
        return "perf"
    if any(k in low for k in ["feat", "add ", "추가", "기능"]):
        return "feat"
    return "other"


def summarize_commits_by_topic(ctx: RepoContext) -> str:
    groups: dict[str, list[CommitInfo]] = defaultdict(list)
    for c in ctx.commits:
        first_line = c.message.splitlines()[0]
        groups[_classify(first_line)].append(c)
    out = []
    counts = Counter({k: len(v) for k, v in groups.items()})
    out.append("**전체 분포**: " + ", ".join(f"{k}={n}" for k, n in counts.most_common()))
    for kind in ["feat", "fix", "perf", "refactor", "other"]:
        items = groups.get(kind, [])[:5]
        if not items:
            continue
        out.append(f"\n**{kind}** (상위 {len(items)}개)")
        for c in items:
            out.append(f"- {c.sha} {c.message.splitlines()[0][:100]}")
    return "\n".join(out)


def find_bugfix_commits(ctx: RepoContext, limit: int = 12) -> str:
    fixes = [c for c in ctx.commits if _classify(c.message.splitlines()[0]) == "fix"]
    if not fixes:
        return "(버그 픽스 커밋 없음)"
    lines = [
        f"- {c.sha} ({c.date.date()}) {c.message.splitlines()[0][:130]}"
        for c in fixes[:limit]
    ]
    return "\n".join(lines)


# === 결과 정리 및 성능 향상 ===

def find_perf_commits(ctx: RepoContext, limit: int = 10) -> str:
    perf = [c for c in ctx.commits if _classify(c.message.splitlines()[0]) == "perf"]
    if not perf:
        return "(성능 관련 커밋 없음)"
    lines = [
        f"- {c.sha} ({c.date.date()}) {c.message.splitlines()[0][:130]}"
        for c in perf[:limit]
    ]
    return "\n".join(lines)


def parse_changelog(ctx: RepoContext) -> Optional[str]:
    for key in ("CHANGELOG.md", "RELEASES.md"):
        if key in ctx.core_files:
            return ctx.core_files[key][:3000]
    return None


# === Cross-cutting ===

def read_file(ctx: RepoContext, path: str) -> str:
    return ctx.core_files.get(path) or ctx.docs_files.get(path) or "(파일 없음)"


def search_code(ctx: RepoContext, pattern: str, max_hits: int = 20) -> str:
    rx = re.compile(pattern)
    hits: list[str] = []
    for path, content in {**ctx.core_files, **ctx.docs_files}.items():
        for i, line in enumerate(content.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{path}:{i}: {line.strip()[:160]}")
                if len(hits) >= max_hits:
                    return "\n".join(hits)
    return "\n".join(hits) if hits else "(매치 없음)"


# ============================================================
# LangChain Tool 래퍼 — Pydantic args_schema로 파라미터별 상세 description
# ============================================================
# tool calling LLM은 args_schema의 description을 읽어서 무엇을 호출할지 결정.
# 따라서 각 파라미터에 *왜 쓰는지, 어떤 값이 적절한지, 예시*까지 적어둔다.


class _ReadFileArgs(BaseModel):
    path: str = Field(
        description=(
            "읽을 파일의 레포 루트 기준 상대 경로. "
            "예: 'src/main.py', 'package.json', 'docs/architecture.md'. "
            "디렉토리 경로 X — 정확한 파일 경로만. "
            "GitHub Loader가 미리 가져온 코어/문서 파일 안에 있어야 매치."
        )
    )


class _SearchCodeArgs(BaseModel):
    pattern: str = Field(
        description=(
            "정규식 패턴. 파이썬 `re` 문법. "
            "예시: "
            r"'def \w+_handler' (핸들러 함수), "
            "'TODO|FIXME' (리뷰 마커), "
            "'class \\w+Manager' (매니저 클래스). "
            "모든 코어/문서 파일의 모든 라인에 매치 시도."
        )
    )
    max_hits: int = Field(
        default=20,
        ge=1, le=200,
        description=(
            "반환할 최대 매치 수. 기본 20. "
            "넓은 패턴(.*, \\w+ 등)으로 결과 폭주 방지. "
            "결과가 부족하면 패턴을 더 좁게 다시 호출하는 게 효율적."
        ),
    )


class _CommitsByTopicArgs(BaseModel):
    pass  # 인자 없음


class _BugfixCommitsArgs(BaseModel):
    limit: int = Field(
        default=12, ge=1, le=50,
        description=(
            "반환할 최대 버그픽스 커밋 수. 기본 12. "
            "너무 많으면 LLM 컨텍스트 낭비, 너무 적으면 패턴 파악 어려움."
        ),
    )


class _PerfCommitsArgs(BaseModel):
    limit: int = Field(
        default=10, ge=1, le=50,
        description="반환할 최대 성능 커밋 수. 기본 10.",
    )


class _NoArgs(BaseModel):
    pass


def make_tools(ctx: RepoContext) -> list[StructuredTool]:
    """주어진 RepoContext에 바인딩된 Tool 리스트.

    LangGraph 노드/에이전트에서 LLM에 bind_tools 할 때 사용.
    각 도구는 ctx에 클로저로 묶여 있어 LLM이 path/pattern만 결정하면 동작.
    """
    return [
        StructuredTool.from_function(
            name="extract_repo_metadata",
            description=(
                "레포의 정적 메타정보를 텍스트로 반환. "
                "포함: 레포 풀네임, 설명, 토픽, 주 언어, 스타/포크 수, 첫 커밋 SHA·날짜·메시지. "
                "어떤 입력도 받지 않음. *문제 인식* 섹션의 '배경'을 작성할 때 우선 호출."
            ),
            func=lambda: extract_repo_metadata(ctx),
            args_schema=_NoArgs,
        ),
        StructuredTool.from_function(
            name="detect_tech_stack",
            description=(
                "package.json/requirements.txt/pyproject.toml/go.mod/Cargo.toml/Dockerfile 등 "
                "manifest 파일을 파싱해 감지된 기술 스택을 마크다운 불릿 리스트로 반환. "
                "추론 X — 실제 manifest에 있는 것만. *현황 파악* 섹션의 기술스택 작성에 사용."
            ),
            func=lambda: detect_tech_stack(ctx),
            args_schema=_NoArgs,
        ),
        StructuredTool.from_function(
            name="summarize_directory_tree",
            description=(
                "코어 디렉토리(src/lib/app 등) + docs/의 파일들을 최상위 디렉토리별로 그룹화한 "
                "마크다운 트리 반환. 디렉토리당 최대 8개 파일 표시. "
                "*현황 파악*의 아키텍처/구성 작성에 사용."
            ),
            func=lambda: summarize_directory_tree(ctx),
            args_schema=_NoArgs,
        ),
        StructuredTool.from_function(
            name="summarize_commits_by_topic",
            description=(
                "Conventional Commits 프리픽스(feat/fix/perf/refactor 등) + 한국어 키워드 "
                "휴리스틱으로 모든 커밋을 분류, 토픽별 분포와 상위 5개 커밋 리스트 반환. "
                "*원인 분석 및 해결책* 섹션에서 개발 흐름 파악에 사용."
            ),
            func=lambda: summarize_commits_by_topic(ctx),
            args_schema=_CommitsByTopicArgs,
        ),
        StructuredTool.from_function(
            name="find_bugfix_commits",
            description=(
                "fix:/bugfix:/hotfix: 프리픽스 또는 한국어 '버그/오류/에러' 키워드를 가진 "
                "커밋만 필터링해 SHA, 날짜, 메시지 첫 줄 반환. "
                "*원인 분석 및 해결책* 섹션에서 실제 발생한 문제 인용 시 사용."
            ),
            func=lambda limit=12: find_bugfix_commits(ctx, limit=limit),
            args_schema=_BugfixCommitsArgs,
        ),
        StructuredTool.from_function(
            name="find_perf_commits",
            description=(
                "perf:/optimize: 프리픽스 또는 '성능' 키워드 커밋만 필터링. "
                "SHA, 날짜, 메시지 첫 줄 반환. *결과 정리 및 성능 향상* 섹션에서 사용."
            ),
            func=lambda limit=10: find_perf_commits(ctx, limit=limit),
            args_schema=_PerfCommitsArgs,
        ),
        StructuredTool.from_function(
            name="parse_changelog",
            description=(
                "CHANGELOG.md 또는 RELEASES.md를 찾아 앞 3000자 반환. "
                "없으면 '(없음)' 반환. *결과 정리* 섹션에서 릴리즈 노트 인용에 사용."
            ),
            func=lambda: parse_changelog(ctx) or "(없음)",
            args_schema=_NoArgs,
        ),
        StructuredTool.from_function(
            name="read_file",
            description=(
                "이미 fetch된 코어/문서 파일의 전체 내용 반환. "
                "파일이 없으면 '(파일 없음)' 반환. 큰 파일 주의 — 컨텍스트 절약 위해 "
                "필요한 부분만 search_code로 먼저 좁히는 것 권장."
            ),
            func=lambda path: read_file(ctx, path),
            args_schema=_ReadFileArgs,
        ),
        StructuredTool.from_function(
            name="search_code",
            description=(
                "정규식 패턴으로 모든 코어/문서 파일의 모든 라인을 검색. "
                "매치된 라인을 'path:line: content' 형식으로 반환. "
                "특정 함수/클래스/패턴 출현 위치 찾을 때 사용."
            ),
            func=lambda pattern, max_hits=20: search_code(ctx, pattern, max_hits=max_hits),
            args_schema=_SearchCodeArgs,
        ),
    ]
