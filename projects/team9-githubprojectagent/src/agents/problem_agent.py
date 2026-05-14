"""문제 인식 — tool calling agent.

LLM이 메타정보 도구를 호출해 사실을 수집한 뒤 4부분 마크다운으로 작성.
"""
from src.agents.base import run_with_tools
from src.models.repo import RepoContext
from src.models.story import Section
from src.tools.section_helpers import make_tools

# 이 섹션에서 사용 가능한 도구 — LLM이 이 화이트리스트 안에서만 호출
TOOL_NAMES = ["extract_repo_metadata", "read_file", "search_code"]

SYSTEM = """당신은 시니어 개발자입니다. 포트폴리오의 *문제 인식* 섹션을 작성합니다.
이 프로젝트가 *왜* 만들어졌는지를 다룹니다.

작성 규칙:
1) 먼저 도구를 호출해 사실을 수집하세요. extract_repo_metadata로 메타를 보고,
   필요하면 read_file('README.md')로 README를 읽으세요.
2) 충분히 모았다고 판단되면 도구 호출 없이 *마크다운 본문만* 출력하세요.
3) 본문 형식:
   ### 배경
   ### 문제 정의
   ### 가설
   ### 목표
4) 근거 없는 추측 금지. 정보가 없으면 "정보 부족"이라고 표시하세요.
5) 분량 ~250-400자."""

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
    return Section(name="problem", title="문제 인식", content=content, sources=[ctx.full_name])
