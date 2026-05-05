"""
VAJANS — ORM Models Registry
=============================
All model classes must be imported here to ensure SQLAlchemy
registers them with the Base registry before relationships are resolved.

This prevents "expression 'X' failed to locate a name" errors.
"""

from app.models.audit import AuditLog
from app.models.audit_chain import AuditChain
from app.models.chunk import Chunk
from app.models.extracted_data import ExtractedData
from app.models.file import File
from app.models.job import Job
from app.models.result import CriterionDB, ExtractionResultDB, Result
from app.models.evaluation import EvaluationResult
from app.models.review import ReviewAction
from app.models.user import User

__all__ = [
    "Job",
    "File",
    "Chunk",
    "ExtractedData",
    "AuditLog",
    "AuditChain",
    "CriterionDB",
    "ExtractionResultDB",
    "Result",
    "EvaluationResult",
    "ReviewAction",
    "User",
]
