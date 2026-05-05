"""VAJANS — File ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from shared.contracts.schemas import FileStatus, FileType


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("job_id", "checksum_sha256", name="uq_files_job_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        SAEnum(FileType, name="filetype", create_type=True),
        nullable=False,
        index=True,
    )
    status: Mapped[FileStatus] = mapped_column(
        SAEnum(FileStatus, name="filestatus", create_type=True),
        nullable=False,
        default=FileStatus.UPLOADED,
        index=True,
    )
    storage_path:     Mapped[str]  = mapped_column(String(1024), nullable=False)
    size_bytes:       Mapped[int]  = mapped_column(Integer, nullable=False)
    mime_type:        Mapped[str]  = mapped_column(String(128), nullable=False)
    checksum_sha256:  Mapped[str]  = mapped_column(String(64), nullable=False)
    page_count:       Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ───────────────────────────────────────────────────
    job: Mapped["Job"] = relationship("Job", back_populates="files")       # noqa: F821
    chunks: Mapped[list["Chunk"]] = relationship(                           # noqa: F821
        "Chunk", back_populates="file", cascade="all, delete-orphan"
    )
    extracted_data: Mapped[list["ExtractedData"]] = relationship(           # noqa: F821
        "ExtractedData", back_populates="file", cascade="all, delete-orphan"
    )
    results: Mapped[list["Result"]] = relationship(                         # noqa: F821
        "Result", back_populates="file", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(                   # noqa: F821
        "AuditLog", back_populates="file"
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} name={self.original_name!r} status={self.status}>"
