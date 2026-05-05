"""
VAJANS — Chunk ORM Model
=========================
Stores RAG-ready text chunks extracted from documents.
Phase 3 will add vector embeddings to these records.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Chunk(Base):
    __tablename__ = "chunks"

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
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page:        Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    text:        Mapped[str] = mapped_column(Text, nullable=False)
    char_start:  Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end:    Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Phase 3 will populate this with the embedding vector (stored as JSON/FAISS)
    embedding_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="Reference ID in the FAISS index for this chunk"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────────────
    file: Mapped["File"] = relationship("File", back_populates="chunks")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Chunk file={self.file_id} idx={self.chunk_index} page={self.page}>"
