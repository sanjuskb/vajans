"""
VAJANS — Analyze API Endpoints (Phase 3 + Phase 4 + Phase 5)
"""

import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import Job
from shared.contracts.schemas import JobStatus, ReviewActionCreate

router = APIRouter(prefix="/analyze")


# ── Phase 3: Trigger AI pipeline ────────────────────────────────────────────

@router.post(
    "/{job_id}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_analysis(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.EXTRACTING, JobStatus.EVALUATING):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in progress: {job.status.value}",
        )

    if job.status == JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail="Job already completed.",
        )

    try:
        from worker.tasks.ai_pipeline import run_ai_pipeline

        task = run_ai_pipeline.apply_async(
            args=[str(job_id)],
            queue="extraction",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "message": "AI pipeline started",
        "job_id": str(job_id),
        "task_id": task.id,
    }


# ── Phase 3: Criteria + extractions ─────────────────────────────────────────

@router.get("/{job_id}/criteria")
async def get_job_criteria(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.models.result import CriterionDB

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(CriterionDB)
        .where(CriterionDB.job_id == job_id)
        # Stable order: (criterion_key, id) -- criterion_key is the
        # logical, data-derived identifier; id breaks any remaining ties.
        .order_by(CriterionDB.criterion_key.asc(), CriterionDB.id.asc())
    )
    criteria = result.scalars().all()

    return {"total": len(criteria), "data": [c.to_dict() for c in criteria]}


@router.get("/{job_id}/extractions")
async def get_job_extractions(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.models.result import ExtractionResultDB

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(ExtractionResultDB).where(ExtractionResultDB.job_id == job_id)
    )
    data = result.scalars().all()

    return {"total": len(data), "data": [d.to_dict() for d in data]}


# ── Phase 4: Evaluation ──────────────────────────────────────────────────────

@router.post("/{job_id}/evaluate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_evaluation(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger Phase 4 deterministic evaluation for a completed extraction job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        from worker.tasks.evaluation import evaluate_job_task
        task = evaluate_job_task.apply_async(args=[str(job_id)], queue="evaluation")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"message": "Evaluation started", "job_id": str(job_id), "task_id": task.id}


@router.get("/{job_id}/evaluation")
async def get_evaluation_results(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return evaluation results in the format the frontend expects.

    Top-level fields (EvaluationResponse interface):
      job_id, final_status, final_score, summary, results, bidders

    - results: flat list of ALL EvaluationResult rows (all bidders)
    - bidders: per-bidder breakdown (QUALIFIED/DISQUALIFIED, score, pass/fail counts)
    - final_status / final_score: aggregate across all bidders
    - summary: {total, pass, fail, unknown} aggregated
    """
    from app.models.evaluation import EvaluationResult
    from app.models.result import CriterionDB
    from app.models.file import File as FileModel

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    rows = (await db.execute(
        select(EvaluationResult)
        .where(EvaluationResult.job_id == job_id)
        # Deterministic ordering: created_at ties resolved by id (UUID).
        # Without the id tiebreak, multiple rows inserted in a single
        # transaction share an identical timestamp and Postgres returns
        # them in arbitrary order — making downstream dedup non-deterministic.
        .order_by(EvaluationResult.created_at.asc(), EvaluationResult.id.asc())
    )).scalars().all()

    empty_response = {
        "job_id":       str(job_id),
        "final_status": "PENDING",
        "final_score":  0.0,
        "summary":      {"total": 0, "pass": 0, "fail": 0, "unknown": 0},
        "results":      [],
        "bidders":      [],
    }
    if not rows:
        return empty_response

    # ── Criteria map ──────────────────────────────────────────────────────
    crit_ids  = list({r.criterion_id for r in rows})
    crit_rows = (await db.execute(
        select(CriterionDB).where(CriterionDB.id.in_(crit_ids))
    )).scalars().all()
    crit_map = {str(c.id): c for c in crit_rows}

    # ── File names map ────────────────────────────────────────────────────
    bidder_file_ids = list({r.bidder_file_id for r in rows if r.bidder_file_id})
    file_map: dict[str, FileModel] = {}
    if bidder_file_ids:
        file_rows = (await db.execute(
            select(FileModel).where(FileModel.id.in_(bidder_file_ids))
        )).scalars().all()
        file_map = {str(f.id): f for f in file_rows}

    # ── Deduplicate: latest per (bidder, criterion) ───────────────────────
    # rows are already sorted by (created_at asc, id asc); the dict overwrite
    # therefore retains the LATEST row deterministically (same id wins on ties).
    latest_map: dict[tuple, EvaluationResult] = {}
    for r in rows:
        key = (str(r.bidder_file_id) if r.bidder_file_id else None,
               str(r.criterion_id))
        latest_map[key] = r

    # Sort deduped list by (bidder_file_id, criterion_id) for stable iteration.
    deduped = sorted(
        latest_map.values(),
        key=lambda r: (str(r.bidder_file_id) if r.bidder_file_id else "",
                       str(r.criterion_id)),
    )

    # ── Group by bidder ───────────────────────────────────────────────────
    by_bidder: dict[str | None, list[EvaluationResult]] = {}
    for r in deduped:
        fid = str(r.bidder_file_id) if r.bidder_file_id else None
        by_bidder.setdefault(fid, []).append(r)

    bidder_summaries = []
    # Iterate bidders in stable order (file name, then id) so that the response
    # array is deterministic across runs regardless of dict insertion order.
    sorted_bidder_keys = sorted(
        by_bidder.keys(),
        key=lambda fid: (
            (file_map[fid].original_name if fid and fid in file_map else ""),
            fid or "",
        ),
    )
    for fid_str in sorted_bidder_keys:
        bidder_rows = by_bidder[fid_str]
        disqualified = any(
            r.verdict == "fail"
            and str(r.criterion_id) in crit_map
            and crit_map[str(r.criterion_id)].mandatory
            for r in bidder_rows
        )
        total_w = sum(r.weighted_score for r in bidder_rows)
        max_w   = sum(r.weight for r in bidder_rows)
        b_score = round(total_w / max_w, 4) if max_w > 0 else 0.0
        b_verd  = [r.verdict for r in bidder_rows]
        f       = file_map.get(fid_str) if fid_str else None
        # Disqualification reasons (failed mandatory criteria) — sorted by label
        # for deterministic presentation.
        disq_reasons = sorted([
            crit_map[str(r.criterion_id)].label
            for r in bidder_rows
            if r.verdict == "fail"
            and str(r.criterion_id) in crit_map
            and crit_map[str(r.criterion_id)].mandatory
        ])
        # Sort the per-bidder results list by criterion_id for stable output.
        sorted_bidder_rows = sorted(bidder_rows, key=lambda r: str(r.criterion_id))
        bidder_summaries.append({
            "bidder_file_id": fid_str,
            "bidder_name":    f.original_name if f else "Unknown",
            "final_status":   "DISQUALIFIED" if disqualified else "QUALIFIED",
            "final_score":    b_score,
            "summary": {
                "total":   len(bidder_rows),
                "pass":    b_verd.count("pass"),
                "fail":    b_verd.count("fail"),
                "unknown": b_verd.count("unknown"),
            },
            "disqualification_reasons": disq_reasons,
            "results": [r.to_dict() for r in sorted_bidder_rows],
        })

    # ── Aggregate across all bidders ──────────────────────────────────────
    all_verdicts   = [r.verdict for r in deduped]
    all_total_w    = sum(r.weighted_score for r in deduped)
    all_max_w      = sum(r.weight for r in deduped)
    final_score    = round(all_total_w / all_max_w, 4) if all_max_w > 0 else 0.0
    any_disq       = any(b["final_status"] == "DISQUALIFIED" for b in bidder_summaries)
    all_disq       = all(b["final_status"] == "DISQUALIFIED" for b in bidder_summaries)

    if all_disq:
        final_status = "DISQUALIFIED"
    elif any_disq:
        final_status = "NEEDS_REVIEW"
    else:
        final_status = "QUALIFIED"

    return {
        "job_id":       str(job_id),
        "final_status": final_status,
        "final_score":  final_score,
        "summary": {
            "total":   len(deduped),
            "pass":    all_verdicts.count("pass"),
            "fail":    all_verdicts.count("fail"),
            "unknown": all_verdicts.count("unknown"),
        },
        "results":  [r.to_dict() for r in deduped],
        "bidders":  bidder_summaries,
    }


# ── Phase 5: Review System ───────────────────────────────────────────────────

@router.post(
    "/{job_id}/review",
    status_code=status.HTTP_201_CREATED,
)
async def submit_review(
    job_id: uuid_lib.UUID,
    body: ReviewActionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a human review decision for one criterion's evaluation result.

    Actions:
    - approve: keep original verdict, no EvaluationResult change
    - edit:    re-evaluate with reviewer-supplied value, append new EvaluationResult
    - reject:  force verdict=fail, append new EvaluationResult
    """
    from app.models.audit import AuditLog
    from app.services.review_engine import apply_review_action, recalculate_job_decision
    from shared.contracts.schemas import AuditAction

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        review = await apply_review_action(
            db=db,
            job_id=job_id,
            criterion_id=body.criterion_id,
            evaluation_result_id=body.evaluation_result_id,
            reviewer_action=body.reviewer_action,
            original_value=body.original_value,
            updated_value=body.updated_value,
            reason=body.reason,
            actor="reviewer",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Append standard audit log entry
    db.add(AuditLog(
        job_id=job_id,
        action=AuditAction.REVIEW_SUBMITTED,
        actor="reviewer",
        details={
            "criterion_id":    str(body.criterion_id),
            "reviewer_action": body.reviewer_action.value,
            "reason":          body.reason,
        },
    ))

    decision = await recalculate_job_decision(db, job_id)

    return {
        "message":          "Review action recorded",
        "review_id":        str(review.id),
        "current_decision": decision,
    }


@router.get("/{job_id}/review")
async def get_review_actions(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all review actions submitted for this job, in chronological order."""
    from app.models.review import ReviewAction

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    rows = (
        await db.execute(
            select(ReviewAction)
            .where(ReviewAction.job_id == job_id)
            .order_by(ReviewAction.created_at.asc())
        )
    ).scalars().all()

    return {"total": len(rows), "data": [r.to_dict() for r in rows]}


# ── Phase 6: Insight & Visualization ────────────────────────────────────────

@router.get("/{job_id}/insights")
async def get_insights(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return structured insight data: summary, per-criterion details, and quality flags."""
    from app.services.insight_engine import (
        generate_job_summary,
        generate_criterion_insights,
        generate_flags,
    )

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    summary  = await generate_job_summary(db, job_id)
    criteria = await generate_criterion_insights(db, job_id)
    flags    = await generate_flags(db, job_id)

    return {"summary": summary, "criteria": criteria, "flags": flags}


@router.get("/{job_id}/comparison")
async def get_comparison(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return per-bidder scores and rankings."""
    from app.services.comparison_engine import compare_bidders

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await compare_bidders(db, job_id)
    return result


@router.get("/{job_id}/dashboard")
async def get_dashboard(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all Phase 6 data combined: summary, criteria, comparison, and flags."""
    from app.services.insight_engine import (
        generate_job_summary,
        generate_criterion_insights,
        generate_flags,
    )
    from app.services.comparison_engine import compare_bidders
    import structlog as _structlog

    _logger = _structlog.get_logger("vajans.dashboard")

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    summary    = await generate_job_summary(db, job_id)
    criteria   = await generate_criterion_insights(db, job_id)
    comparison = await compare_bidders(db, job_id)
    flags      = await generate_flags(db, job_id)

    _logger.info("Dashboard response built", job_id=str(job_id))

    return {
        "summary":    summary,
        "criteria":   criteria,
        "comparison": comparison,
        "flags":      flags,
    }


@router.get("/{job_id}/audit")
async def get_audit_trail(
    job_id: uuid_lib.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the full cryptographic audit chain for this job.
    Includes chain integrity verification result.
    """
    from app.services.audit_logger import verify_chain

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return await verify_chain(db, job_id)
