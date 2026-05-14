from dataclasses import dataclass
from typing import Optional


@dataclass
class ConversationDTO:
    id: str
    agent_a_id: str
    agent_b_id: str
    status: str  # pending | processing | completed | failed
    created_at: str
    completed_at: Optional[str] = None
