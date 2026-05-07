"""VAJANS — File Upload API Endpoints."""

import asyncio
import io
import uuid
from pathlib import Path
from typing import List

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.file import File as FileModel
from app.models.audit import AuditLog
from app.services.storage import storage
from shared.contracts.schemas import (
    AuditAction,
    FileCreate,
    FileRead,
    FileStatus,
    FileType,
)

router = APIRouter(prefix="/files")
logger = structlog.get_logger("vajans.files")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_file(
    job_id: uuid.UUID = Form(...),
    file_type: FileType = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a tender or bidder document.
    Stores the file, records metadata, enqueues ingestion task.
    """
    logger.info("File upload received",
                filename=file.filename, job_id=str(job_id), file_type=file_type.value)

    # ── Validate mime ────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # ── Read bytes ───────────────────────────────────────────────────────
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")

    checksum = storage().compute_checksum(raw)

    # ── Duplicate check (before storage write — no orphaned files on disk) ──
    existing = await db.scalar(
        select(FileModel)
        .where(FileModel.job_id == job_id)
        .where(FileModel.checksum_sha256 == checksum)
    )
    if existing:
        logger.info(
            "Duplicate upload rejected",
            job_id=str(job_id),
            checksum=checksum,
            existing_file_id=str(existing.id),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_file",
                "message": "A file with identical content already exists for this job.",
                "existing_file_id": str(existing.id),
            },
        )

    logical_path = f"jobs/{job_id}/{file_type.value}/{uuid.uuid4()}_{Path(file.filename).name}"

    # ── Persist to storage (run in thread to avoid blocking event loop) ──
    await asyncio.to_thread(storage().save, logical_path, raw)
    logger.info("File stored", path=logical_path, size_bytes=len(raw))

    # ── DB record ────────────────────────────────────────────────────────
    db_file = FileModel(
        job_id=job_id,
        original_name=file.filename,
        file_type=file_type,
        status=FileStatus.UPLOADED,
        storage_path=logical_path,
        size_bytes=len(raw),
        mime_type=file.content_type,
        checksum_sha256=checksum,
    )
    db.add(db_file)
    await db.flush()

    log = AuditLog(
        job_id=job_id,
        file_id=db_file.id,
        action=AuditAction.FILE_UPLOADED,
        details={
            "original_name": file.filename,
            "size_bytes": len(raw),
            "checksum": checksum,
        },
    )
    db.add(log)
    await db.commit()
    await db.refresh(db_file)

    # ── Enqueue ingestion (non-blocking) ─────────────────────────────────
    try:
        from worker.tasks.ingestion import ingest_file
        _fid = str(db_file.id)
        _jid = str(job_id)
        _ft  = file_type.value
        task = await asyncio.to_thread(
            lambda: ingest_file.apply_async(args=[_fid, _jid, _ft], queue="ingestion")
        )
        logger.info("Ingestion task queued",
                    file_id=_fid, job_id=_jid, task_id=task.id)
    except Exception as exc:
        # Do not fail the upload if broker is unavailable; log for visibility
        logger.error("Failed to enqueue ingestion task",
                     file_id=str(db_file.id), error=str(exc))

    return _to_read(db_file)


@router.get("/job/{job_id}", response_model=List[FileRead])
async def list_files_for_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    List all files belonging to a job, enriched with the post-ingestion
    `ocr_quality` and `document_kind` signals sourced from the latest
    INGESTION_DONE audit log per file. This is what powers the Documents
    tab's OCR-quality column on the frontend.
    """
    files = (await db.execute(
        select(FileModel)
        .where(FileModel.job_id == job_id)
        .order_by(FileModel.created_at)
    )).scalars().all()
    enrichment = await _ingestion_enrichment_for_job(db, job_id)
    return [_to_read(f, enrichment.get(str(f.id))) for f in files]


@router.get("/{file_id}/download")
async def download_file(file_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Stream the raw file bytes back to the client with a download header."""
    f = await db.get(FileModel, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        raw = await asyncio.to_thread(storage().load, f.storage_path)
    except (FileNotFoundError, Exception) as exc:
        logger.error("File data missing from storage", file_id=str(file_id), error=str(exc))
        raise HTTPException(status_code=404, detail="File data not found on storage")
    return StreamingResponse(
        io.BytesIO(raw),
        media_type=f.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{f.original_name}"'},
    )


@router.get("/{file_id}/inline")
async def inline_file(file_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Stream the raw file bytes for INLINE rendering in the browser
    (e.g., loaded by the in-app react-pdf viewer).

    Differences from /download:
      - Content-Disposition is `inline`, not `attachment`.
      - Adds `Accept-Ranges: bytes` so pdf.js can range-fetch large PDFs.
      - Adds permissive cache header so subsequent page renders are fast.
    """
    f = await db.get(FileModel, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        raw = await asyncio.to_thread(storage().load, f.storage_path)
    except (FileNotFoundError, Exception) as exc:
        logger.error("File data missing from storage", file_id=str(file_id), error=str(exc))
        raise HTTPException(status_code=404, detail="File data not found on storage")
    return StreamingResponse(
        io.BytesIO(raw),
        media_type=f.mime_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{f.original_name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=300",
            "Content-Length": str(len(raw)),
        },
    )


@router.get("/{file_id}", response_model=FileRead)
async def get_file(file_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    f = await db.get(FileModel, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    enrichment = await _ingestion_enrichment_for_files(db, [file_id])
    return _to_read(f, enrichment.get(str(file_id)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _ingestion_enrichment_for_job(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> dict[str, dict]:
    """
    Build {file_id_str: {"ocr_quality": float|None, "document_kind": str|None}}
    by reading the latest INGESTION_DONE audit log per file in this job.

    Single round-trip; deterministic ordering matches `insight_engine`'s
    OCR-quality lookup so the Documents tab and the dashboard insights
    show the same number for the same file.
    """
    # Local import: avoids a circular import at module load time
    # (audit ↔ shared.contracts.schemas ↔ files endpoint).
    from shared.contracts.schemas import AuditAction

    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.job_id == job_id)
        .where(AuditLog.action == AuditAction.INGESTION_DONE)
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )).scalars().all()

    return _coalesce_ingestion_rows(rows)


async def _ingestion_enrichment_for_files(
    db: AsyncSession,
    file_ids: list[uuid.UUID],
) -> dict[str, dict]:
    """Same shape as _ingestion_enrichment_for_job, but scoped to file ids
    (used by the single-file endpoint where we don't know the job id)."""
    if not file_ids:
        return {}
    from shared.contracts.schemas import AuditAction

    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.action == AuditAction.INGESTION_DONE)
        .where(AuditLog.file_id.in_(file_ids))
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )).scalars().all()

    return _coalesce_ingestion_rows(rows)


def _coalesce_ingestion_rows(rows) -> dict[str, dict]:
    """
    Reduce a chronologically-ordered audit-log slice to the latest
    {ocr_quality, document_kind} per file_id. The "latest wins" rule
    matches re-ingestion semantics elsewhere in the codebase.
    """
    out: dict[str, dict] = {}
    for r in rows:
        if r.file_id is None or not isinstance(r.details, dict):
            continue
        d = r.details
        oq = d.get("ocr_quality")
        kind = d.get("document_kind")
        try:
            oq_val = float(oq) if oq is not None else None
        except (TypeError, ValueError):
            oq_val = None
        out[str(r.file_id)] = {
            "ocr_quality":   oq_val,
            "document_kind": kind if isinstance(kind, str) else None,
        }
    return out


def _to_read(f: FileModel, enrichment: dict | None = None) -> FileRead:
    enrichment = enrichment or {}
    return FileRead(
        id=f.id,
        job_id=f.job_id,
        original_name=f.original_name,
        file_type=f.file_type,
        status=f.status,
        storage_path=f.storage_path,
        size_bytes=f.size_bytes,
        mime_type=f.mime_type,
        checksum_sha256=f.checksum_sha256,
        page_count=f.page_count,
        created_at=f.created_at,
        updated_at=f.updated_at,
        ocr_quality=enrichment.get("ocr_quality"),
        document_kind=enrichment.get("document_kind"),
    )
