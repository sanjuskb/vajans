"""VAJANS — Phase 5 ReviewAction ORM model (append-only, immutable records)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from shared.contracts.schemas import ReviewerAction


class ReviewAction(Base):
    """
    Immutable record of every human review decision.
    Never updated. Never deleted. Only appended.
    """
    __tablename__ = "review_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_action: Mapped[ReviewerAction] = mapped_column(
        SAEnum(ReviewerAction, name="revieweraction", create_type=True),
        nullable=False,
    )
    original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_value:  Mapped[str | None] = mapped_column(Text, nullable=True)
    reason:         Mapped[str]        = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True,
    )

    # Relationships (read-only navigation)
    job: Mapped["Job"] = relationship("Job")  # noqa: F821

    def to_dict(self) -> dict:
        out: dict = {}
        for k, v in vars(self).items():
            if k.startswith("_"):
                continue
            if isinstance(v, uuid.UUID):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, ReviewerAction):
                out[k] = v.value
            else:
                out[k] = v
        return out

    def __repr__(self) -> str:
        return (
            f"<ReviewAction job={self.job_id} criterion={self.criterion_id} "
            f"action={self.reviewer_action} at={self.created_at}>"
        )
