"""Notion 발행 — 공식 SDK 사용 (MCP는 stdio 클라이언트 복잡도 회피).
실패 시 로컬 .md 파일로 폴백 백업."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from notion_client import Client
from notion_client.errors import APIResponseError

from src import config
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

log = logging.getLogger(__name__)

NOTION_BLOCK_BATCH = 100  # API 한 번 호출당 블록 제한


def _backup_local(ctx: RepoContext, story: StoryDraft, template: NotionTemplate) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = config.OUTPUT_DIR / f"{ctx.owner}_{ctx.name}_{template.id}_{ts}.md"
    parts: list[str] = [f"# {ctx.full_name}", "", ctx.description or "", ""]
    for section in (story.problem, story.status, story.cause, story.result):
        if section:
            parts.append(f"## {section.title}\n\n{section.content}\n")
    out.write_text("\n".join(parts), encoding="utf-8")
    log.info("local backup: %s", out)
    return out


def publish(
    story: StoryDraft,
    ctx: RepoContext,
    template: NotionTemplate,
    parent_page_id: Optional[str] = None,
    notion_token: Optional[str] = None,
) -> dict:
    """결과 dict — {success, page_url|None, backup_path}"""
    backup = _backup_local(ctx, story, template)

    token = notion_token or config.NOTION_TOKEN
    parent = parent_page_id or config.NOTION_PARENT_PAGE_ID
    if not token or not parent:
        log.warning("Notion 토큰/parent page_id 없음 — 로컬 백업만 생성됨.")
        return {"success": False, "page_url": None, "backup_path": str(backup),
                "error": "Notion 자격증명 미설정"}

    client = Client(auth=token)
    blocks = template.render(story, ctx)
    title = f"{ctx.full_name} — 포트폴리오 ({template.name})"

    try:
        page = client.pages.create(
            parent={"page_id": parent},
            properties={"title": [{"type": "text", "text": {"content": title}}]},
            children=blocks[:NOTION_BLOCK_BATCH],
        )
        # 100개 초과분은 append
        for i in range(NOTION_BLOCK_BATCH, len(blocks), NOTION_BLOCK_BATCH):
            client.blocks.children.append(
                block_id=page["id"],
                children=blocks[i : i + NOTION_BLOCK_BATCH],
            )
        return {"success": True, "page_url": page.get("url"),
                "backup_path": str(backup)}
    except APIResponseError as e:
        log.error("Notion 발행 실패: %s", e)
        return {"success": False, "page_url": None, "backup_path": str(backup),
                "error": str(e)}
