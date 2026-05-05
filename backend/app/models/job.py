"""VAJANS — Job ORM model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from shared.contracts.schemas import JobStatus


def utcnow():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="jobstatus", create_type=True),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ───────────────────────────────────────────────────
    files: Mapped[list["File"]] = relationship(          # noqa: F821
        "File", back_populates="job", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship( # noqa: F821
        "AuditLog", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status} title={self.title!r}>"
