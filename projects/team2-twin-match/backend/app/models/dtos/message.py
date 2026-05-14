from dataclasses import dataclass


@dataclass
class MessageDTO:
    id: str
    conversation_id: str
    agent_id: str
    content: str
    turn_number: int
    created_at: str
