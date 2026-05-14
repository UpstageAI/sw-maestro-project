"""STAR — 면접 친화 내러티브 (Situation/Task/Action/Result).

4섹션을 STAR 프레임으로 매핑:
- Situation = 문제 인식
- Task     = 현황 파악 (해결해야 할 일)
- Action    = 원인 분석 및 해결책
- Result    = 결과 정리 및 성능 향상

각 단계 제목에 STAR 라벨을 함께 표기."""
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

from ._blocks import callout, code, divider, heading, md_to_blocks, para


STAR_MAP = {
    "problem": ("S", "Situation"),
    "status": ("T", "Task"),
    "cause": ("A", "Action"),
    "result": ("R", "Result"),
}


def render(story: StoryDraft, ctx: RepoContext) -> list[dict]:
    blocks: list[dict] = [
        heading(1, f"{ctx.full_name}"),
        para("면접용 STAR 포맷 포트폴리오"),
        callout("⭐", "S(상황) → T(과제) → A(행동) → R(결과) 순서로 정리"),
        divider(),
    ]
    for section in (story.problem, story.status, story.cause, story.result):
        if not section:
            continue
        letter, label = STAR_MAP[section.name]
        blocks.append(heading(2, f"[{letter}] {label} — {section.title}"))
        blocks.extend(md_to_blocks(section.content))
        blocks.append(divider())

    if story.architecture:
        blocks.append(heading(3, "참고 — 시스템 아키텍처"))
        blocks.append(code(story.architecture, "mermaid"))
    if story.dataflow:
        blocks.append(heading(3, "참고 — 데이터 플로우"))
        blocks.append(code(story.dataflow, "mermaid"))

    return blocks


def preview(story: StoryDraft, ctx: RepoContext) -> str:
    parts = [
        f"# {ctx.full_name}",
        "",
        "면접용 STAR 포맷 포트폴리오",
        "",
        "⭐ S(상황) → T(과제) → A(행동) → R(결과) 순서로 정리",
        "",
        "---",
        "",
    ]
    for s in (story.problem, story.status, story.cause, story.result):
        if not s:
            continue
        letter, label = STAR_MAP[s.name]
        parts += [f"## [{letter}] {label} — {s.title}", "", s.content, "", "---", ""]
    if story.architecture:
        parts += ["### 참고 — 시스템 아키텍처", "", "```mermaid", story.architecture, "```", ""]
    if story.dataflow:
        parts += ["### 참고 — 데이터 플로우", "", "```mermaid", story.dataflow, "```", ""]
    return "\n".join(parts)


TEMPLATE = NotionTemplate(
    id="star",
    name="STAR (면접용)",
    description="Situation/Task/Action/Result 4단계 매핑. 면접 준비용 내러티브.",
    render=render,
    preview_md=preview,
)
