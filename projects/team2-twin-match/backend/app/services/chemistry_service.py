"""FR-005: Matchmaker Agent 기반 케미 분석.

담당자 TODO:
1. 사전 검증: conversation 존재, status == 'completed', messages 존재.
2. 캐시 확인: chemistry_repository.get_by_conversation 이 있으면 즉시 반환.
3. matchmaker = agent_repository.get_matchmaker()
4. prompt = build_chemistry_prompt(messages)
5. solar_client.chat_completion(matchmaker.system_prompt, [{"role": "user", "content": prompt}],
                                  temperature=0.3, response_format={"type": "json_object"})
6. JSON 파싱 → 검증 → ChemistryDTO → repository.create.
"""

from app.core.errors.error import (
    ConversationNotCompletedException,
    ConversationNotFoundException,
    NoMessagesException,
)
from app.models.dtos.chemistry import ChemistryDTO
from app.repositories.agent_repository import AgentRepository
from app.repositories.chemistry_repository import ChemistryRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class ChemistryService:
    def __init__(
        self,
        agent_repository: AgentRepository,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        chemistry_repository: ChemistryRepository,
    ):
        self.agent_repository = agent_repository
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.chemistry_repository = chemistry_repository

    async def analyze(self, conversation_id: str) -> ChemistryDTO:
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundException()
        if conv.status != "completed":
            raise ConversationNotCompletedException()

        cached = await self.chemistry_repository.get_by_conversation(conversation_id)
        if cached is not None:
            return cached

        messages = await self.message_repository.list_by_conversation(conversation_id)
        if not messages:
            raise NoMessagesException()

        # TODO: Matchmaker Agent + Solar 호출 → JSON 파싱 → ChemistryDTO → 저장.
        raise NotImplementedError
