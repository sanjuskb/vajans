"""
VAJANS — Extraction Tasks
==========================
LLM-powered field extraction from chunks.
Phase 3 will implement the real body.
"""

import uuid
from typing import Any

import structlog

from worker.celery_app import celery_app
from worker.tasks.base import BaseTask, run_async

logger = structlog.get_logger("vajans.worker.extraction")


@celery_app.task(bind=True, base=BaseTask, name="worker.tasks.extraction.extract_bidder")
def extract_bidder(self, file_id: str, job_id: str, criteria_ids: list[str]) -> dict[str, Any]:
    """
    Extract structured fields from a bidder document.
    Uses RAG + LLM; returns BidderExtraction schema.
    Phase 3 implements the body.
    """
    logger.info("Starting extraction", file_id=file_id, job_id=job_id)
    try:
        result = run_async(_extract_async(
            uuid.UUID(file_id), uuid.UUID(job_id), criteria_ids
        ))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


async def _extract_async(
    file_id: uuid.UUID, job_id: uuid.UUID, criteria_ids: list[str]
) -> dict[str, Any]:
    # Phase 3: implement with RAG + LLM extraction
    return {
        "file_id": str(file_id),
        "job_id": str(job_id),
        "fields_extracted": 0,
        "status": "scaffold — implement in Phase 3",
    }


@celery_app.task(bind=True, base=BaseTask, name="worker.tasks.extraction.extract_criteria")
def extract_criteria(self, tender_file_id: str, job_id: str) -> dict[str, Any]:
    """
    Extract evaluation criteria from the tender document.
    Phase 3 implements the body.
    """
    logger.info("Extracting criteria", tender_file_id=tender_file_id, job_id=job_id)
    return {"tender_file_id": tender_file_id, "job_id": job_id, "status": "scaffold"}
