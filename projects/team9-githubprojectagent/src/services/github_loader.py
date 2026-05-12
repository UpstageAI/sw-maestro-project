"""GitHub 레포 fetch — tarball 기반 빠른 fetch.

기존 방식 (느림):
  repo.get_contents(path) × 30파일 = 30회 직렬 API 콜
  + repo.get_commits()[:300] = 30개씩 페이지 = 10회
  → ~44회 직렬 호출. Docker 네트워크 + 0.5~2s/콜 = 60~120초 소요.

새 방식 (빠름):
  tarball 다운로드 = 1회 (압축된 전체 트리)
  + commits per_page=100 = 3회
  + 메타(repo/topics/readme/rate) = 4회
  → ~8회. 5~15초 정도로 단축.

⚠ c.stats 접근 금지 (커밋당 별도 콜 발생). additions/deletions는 항상 0.
"""
import io
import logging
import re
import tarfile
import time
from typing import Callable, Optional

import requests
from github import Auth, Github, GithubException, RateLimitExceededException
from urllib3.util.retry import Retry

from src import config
from src.models.repo import CommitInfo, RepoContext

log = logging.getLogger(__name__)

REPO_URL_RE = re.compile(r"github\.com[:/]+([^/]+)/([^/.]+)")

# rate limit 시 PyGithub 자동 재시도(최대 1시간 sleep) 차단
_NO_RETRY = Retry(total=0, backoff_factor=0)
_PER_PAGE = 100  # commits 페이지 사이즈 (max 100)

# tarball 안전장치 — 거대 레포 대응
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024  # 50 MB

ProgressFn = Callable[[str], None]


def parse_repo_url(url: str) -> tuple[str, str]:
    m = REPO_URL_RE.search(url.strip())
    if not m:
        raise ValueError(f"GitHub 레포 URL을 파싱할 수 없습니다: {url}")
    return m.group(1), m.group(2)


def _is_core_path(path: str) -> bool:
    if path in config.CORE_FILES:
        return True
    parts = path.split("/")
    return len(parts) > 1 and parts[0] in config.CORE_DIRS


def _check_rate_limit(gh: Github, has_pat: bool, progress: ProgressFn) -> None:
    """Rate limit 사전 체크. 부족하면 명확한 에러."""
    try:
        rl = gh.get_rate_limit()
        core = rl.core
        progress(
            f"rate limit: {core.remaining}/{core.limit} "
            f"(reset {core.reset.strftime('%H:%M:%S')})"
        )
        if core.remaining < 10:
            msg = (
                f"GitHub API 한도 부족: {core.remaining}/{core.limit} 남음. "
                f"리셋 시각: {core.reset}. "
            )
            if not has_pat:
                msg += (
                    "PAT 없이 60/hour 제한입니다. "
                    "https://github.com/settings/tokens 에서 토큰 만들어 입력하세요."
                )
            raise ValueError(msg)
    except RateLimitExceededException as e:
        raise ValueError(
            "GitHub API 한도 이미 초과. 1시간 기다리거나 PAT를 사용하세요."
        ) from e


def _fetch_tarball(
    owner: str,
    name: str,
    ref: str,
    token: Optional[str],
    progress: ProgressFn,
) -> tuple[dict[str, str], dict[str, str]]:
    """tarball 1회 다운로드 → 코어/문서 파일 추출.

    Returns: (core_files, docs_files)
    """
    t0 = time.time()
    url = f"https://api.github.com/repos/{owner}/{name}/tarball/{ref}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    progress(f"tarball 다운로드 시작 (ref={ref})")
    try:
        # (connect_timeout, read_timeout)
        r = requests.get(url, headers=headers, timeout=(10, 60))
    except requests.RequestException as e:
        raise ValueError(f"tarball 다운로드 실패: {e}") from e

    if r.status_code == 403:
        raise ValueError("GitHub API 한도 초과 또는 권한 부족 (tarball 403)")
    if r.status_code == 404:
        raise ValueError(f"tarball 못 찾음 (404): {owner}/{name}@{ref}")
    r.raise_for_status()

    size_kb = len(r.content) // 1024
    progress(f"tarball 받음 ({size_kb} KB, {time.time() - t0:.1f}s)")
    if len(r.content) > MAX_ARCHIVE_BYTES:
        raise ValueError(
            f"레포 tarball이 너무 큼: {size_kb} KB > {MAX_ARCHIVE_BYTES // 1024} KB"
        )

    core_files: dict[str, str] = {}
    docs_files: dict[str, str] = {}

    t1 = time.time()
    with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tar:
        picked = 0
        for member in tar.getmembers():
            if not member.isfile():
                continue
            if picked >= config.MAX_FILES_FETCH:
                break
            # member.name = "<owner>-<repo>-<shortsha>/path/to/file"
            parts = member.name.split("/", 1)
            if len(parts) < 2:
                continue
            rel_path = parts[1]

            is_core = _is_core_path(rel_path)
            is_docs = rel_path.startswith("docs/") and (
                rel_path.endswith(".md") or rel_path.endswith(".rst")
            )
            if not (is_core or is_docs):
                continue
            if member.size and member.size > config.MAX_FILE_SIZE_KB * 1024:
                continue

            try:
                f = tar.extractfile(member)
                if f is None:
                    continue
                content = f.read().decode("utf-8", errors="replace")
            except Exception as e:
                log.warning("tarball 파일 추출 실패 %s: %s", rel_path, e)
                continue

            if is_docs:
                docs_files[rel_path] = content
            else:
                core_files[rel_path] = content
            picked += 1

    progress(f"파일 {picked}개 추출 (core {len(core_files)}, docs {len(docs_files)}, "
             f"{time.time() - t1:.1f}s)")
    return core_files, docs_files


def fetch_repo(
    url: str,
    pat: Optional[str] = None,
    progress: Optional[ProgressFn] = None,
) -> RepoContext:
    """레포 메타 + commits + 코어/문서 파일 fetch (tarball 기반)."""
    progress = progress or (lambda _msg: None)
    t_total = time.time()
    owner, name = parse_repo_url(url)
    token = pat or config.GITHUB_PAT_DEFAULT

    gh = (
        Github(auth=Auth.Token(token), retry=_NO_RETRY, per_page=_PER_PAGE) if token
        else Github(retry=_NO_RETRY, per_page=_PER_PAGE)
    )

    if not token:
        progress("⚠ PAT 없음 — 공개 레포로 시도 (rate limit 60/hour)")
    _check_rate_limit(gh, has_pat=bool(token), progress=progress)

    # 1. 레포 메타
    t0 = time.time()
    progress(f"레포 메타 fetch: {owner}/{name}")
    try:
        repo = gh.get_repo(f"{owner}/{name}")
    except GithubException as e:
        if e.status == 404:
            raise ValueError(
                f"레포를 찾을 수 없습니다: {owner}/{name}. Private 레포라면 PAT가 필요합니다."
            ) from e
        if e.status == 403:
            raise ValueError(f"권한 부족 또는 한도 초과: {e}") from e
        raise

    ctx = RepoContext(
        owner=owner,
        name=name,
        description=repo.description,
        topics=list(repo.get_topics()),
        primary_language=repo.language,
        stars=repo.stargazers_count,
        forks=repo.forks_count,
        is_private=repo.private,
    )
    progress(f"레포 메타 OK ({time.time() - t0:.1f}s)")

    # 2. README
    t0 = time.time()
    try:
        readme_obj = repo.get_readme()
        ctx.readme = readme_obj.decoded_content.decode("utf-8", errors="replace")
        progress(f"README {len(ctx.readme)}자 ({time.time() - t0:.1f}s)")
    except GithubException:
        ctx.readme = None
        progress("README 없음")

    # 3. Commits — per_page=100 → 300커밋이면 3회 호출
    t0 = time.time()
    commits: list[CommitInfo] = []
    try:
        progress(f"commits fetch (max {config.MAX_COMMITS_FETCH}, per_page={_PER_PAGE})")
        for i, c in enumerate(repo.get_commits()[: config.MAX_COMMITS_FETCH]):
            try:
                commits.append(CommitInfo(
                    sha=c.sha[:7],
                    message=c.commit.message,
                    author=c.commit.author.name if c.commit.author else "unknown",
                    date=(
                        c.commit.author.date if c.commit.author
                        else c.commit.committer.date
                    ),
                ))
            except Exception as e:
                log.warning("커밋 %d 처리 실패: %s", i, e)
                continue
            if i and (i + 1) % _PER_PAGE == 0:
                progress(f"  ... commits {i + 1}/{config.MAX_COMMITS_FETCH} ({time.time() - t0:.1f}s)")
        progress(f"commits {len(commits)}개 OK ({time.time() - t0:.1f}s)")
    except RateLimitExceededException as e:
        raise ValueError("GitHub API 한도 초과 (commits)") from e
    except GithubException as e:
        log.warning("커밋 fetch 일부 실패: %s", e)
    ctx.commits = commits

    # 4. 파일 — tarball 1회로 모두 받기
    try:
        ref = repo.default_branch or "main"
        core_files, docs_files = _fetch_tarball(
            owner=owner,
            name=name,
            ref=ref,
            token=token,
            progress=progress,
        )
        ctx.core_files = core_files
        ctx.docs_files = docs_files
    except Exception as e:
        log.warning("tarball 실패, 빈 파일 세트로 진행: %s", e)
        progress(f"⚠ tarball 실패: {e} — 빈 파일 세트로 진행")

    progress(f"=== 전체 fetch 완료: {time.time() - t_total:.1f}s ===")
    log.info(
        "fetched %s — commits=%d core_files=%d docs=%d total=%.1fs",
        ctx.full_name, len(ctx.commits), len(ctx.core_files), len(ctx.docs_files),
        time.time() - t_total,
    )
    return ctx
