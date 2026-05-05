"""
VAJANS — Shared Data Contracts
================================
All Pydantic schemas used across the pipeline.
These are the canonical data definitions — DB models, API responses,
and inter-service messages all derive from / align with these.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING   = "pending"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"
    COMPLETED  = "completed"
    FAILED     = "failed"


class FileType(str, Enum):
    TENDER  = "tender"
    BIDDER  = "bidder"


class FileStatus(str, Enum):
    UPLOADED    = "uploaded"
    PROCESSING  = "processing"
    PROCESSED   = "processed"
    FAILED      = "failed"


class CriterionType(str, Enum):
    NUMERIC    = "numeric"
    BOOLEAN    = "boolean"
    ENUM       = "enum"
    TEXT       = "text"
    DATE       = "date"


class CriterionOperator(str, Enum):
    GTE  = "gte"   # greater than or equal
    LTE  = "lte"   # less than or equal
    GT   = "gt"
    LT   = "lt"
    EQ   = "eq"
    NEQ  = "neq"
    IN   = "in"
    CONTAINS = "contains"


class EvaluationVerdict(str, Enum):
    PASS    = "pass"
    FAIL    = "fail"
    PARTIAL = "partial"
    UNKNOWN = "unknown"   # field not found


class TrustLevel(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class AuditAction(str, Enum):
    JOB_CREATED        = "job_created"
    FILE_UPLOADED      = "file_uploaded"
    INGESTION_STARTED  = "ingestion_started"
    INGESTION_DONE     = "ingestion_done"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_DONE    = "extraction_done"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_DONE    = "evaluation_done"
    ROUTING_DONE       = "routing_done"
    ERROR              = "error"
    REVIEW_NEEDED      = "review_needed"
    REVIEW_SUBMITTED   = "review_submitted"


class ReviewerAction(str, Enum):
    APPROVE = "approve"
    EDIT    = "edit"
    REJECT  = "reject"


# ---------------------------------------------------------------------------
# Core building blocks
# ---------------------------------------------------------------------------

class SourceRef(BaseModel):
    """Precise pointer back to the document excerpt that produced a value."""
    file_id:   uuid.UUID
    page:      int
    snippet:   str          # ≤ 500 chars of raw text
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)


class ExtractionWarning(BaseModel):
    code:    str
    message: str
    field:   Optional[str] = None


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobCreate(BaseModel):
    title:      str = Field(min_length=3, max_length=255)
    created_by: str = Field(max_length=128)
    metadata:   Dict[str, Any] = Field(default_factory=dict)


class JobRead(BaseModel):
    id:         uuid.UUID
    title:      str
    status:     JobStatus
    created_by: str
    metadata:   Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------

class FileCreate(BaseModel):
    job_id:        uuid.UUID
    original_name: str = Field(max_length=512)
    file_type:     FileType
    storage_path:  str
    size_bytes:    int = Field(ge=0)
    mime_type:     str = Field(max_length=128)
    checksum_sha256: str = Field(min_length=64, max_length=64)


class FileRead(BaseModel):
    id:              uuid.UUID
    job_id:          uuid.UUID
    original_name:   str
    file_type:       FileType
    status:          FileStatus
    storage_path:    str
    size_bytes:      int
    mime_type:       str
    checksum_sha256: str
    page_count:      Optional[int]
    created_at:      datetime
    updated_at:      datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Chunk  (RAG unit)
# ---------------------------------------------------------------------------

class ChunkCreate(BaseModel):
    file_id:    uuid.UUID
    page:       int = Field(ge=0)
    chunk_index: int = Field(ge=0)
    text:       str
    char_start: int
    char_end:   int
    embedding:  Optional[List[float]] = None   # populated after embedding pass


class ChunkRead(ChunkCreate):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# ExtractedDocument  (top-level parsed representation of a file)
# ---------------------------------------------------------------------------

class ExtractedDocument(BaseModel):
    file_id:     uuid.UUID
    job_id:      uuid.UUID
    raw_text:    str
    page_texts:  Dict[int, str]            # page_number → text
    metadata:    Dict[str, Any]
    warnings:    List[ExtractionWarning] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Criterion  (rule schema — comes from tender document extraction)
# ---------------------------------------------------------------------------

class Criterion(BaseModel):
    """
    A single evaluation rule parsed from the tender document.
    Example: {"field": "annual_turnover", "operator": "gte", "threshold": 5_000_000, ...}
    """
    id:          str = Field(description="Unique slug, e.g. 'annual_turnover_min'")
    label:       str = Field(description="Human-readable label")
    field:       str = Field(description="Canonical field name in ExtractedField")
    criterion_type: CriterionType
    operator:    CriterionOperator
    threshold:   Any = Field(description="Value to compare against; type matches criterion_type")
    unit:        Optional[str] = None
    mandatory:   bool = True
    weight:      float = Field(default=1.0, ge=0.0, le=10.0,
                               description="Score weight when criterion is not binary")
    source:      Optional[SourceRef] = None

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("threshold must not be None")
        return v


class CriteriaSet(BaseModel):
    """All criteria extracted from one tender document."""
    job_id:       uuid.UUID
    tender_file_id: uuid.UUID
    criteria:     List[Criterion]
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    version:      int = 1


# ---------------------------------------------------------------------------
# ExtractedField  (one value pulled from a bidder document)
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    field:      str                  # must match Criterion.field
    raw_value:  str                  # exactly as extracted
    parsed_value: Any                # after normalization
    unit:       Optional[str] = None
    source:     SourceRef
    confidence: float = Field(ge=0.0, le=1.0)
    warnings:   List[ExtractionWarning] = Field(default_factory=list)


class BidderExtraction(BaseModel):
    """All extracted fields for a single bidder."""
    job_id:     uuid.UUID
    file_id:    uuid.UUID
    bidder_name: str
    fields:     List[ExtractedField]
    raw_json:   Dict[str, Any]        # full LLM response, for audit
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    model_used: str


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------

class CriterionResult(BaseModel):
    criterion_id:  str
    verdict:       EvaluationVerdict
    extracted_value: Any
    threshold:     Any
    operator:      CriterionOperator
    score:         float = Field(ge=0.0, le=1.0)
    source:        Optional[SourceRef] = None
    reason:        str                  # deterministic, human-readable


class EvaluationResult(BaseModel):
    """Complete evaluation of one bidder against the full criteria set."""
    id:              uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id:          uuid.UUID
    file_id:         uuid.UUID
    bidder_name:     str
    overall_verdict: EvaluationVerdict
    total_score:     float = Field(ge=0.0)
    max_score:       float = Field(ge=0.0)
    pass_count:      int = Field(ge=0)
    fail_count:      int = Field(ge=0)
    unknown_count:   int = Field(ge=0)
    criterion_results: List[CriterionResult]
    evaluated_at:    datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# TrustScore
# ---------------------------------------------------------------------------

class TrustScoreBreakdown(BaseModel):
    extraction_confidence_avg: float = Field(ge=0.0, le=1.0)
    field_coverage_ratio:      float = Field(ge=0.0, le=1.0)
    contradiction_penalty:     float = Field(ge=0.0, le=1.0,
                                             description="1.0 = no contradictions")
    ocr_noise_penalty:         float = Field(ge=0.0, le=1.0,
                                             description="1.0 = clean text")


class TrustScore(BaseModel):
    id:            uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id:        uuid.UUID
    file_id:       uuid.UUID
    bidder_name:   str
    score:         float = Field(ge=0.0, le=1.0)
    level:         TrustLevel
    breakdown:     TrustScoreBreakdown
    flags:         List[str] = Field(default_factory=list)
    computed_at:   datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    job_id:    uuid.UUID
    file_id:   Optional[uuid.UUID] = None
    action:    AuditAction
    actor:     str = Field(max_length=128, default="system")
    details:   Dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(AuditLogCreate):
    id:         uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Phase 5 — Review System
# ---------------------------------------------------------------------------

class ReviewActionCreate(BaseModel):
    criterion_id:         uuid.UUID
    evaluation_result_id: Optional[uuid.UUID] = None
    reviewer_action:      ReviewerAction
    original_value:       Optional[str] = None
    updated_value:        Optional[str] = None
    reason:               str = Field(min_length=1, max_length=2048)


class ReviewActionRead(BaseModel):
    id:                   uuid.UUID
    job_id:               uuid.UUID
    criterion_id:         uuid.UUID
    evaluation_result_id: Optional[uuid.UUID]
    reviewer_action:      ReviewerAction
    original_value:       Optional[str]
    updated_value:        Optional[str]
    reason:               str
    created_at:           datetime

    model_config = ConfigDict(from_attributes=True)


class AuditChainEntry(BaseModel):
    id:            uuid.UUID
    job_id:        uuid.UUID
    action_type:   str
    payload:       Dict[str, Any]
    previous_hash: str
    current_hash:  str
    created_at:    datetime

    model_config = ConfigDict(from_attributes=True)


class AuditTrailResponse(BaseModel):
    job_id:        str
    total_entries: int
    chain_valid:   bool
    entries:       List[AuditChainEntry]


# ---------------------------------------------------------------------------
# Phase 6 — Insight & Visualization Layer
# ---------------------------------------------------------------------------

class JobSummaryResponse(BaseModel):
    total_criteria:  int
    pass_count:      int = Field(alias="pass")
    fail_count:      int = Field(alias="fail")
    unknown_count:   int = Field(alias="unknown")
    final_score:     float
    final_status:    str
    review_required: bool

    model_config = ConfigDict(populate_by_name=True)


class CriterionInsight(BaseModel):
    criterion_id:    str
    label:           str
    verdict:         str
    explanation:     str
    weight:          float
    importance_level: str   # high / medium / low


class InsightFlag(BaseModel):
    code:              str
    message:           str
    severity:          str   # critical / warning / info
    affected_criteria: Optional[List[str]] = None


class InsightResponse(BaseModel):
    summary:  Dict[str, Any]
    criteria: List[CriterionInsight]
    flags:    List[InsightFlag]


class BidderComparison(BaseModel):
    bidder_id:      str
    bidder_name:    str
    total_score:    float
    pass_count:     int = Field(alias="pass")
    fail_count:     int = Field(alias="fail")
    unknown_count:  int = Field(alias="unknown")
    total_criteria: int

    model_config = ConfigDict(populate_by_name=True)


class BidderRanking(BaseModel):
    rank:        int
    bidder_id:   str
    bidder_name: str
    total_score: float


class ComparisonResponse(BaseModel):
    bidders:  List[BidderComparison]
    rankings: List[BidderRanking]


class DashboardResponse(BaseModel):
    summary:    Dict[str, Any]
    criteria:   List[CriterionInsight]
    comparison: Dict[str, Any]
    flags:      List[InsightFlag]
