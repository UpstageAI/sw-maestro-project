import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.session import Base


class ChemistryAnalysis(Base):
    __tablename__ = "chemistry_analyses"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    oneliner: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-encoded list[str]
    good_points: Mapped[str] = mapped_column(Text, nullable=False)
    concerns: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-encoded dict
    metrics: Mapped[str] = mapped_column(Text, nullable=False)
    final_comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
    )
