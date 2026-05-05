"""
VAJANS — Celery Ingestion Task (Phase 2)
=========================================
Receives file_id + job_id from the upload API,
calls the ingestion engine, and persists results to DB.
"""

from __future__ import annotations

import uuid

import structlog
from celery import Task

from app.engines.ingestion import IngestionError, process_document
from worker.celery_app import celery_app

logger = structlog.get_logger("vajans.worker.ingestion")


class IngestionTask(Task):
    """Base class with shared error handling for ingestion tasks."""
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Ingestion task failed",
            task_id=task_id,
            exc_type=type(exc).__name__,
            exc=str(exc),
        )


@celery_app.task(
    bind=True,
    base=IngestionTask,
    name="worker.tasks.ingestion.ingest_file",
    max_retries=3,
    acks_late=True,
)
def ingest_file(self, file_id: str, job_id: str, file_type: str = "unknown") -> dict:
    """
    Celery task: ingest a single uploaded file.

    Args:
        file_id:  UUID string of the file record in DB.
        job_id:   UUID string of the parent job.

    Returns:
        dict with ingestion summary (for Celery result backend).
    """
    import asyncio
    from app.core.settings import settings
    from app.db.session import get_db_context
    # Import all models so SQLAlchemy mapper can resolve cross-model relationships
    import app.models.job, app.models.chunk, app.models.extracted_data, app.models.result, app.models.audit  # noqa: F401
    from app.models.file import File as FileModel
    from app.models.audit import AuditLog
    from shared.contracts.schemas import AuditAction, FileStatus

    log = logger.bind(file_id=file_id, job_id=job_id)
    log.info("Ingestion task received")

    async def _run() -> dict:
        async with get_db_context() as db:
            # ── Fetch file record ────────────────────────────────────────
            db_file = await db.get(FileModel, uuid.UUID(file_id))
            if not db_file:
                log.error("File record not found in DB — marking task as failed",
                          file_id=file_id, job_id=job_id)
                # file_id=None: FK to files.id is nullable; we cannot reference
                # a row that does not exist, but the job_id is still valid.
                db.add(AuditLog(
                    job_id=uuid.UUID(job_id),
                    file_id=None,
                    action=AuditAction.ERROR,
                    actor="system",
                    details={
                        "error": "file_record_not_found",
                        "missing_file_id": file_id,
                    },
                ))
                # Commit before raising so the audit entry survives the rollback
                # that get_db_context performs when it catches the exception below.
                await db.commit()
                raise IngestionError(
                    f"File record {file_id} not found in database",
                    code="FILE_RECORD_NOT_FOUND",
                )

            # ── Update status → processing ───────────────────────────────
            db_file.status = FileStatus.PROCESSING
            await db.flush()

            # ── Write audit log: ingestion started ───────────────────────
            db.add(AuditLog(
                job_id=uuid.UUID(job_id),
                file_id=uuid.UUID(file_id),
                action=AuditAction.INGESTION_STARTED,
                actor="system",
                details={"file_name": db_file.original_name},
            ))
            await db.flush()

            # ── Resolve file path ────────────────────────────────────────
            from pathlib import Path
            storage_root = Path(settings.STORAGE_LOCAL_PATH).resolve()
            file_path = storage_root / db_file.storage_path

            # ── Run ingestion engine ─────────────────────────────────────
            try:
                result = process_document(
                    file_path=file_path,
                    job_id=job_id,
                    file_id=file_id,
                    file_type=file_type,
                )

                # ── Persist extracted text + page count ──────────────────
                db_file.page_count = result.page_count
                db_file.status = FileStatus.PROCESSED

                # Store raw_text and chunks in DB
                # (chunk storage will be expanded in Phase 3)
                await _persist_chunks(db, result, uuid.UUID(file_id), uuid.UUID(job_id))

                # ── Write audit log: ingestion done ──────────────────────
                db.add(AuditLog(
                    job_id=uuid.UUID(job_id),
                    file_id=uuid.UUID(file_id),
                    action=AuditAction.INGESTION_DONE,
                    actor="system",
                    details={
                        "page_count": result.page_count,
                        "chunk_count": result.chunk_count,
                        "char_count": result.char_count,
                        "ocr_quality": result.ocr_quality_score,
                        "document_kind": result.document_kind.value,
                        "warning_count": len(result.warnings),
                    },
                ))

                log.info(
                    "Ingestion task complete",
                    pages=result.page_count,
                    chunks=result.chunk_count,
                    ocr_quality=result.ocr_quality_score,
                )

                return {
                    "status": "success",
                    "file_id": file_id,
                    "job_id": job_id,
                    "page_count": result.page_count,
                    "chunk_count": result.chunk_count,
                    "ocr_quality_score": result.ocr_quality_score,
                    "document_kind": result.document_kind.value,
                }

            except Exception as exc:
                log.error(
                    "Ingestion engine error",
                    exc_type=type(exc).__name__,
                    exc=str(exc),
                    attempt=self.request.retries,
                )
                db_file.status = FileStatus.FAILED
                db.add(AuditLog(
                    job_id=uuid.UUID(job_id),
                    file_id=uuid.UUID(file_id),
                    action=AuditAction.ERROR,
                    actor="system",
                    details={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "attempt": self.request.retries,
                    },
                ))
                # Commit FAILED status now, before raising the Retry exception.
                # get_db_context will call rollback() when it sees the Retry
                # exception propagate — but since we already committed, that
                # rollback is a safe no-op.  Without this commit the FAILED
                # status and error audit log would be silently discarded.
                await db.commit()

                # Exponential backoff: 30 s, 60 s, 120 s
                backoff = 30 * (2 ** self.request.retries)
                try:
                    raise self.retry(exc=exc, countdown=backoff)
                except self.MaxRetriesExceededError:
                    log.error("Max retries exceeded for ingestion task")
                    return {
                        "status": "failed",
                        "file_id": file_id,
                        "error": str(exc),
                    }

    return asyncio.run(_run())


async def _persist_chunks(db, result, file_id: uuid.UUID, job_id: uuid.UUID):
    """
    Idempotently persist text chunks for a file.

    Deletes any existing chunks for this file_id first so that a retry
    after a worker crash (task_acks_late=True can redeliver committed tasks)
    never creates duplicate chunks.
    """
    from app.models.chunk import Chunk
    from sqlalchemy import delete

    # Remove any chunks from a previous attempt that already committed.
    await db.execute(delete(Chunk).where(Chunk.file_id == file_id))

    # Insert fresh chunks with a monotonically advancing search cursor so
    # repeated prefixes don't cause char_start to point at the wrong position.
    search_cursor = 0
    for idx, chunk_text in enumerate(result.chunks):
        if chunk_text:
            char_start = result.raw_text.find(chunk_text[:50], search_cursor)
            if char_start == -1:
                char_start = search_cursor
            char_end = char_start + len(chunk_text)
            search_cursor = char_start  # advance; next chunk starts at or after here
        else:
            char_start = 0
            char_end = 0

        db.add(Chunk(
            file_id=file_id,
            job_id=job_id,
            chunk_index=idx,
            text=chunk_text,
            page=_estimate_page(chunk_text, result.page_texts),
            char_start=char_start,
            char_end=char_end,
        ))

    await db.flush()


def _estimate_page(chunk_text: str, page_texts: dict[int, str]) -> int:
    """
    Estimate which page a chunk came from by finding which
    page text contains the most overlap with the chunk.
    Returns 1 if no match found.
    """
    if not chunk_text or not page_texts:
        return 1

    snippet = chunk_text[:100]
    for page_num, page_text in page_texts.items():
        if snippet in page_text:
            return page_num
    return 1
