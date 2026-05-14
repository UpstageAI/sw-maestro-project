"""FR-001 / FR-002: Clone Agent 생성 및 조회."""

import json
from typing import List, Tuple

from app.core.errors.error import (
    AgentNotFoundException,
    PersonaTextEmptyException,
    PersonaTextTooLongException,
    PersonaTextTooShortException,
)
from app.core.logger import logger
from app.core.solar_client import chat_completion
from app.models.dtos.agent import AgentDTO, CreateAgentDTO
from app.prompts.agent_prompt import (
    EXTRACTION_SYSTEM,
    PERSONA_EXTRACTION_PROMPT,
    build_system_prompt,
)
from app.repositories.agent_repository import AgentRepository
from app.utils.text_utils import MAX_PERSONA_LENGTH, MIN_PERSONA_LENGTH, normalize_text


class AgentService:
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository

    async def create_clone_agent(self, dto: CreateAgentDTO) -> AgentDTO:
        if not dto.persona_text or not dto.persona_text.strip():
            raise PersonaTextEmptyException()
        normalized = normalize_text(dto.persona_text)
        if len(normalized) < MIN_PERSONA_LENGTH:
            raise PersonaTextTooShortException()
        if len(normalized) > MAX_PERSONA_LENGTH:
            raise PersonaTextTooLongException()

        # Solar: job/tags 추출. 실패해도 system_prompt 생성엔 영향 없음.
        job, tags = await self._extract_persona_meta(normalized)

        # 페르소나 원문을 그대로 보존 + 고정 대화 규칙 추가.
        system_prompt = build_system_prompt(normalized)

        return await self.agent_repository.create_clone(
            name=dto.name,
            age=dto.age,
            gender=dto.gender,
            job=job,
            tags=tags,
            persona_text=normalized,
            system_prompt=system_prompt,
        )

    async def get_agent(self, agent_id: str) -> AgentDTO:
        agent = await self.agent_repository.get_by_id(agent_id)
        if agent is None:
            raise AgentNotFoundException()
        return agent

    async def list_clones(self) -> List[AgentDTO]:
        return await self.agent_repository.list_clones()

    async def _extract_persona_meta(
        self, persona_text: str
    ) -> Tuple[str, List[str]]:
        """Solar 로 job/tags 추출. 실패 시 빈 값 fallback."""
        prompt = PERSONA_EXTRACTION_PROMPT.format(persona_text=persona_text)
        try:
            raw = await chat_completion(
                system_prompt=EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(raw)
        except Exception as e:
            logger.warning("persona extraction failed → fallback: %s", e)
            return "", []

        if not isinstance(parsed, dict):
            return "", []

        job = parsed.get("job")
        if not isinstance(job, str):
            job = ""

        tags_raw = parsed.get("tags", [])
        if not isinstance(tags_raw, list):
            tags_raw = []
        tags = [t for t in tags_raw if isinstance(t, str) and t.strip()]

        return job, tags
