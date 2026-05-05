"""VAJANS — AuditLog ORM model (append-only, never updated or deleted)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from shared.contracts.schemas import AuditAction


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="auditaction", create_type=True),
        nullable=False,
        index=True,
    )
    actor:   Mapped[str]  = mapped_column(String(128), nullable=False, default="system")
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True
    )

    # IMPORTANT: no update triggers — this table is append-only
    job:  Mapped["Job"]         = relationship("Job",  back_populates="audit_logs")   # noqa: F821
    file: Mapped["File | None"] = relationship("File", back_populates="audit_logs")   # noqa: F821

    def __repr__(self) -> str:
        return f"<AuditLog job={self.job_id} action={self.action} at={self.created_at}>"
