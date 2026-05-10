"""원인 분석 및 해결책 — 두 LLM 협업.

1. **issue_predictor** (tool calling, deep): 도구로 커밋·소스를 직접 조사 →
   소스/UI/인프라/의존성 4레벨 문제 정의.
2. **writer** (single-shot, deep): predictor 결과를 받아 섹션 본문 작성."""
from src.agents.base import invoke, run_with_tools
from src.models.repo import RepoContext
from src.models.story import Section
from src.tools.section_helpers import make_tools

PREDICTOR_TOOLS = [
    "summarize_commits_by_topic",
    "find_bugfix_commits",
    "read_file",
    "search_code",
]

PREDICTOR_SYSTEM = """당신은 시니어 개발자입니다. 이 프로젝트에서 *실제로 발생했거나 발생할 가능성이 높은 문제*를
4가지 레벨로 나누어 정의합니다.

레벨:
1) **소스코드 레벨** — 함수/클래스 단위 버그, 잘못된 알고리즘, 타입 오류
2) **UI/UX 레벨** — 입력 처리, 예외 메시지, 상호작용 흐름
3) **인프라 레벨** — 배포, 환경 변수, 의존성 버전, 스케일링
4) **함수 종속성 / 아키텍처 레벨** — 모듈 결합도, 순환 의존, 인터페이스 어긋남

도구 사용:
- summarize_commits_by_topic, find_bugfix_commits로 흐름 파악
- read_file / search_code로 의심 파일 직접 확인
- 충분히 조사한 뒤 도구 호출 없이 *마크다운만* 출력

각 레벨마다 2-4개 문제, 가능하면 커밋 SHA 또는 파일 경로 인용. 추측은 *(추정)* 표기. 800자 이내."""

PREDICTOR_USER_TMPL = """레포: {repo}

압축 요약 참고용:
{summary}
"""

WRITER_PROMPT = """\
당신은 시니어 개발자의 시점에서 포트폴리오 한 섹션을 작성합니다.
이 섹션은 *원인 분석 및 해결책*입니다.

아래 *문제 예측 결과*를 토대로 다음 구조의 한국어 마크다운을 작성하세요:
- ### 핵심 문제 1-3개 — 각각:
  - **증상** (관찰된 현상)
  - **원인** (왜 그랬는지)
  - **해결** (어떻게 풀었는지, 가능하면 커밋/파일 인용)
  - **트레이드오프** (선택의 비용)

근거 없는 주장 금지. 분량 ~400-700자.

== 문제 예측 (predictor 결과) ==
{prediction}
"""


def run(ctx: RepoContext) -> Section:
    pred_tools = [t for t in make_tools(ctx) if t.name in PREDICTOR_TOOLS]

    # LLM #1 — 도구 사용해 문제 예측
    prediction = run_with_tools(
        system=PREDICTOR_SYSTEM,
        user=PREDICTOR_USER_TMPL.format(
            repo=ctx.full_name,
            summary=ctx.commit_summary or "(없음)",
        ),
        tools=pred_tools,
        deep=True,
    )

    # LLM #2 — 작성 (단순 호출)
    content = invoke(
        WRITER_PROMPT.format(prediction=prediction),
        deep=True,
    )
    return Section(name="cause", title="원인 분석 및 해결책", content=content)
