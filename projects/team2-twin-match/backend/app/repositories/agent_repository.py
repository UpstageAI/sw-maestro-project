"""Agent CRUD against `agents` table."""

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors.error import DatabaseException
from app.core.logger import logger
from app.models.db.agent import Agent
from app.models.dtos.agent import AgentDTO


class AgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_clone(
        self,
        *,
        name: str,
        age: int,
        gender: str,
        job: Optional[str],
        tags: List[str],
        persona_text: str,
        system_prompt: str,
    ) -> AgentDTO:
        """Insert a new clone Agent and return its DTO."""
        row = Agent(
            agent_type="clone",
            name=name,
            age=age,
            gender=gender,
            job=job,
            tags=json.dumps(tags or [], ensure_ascii=False),
            persona_text=persona_text,
            system_prompt=system_prompt,
        )
        try:
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error("create_clone failed: %s", e)
            raise DatabaseException()
        return self._to_dto(row)

    async def get_by_id(self, agent_id: str) -> Optional[AgentDTO]:
        """Return the Agent matching `agent_id`, or `None`."""
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_dto(row) if row else None

    async def list_clones(self) -> List[AgentDTO]:
        """Return all Agents where `agent_type = 'clone'`, newest first."""
        stmt = (
            select(Agent)
            .where(Agent.agent_type == "clone")
            .order_by(Agent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [self._to_dto(row) for row in result.scalars().all()]

    async def list_clones_excluding(self, agent_id: str) -> List[AgentDTO]:
        """Used by Conversation matching (Strategy A: instant random pool)."""
        stmt = (
            select(Agent)
            .where(Agent.agent_type == "clone", Agent.id != agent_id)
            .order_by(Agent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [self._to_dto(row) for row in result.scalars().all()]

    async def get_matchmaker(self) -> Optional[AgentDTO]:
        """Return the singleton Matchmaker Agent (`agent_type = 'matchmaker'`)."""
        stmt = select(Agent).where(Agent.agent_type == "matchmaker").limit(1)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_dto(row) if row else None

    @staticmethod
    def _to_dto(row: Agent) -> AgentDTO:
        return AgentDTO(
            id=row.id,
            agent_type=row.agent_type,
            name=row.name,
            age=row.age,
            gender=row.gender,
            job=row.job,
            tags=json.loads(row.tags) if row.tags else [],
            persona_text=row.persona_text,
            system_prompt=row.system_prompt,
            created_at=row.created_at,
        )
