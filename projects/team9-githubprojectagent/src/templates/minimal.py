"""미니멀 — 4섹션 + 다이어그램만 깔끔하게."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

from ._blocks import code, divider, heading, md_to_blocks, para


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    blocks: list[dict] = [
        heading(1, ctx.full_name),
        para(ctx.description or "(설명 없음)"),
        divider(),
    ]
    for section in (story.problem, story.status, story.cause, story.result):
        if not section:
            continue
        blocks.append(heading(2, section.title))
        blocks.extend(md_to_blocks(section.content))
        blocks.append(divider())
    if story.architecture:
        blocks.append(heading(2, "시스템 아키텍처"))
        blocks.append(code(story.architecture, "mermaid"))
        blocks.append(divider())
    if story.dataflow:
        blocks.append(heading(2, "데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))
    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    parts = [f"# {ctx.full_name}", "", ctx.description or "_(설명 없음)_", "", "---", ""]
    for s in (story.problem, story.status, story.cause, story.result):
        if s:
            parts += [f"## {s.title}", "", s.content, "", "---", ""]
    if story.architecture:
        parts += ["## 시스템 아키텍처", "", "```mermaid", story.architecture, "```", "", "---", ""]
    if story.dataflow:
        parts += ["## 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="minimal",
    name="미니멀",
    description="4섹션 + 다이어그램만 깔끔하게.",
    render=render,
    preview_md=preview,
)
