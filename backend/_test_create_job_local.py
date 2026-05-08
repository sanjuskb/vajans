#!/usr/bin/env python3
"""Reproduce the exact create_job code path against Supabase to see the real error."""
import os, sys, traceback
from pathlib import Path
os.environ["ENVIRONMENT"] = "production"
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

import app.models  # noqa: F401
from app.db.session import AsyncSessionLocal, engine
from app.models.job import Job
from app.models.audit import AuditLog
from shared.contracts.schemas import AuditAction, JobStatus


async def main():
    print("Engine host:", engine.url.host)
    try:
        async with AsyncSessionLocal() as db:
            job = Job(
                title="test_local",
                created_by="procurement.officer",
                status=JobStatus.PENDING,
                metadata_={"tender_ref": "test/x", "description": "local test"},
            )
            db.add(job)
            await db.flush()
            print("[ok] job.flush, id=", job.id)

            log = AuditLog(
                job_id=job.id,
                action=AuditAction.JOB_CREATED,
                actor="procurement.officer",
                details={"title": "test_local"},
            )
            db.add(log)
            await db.commit()
            await db.refresh(job)
            print("[ok] commit, id=", job.id, "title=", job.title, "status=", job.status)
    except Exception as e:
        print("[FAIL]", type(e).__name__, str(e))
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
