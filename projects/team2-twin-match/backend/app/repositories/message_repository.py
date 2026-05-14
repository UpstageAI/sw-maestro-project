"""Message CRUD against `messages` table."""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dtos.message import MessageDTO


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        conversation_id: str,
        agent_id: str,
        content: str,
        turn_number: int,
    ) -> MessageDTO:
        raise NotImplementedError

    async def list_by_conversation(self, conversation_id: str) -> List[MessageDTO]:
        """Return messages ordered by `turn_number` ascending."""
        raise NotImplementedError
