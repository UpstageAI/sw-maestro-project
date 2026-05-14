"""머지 레이어 — 4섹션 + 다이어그램 2개를 최종 한 덩어리로 정리.

LLM 호출 없는 deterministic 합성. 일관된 머리말/순서 보장.
템플릿 render는 이 결과를 추가로 가공해 Notion blocks를 만든다."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft


def run(draft: StoryDraft, ctx: RepoContext) -> str:
    parts: list[str] = [
        f"# {ctx.full_name}",
        "",
        ctx.description or "_(설명 없음)_",
        "",
        "---",
        "",
    ]

    for section in (draft.problem, draft.status, draft.cause, draft.result):
        if not section:
            continue
        parts += [f"## {section.title}", "", section.content, "", "---", ""]

    if draft.architecture:
        parts += [
            "## 시스템 아키텍처",
            "",
            "```mermaid",
            draft.architecture,
            "```",
            "",
            "---",
            "",
        ]

    if draft.dataflow:
        parts += [
            "## 데이터 플로우",
            "",
            "```mermaid",
            draft.dataflow,
            "```",
            "",
        ]

    return "\n".join(parts)
