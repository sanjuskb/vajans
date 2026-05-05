"""VAJANS — Job API Endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import Job
from app.models.audit import AuditLog
from shared.contracts.schemas import (
    AuditAction,
    AuditLogCreate,
    JobCreate,
    JobRead,
    JobStatus,
)

router = APIRouter(prefix="/jobs")


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    """Create a new evaluation job."""
    job = Job(
        title=payload.title,
        created_by=payload.created_by,
        status=JobStatus.PENDING,
        metadata_=payload.metadata,
    )
    db.add(job)
    await db.flush()  # populate id before audit log

    log = AuditLog(
        job_id=job.id,
        action=AuditAction.JOB_CREATED,
        actor=payload.created_by,
        details={"title": payload.title},
    )
    db.add(log)
    await db.commit()
    await db.refresh(job)
    return _to_read(job)


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all jobs, newest first."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit)
    )
    return [_to_read(j) for j in result.scalars().all()]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific job by ID."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_read(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a job and all related data (cascades via FK)."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_read(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        status=job.status,
        created_by=job.created_by,
        metadata=job.metadata_,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
