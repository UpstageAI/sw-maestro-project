"""디테일드 — 메타 정보 + 4섹션 + 다이어그램 + 부록."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate
from src.tools.section_helpers import detect_tech_stack, summarize_directory_tree

from ._blocks import bullet, code, divider, heading, md_to_blocks, para


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    blocks: list[dict] = [
        heading(1, ctx.full_name),
        para(ctx.description or "(설명 없음)"),
        heading(3, "메타"),
        bullet(f"주 언어: {ctx.primary_language or '-'}"),
        bullet(f"스타/포크: {ctx.stars}/{ctx.forks}"),
        bullet(f"토픽: {', '.join(ctx.topics) or '-'}"),
        bullet(f"총 커밋: {len(ctx.commits)}"),
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
    if story.dataflow:
        blocks.append(heading(2, "데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))
    blocks.append(divider())

    blocks.append(heading(2, "부록 — 기술 스택"))
    blocks.extend(md_to_blocks(detect_tech_stack(ctx)))
    blocks.append(heading(2, "부록 — 디렉토리"))
    blocks.extend(md_to_blocks(summarize_directory_tree(ctx)))
    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    parts = [
        f"# {ctx.full_name}", "",
        ctx.description or "_(설명 없음)_", "",
        "### 메타",
        f"- 주 언어: {ctx.primary_language or '-'}",
        f"- 스타/포크: {ctx.stars}/{ctx.forks}",
        f"- 토픽: {', '.join(ctx.topics) or '-'}",
        f"- 총 커밋: {len(ctx.commits)}", "", "---", "",
    ]
    for s in (story.problem, story.status, story.cause, story.result):
        if s:
            parts += [f"## {s.title}", "", s.content, "", "---", ""]
    if story.architecture:
        parts += ["## 시스템 아키텍처", "", "```mermaid", story.architecture, "```", ""]
    if story.dataflow:
        parts += ["## 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    parts += ["", "---", "", "## 부록 — 기술 스택", "", detect_tech_stack(ctx), ""]
    parts += ["## 부록 — 디렉토리", "", summarize_directory_tree(ctx), ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="detailed",
    name="디테일드",
    description="메타 + 4섹션 + 다이어그램 + 기술스택/디렉토리 부록.",
    render=render,
    preview_md=preview,
)
