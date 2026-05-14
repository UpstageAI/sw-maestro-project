"""프로젝트 레코드 — 표 기반의 구조화된 레이아웃.

상단에 프로젝트 정보 표(역할/기간/스택/링크) → 4섹션 → 다이어그램.
이력서 스타일."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

from ._blocks import code, divider, heading, md_to_blocks, para, table


def _date_range(ctx: RepoContext) -> str:
    if not ctx.commits:
        return "-"
    last = ctx.commits[0].date.date()
    first = ctx.commits[-1].date.date()
    return f"{first} ~ {last}"


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    info_table = table(
        rows=[
            ["항목", "내용"],
            ["프로젝트", ctx.full_name],
            ["설명", ctx.description or "-"],
            ["주 언어", ctx.primary_language or "-"],
            ["토픽", ", ".join(ctx.topics) or "-"],
            ["기간", _date_range(ctx)],
            ["커밋 수", str(len(ctx.commits))],
            ["스타 / 포크", f"{ctx.stars} / {ctx.forks}"],
        ],
        has_header=True,
    )

    blocks: list[dict] = [
        heading(1, ctx.full_name),
        para("프로젝트 레코드"),
        info_table,
        divider(),
    ]
    section_titles_table = table(
        rows=[
            ["문제 인식", "현황 파악", "원인 분석 및 해결책", "결과 정리 및 성능 향상"],
        ],
        has_header=False,
    )
    blocks.append(section_titles_table)
    blocks.append(divider())

    for section in (story.problem, story.status, story.cause, story.result):
        if not section:
            continue
        blocks.append(heading(2, section.title))
        blocks.extend(md_to_blocks(section.content))
        blocks.append(divider())

    if story.architecture:
        blocks.append(heading(2, "시스템 아키텍처"))
        blocks.append(code(story.architecture, "mermaid"))
    if story.dataflow:
        blocks.append(heading(2, "데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))

    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    parts = [
        f"# {ctx.full_name}",
        "",
        "프로젝트 레코드",
        "",
        "| 항목 | 내용 |",
        "|---|---|",
        f"| 프로젝트 | {ctx.full_name} |",
        f"| 설명 | {ctx.description or '-'} |",
        f"| 주 언어 | {ctx.primary_language or '-'} |",
        f"| 토픽 | {', '.join(ctx.topics) or '-'} |",
        f"| 기간 | {_date_range(ctx)} |",
        f"| 커밋 수 | {len(ctx.commits)} |",
        f"| 스타 / 포크 | {ctx.stars} / {ctx.forks} |",
        "",
        "---",
        "",
    ]
    for s in (story.problem, story.status, story.cause, story.result):
        if s:
            parts += [f"## {s.title}", "", s.content, "", "---", ""]
    if story.architecture:
        parts += ["## 시스템 아키텍처", "", "```mermaid", story.architecture, "```", ""]
    if story.dataflow:
        parts += ["## 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="project_record",
    name="프로젝트 레코드",
    description="이력서 스타일 — 프로젝트 정보 표 + 4섹션 + 다이어그램.",
    render=render,
    preview_md=preview,
)
