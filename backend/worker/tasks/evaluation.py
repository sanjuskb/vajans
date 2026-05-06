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
    from app.services.evaluation_engine import (
        evaluate_criterion,
        compute_final_decision,
    )
    from app.services.audit_logger import log_action as log_chain
    from shared.contracts.schemas import AuditAction, JobStatus, FileType

    job_uuid = uuid.UUID(job_id)

    async with get_db_context() as db:

        # ── guard: job must exist ─────────────────────────────────────────
        job = await db.get(Job, job_uuid)
        if not job:
            logger.error("Job not found", job_id=job_id)
            return {"status": "error", "reason": "job_not_found"}

        # ── fetch criteria ──────────────────────────────────────────
        # Stable order so the EvaluationResult rows produced for this job
        # are inserted in a reproducible sequence.
        criteria_rows = (await db.execute(
            select(CriterionDB)
            .where(CriterionDB.job_id == job_uuid)
            .order_by(CriterionDB.criterion_key.asc(), CriterionDB.id.asc())
        )).scalars().all()

        if not criteria_rows:
            logger.warning("No criteria found", job_id=job_id)
            return {"status": "error", "reason": "no_criteria"}

        # ── fetch all bidder files ───────────────────────────────
        bidder_files = (await db.execute(
            select(File)
            .where(File.job_id == job_uuid)
            .where(File.file_type == FileType.BIDDER)
            # Stable processing order across re-runs.
            .order_by(File.created_at.asc(), File.id.asc())
        )).scalars().all()

        if not bidder_files:
            logger.warning("No bidder files found", job_id=job_id)
            bidder_files = []

        # ── evaluate each bidder separately (per-criterion caching) ──────
        all_results: list[dict] = []

        for bidder_file in bidder_files:
            fid = bidder_file.id
            bidder_name = bidder_file.original_name

            # Fetch this bidder's extractions (best confidence per criterion).
            # Tiebreak by oldest row + lowest id so two equal-confidence rows
            # always select the SAME parsed_value across runs.
            extraction_rows = (await db.execute(
                select(ExtractionResultDB)
                .where(ExtractionResultDB.job_id == job_uuid)
                .where(ExtractionResultDB.file_id == fid)
                .where(ExtractionResultDB.not_found == False)   # noqa: E712
                .order_by(
                    ExtractionResultDB.extraction_confidence.desc(),
                    ExtractionResultDB.created_at.asc(),
                    ExtractionResultDB.id.asc(),
                )
            )).scalars().all()

            cid_value_map: dict[str, Any] = {}
            cid_confidence_map: dict[str, float] = {}
            for row in extraction_rows:
                cid = str(row.criterion_id)
                if cid not in cid_value_map:
                    cid_value_map[cid] = row.parsed_value
                    cid_confidence_map[cid] = float(row.extraction_confidence)

            bidder_results: list[dict] = []
            pending_to_persist: list[tuple[Any, dict]] = []
            cache_hits = 0

            for criterion_db in criteria_rows:
                criterion_dict = criterion_db.to_dict()

                # ── Per-criterion cache check ───────────────────────────
                # Same (job, bidder_file, criterion) → reuse cached verdict.
                # Guarantees same-input-same-output across pipeline re-runs.
                existing_eval = (await db.execute(
                    select(EvaluationResult)
                    .where(EvaluationResult.job_id == job_uuid)
                    .where(EvaluationResult.bidder_file_id == fid)
                    .where(EvaluationResult.criterion_id == criterion_db.id)
                    .limit(1)
                )).scalars().first()

                if existing_eval is not None:
                    bidder_results.append({
                        "criterion_id":   str(criterion_db.id),
                        "criterion_key":  criterion_db.criterion_key,
                        "verdict":        existing_eval.verdict,
                        "score":          existing_eval.score,
                        "weight":         existing_eval.weight,
                        "weighted_score": existing_eval.weighted_score,
                        "explanation":    existing_eval.explanation,
                    })
                    cache_hits += 1
                    continue

                # ── Fresh evaluation (deterministic Python) ─────────────
                extracted_value = cid_value_map.get(str(criterion_db.id))
                conf = cid_confidence_map.get(str(criterion_db.id), 0.87)

                row = evaluate_criterion(criterion_dict, extracted_value, conf)
                row["criterion_id"]  = str(criterion_db.id)
                row["criterion_key"] = criterion_db.criterion_key
                bidder_results.append(row)
                pending_to_persist.append((criterion_db, row))

            # ── Compute decision over ALL results (cached + new) ────────
            criteria_lookup = {c.criterion_key: c.to_dict() for c in criteria_rows}
            decision = compute_final_decision(bidder_results, criteria_lookup)

            logger.info(
                "Per-bidder decision computed",
                job_id=job_id,
                file_id=str(fid),
                cached=cache_hits,
                fresh=len(pending_to_persist),
                final_status=decision["final_status"],
                final_score=decision["final_score"],
            )

            # ── Persist newly-evaluated rows only ───────────────────────
            for criterion_db, r in pending_to_persist:
                db.add(EvaluationResult(
                    job_id=job_uuid,
                    criterion_id=criterion_db.id,
                    bidder_file_id=fid,
                    verdict=str(r["verdict"]),
                    score=float(r["score"]),
                    weight=float(r.get("weight", 1.0)),
                    weighted_score=float(r.get("weighted_score", 0.0)),
                    explanation=str(r["explanation"]),
                ))

            for r in bidder_results:
                r["bidder_file_id"] = str(fid)
                r["bidder_name"]    = bidder_name
                r["final_status"]   = decision["final_status"]
                r["final_score"]    = decision["final_score"]
            all_results.extend(bidder_results)

        # ── Fallback: no bidder files → global per-criterion evaluation ──
        if not bidder_files:
            extraction_rows = (await db.execute(
                select(ExtractionResultDB)
                .where(ExtractionResultDB.job_id == job_uuid)
                .where(ExtractionResultDB.not_found == False)   # noqa: E712
                .order_by(
                    ExtractionResultDB.extraction_confidence.desc(),
                    ExtractionResultDB.created_at.asc(),
                    ExtractionResultDB.id.asc(),
                )
            )).scalars().all()

            cid_value_map = {}
            cid_confidence_map = {}
            for row in extraction_rows:
                cid = str(row.criterion_id)
                if cid not in cid_value_map:
                    cid_value_map[cid] = row.parsed_value
                    cid_confidence_map[cid] = float(row.extraction_confidence)

            global_results: list[dict] = []
            global_pending: list[tuple[Any, dict]] = []

            for criterion_db in criteria_rows:
                existing_eval = (await db.execute(
                    select(EvaluationResult)
                    .where(EvaluationResult.job_id == job_uuid)
                    .where(EvaluationResult.bidder_file_id.is_(None))
                    .where(EvaluationResult.criterion_id == criterion_db.id)
                    .limit(1)
                )).scalars().first()

                if existing_eval is not None:
                    global_results.append({
                        "criterion_id":   str(criterion_db.id),
                        "criterion_key":  criterion_db.criterion_key,
                        "verdict":        existing_eval.verdict,
                        "score":          existing_eval.score,
                        "weight":         existing_eval.weight,
                        "weighted_score": existing_eval.weighted_score,
                        "explanation":    existing_eval.explanation,
                    })
                    continue

                extracted_value = cid_value_map.get(str(criterion_db.id))
                conf = cid_confidence_map.get(str(criterion_db.id), 0.87)
                row = evaluate_criterion(criterion_db.to_dict(), extracted_value, conf)
                row["criterion_id"]  = str(criterion_db.id)
                row["criterion_key"] = criterion_db.criterion_key
                global_results.append(row)
                global_pending.append((criterion_db, row))

            criteria_lookup = {c.criterion_key: c.to_dict() for c in criteria_rows}
            compute_final_decision(global_results, criteria_lookup)

            for criterion_db, r in global_pending:
                db.add(EvaluationResult(
                    job_id=job_uuid,
                    criterion_id=criterion_db.id,
                    verdict=str(r["verdict"]),
                    score=float(r["score"]),
                    weight=float(r.get("weight", 1.0)),
                    weighted_score=float(r.get("weighted_score", 0.0)),
                    explanation=str(r["explanation"]),
                ))
            all_results = global_results

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
