"""VAJANS — Review Queue Entry ORM model.

One row per (job, bidder_file, criterion) triple that requires human resolution.
Created by `evaluate_job_task` whenever a criterion cannot be deterministically
resolved (verdict=unknown) or has extraction_confidence below threshold.

Lifecycle:
  pending   → human reviews via POST /v1/analyze/{job_id}/review
  resolved  → marked after review action is submitted; triggers job completion
              check once all entries for the job are resolved.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from shared.contracts.schemas import ReviewQueueStatus


class ReviewQueueEntry(Base):
    """Persistent escalation record for one criterion that needs human review."""

    __tablename__ = "review_queue_entries"

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
    bidder_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evaluation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    escalation_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="Snapshot of {verdict, score, extraction_confidence, not_found} at escalation time",
    )

    status: Mapped[ReviewQueueStatus] = mapped_column(
        SAEnum(ReviewQueueStatus, name="reviewqueuestatus", create_type=True),
        nullable=False,
        default=ReviewQueueStatus.PENDING,
        index=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True,
    )

    def to_dict(self) -> dict:
        out: dict = {}
        for k, v in vars(self).items():
            if k.startswith("_"):
                continue
            if isinstance(v, uuid.UUID):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, ReviewQueueStatus):
                out[k] = v.value
            else:
                out[k] = v
        return out

    def __repr__(self) -> str:
        return (
            f"<ReviewQueueEntry job={self.job_id} criterion={self.criterion_id} "
            f"status={self.status} at={self.created_at}>"
        )
