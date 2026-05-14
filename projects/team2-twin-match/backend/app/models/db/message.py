import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.session import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "turn_number", name="uq_messages_conversation_turn"
        ),
        Index("idx_messages_conversation", "conversation_id"),
    )
