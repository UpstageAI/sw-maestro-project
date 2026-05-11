from pydantic import BaseModel

from app.models.dtos.message import MessageDTO


class MessageResp(BaseModel):
    id: str
    conversation_id: str
    agent_id: str
    content: str
    turn_number: int
    created_at: str

    @classmethod
    def from_dto(cls, dto: MessageDTO) -> "MessageResp":
        return cls(
            id=dto.id,
            conversation_id=dto.conversation_id,
            agent_id=dto.agent_id,
            content=dto.content,
            turn_number=dto.turn_number,
            created_at=dto.created_at,
        )
