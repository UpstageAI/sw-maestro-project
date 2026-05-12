"""시스템 아키텍처 다이어그램 (Mermaid)."""
import re

from src.agents.base import invoke
from src.models.repo import RepoContext
from src.tools.section_helpers import detect_tech_stack, summarize_directory_tree

PROMPT = """\
당신은 시니어 개발자입니다. 아래 정보로 *Mermaid* `flowchart TD` 형식의
시스템 아키텍처 다이어그램을 생성하세요.

## 엄격한 문법 규칙 (반드시 지킬 것 — 어기면 Mermaid 파싱 실패)

1. **노드 ID는 영문 알파벳/숫자만**. 한글 ID 금지.
   - 좋은 예: `API`, `DB1`, `WebClient`, `FastAPIServer`
   - 나쁜 예: `웹클라이언트`, `API 서버`, `DB-1`
2. **라벨은 반드시 큰따옴표로 감싸기**. 한국어/괄호/공백 안전.
   - 좋은 예: `API["FastAPI 서버 (src/main.py)"]`
   - 나쁜 예: `API[FastAPI 서버 (src/main.py)]` ← 괄호 때문에 파싱 실패
3. **화살표 라벨도 따옴표**: `A -->|"요청"| B`
4. **shape: `[]` (rectangle), `()` (rounded), `[(  )]` (cylinder=DB), `{{}}` (rhombus=decision)**
5. **subgraph는 영문 ID + 따옴표 라벨**: `subgraph G1["그룹 이름"]`
6. 줄 끝 세미콜론 X. 한 줄 한 노드/엣지.

## 작성 가이드
- 핵심 컴포넌트 5~12개 (서비스/DB/외부 API/클라이언트)
- 화살표는 의존/통신 방향
- 추정 노드는 라벨 끝에 ` *?`
- 첫 줄은 반드시 `flowchart TD`로 시작
- *Mermaid 코드만* 출력. ```mermaid 펜스 X. 설명 X.

## 입력
== 레포 ==
{repo}

== 기술 스택 ==
{stack}

== 디렉토리 트리 ==
{tree}

== 압축 요약 ==
{summary}

## 출력 예시 (이 형태로)
flowchart TD
    Client["웹 브라우저"] -->|"HTTP"| API["FastAPI 서버 (src/main.py)"]
    API --> DB[("PostgreSQL DB")]
    API --> Cache[("Redis *?")]
    API --> Worker["배경 워커 (scheduler.py)"]
"""


def _strip_fence(text: str) -> str:
    m = re.search(r"```(?:mermaid)?\s*([\s\S]+?)\s*```", text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _sanitize_mermaid(code: str) -> str:
    """LLM 출력의 흔한 실수 자동 보정."""
    lines = [ln.rstrip() for ln in code.splitlines() if ln.strip()]
    if not lines:
        return "flowchart TD\n    Empty[\"(다이어그램 비어있음)\"]"
    first = lines[0].lower()
    if not (first.startswith("flowchart") or first.startswith("graph")
            or first.startswith("sequencediagram")):
        lines.insert(0, "flowchart TD")
    code = "\n".join(lines)
    # cylinder 안에 또 다른 노드 라벨 중첩: A[(B["text"])] → A[("text")]
    code = re.sub(r'\[\(\s*\w+\s*\[\s*"([^"]*)"\s*\]\s*\)\]', r'[("\1")]', code)
    # 닫는 괄호/대괄호 직후 영문 식별자 + 화살표가 붙어 한 줄에 두 엣지: ]API --> → ]\n    API -->
    code = re.sub(
        r'(\]|\))\s*([A-Z][A-Za-z0-9_]*\s+(?:-->|---|->|->>|-->>|--))',
        r'\1\n    \2', code,
    )
    return code


def run(ctx: RepoContext) -> str:
    raw = invoke(
        PROMPT.format(
            repo=ctx.full_name,
            stack=detect_tech_stack(ctx),
            tree=summarize_directory_tree(ctx),
            summary=ctx.commit_summary or "(없음)",
        ),
        deep=True,
    )
    return _sanitize_mermaid(_strip_fence(raw))
