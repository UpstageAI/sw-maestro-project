"""트러블슈팅 포커스 — 원인 분석 및 해결책 섹션을 메인으로."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate
from src.tools.section_helpers import find_bugfix_commits, summarize_commits_by_topic

from ._blocks import code, divider, heading, md_to_blocks, para


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    blocks: list[dict] = [
        heading(1, f"{ctx.full_name} — 트러블슈팅 회고"),
        para(ctx.description or "(설명 없음)"),
        divider(),
    ]
    if story.problem:
        blocks.append(heading(2, story.problem.title))
        blocks.extend(md_to_blocks(story.problem.content))
    if story.status:
        blocks.append(heading(3, story.status.title))
        blocks.extend(md_to_blocks(story.status.content))
    blocks.append(divider())
    if story.cause:
        blocks.append(heading(1, "🛠 " + story.cause.title))
        blocks.extend(md_to_blocks(story.cause.content))
    blocks.append(divider())
    if story.result:
        blocks.append(heading(2, story.result.title))
        blocks.extend(md_to_blocks(story.result.content))
    blocks.append(divider())
    if story.architecture:
        blocks.append(heading(3, "참고 — 시스템 아키텍처"))
        blocks.append(code(story.architecture, "mermaid"))
    if story.dataflow:
        blocks.append(heading(3, "참고 — 데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))
    blocks.append(heading(2, "부록 — 커밋 토픽 분포"))
    blocks.extend(md_to_blocks(summarize_commits_by_topic(ctx)))
    blocks.append(heading(2, "부록 — 버그 픽스 커밋"))
    blocks.extend(md_to_blocks(find_bugfix_commits(ctx, limit=20)))
    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    parts = [
        f"# {ctx.full_name} — 트러블슈팅 회고", "",
        ctx.description or "_(설명 없음)_", "", "---", "",
    ]
    if story.problem:
        parts += [f"## {story.problem.title}", "", story.problem.content, ""]
    if story.status:
        parts += [f"### {story.status.title}", "", story.status.content, ""]
    parts.append("---\n")
    if story.cause:
        parts += [f"# 🛠 {story.cause.title}", "", story.cause.content, ""]
    parts.append("---\n")
    if story.result:
        parts += [f"## {story.result.title}", "", story.result.content, ""]
    if story.architecture:
        parts += ["", "### 참고 — 시스템 아키텍처", "", "```mermaid", story.architecture, "```", ""]
    if story.dataflow:
        parts += ["### 참고 — 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    parts += ["", "## 부록 — 커밋 토픽 분포", "", summarize_commits_by_topic(ctx), ""]
    parts += ["## 부록 — 버그 픽스 커밋", "", find_bugfix_commits(ctx, limit=20), ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="troubleshooting",
    name="트러블슈팅 포커스",
    description="원인 분석 및 해결책을 메인으로, 커밋 분포 부록 포함.",
    render=render,
    preview_md=preview,
)
