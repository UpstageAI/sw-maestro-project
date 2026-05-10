"""데이터 플로우 다이어그램 (Mermaid)."""
import re

from src.agents.base import invoke
from src.models.repo import RepoContext
from src.tools.section_helpers import detect_tech_stack, summarize_directory_tree

PROMPT = """\
당신은 시니어 개발자입니다. 아래 정보로 *Mermaid* `flowchart LR` 또는 `sequenceDiagram` 형식의
데이터 플로우 다이어그램을 생성하세요.

## 엄격한 문법 규칙 (반드시 지킬 것 — 어기면 Mermaid 파싱 실패)

### flowchart LR 선택 시
1. **노드 ID는 영문 알파벳/숫자만**. 한글 ID 금지.
   - 좋은 예: `User`, `WebForm`, `APIServer`, `DB1`
   - 나쁜 예: `사용자`, `API 서버`
2. **라벨은 반드시 큰따옴표로 감싸기**.
   - 좋은 예: `User["사용자 (브라우저)"]`
   - 나쁜 예: `User[사용자 (브라우저)]` ← 괄호 파싱 실패
3. **화살표 라벨도 따옴표**: `A -->|"검증된 입력"| B`
4. 첫 줄은 반드시 `flowchart LR`로 시작.

### sequenceDiagram 선택 시
1. participant 이름은 영문/숫자만. 한국어 표시명은 `as`로:
   - `participant U as 사용자`
   - `participant API as FastAPI 서버`
2. 메시지: `U->>API: 요청 본문`
3. 첫 줄은 `sequenceDiagram`.

## 공통
- 사용자 입력 → 처리 → 출력 흐름이 보이도록
- 추정은 라벨 끝에 ` *?`
- *Mermaid 코드만* 출력. 펜스 X. 설명 X.

## 입력
== 레포 ==
{repo}

== 기술 스택 ==
{stack}

== 디렉토리 트리 ==
{tree}

== 압축 요약 ==
{summary}

== 사용자 첨부 정보 ==
{attached}

## 출력 예시 (sequenceDiagram 형태)
sequenceDiagram
    participant U as 사용자
    participant API as FastAPI 서버
    participant DB as PostgreSQL
    U->>API: POST /book {{date, slot}}
    API->>DB: SELECT existing
    DB-->>API: row count
    API->>DB: INSERT booking
    DB-->>API: ok
    API-->>U: 201 Created
"""


def _strip_fence(text: str) -> str:
    m = re.search(r"```(?:mermaid)?\s*([\s\S]+?)\s*```", text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _sanitize_mermaid(code: str) -> str:
    lines = [ln.rstrip() for ln in code.splitlines() if ln.strip()]
    if not lines:
        return "flowchart LR\n    Empty[\"(다이어그램 비어있음)\"]"
    first = lines[0].lower()
    if not (first.startswith("flowchart") or first.startswith("graph")
            or first.startswith("sequencediagram")):
        lines.insert(0, "flowchart LR")
    code = "\n".join(lines)
    # cylinder 안 중첩 라벨: A[(B["text"])] → A[("text")]
    code = re.sub(r'\[\(\s*\w+\s*\[\s*"([^"]*)"\s*\]\s*\)\]', r'[("\1")]', code)
    # 한 줄에 여러 엣지 분리
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
            attached=ctx.user_attached_info or "(없음)",
        ),
        deep=True,
    )
    return _sanitize_mermaid(_strip_fence(raw))
