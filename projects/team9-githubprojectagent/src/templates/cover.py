"""커버형 — 큰 헤더 + 콜아웃 요약 + 메타 표 + 4섹션 + 다이어그램.

Notion 포트폴리오 갤러리에서 흔히 보이는 '커버 이미지가 어울리는' 레이아웃.
실제 커버 이미지는 사용자가 Notion에서 직접 추가 (API로 cover 설정은 가능하나
이미지 URL이 없어 생략, 사용자가 페이지 상단에서 추가하면 됨)."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

from ._blocks import bullet, callout, code, divider, heading, md_to_blocks, para, quote


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    blocks: list[dict] = [
        heading(1, ctx.full_name),
        quote(ctx.description or "프로젝트 한 줄 설명"),
        callout(
            "💡",
            f"{(story.problem.content.splitlines()[0] if story.problem else '')[:120] or '핵심 문제 한 줄'}",
        ),
        heading(3, "프로젝트 메타"),
        bullet(f"주 언어: {ctx.primary_language or '-'}"),
        bullet(f"기간: 첫 커밋 ~ 최근 (총 {len(ctx.commits)}커밋)"),
        bullet(f"스타/포크: {ctx.stars}/{ctx.forks}"),
        bullet(f"토픽: {', '.join(ctx.topics) or '-'}"),
        divider(),
    ]
    for section in (story.problem, story.status, story.cause, story.result):
        if not section:
            continue
        blocks.append(heading(2, section.title))
        blocks.extend(md_to_blocks(section.content))
        blocks.append(divider())

    if story.architecture:
        blocks.append(heading(2, "🏗 시스템 아키텍처"))
        blocks.append(code(story.architecture, "mermaid"))
        blocks.append(divider())
    if story.dataflow:
        blocks.append(heading(2, "🔄 데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))

    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    summary = (story.problem.content.splitlines()[0] if story.problem else "")[:120]
    parts = [
        f"# {ctx.full_name}",
        "",
        f"> {ctx.description or '프로젝트 한 줄 설명'}",
        "",
        f"💡 **{summary or '핵심 문제 한 줄'}**",
        "",
        "### 프로젝트 메타",
        f"- 주 언어: {ctx.primary_language or '-'}",
        f"- 기간: 첫 커밋 ~ 최근 (총 {len(ctx.commits)}커밋)",
        f"- 스타/포크: {ctx.stars}/{ctx.forks}",
        f"- 토픽: {', '.join(ctx.topics) or '-'}",
        "",
        "---",
        "",
    ]
    for s in (story.problem, story.status, story.cause, story.result):
        if s:
            parts += [f"## {s.title}", "", s.content, "", "---", ""]
    if story.architecture:
        parts += ["## 🏗 시스템 아키텍처", "", "```mermaid", story.architecture, "```", "", "---", ""]
    if story.dataflow:
        parts += ["## 🔄 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="cover",
    name="커버형",
    description="큰 타이틀 + 콜아웃 요약 + 메타 + 4섹션 + 다이어그램. 갤러리 뷰 친화적.",
    render=render,
    preview_md=preview,
)
