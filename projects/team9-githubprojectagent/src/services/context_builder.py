"""커밋 + README 1회 LLM 압축 + 시크릿 스캔. 결과는 RepoContext에 채워 넣음."""
import logging

from src.agents.base import invoke
from src.models.repo import RepoContext
from src.tools.secret_scanner import redact_secrets

log = logging.getLogger(__name__)

COMPRESS_PROMPT = """\
아래는 GitHub 레포 `{repo}`의 커밋 로그(최신순)와 README입니다.
포트폴리오 작성을 위해 다음을 *한국어*로 압축 요약하세요:

1) 프로젝트가 해결하려는 문제 (1-2문장)
2) 주요 기능/스코프 (불릿 3-5개)
3) 개발 흐름 (시간순 — 초기 구현 → 주요 변화 → 최근 작업, 4-7개)
4) 눈에 띄는 버그 픽스/리팩터링/성능 개선 (불릿 3-5개, 가능하면 커밋 SHA 인용)

응답은 마크다운, 800단어 이내.

=== README (앞부분) ===
{readme}

=== Commits (최신순, 최대 {n_commits}개) ===
{commits}
"""


def _format_commits(ctx: RepoContext, limit: int = 150) -> str:
    lines = []
    for c in ctx.commits[:limit]:
        msg = c.message.split("\n")[0][:120]
        lines.append(f"- {c.sha} ({c.date.date()}) {msg}")
    return "\n".join(lines)


def compress_context(ctx: RepoContext) -> RepoContext:
    """LLM 1회 호출로 commits + README를 압축. 결과를 ctx.commit_summary에 저장."""
    if not ctx.commits and not ctx.readme:
        ctx.commit_summary = "(커밋/README 없음)"
        return ctx

    readme_excerpt = (ctx.readme or "")[:6000]
    commits_block = _format_commits(ctx, limit=150)

    # 시크릿 누락 방어
    readme_excerpt = redact_secrets(readme_excerpt)

    prompt = COMPRESS_PROMPT.format(
        repo=ctx.full_name,
        readme=readme_excerpt or "(README 없음)",
        commits=commits_block or "(커밋 없음)",
        n_commits=min(150, len(ctx.commits)),
    )

    ctx.commit_summary = invoke(prompt, deep=False)
    log.info("compressed context — %d chars", len(ctx.commit_summary))
    return ctx


def sanitize_files(ctx: RepoContext) -> RepoContext:
    """소스/문서를 LLM에 보내기 전 시크릿 마스킹."""
    ctx.core_files = {p: redact_secrets(c) for p, c in ctx.core_files.items()}
    ctx.docs_files = {p: redact_secrets(c) for p, c in ctx.docs_files.items()}
    if ctx.readme:
        ctx.readme = redact_secrets(ctx.readme)
    return ctx
