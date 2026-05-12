"""Conversation CRUD against `conversations` table."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dtos.conversation import ConversationDTO


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, *, agent_a_id: str, agent_b_id: str
    ) -> ConversationDTO:
        """Insert a new Conversation with status='pending'."""
        raise NotImplementedError

    async def get_by_id(self, conversation_id: str) -> Optional[ConversationDTO]:
        raise NotImplementedError

    async def update_status(
        self,
        conversation_id: str,
        *,
        status: str,
        completed_at: Optional[str] = None,
    ) -> Optional[ConversationDTO]:
        """Update status (and optionally completed_at)."""
        raise NotImplementedError
