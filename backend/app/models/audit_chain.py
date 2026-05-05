"""VAJANS — Phase 5 AuditChain ORM model (cryptographic hash chain, append-only)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AuditChain(Base):
    """
    Cryptographically linked audit log.
    current_hash = sha256(previous_hash + json.dumps(payload, sort_keys=True))
    First entry: previous_hash = sha256("GENESIS").hexdigest()
    Never updated. Never deleted.
    """
    __tablename__ = "audit_chain"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str]  = mapped_column(String(128), nullable=False)
    payload:     Mapped[dict] = mapped_column(JSONB,        nullable=False, default=dict)

    # Hash chain fields — immutable once written
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash:  Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), index=True,
    )

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
            else:
                out[k] = v
        return out

    def __repr__(self) -> str:
        return (
            f"<AuditChain job={self.job_id} action={self.action_type} "
            f"hash={self.current_hash[:8]}... at={self.created_at}>"
        )
