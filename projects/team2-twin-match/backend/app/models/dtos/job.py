from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class JobDTO:
    id: str
    conversation_id: str
    status: str  # pending | processing | completed | failed
    result: Optional[Any] = None  # parsed JSON payload
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
