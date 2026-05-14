from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.dtos.agent import AgentDTO, CreateAgentDTO


class AgentCreateReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    age: int = Field(..., ge=18, le=80)
    gender: str = Field(..., pattern=r"^[FMX]$")
    persona_text: str = Field(..., max_length=5000)

    def to_dto(self) -> CreateAgentDTO:
        return CreateAgentDTO(
            name=self.name,
            age=self.age,
            gender=self.gender,
            persona_text=self.persona_text,
        )


class AgentResp(BaseModel):
    id: str
    agent_type: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    job: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    persona_text: Optional[str] = None
    system_prompt: str
    created_at: str

    @classmethod
    def from_dto(cls, dto: AgentDTO) -> "AgentResp":
        return cls(
            id=dto.id,
            agent_type=dto.agent_type,
            name=dto.name,
            age=dto.age,
            gender=dto.gender,
            job=dto.job,
            tags=dto.tags,
            persona_text=dto.persona_text,
            system_prompt=dto.system_prompt,
            created_at=dto.created_at,
        )
