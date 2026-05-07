"""VAJANS — Global Review Queue API Endpoints.

Provides a single source-of-truth view of all pending review items across
every job, derived from the `review_queue_entries` DB table (never computed
synthetically at the frontend).

Endpoints
---------
GET /v1/review-queue/
    All pending entries, newest first.  Optional ?job_id= filter.

GET /v1/review-queue/job/{job_id}
    All entries (pending + resolved) for a single job.
"""

import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from shared.contracts.schemas import ReviewQueueStatus

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _enrich_entry(entry, db: AsyncSession) -> dict:
    """Attach human-readable label and bidder name to a raw entry dict."""
    from app.models.result import CriterionDB
    from app.models.file import File as FileModel

    out = entry.to_dict()

    # Criterion label
    if entry.criterion_id:
        crit = await db.get(CriterionDB, entry.criterion_id)
        if crit:
            out["criterion_label"] = crit.label
            out["criterion_key"]   = crit.criterion_key
            out["mandatory"]       = crit.mandatory

    # Bidder file name
    if entry.bidder_file_id:
        f = await db.get(FileModel, entry.bidder_file_id)
        if f:
            out["bidder_name"] = f.original_name

    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def list_review_queue(
    job_id:  Optional[uuid_lib.UUID] = Query(default=None),
    resolved: bool = Query(default=False, description="Include resolved entries"),
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all review queue entries, newest first.

    By default only returns pending entries.
    Use ?resolved=true to include resolved entries as well.
    Use ?job_id=<uuid> to filter to a single job.
    """
    from app.models.review_queue import ReviewQueueEntry

    q = select(ReviewQueueEntry).order_by(ReviewQueueEntry.created_at.desc())

    if not resolved:
        q = q.where(ReviewQueueEntry.status == ReviewQueueStatus.PENDING)

    if job_id is not None:
        q = q.where(ReviewQueueEntry.job_id == job_id)

    q = q.offset(skip).limit(limit)

    rows = (await db.execute(q)).scalars().all()
    enriched = [await _enrich_entry(r, db) for r in rows]

    # Also include job title for display convenience
    if rows:
        from app.models.job import Job
        job_ids = list({r.job_id for r in rows})
        job_rows = (await db.execute(
            select(Job).where(Job.id.in_(job_ids))
        )).scalars().all()
        job_title_map = {str(j.id): j.title for j in job_rows}
        for entry_dict in enriched:
            entry_dict["job_title"] = job_title_map.get(entry_dict.get("job_id", ""), "")
            entry_dict["job_updated_at"] = None

        # Attach job.updated_at for "escalated at" display
        job_upd_map = {str(j.id): j.updated_at.isoformat() if j.updated_at else None for j in job_rows}
        for entry_dict in enriched:
            entry_dict["job_updated_at"] = job_upd_map.get(entry_dict.get("job_id", ""))

    return {"total": len(enriched), "data": enriched}


@router.get("/job/{job_id}")
async def get_job_review_queue(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all review queue entries (pending and resolved) for a single job."""
    from app.models.job import Job
    from app.models.review_queue import ReviewQueueEntry

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    rows = (await db.execute(
        select(ReviewQueueEntry)
        .where(ReviewQueueEntry.job_id == job_id)
        .order_by(ReviewQueueEntry.created_at.asc())
    )).scalars().all()

    pending  = sum(1 for r in rows if r.status == ReviewQueueStatus.PENDING)
    resolved = sum(1 for r in rows if r.status == ReviewQueueStatus.RESOLVED)

    enriched = [await _enrich_entry(r, db) for r in rows]

    return {
        "job_id":   str(job_id),
        "pending":  pending,
        "resolved": resolved,
        "total":    len(rows),
        "data":     enriched,
    }
