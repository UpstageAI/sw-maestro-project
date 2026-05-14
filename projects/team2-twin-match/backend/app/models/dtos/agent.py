from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentDTO:
    id: str
    agent_type: str  # "clone" | "matchmaker"
    name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    job: Optional[str]
    tags: List[str] = field(default_factory=list)
    persona_text: Optional[str] = None
    system_prompt: str = ""
    created_at: str = ""


@dataclass
class CreateAgentDTO:
    """Input shape used by AgentService.create_clone_agent."""

    name: str
    age: int
    gender: str
    persona_text: str
