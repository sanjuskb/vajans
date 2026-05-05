"""VAJANS — Phase 4 Evaluation Result ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EvaluationResult(Base):
    """One criterion-level evaluation result for a job."""
    __tablename__ = "evaluation_results"

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
    verdict:        Mapped[str]   = mapped_column(String(16), nullable=False)   # pass/fail/unknown
    score:          Mapped[float] = mapped_column(Float,      nullable=False, default=0.0)
    weight:         Mapped[float] = mapped_column(Float,      nullable=False, default=1.0)
    weighted_score: Mapped[float] = mapped_column(Float,      nullable=False, default=0.0)
    explanation:    Mapped[str]   = mapped_column(Text,        nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self) -> dict:
        out = {}
        for k, v in vars(self).items():
            if k.startswith("_"):
                continue
            if isinstance(v, uuid.UUID):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            else:
                out[k] = v
        return out
