from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.core.db.session import async_session_factory, close_db, init_db, ping_db
from app.core.logger import logger
from app.prompts.matchmaker_prompt import MATCHMAKER_SYSTEM_PROMPT


MATCHMAKER_AGENT_ID = "matchmaker-00000000-0000-0000-0000-000000000001"


async def _ensure_matchmaker_agent() -> None:
    """Seed the Matchmaker Agent on first boot (idempotent)."""
    from sqlalchemy import select

    from app.models.db.agent import Agent

    async with async_session_factory() as session:
        existing = (
            await session.execute(select(Agent).where(Agent.id == MATCHMAKER_AGENT_ID))
        ).scalar_one_or_none()
        if existing is not None:
            return

        session.add(
            Agent(
                id=MATCHMAKER_AGENT_ID,
                agent_type="matchmaker",
                name=None,
                age=None,
                gender=None,
                job=None,
                tags=None,
                persona_text=None,
                system_prompt=MATCHMAKER_SYSTEM_PROMPT,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        await session.commit()
        logger.info("Matchmaker Agent seeded (id=%s)", MATCHMAKER_AGENT_ID)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ping_db()
    await _ensure_matchmaker_agent()

    yield

    await close_db()
