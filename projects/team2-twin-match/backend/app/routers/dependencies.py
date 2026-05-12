"""FastAPI dependency wiring (DB session → repositories → services)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_db
from app.repositories.agent_repository import AgentRepository
from app.repositories.chemistry_repository import ChemistryRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.message_repository import MessageRepository
from app.services.agent_service import AgentService
from app.services.chemistry_service import ChemistryService
from app.services.conversation_service import ConversationService
from app.services.job_service import JobService


# Repository providers ------------------------------------------------------
def get_agent_repository(db: AsyncSession = Depends(get_db)) -> AgentRepository:
    return AgentRepository(db)


def get_conversation_repository(
    db: AsyncSession = Depends(get_db),
) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_chemistry_repository(
    db: AsyncSession = Depends(get_db),
) -> ChemistryRepository:
    return ChemistryRepository(db)


def get_job_repository(db: AsyncSession = Depends(get_db)) -> JobRepository:
    return JobRepository(db)


# Service providers ---------------------------------------------------------
def get_agent_service(
    agent_repo: AgentRepository = Depends(get_agent_repository),
) -> AgentService:
    return AgentService(agent_repository=agent_repo)


def get_conversation_service(
    agent_repo: AgentRepository = Depends(get_agent_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
    chem_repo: ChemistryRepository = Depends(get_chemistry_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ConversationService:
    return ConversationService(
        agent_repository=agent_repo,
        conversation_repository=conv_repo,
        message_repository=msg_repo,
        chemistry_repository=chem_repo,
        job_repository=job_repo,
    )


def get_chemistry_service(
    agent_repo: AgentRepository = Depends(get_agent_repository),
    conv_repo: ConversationRepository = Depends(get_conversation_repository),
    msg_repo: MessageRepository = Depends(get_message_repository),
    chem_repo: ChemistryRepository = Depends(get_chemistry_repository),
) -> ChemistryService:
    return ChemistryService(
        agent_repository=agent_repo,
        conversation_repository=conv_repo,
        message_repository=msg_repo,
        chemistry_repository=chem_repo,
    )


def get_job_service(
    job_repo: JobRepository = Depends(get_job_repository),
) -> JobService:
    return JobService(job_repository=job_repo)
