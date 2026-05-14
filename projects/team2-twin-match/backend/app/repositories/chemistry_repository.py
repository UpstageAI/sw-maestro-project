"""ChemistryAnalysis CRUD against `chemistry_analyses` table."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dtos.chemistry import ChemistryDTO


class ChemistryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_conversation(self, conversation_id: str) -> Optional[ChemistryDTO]:
        """Return the cached analysis for `conversation_id`, or `None`."""
        raise NotImplementedError

    async def create(
        self, *, conversation_id: str, dto: ChemistryDTO
    ) -> ChemistryDTO:
        """Persist a fresh analysis. JSON-encode list/dict fields before insert."""
        raise NotImplementedError
