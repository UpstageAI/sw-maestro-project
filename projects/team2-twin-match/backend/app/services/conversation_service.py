"""FR-003 / FR-004: 매칭 및 20턴 대화 시뮬레이션.

담당자 TODO:
1. `match_agents`: 요청 Agent 존재 확인 → list_clones_excluding → random.choice →
   conversation 생성.
2. `start_conversation`: 사전 검증 + Job 생성 후 즉시 반환. 실제 루프는
   `run_conversation_loop` 에서 구현. main.py 의 라우터에서
   `BackgroundTasks.add_task(svc.run_conversation_loop, conversation_id, job_id)` 로 등록.
3. `run_conversation_loop`: 20턴 동안 Solar 호출 → message 저장 → 종료/실패 처리.
4. `get_conversation_result`: conversation + messages + chemistry(있으면) 묶어서 반환.
"""

from typing import Tuple

from app.core.errors.error import (
    AgentNotFoundException,
    ConversationAlreadyCompletedException,
    ConversationNotFoundException,
    ConversationResultNotFoundException,
    NoMatchableAgentException,
)
from app.models.dtos.conversation import ConversationDTO
from app.models.schemas.conversation import ConversationResultResp
from app.repositories.agent_repository import AgentRepository
from app.repositories.chemistry_repository import ChemistryRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.message_repository import MessageRepository

TOTAL_TURNS = 20


class ConversationService:
    def __init__(
        self,
        agent_repository: AgentRepository,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        chemistry_repository: ChemistryRepository,
        job_repository: JobRepository,
    ):
        self.agent_repository = agent_repository
        self.conversation_repository = conversation_repository
        self.message_repository = message_repository
        self.chemistry_repository = chemistry_repository
        self.job_repository = job_repository

    async def match_agents(self, agent_id: str) -> ConversationDTO:
        # Skeleton: validate input + raise sensible domain errors.
        requester = await self.agent_repository.get_by_id(agent_id)
        if requester is None:
            raise AgentNotFoundException()

        candidates = await self.agent_repository.list_clones_excluding(agent_id)
        if not candidates:
            raise NoMatchableAgentException()

        # TODO: random.choice(candidates) → conversation_repository.create(...)
        raise NotImplementedError

    async def start_conversation(self, conversation_id: str) -> Tuple[str, str]:
        """Returns `(job_id, message)`. Caller adds `run_conversation_loop` to BG tasks."""
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundException()
        if conv.status == "completed":
            raise ConversationAlreadyCompletedException()

        # TODO: job_repository.create(...) → return (job.id, "대화가 시작되었습니다")
        raise NotImplementedError

    async def run_conversation_loop(
        self, conversation_id: str, job_id: str
    ) -> None:
        """Background-task entrypoint. Must own its own DB session lifecycle.

        BackgroundTasks runs after the request session is closed, so do **not**
        reuse `self.*_repository` here. Open a fresh `async_session_factory()`
        session and instantiate repositories inside this method.
        """
        # TODO: 20턴 루프 (Agent A → Agent B), Solar 호출, 메시지 저장,
        # 마지막에 conversation 상태 'completed' + job result 저장.
        raise NotImplementedError

    async def get_conversation_result(
        self, conversation_id: str
    ) -> ConversationResultResp:
        conv = await self.conversation_repository.get_by_id(conversation_id)
        if conv is None:
            raise ConversationResultNotFoundException()

        # TODO: messages + chemistry 조회 후 ConversationResultResp 조립.
        raise NotImplementedError
