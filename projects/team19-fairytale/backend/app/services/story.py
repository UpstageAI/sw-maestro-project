from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from datetime import date

from psycopg import AsyncConnection

from app.exceptions import StoryGenerationError
from app.models.api import Person, StoryGenerateRequest, StoryRequest
from app.service import generate_story as generate_story_sync

logger = logging.getLogger(__name__)


def _build_diary(child: Mapping[str, object], request: StoryGenerateRequest) -> str:
    """child 프로필과 request 정보를 하나의 diary 텍스트로 조합한다."""
    parts = [
        f"[아이 정보] 이름: {child.get('name', '')}, "
        f"나이: {child.get('age', '')}세, "
        f"성격: {child.get('personality', '')}, "
        f"좋아하는 캐릭터: {child.get('favorite_character', '')}",
        f"[상황] {request.situation}",
        f"[원하는 교훈] {request.lesson}",
        f"[분위기] {request.mood}",
        f"[카테고리] {request.category}",
    ]
    return "\n".join(parts)


async def generate_story(
    child: Mapping[str, object],
    request: StoryGenerateRequest,
    db: AsyncConnection,
) -> dict[str, object]:
    """service.py의 LangGraph 워크플로우를 호출하고, 결과를 DB에 저장한다."""

    story_request = StoryRequest(
        diary_date=date.today(),
        diary=_build_diary(child, request),
        people=[
            Person(
                name=str(child.get("name", "")),
                relation="주인공",
                kind="아이",
                closeness=5,
                role_today="동화의 주인공",
                traits=[
                    str(child.get("personality", "")),
                    str(child.get("favorite_character", "")),
                ],
            ),
        ],
    )

    story = await asyncio.to_thread(generate_story_sync, story_request)

    row = await _save_story(
        db=db,
        user_id=str(child["user_id"]),
        child_id=str(child["id"]),
        title=story.title,
        body=story.body,
        lesson=request.lesson,
    )
    return row


async def _save_story(
    *,
    db: AsyncConnection,
    user_id: str,
    child_id: str,
    title: str,
    body: str,
    lesson: str,
) -> dict[str, object]:
    async with db.cursor() as cur:
        await cur.execute(
            """
            insert into public.stories (user_id, child_id, title, body, lesson)
            values (%s::uuid, %s::uuid, %s, %s, %s)
            returning
                id::text as id,
                title,
                body,
                lesson,
                image_url,
                audio_url,
                created_at
            """,
            (user_id, child_id, title, body, lesson),
        )
        row = await cur.fetchone()

    await db.commit()

    if row is None:
        raise StoryGenerationError(
            "Failed to save story to database.", stage="finalize"
        )

    return dict(row)
