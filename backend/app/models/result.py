"""VAJANS — Result ORM models (Phase 3 criteria + extractions, Phase 4 evaluation)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from shared.contracts.schemas import EvaluationVerdict, TrustLevel


# ---------------------------------------------------------------------------
# Phase 3 — Criteria extracted from tender document
# ---------------------------------------------------------------------------

class CriterionDB(Base):
    """One eligibility criterion extracted from the tender by the LLM."""
    __tablename__ = "criteria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tender_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_key:   Mapped[str]       = mapped_column(String(255), nullable=False)
    label:           Mapped[str]       = mapped_column(String(512), nullable=False)
    criterion_type:  Mapped[str]       = mapped_column(String(64),  nullable=False, default="technical")
    description:     Mapped[str]       = mapped_column(Text,        nullable=False, default="")
    mandatory:       Mapped[bool]      = mapped_column(Boolean,     nullable=False, default=True)
    threshold_value:   Mapped[float | None] = mapped_column(Float,       nullable=True)
    threshold_unit:    Mapped[str | None]   = mapped_column(String(128), nullable=True)
    time_window_years: Mapped[float | None] = mapped_column(Float,       nullable=True)
    operator:        Mapped[str | None]  = mapped_column(String(32), nullable=True)
    ambiguous:       Mapped[bool]      = mapped_column(Boolean,     nullable=False, default=False)
    source_snippet:  Mapped[str | None]  = mapped_column(Text,      nullable=True)

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


# ---------------------------------------------------------------------------
# Phase 3 — Per-criterion extraction result for one bidder file
# ---------------------------------------------------------------------------

class ExtractionResultDB(Base):
    """One extracted field value for a specific criterion + bidder file pair."""
    __tablename__ = "extraction_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name:            Mapped[str]       = mapped_column(String(255), nullable=False)
    raw_value:             Mapped[str | None]  = mapped_column(Text, nullable=True)
    parsed_value:          Mapped[str | None]  = mapped_column(Text, nullable=True)
    unit:                  Mapped[str | None]  = mapped_column(String(128), nullable=True)
    source_snippet:        Mapped[str | None]  = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float]     = mapped_column(Float,   nullable=False, default=0.0)
    not_found:             Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    raw_llm_output:        Mapped[str]       = mapped_column(Text,    nullable=False, default="")
    # 1-indexed page number where source_snippet was found (best-effort match
    # against the bidder's chunked text). Null if no match could be resolved.
    page_number:           Mapped[int | None] = mapped_column(Integer, nullable=True)

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


# ---------------------------------------------------------------------------
# Phase 4 — Final evaluation result for one bidder
# ---------------------------------------------------------------------------

class Result(Base):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_name:     Mapped[str]               = mapped_column(String(255), nullable=False)
    overall_verdict: Mapped[EvaluationVerdict]  = mapped_column(
        SAEnum(EvaluationVerdict, name="evaluationverdict", create_type=True),
        nullable=False,
        index=True,
    )
    total_score:   Mapped[float] = mapped_column(Float,   nullable=False)
    max_score:     Mapped[float] = mapped_column(Float,   nullable=False)
    pass_count:    Mapped[int]   = mapped_column(Integer, nullable=False)
    fail_count:    Mapped[int]   = mapped_column(Integer, nullable=False)
    unknown_count: Mapped[int]   = mapped_column(Integer, nullable=False)

    criterion_results_json: Mapped[list] = mapped_column(
        "criterion_results", JSONB, nullable=False, default=list
    )

    trust_score:   Mapped[float | None]     = mapped_column(Float, nullable=True)
    trust_level:   Mapped[TrustLevel | None] = mapped_column(
        SAEnum(TrustLevel, name="trustlevel", create_type=True), nullable=True
    )
    trust_breakdown_json: Mapped[dict | None] = mapped_column(
        "trust_breakdown", JSONB, nullable=True
    )
    trust_flags_json: Mapped[list | None] = mapped_column(
        "trust_flags", JSONB, nullable=True
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    file: Mapped["File"] = relationship("File", back_populates="results")  # noqa: F821
