"""결과 정리 및 성능 향상 — tool calling agent."""
from src.agents.base import run_with_tools
from src.models.repo import RepoContext
from src.models.story import Section
from src.tools.section_helpers import make_tools

TOOL_NAMES = ["find_perf_commits", "parse_changelog", "read_file"]

SYSTEM = """당신은 시니어 개발자입니다. 포트폴리오의 *결과 정리 및 성능 향상* 섹션을 작성합니다.

작성 규칙:
1) find_perf_commits로 성능 관련 커밋 확인, parse_changelog로 릴리즈 노트 확인.
2) 필요하면 read_file로 README의 결과/벤치마크 부분을 읽으세요.
3) 충분히 모았다고 판단되면 도구 호출 없이 *마크다운 본문만* 출력하세요.
4) 본문 형식:
   ### 결과물
   ### 측정 가능한 향상
   ### 회고
   ### 다음 단계  (불릿마다 *(제안)* 표기)
5) 근거 없는 수치 금지. 측정값이 없으면 "측정 부재"로 표시. 분량 ~300-500자."""

USER_TMPL = """레포: {repo}

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
            attached=ctx.user_attached_info or "(없음)",
            summary=ctx.commit_summary or "(없음)",
        ),
        tools=tools,
        deep=False,
    )
    return Section(name="result", title="결과 정리 및 성능 향상", content=content)
