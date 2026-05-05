"""
VAJANS — Evaluation Tasks (Phase 4 + Phase 5 integration)
===========================================================
Deterministic rule engine evaluation + review flagging.
"""

import uuid
from typing import Any

import structlog
from asgiref.sync import async_to_sync

from worker.celery_app import celery_app
from worker.tasks.base import BaseTask, run_async

logger = structlog.get_logger("vajans.worker.evaluation")


# ── Scaffold tasks (unchanged) ───────────────────────────────────────────────

@celery_app.task(bind=True, base=BaseTask, name="worker.tasks.evaluation.evaluate_bidder")
def evaluate_bidder(self, file_id: str, job_id: str) -> dict[str, Any]:
    logger.info("Starting evaluation", file_id=file_id, job_id=job_id)
    try:
        result = run_async(_evaluate_async(uuid.UUID(file_id), uuid.UUID(job_id)))
        return result
    except Exception as exc:
        raise self.retry(exc=exc)


async def _evaluate_async(file_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
    return {
        "file_id": str(file_id),
        "job_id": str(job_id),
        "status": "scaffold — implement in Phase 4",
    }


@celery_app.task(bind=True, base=BaseTask, name="worker.tasks.evaluation.evaluate_job")
def evaluate_job(self, job_id: str) -> dict[str, Any]:
    logger.info("Starting job evaluation", job_id=job_id)
    return {"job_id": job_id, "status": "scaffold"}


# ── Phase 4 + 5 task ─────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    base=BaseTask,
    name="worker.tasks.evaluation.evaluate_job_task",
    max_retries=2,
    acks_late=True,
)
def evaluate_job_task(self, job_id: str) -> dict[str, Any]:
    """
    Phase 4 deterministic evaluation + Phase 5 review flagging.

    Flow:
      1. Fetch all criteria for the job
      2. Fetch best extraction per criterion (highest confidence, not not_found)
      3. Run evaluation engine (pure Python)
      4. Persist EvaluationResult rows
      5. Update job status → COMPLETED
      6. If any UNKNOWN exists → flag for review, log to audit chain
      7. If all resolved → log finalized status to audit chain
    """
    logger.info("Evaluation task started", job_id=job_id)
    try:
        return async_to_sync(_run_evaluation)(job_id)
    except Exception as exc:
        logger.error("Evaluation task failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


async def _run_evaluation(job_id: str) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.session import get_db_context
    from app.models.job import Job
    from app.models.file import File
    from app.models.result import CriterionDB, ExtractionResultDB
    from app.models.evaluation import EvaluationResult
    from app.models.audit import AuditLog
    from app.services.evaluation_engine import evaluate_job
    from app.services.audit_logger import log_action as log_chain
    from shared.contracts.schemas import AuditAction, JobStatus, FileType

    job_uuid = uuid.UUID(job_id)

    async with get_db_context() as db:

        # ── guard: job must exist ─────────────────────────────────────────
        job = await db.get(Job, job_uuid)
        if not job:
            logger.error("Job not found", job_id=job_id)
            return {"status": "error", "reason": "job_not_found"}

        # ── fetch criteria ────────────────────────────────────────────────
        criteria_rows = (await db.execute(
            select(CriterionDB).where(CriterionDB.job_id == job_uuid)
        )).scalars().all()

        if not criteria_rows:
            logger.warning("No criteria found", job_id=job_id)
            return {"status": "error", "reason": "no_criteria"}

        criteria_dicts = [c.to_dict() for c in criteria_rows]

        # ── fetch all bidder files ────────────────────────────────────────
        bidder_files = (await db.execute(
            select(File)
            .where(File.job_id == job_uuid)
            .where(File.file_type == FileType.BIDDER)
        )).scalars().all()

        if not bidder_files:
            logger.warning("No bidder files found", job_id=job_id)
            bidder_files = []

        # ── evaluate each bidder separately (with per-bidder caching) ───────
        all_results: list[dict] = []

        for bidder_file in bidder_files:
            fid = bidder_file.id

            # Cache check: if this bidder already has evaluation results, skip
            existing_count = (await db.execute(
                select(EvaluationResult)
                .where(EvaluationResult.job_id == job_uuid)
                .where(EvaluationResult.bidder_file_id == fid)
                .limit(1)
            )).scalars().first()

            if existing_count is not None:
                logger.info(
                    "Evaluation cache hit — skipping bidder",
                    job_id=job_id,
                    file_id=str(fid),
                )
                # Re-fetch existing results to include in all_results
                cached_rows = (await db.execute(
                    select(EvaluationResult)
                    .where(EvaluationResult.job_id == job_uuid)
                    .where(EvaluationResult.bidder_file_id == fid)
                )).scalars().all()
                for r in cached_rows:
                    all_results.append({
                        "criterion_id": str(r.criterion_id),
                        "verdict":      r.verdict,
                        "score":        r.score,
                        "weight":       r.weight,
                        "weighted_score": r.weighted_score,
                        "explanation":  r.explanation,
                        "bidder_file_id": str(fid),
                        "bidder_name":    bidder_file.original_name,
                        "final_status":   "QUALIFIED" if r.score > 0.0 else "DISQUALIFIED",
                        "final_score":    r.score,
                    })
                continue

            # Fetch this bidder's extractions (best per criterion)
            extraction_rows = (await db.execute(
                select(ExtractionResultDB)
                .where(ExtractionResultDB.job_id == job_uuid)
                .where(ExtractionResultDB.file_id == fid)
                .where(ExtractionResultDB.not_found == False)   # noqa: E712
                .order_by(ExtractionResultDB.extraction_confidence.desc())
            )).scalars().all()

            # Build criterion_id → best parsed_value map for this bidder
            cid_value_map: dict[str, Any] = {}
            for row in extraction_rows:
                cid = str(row.criterion_id)
                if cid not in cid_value_map:
                    cid_value_map[cid] = row.parsed_value

            # Map criterion_key → extracted value for the engine
            key_value_map: dict[str, Any] = {}
            for c in criteria_rows:
                val = cid_value_map.get(str(c.id))
                key_value_map[c.criterion_key] = val

            engine_output = evaluate_job(criteria_dicts, key_value_map)
            results  = engine_output["results"]
            decision = engine_output["decision"]

            logger.info(
                "Per-bidder decision computed",
                job_id=job_id,
                file_id=str(fid),
                final_status=decision["final_status"],
                final_score=decision["final_score"],
            )

            # Persist EvaluationResult rows with bidder_file_id
            for r in results:
                cid = r.get("criterion_id")
                if not cid:
                    continue
                db.add(EvaluationResult(
                    job_id=job_uuid,
                    criterion_id=uuid.UUID(str(cid)),
                    bidder_file_id=fid,
                    verdict=str(r["verdict"]),
                    score=float(r["score"]),
                    weight=float(r.get("weight", 1.0)),
                    weighted_score=float(r.get("weighted_score", 0.0)),
                    explanation=str(r["explanation"]),
                ))

            for r in results:
                r["bidder_file_id"] = str(fid)
                r["bidder_name"]    = bidder_file.original_name
                r["final_status"]   = decision["final_status"]
                r["final_score"]    = decision["final_score"]
            all_results.extend(results)

        # If no bidder files, fall back to global best-extraction mode
        if not bidder_files:
            extraction_rows = (await db.execute(
                select(ExtractionResultDB)
                .where(ExtractionResultDB.job_id == job_uuid)
                .where(ExtractionResultDB.not_found == False)   # noqa: E712
                .order_by(ExtractionResultDB.extraction_confidence.desc())
            )).scalars().all()

            cid_value_map = {}
            for row in extraction_rows:
                cid = str(row.criterion_id)
                if cid not in cid_value_map:
                    cid_value_map[cid] = row.parsed_value

            key_value_map = {c.criterion_key: cid_value_map.get(str(c.id)) for c in criteria_rows}
            engine_output = evaluate_job(criteria_dicts, key_value_map)
            results  = engine_output["results"]

            for r in results:
                cid = r.get("criterion_id")
                if not cid:
                    continue
                db.add(EvaluationResult(
                    job_id=job_uuid,
                    criterion_id=uuid.UUID(str(cid)),
                    verdict=str(r["verdict"]),
                    score=float(r["score"]),
                    weight=float(r.get("weight", 1.0)),
                    weighted_score=float(r.get("weighted_score", 0.0)),
                    explanation=str(r["explanation"]),
                ))
            all_results = results

        unknown_count = sum(1 for r in all_results if r["verdict"] == "unknown")
        pass_count    = sum(1 for r in all_results if r["verdict"] == "pass")
        fail_count    = sum(1 for r in all_results if r["verdict"] == "fail")

        # ── update job status → COMPLETED ─────────────────────────────────
        job.status = JobStatus.COMPLETED
        job.metadata_ = {
            **(job.metadata_ or {}),
            "evaluation_complete": True,
            "evaluation_pass":    pass_count,
            "evaluation_fail":    fail_count,
            "evaluation_unknown": unknown_count,
        }

        # ── standard audit log ────────────────────────────────────────────
        db.add(AuditLog(
            job_id=job_uuid,
            action=AuditAction.EVALUATION_DONE,
            actor="system",
            details={
                "total":         len(all_results),
                "pass":          pass_count,
                "fail":          fail_count,
                "unknown":       unknown_count,
                "bidders_evaluated": len(bidder_files),
            },
        ))

        # ── Phase 5: audit chain entry ────────────────────────────────────
        if unknown_count > 0:
            db.add(AuditLog(
                job_id=job_uuid,
                action=AuditAction.REVIEW_NEEDED,
                actor="system",
                details={
                    "unknown_count":   unknown_count,
                    "review_required": True,
                    "message": (
                        f"{unknown_count} criterion/criteria could not be evaluated "
                        "deterministically — human review required."
                    ),
                },
            ))
            await log_chain(
                db=db,
                job_id=job_uuid,
                action_type="evaluation_complete_review_needed",
                payload={
                    "job_id":            job_id,
                    "total":             len(all_results),
                    "pass":              pass_count,
                    "fail":              fail_count,
                    "unknown":           unknown_count,
                    "bidders_evaluated": len(bidder_files),
                    "review_required":   True,
                },
            )
        else:
            await log_chain(
                db=db,
                job_id=job_uuid,
                action_type="evaluation_complete_finalized",
                payload={
                    "job_id":            job_id,
                    "total":             len(all_results),
                    "pass":              pass_count,
                    "fail":              fail_count,
                    "unknown":           0,
                    "bidders_evaluated": len(bidder_files),
                },
            )

        logger.info(
            "Evaluation task complete",
            job_id=job_id,
            total=len(all_results),
            bidders=len(bidder_files),
        )
        return {
            "status":            "success",
            "job_id":            job_id,
            "evaluated":         len(all_results),
            "pass":              pass_count,
            "fail":              fail_count,
            "unknown":           unknown_count,
            "bidders_evaluated": len(bidder_files),
            "review_required":   unknown_count > 0,
        }
