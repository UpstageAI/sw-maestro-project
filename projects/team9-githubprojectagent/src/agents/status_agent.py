"""현황 파악 — tool calling agent."""
from src.agents.base import run_with_tools
from src.models.repo import RepoContext
from src.models.story import Section
from src.tools.section_helpers import make_tools

TOOL_NAMES = [
    "detect_tech_stack",
    "summarize_directory_tree",
    "read_file",
    "search_code",
]

SYSTEM = """당신은 시니어 개발자입니다. 포트폴리오의 *현황 파악* 섹션을 작성합니다.
프로젝트가 *어떻게 구성*되어 있는지를 다룹니다.

작성 규칙:
1) detect_tech_stack과 summarize_directory_tree를 우선 호출하세요.
2) 필요하면 read_file로 핵심 파일을 읽거나 search_code로 패턴을 찾으세요.
3) 충분히 모았다고 판단되면 도구 호출 없이 *마크다운 본문만* 출력하세요.
4) 본문 형식:
   ### 기술 스택
   ### 아키텍처/구성
   ### 데이터 흐름 / 인터페이스
   ### 규모/성숙도
5) 근거 없는 추측 금지. 분량 ~300-500자."""

USER_TMPL = """레포: {repo}
주 언어: {lang}
스타/포크: {stars}/{forks}
총 커밋: {n_commits}

사용자 첨부 정보:
{attached}

압축 요약 참고용:
{summary}
"""


def run(ctx: RepoContext) -> Section:
    tools = [t for t in make_tools(ctx) if t.name in TOOL_NAMES]
    content = run_with_tools(
        system=SYSTEM,
        user=USER_TMPL.format(
            repo=ctx.full_name,
            lang=ctx.primary_language or "(없음)",
            stars=ctx.stars,
            forks=ctx.forks,
            n_commits=len(ctx.commits),
            attached=ctx.user_attached_info or "(없음)",
            summary=ctx.commit_summary or "(없음)",
        ),
        tools=tools,
        deep=False,
    )
    return Section(name="status", title="현황 파악", content=content)
