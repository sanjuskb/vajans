"""
VAJANS — AI Pipeline Celery Task (Phase 3)
==========================================
Orchestrates the full AI pipeline for one job:
  chunks → embeddings → FAISS → extraction → DB storage

This task runs after ingestion is complete for all files in a job.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from asgiref.sync import async_to_sync


def _parse_threshold(val) -> Optional[float]:
    """
    Safely coerce an LLM-supplied threshold value to float.
    Handles int, float, str, and mixed strings like "5 crore".
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    match = re.search(r"\d+(?:\.\d+)?", str(val))
    return float(match.group()) if match else None


def _build_fields_spec(criterion_raw: Dict) -> List[Dict[str, str]]:
    """
    Build field specification list for a criterion.
    Adds type-specific extraction hints so the LLM knows what to look for.
    """
    key   = (criterion_raw.get("id") or "").lower()
    label = criterion_raw.get("label", "")
    desc  = criterion_raw.get("description", "")
    field_name = criterion_raw.get("id", "value")

    if any(k in key for k in ("turnover", "revenue", "financial")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: The annual turnover or revenue figure in Crore INR.\n"
                "LOOK FOR: 'Annual Turnover', 'Turnover', 'Revenue from Operations', "
                "amounts followed by Cr / Crore / Lakhs.\n"
                "RETURN: If multiple years (FY22, FY23, FY24), return the AVERAGE of last 3 years in Crore.\n"
                "EXAMPLE: '8.2 Cr' → parsed_value=8.2, unit='crore INR'"
            ),
        }]
    elif any(k in key for k in ("project", "work", "experience", "similar")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: Count of completed similar projects worth ≥ 2 Crore each.\n"
                "LOOK FOR: Project names, contract values, completion certificates.\n"
                "RETURN: INTEGER count of qualifying projects.\n"
                "EXAMPLE: 5 qualifying projects → parsed_value=5, unit='projects'"
            ),
        }]
    elif any(k in key for k in ("gst", "gstin", "tax")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: GST registration number (15-character alphanumeric).\n"
                "LOOK FOR: Pattern like '29AABCI1234F1Z5', 'GSTIN', 'GST No'.\n"
                "RETURN: The full GST number string if found."
            ),
        }]
    elif any(k in key for k in ("iso", "certif", "quality")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: ISO 9001 certification status.\n"
                "LOOK FOR: 'ISO 9001', certificate number, validity/expiry date.\n"
                "RETURN: 'valid' if currently certified, 'expired' if expired or past date.\n"
                "EXAMPLE: 'ISO 9001:2015 valid till 2026' → parsed_value='valid'"
            ),
        }]
    elif any(k in key for k in ("epf", "esi", "pf", "provident")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: EPF/ESI registration status.\n"
                "LOOK FOR: 'EPF Number', 'ESI Code', 'PF Registration', registration numbers.\n"
                "RETURN: 'registered' if EPF/ESI registration is present."
            ),
        }]
    elif any(k in key for k in ("blacklist", "debar", "integrity", "litigation")):
        return [{
            "field_name": field_name,
            "description": (
                f"{desc}\n"
                "EXTRACT: Blacklisting/debarment status.\n"
                "LOOK FOR: 'not blacklisted', 'not debarred', 'clean record', declarations.\n"
                "RETURN: 'not_blacklisted' if company has clean record."
            ),
        }]
    else:
        return [{
            "field_name": field_name,
            "description": desc or label,
        }]


import structlog
from celery import Task

from worker.celery_app import celery_app

logger = structlog.get_logger("vajans.worker.ai_pipeline")


class AIPipelineTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: ARG002
        logger.error(
            "AI pipeline task failed",
            task_id=task_id,
            exc_type=type(exc).__name__,
            exc=str(exc),
        )


@celery_app.task(
    bind=True,
    base=AIPipelineTask,
    name="worker.tasks.ai_pipeline.run_ai_pipeline",
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
def run_ai_pipeline(self, job_id: str) -> Dict[str, Any]:
    """
    Main AI pipeline task.

    Steps:
    1. Fetch all chunks for the job from DB
    2. Generate embeddings for all chunks
    3. Store embeddings in FAISS (per-job index)
    4. Update chunk records with embedding references
    5. Extract tender criteria (from tender document)
    6. For each bidder file, extract fields per criterion
    7. Store results in DB
    8. Update job status
    """
    log = logger.bind(job_id=job_id)
    log.info("AI pipeline task started")

    return async_to_sync(_run_pipeline)(job_id, self)


async def _mark_job_failed(job_id: str, reason: str) -> None:
    from app.db.session import get_db_context
    from app.models.job import Job
    from shared.contracts.schemas import JobStatus

    try:
        async with get_db_context() as db:
            job = await db.get(Job, uuid.UUID(job_id))
            if job:
                job.status = JobStatus.FAILED
                logger.error("Job marked FAILED", job_id=job_id, reason=reason)
    except Exception as mark_exc:
        logger.error("Could not mark job FAILED", job_id=job_id, error=str(mark_exc))


async def _run_pipeline(job_id: str, task) -> Dict[str, Any]:  # noqa: ARG001
    try:
        return await _run_pipeline_inner(job_id)
    except Exception as exc:
        await _mark_job_failed(job_id, str(exc))
        raise


async def _run_pipeline_inner(job_id: str) -> Dict[str, Any]:
    from app.db.session import get_db_context
    from app.models.job import Job
    from app.models.chunk import Chunk
    from app.models.file import File as FileModel
    from app.models.audit import AuditLog
    from shared.contracts.schemas import AuditAction, JobStatus, FileType
    from sqlalchemy import select

    async with get_db_context() as db:

        # ── 0. Update job status ─────────────────────────────────────────
        job = await db.get(Job, uuid.UUID(job_id))
        if not job:
            logger.error("Job not found", job_id=job_id)
            return {"status": "error", "reason": "job_not_found"}

        job.status = JobStatus.EXTRACTING
        db.add(AuditLog(
            job_id=uuid.UUID(job_id),
            action=AuditAction.EXTRACTION_STARTED,
            actor="system",
            details={},
        ))
        await db.flush()

        # ── 1. Fetch all chunks for this job ─────────────────────────────
        chunks_result = await db.execute(
            select(Chunk)
            .where(Chunk.job_id == uuid.UUID(job_id))
            .order_by(Chunk.file_id, Chunk.chunk_index)
        )
        all_chunks = chunks_result.scalars().all()

        if not all_chunks:
            logger.warning("No chunks found for job", job_id=job_id)
            raise ValueError("no_chunks")

        log = logger.bind(job_id=job_id, total_chunks=len(all_chunks))
        log.info("Chunks fetched from DB")

        # Update metadata: ingestion complete
        job.metadata_ = {
            **(job.metadata_ or {}),
            "ingestion_complete": True,
            "total_chunks": len(all_chunks),
        }
        await db.flush()

        # ── 2. Generate embeddings for all chunks ─────────────────────────
        try:
            from app.engines.embedding import generate_embeddings
            chunk_texts = [c.text for c in all_chunks]
            chunk_ids   = [str(c.id) for c in all_chunks]

            embeddings = await generate_embeddings(chunk_texts, chunk_ids)
            log.info("Embeddings generated", count=len(embeddings))
        except Exception as exc:
            log.error("Embedding generation failed", error=str(exc))
            raise

        # ── 3. Store in FAISS ─────────────────────────────────────────────
        try:
            from app.engines.vector_store import add_embeddings
            add_embeddings(
                job_id=job_id,
                chunk_ids=chunk_ids,
                embeddings=embeddings,
            )
            log.info("Embeddings stored in FAISS")
        except Exception as exc:
            log.error("FAISS storage failed", error=str(exc))
            raise

        # ── 4. Update chunk records with FAISS reference ──────────────────
        for chunk, emb_idx in zip(all_chunks, range(len(all_chunks))):
            chunk.embedding_id = f"faiss:{job_id}:{emb_idx}"
        await db.flush()

        # ── 5. Get tender file and extract criteria ───────────────────────
        tender_files_result = await db.execute(
            select(FileModel).where(
                FileModel.job_id == uuid.UUID(job_id),
                FileModel.file_type == FileType.TENDER,
            )
        )
        tender_files = tender_files_result.scalars().all()

        if not tender_files:
            log.error("No tender file found for job")
            raise ValueError("no_tender_file")

        tender_file = tender_files[0]

        tender_chunks_result = await db.execute(
            select(Chunk).where(Chunk.file_id == tender_file.id)
        )
        tender_chunks = tender_chunks_result.scalars().all()
        tender_text = "\n\n".join(c.text for c in tender_chunks)

        # Extract criteria from tender
        try:
            from app.engines.extraction import extract_tender_criteria
            criteria_data = await extract_tender_criteria(tender_text)
            criteria_list = criteria_data.get("criteria", [])
            log.info("Tender criteria extracted", count=len(criteria_list))
        except Exception as exc:
            log.error("Tender criteria extraction failed", error=str(exc))
            raise

        # ── 6. Store criteria in DB (idempotent — skip existing criterion_key) ─
        from app.models.result import CriterionDB
        stored_criteria = []

        # Load any criteria already stored for this job (handles retries)
        existing_criteria_result = await db.execute(
            select(CriterionDB).where(CriterionDB.job_id == uuid.UUID(job_id))
        )
        existing_criteria = existing_criteria_result.scalars().all()
        existing_keys = {c.criterion_key: c for c in existing_criteria}

        for c in criteria_list:
            ckey = c.get("id", "unknown")
            if ckey in existing_keys:
                # Reuse the already-stored criterion (do not insert duplicate)
                log.debug("Skipping duplicate criterion_key", criterion_key=ckey)
                stored_criteria.append((c, existing_keys[ckey]))
                continue

            db_criterion = CriterionDB(
                job_id=uuid.UUID(job_id),
                tender_file_id=tender_file.id,
                criterion_key=ckey,
                label=c.get("label", ""),
                criterion_type=c.get("criterion_type", "technical"),
                description=c.get("description", ""),
                mandatory=c.get("mandatory", True),
                threshold_value=_parse_threshold(c.get("threshold_value")),
                threshold_unit=c.get("threshold_unit"),
                time_window_years=_parse_threshold(c.get("time_window_years")),
                operator=c.get("operator"),
                ambiguous=c.get("ambiguous", False),
                source_snippet=c.get("source_snippet"),
            )
            db.add(db_criterion)
            existing_keys[ckey] = db_criterion
            stored_criteria.append((c, db_criterion))
        await db.flush()

        # Update metadata: criteria extracted
        job.metadata_ = {
            **(job.metadata_ or {}),
            "criteria_count": len(criteria_list),
            "criteria_extracted": True,
        }
        await db.flush()

        # ── 7. Process each bidder file ───────────────────────────────────
        bidder_files_result = await db.execute(
            select(FileModel).where(
                FileModel.job_id == uuid.UUID(job_id),
                FileModel.file_type == FileType.BIDDER,
            )
        )
        bidder_files = bidder_files_result.scalars().all()
        log.info("Processing bidder files", count=len(bidder_files))

        extraction_results = []

        for bidder_file in bidder_files:
            file_result = await _process_bidder_file(
                db=db,
                job_id=job_id,
                bidder_file=bidder_file,
                stored_criteria=stored_criteria,
            )
            extraction_results.append(file_result)

        # Update metadata: extraction complete
        job.metadata_ = {
            **(job.metadata_ or {}),
            "extraction_complete": True,
            "bidder_count": len(bidder_files),
        }

        # ── 8. Finalize job ───────────────────────────────────────────────
        job.status = JobStatus.EVALUATING

        db.add(AuditLog(
            job_id=uuid.UUID(job_id),
            action=AuditAction.EXTRACTION_DONE,
            actor="system",
            details={
                "criteria_count": len(criteria_list),
                "bidder_files_processed": len(bidder_files),
                "total_chunks": len(all_chunks),
            },
        ))

        log.info(
            "AI pipeline complete",
            criteria=len(criteria_list),
            bidders=len(bidder_files),
        )

        pipeline_result = {
            "status": "success",
            "job_id": job_id,
            "criteria_extracted": len(criteria_list),
            "bidders_processed": len(bidder_files),
            "total_chunks_embedded": len(all_chunks),
        }

    # ── Auto-trigger Phase 4 evaluation (OUTSIDE the db context) ─────────
    from worker.tasks.evaluation import evaluate_job_task
    evaluate_job_task.apply_async(args=[job_id], queue="evaluation")
    log.info("Phase 4 evaluation task queued", job_id=job_id)

    return pipeline_result


async def _process_bidder_file(
    db,
    job_id: str,
    bidder_file,
    stored_criteria: List,
) -> Dict[str, Any]:
    """
    For one bidder file, extract fields for each criterion.

    CRITICAL FIX: We always provide ALL bidder chunks to the LLM.
    FAISS retrieval is attempted first to narrow down relevant sections,
    but if it finds no bidder-specific chunks (e.g., tender chunks dominate
    the top-k results), we fall back to ALL chunks from this bidder file.
    This prevents the common failure mode where relevant_texts is empty.
    """
    from sqlalchemy import select
    from app.models.chunk import Chunk
    from app.models.result import ExtractionResultDB
    from app.engines.retrieval import retrieve_chunks
    from app.engines.extraction import extract_criterion_fields

    log = logger.bind(job_id=job_id, file_id=str(bidder_file.id))
    log.info("Processing bidder file", name=bidder_file.original_name)

    # ── Get ALL chunks for this bidder upfront ────────────────────────────
    bidder_chunks_result = await db.execute(
        select(Chunk)
        .where(Chunk.file_id == bidder_file.id)
        .order_by(Chunk.chunk_index)
    )
    all_bidder_chunks = bidder_chunks_result.scalars().all()
    bidder_chunk_ids  = {str(c.id) for c in all_bidder_chunks}
    all_bidder_texts  = [c.text for c in all_bidder_chunks]

    log.info(
        "Bidder chunks loaded",
        name=bidder_file.original_name,
        chunk_count=len(all_bidder_chunks),
    )

    results_stored = 0

    # Pre-load file checksum for cross-job caching
    from app.models.file import File as FileModel
    from app.models.result import CriterionDB
    file_record = await db.get(FileModel, bidder_file.id)
    file_checksum = file_record.checksum_sha256 if file_record else None

    for criterion_raw, criterion_db in stored_criteria:
        try:
            # ── Cache check 1: same job, same file/criterion ──────────────
            existing_extraction = (await db.execute(
                select(ExtractionResultDB).where(
                    ExtractionResultDB.file_id == bidder_file.id,
                    ExtractionResultDB.criterion_id == criterion_db.id,
                )
            )).scalars().first()

            if existing_extraction is not None:
                log.debug(
                    "Extraction cache hit (same job)",
                    criterion=criterion_raw.get("id"),
                )
                results_stored += 1
                continue

            # ── Cache check 2: cross-job by (file checksum, criterion_key) ─
            # If the same file content was already extracted for any prior job,
            # clone the result to guarantee identical outputs for identical inputs.
            if file_checksum:
                cross_job_hit = (await db.execute(
                    select(ExtractionResultDB)
                    .join(FileModel, ExtractionResultDB.file_id == FileModel.id)
                    .join(CriterionDB, ExtractionResultDB.criterion_id == CriterionDB.id)
                    .where(
                        FileModel.checksum_sha256 == file_checksum,
                        CriterionDB.criterion_key == criterion_db.criterion_key,
                        ExtractionResultDB.not_found == False,  # noqa: E712
                    )
                    .order_by(ExtractionResultDB.extraction_confidence.desc())
                    .limit(1)
                )).scalars().first()

                if cross_job_hit is not None:
                    log.info(
                        "Cross-job extraction cache hit -- cloning result",
                        criterion=criterion_raw.get("id"),
                        source_file=str(cross_job_hit.file_id),
                    )
                    db_cloned = ExtractionResultDB(
                        job_id=uuid.UUID(job_id),
                        file_id=bidder_file.id,
                        criterion_id=criterion_db.id,
                        field_name=cross_job_hit.field_name,
                        raw_value=cross_job_hit.raw_value,
                        parsed_value=cross_job_hit.parsed_value,
                        unit=cross_job_hit.unit,
                        source_snippet=cross_job_hit.source_snippet,
                        extraction_confidence=cross_job_hit.extraction_confidence,
                        not_found=cross_job_hit.not_found,
                        raw_llm_output=cross_job_hit.raw_llm_output,
                    )
                    db.add(db_cloned)
                    await db.flush()
                    results_stored += 1
                    continue

            # ── Try FAISS retrieval first ─────────────────────────────────
            try:
                retrieval = await retrieve_chunks(
                    query=(
                        f"{criterion_raw.get('label', '')} "
                        f"{criterion_raw.get('description', '')}"
                    ),
                    job_id=job_id,
                    db=db,
                    top_k=15,       # higher top_k to increase chance of bidder hits
                    min_score=0.15, # lower threshold
                )
                # Filter to this bidder's chunks only
                relevant_texts = [
                    rc.text for rc in retrieval.chunks
                    if rc.chunk_id in bidder_chunk_ids
                ]
            except Exception as retrieval_exc:
                log.warning(
                    "FAISS retrieval failed, using all bidder chunks",
                    error=str(retrieval_exc),
                )
                relevant_texts = []

            # ── Fallback: use ALL bidder chunks if FAISS returned none ────
            if not relevant_texts:
                relevant_texts = all_bidder_texts
                log.debug(
                    "Using all bidder chunks (FAISS fallback)",
                    criterion=criterion_raw.get("id"),
                    chunk_count=len(relevant_texts),
                )

            # ── Build field spec with type-specific hints ─────────────────
            fields_spec = _build_fields_spec(criterion_raw)

            # ── Extract fields via LLM + regex fallback ───────────────────
            extraction = await extract_criterion_fields(
                criterion_id=criterion_raw.get("id", ""),
                criterion_label=criterion_raw.get("label", ""),
                criterion_description=criterion_raw.get("description", ""),
                fields_to_extract=fields_spec,
                retrieved_chunks=relevant_texts,
            )

            # ── Store in DB ───────────────────────────────────────────────
            for ef in extraction.fields:
                db_result = ExtractionResultDB(
                    job_id=uuid.UUID(job_id),
                    file_id=bidder_file.id,
                    criterion_id=criterion_db.id,
                    field_name=ef.field_name,
                    raw_value=ef.raw_value,
                    parsed_value=(
                        str(ef.parsed_value)
                        if ef.parsed_value is not None
                        else None
                    ),
                    unit=ef.unit,
                    source_snippet=ef.source_snippet,
                    extraction_confidence=ef.confidence,
                    not_found=ef.not_found,
                    raw_llm_output=extraction.raw_llm_output,
                )
                db.add(db_result)
                results_stored += 1

            await db.flush()

            log.debug(
                "Criterion extraction stored",
                criterion=criterion_raw.get("id"),
                not_found=extraction.fields[0].not_found if extraction.fields else True,
                confidence=extraction.fields[0].confidence if extraction.fields else 0,
            )

        except Exception as exc:
            log.error(
                "Criterion extraction failed for bidder",
                criterion=criterion_raw.get("id"),
                error=str(exc),
            )
            # Continue — don't fail the entire bidder

    log.info("Bidder file processed", results_stored=results_stored)
    return {"file_id": str(bidder_file.id), "results_stored": results_stored}
