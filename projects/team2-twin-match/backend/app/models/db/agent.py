import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.session import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_type: Mapped[str] = mapped_column(String(16), nullable=False, default="clone")
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    job: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # JSON-encoded list[str], e.g. '["#INTP","#등산"]'
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    persona_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('clone', 'matchmaker')", name="check_agent_type"
        ),
        CheckConstraint(
            "gender IS NULL OR gender IN ('F', 'M', 'X')", name="check_gender"
        ),
        Index("idx_agents_type", "agent_type"),
        Index("idx_agents_created_at", "created_at"),
    )
