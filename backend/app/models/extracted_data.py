"""VAJANS — ExtractedData ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ExtractedData(Base):
    """
    Stores the structured extraction result for one file.
    raw_json holds the full LLM output for audit.
    fields_json is the normalised list of ExtractedField dicts.
    """
    __tablename__ = "extracted_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_name:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_used:   Mapped[str]        = mapped_column(String(128), nullable=False)
    fields_json:  Mapped[dict]       = mapped_column(JSONB, nullable=False, default=list)
    raw_json:     Mapped[dict]       = mapped_column(JSONB, nullable=False, default=dict)
    warnings_json: Mapped[list]      = mapped_column("warnings", JSONB, nullable=False, default=list)

    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    file: Mapped["File"] = relationship("File", back_populates="extracted_data")  # noqa: F821
