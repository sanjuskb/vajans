"""VAJANS — Phase 6 Insight Engine"""

import uuid as uuid_mod
from typing import Any, Dict, List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vajans.insight_engine")


async def _get_all_results(db: AsyncSession, job_id: uuid_mod.UUID) -> list:
    """
    Return the latest EvaluationResult per (bidder_file_id, criterion_id) pair.
    This correctly handles multi-bidder jobs — each bidder keeps their own results.
    """
    from app.models.evaluation import EvaluationResult

    all_rows = (
        await db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.job_id == job_id)
            # Stable ordering: id breaks created_at ties so dedup
            # selects the same "latest" row across re-runs.
            .order_by(EvaluationResult.created_at.asc(),
                      EvaluationResult.id.asc())
        )
    ).scalars().all()

    # Deduplicate: keep latest per (bidder_file_id, criterion_id)
    latest: dict[tuple, Any] = {}
    for row in all_rows:
        key = (str(row.bidder_file_id) if row.bidder_file_id else "__none__",
               str(row.criterion_id))
        latest[key] = row

    return list(latest.values())


async def _get_criteria_rows(db: AsyncSession, job_id: uuid_mod.UUID) -> list:
    """Return deduplicated CriterionDB rows for a job (one per criterion_key)."""
    from app.models.result import CriterionDB
    all_rows = (
        await db.execute(
            select(CriterionDB)
            .where(CriterionDB.job_id == job_id)
            .order_by(CriterionDB.created_at.asc(), CriterionDB.id.asc())
        )
    ).scalars().all()
    # Deduplicate by criterion_key — keep the first (oldest) occurrence
    seen: dict[str, CriterionDB] = {}
    for row in all_rows:
        if row.criterion_key not in seen:
            seen[row.criterion_key] = row
    return list(seen.values())


async def _get_criteria_map(db: AsyncSession, criterion_ids: list) -> dict:
    from app.models.result import CriterionDB
    if not criterion_ids:
        return {}
    rows = (
        await db.execute(
            select(CriterionDB).where(
                CriterionDB.id.in_([uuid_mod.UUID(cid) for cid in criterion_ids])
            )
        )
    ).scalars().all()
    return {str(c.id): c for c in rows}


async def generate_job_summary(db: AsyncSession, job_id: uuid_mod.UUID) -> Dict[str, Any]:
    """
    Return job-level evaluation summary.

    For multi-bidder jobs: aggregates across ALL bidder results.
    total_criteria = unique criterion count (not multiplied by bidder count).
    pass/fail/unknown = totals across all (bidder × criterion) pairs.
    """
    logger.info("Generating job summary", job_id=str(job_id))

    # Get unique criteria count
    crit_rows = await _get_criteria_rows(db, job_id)
    total_criteria = len(crit_rows)

    if total_criteria == 0:
        return {
            "total_criteria": 0,
            "pass": 0,
            "fail": 0,
            "unknown": 0,
            "final_score": 0.0,
            "final_status": "PENDING",
            "review_required": False,
            "bidder_count": 0,
        }

    results = await _get_all_results(db, job_id)

    if not results:
        return {
            "total_criteria": total_criteria,
            "pass": 0,
            "fail": 0,
            "unknown": 0,
            "final_score": 0.0,
            "final_status": "PENDING",
            "review_required": False,
            "bidder_count": 0,
        }

    crit_ids = list({str(r.criterion_id) for r in results})
    crit_map = await _get_criteria_map(db, crit_ids)

    # Count unique bidders
    bidder_ids = {str(r.bidder_file_id) for r in results if r.bidder_file_id}
    bidder_count = len(bidder_ids) if bidder_ids else 1

    verdicts = [r.verdict for r in results]
    pass_count    = verdicts.count("pass")
    fail_count    = verdicts.count("fail")
    unknown_count = verdicts.count("unknown")

    total_weighted = sum(r.weighted_score for r in results)
    max_possible   = sum(r.weight for r in results)
    final_score    = round(total_weighted / max_possible, 4) if max_possible > 0 else 0.0

    # Disqualified if any mandatory criterion fails for any bidder
    disqualified = any(
        r.verdict == "fail"
        and crit_map.get(str(r.criterion_id)) is not None
        and crit_map[str(r.criterion_id)].mandatory
        for r in results
    )
    final_status    = "DISQUALIFIED" if disqualified else "QUALIFIED"
    review_required = unknown_count > 0 or fail_count > 0

    return {
        "total_criteria": total_criteria,
        "pass":           pass_count,
        "fail":           fail_count,
        "unknown":        unknown_count,
        "final_score":    final_score,
        "final_status":   final_status,
        "review_required": review_required,
        "bidder_count":   bidder_count,
    }


async def generate_criterion_insights(
    db: AsyncSession, job_id: uuid_mod.UUID
) -> List[Dict[str, Any]]:
    """
    Return per-criterion insight details.
    For multi-bidder jobs, returns one insight entry per (bidder × criterion) pair,
    with bidder context included.
    """
    results = await _get_all_results(db, job_id)

    if not results:
        return []

    crit_ids = [str(r.criterion_id) for r in results]
    crit_map = await _get_criteria_map(db, crit_ids)

    # Load bidder file names
    from app.models.file import File as FileModel
    bidder_file_ids = list({r.bidder_file_id for r in results if r.bidder_file_id})
    file_map: dict[str, str] = {}
    if bidder_file_ids:
        file_rows = (
            await db.execute(
                select(FileModel).where(FileModel.id.in_(bidder_file_ids))
            )
        ).scalars().all()
        file_map = {str(f.id): f.original_name for f in file_rows}

    insights = []
    for r in results:
        crit = crit_map.get(str(r.criterion_id))
        if crit is None:
            importance = "medium"
        elif crit.mandatory:
            importance = "high"
        elif r.weight >= 2.0:
            importance = "medium"
        else:
            importance = "low"

        bidder_name = file_map.get(str(r.bidder_file_id), "") if r.bidder_file_id else ""

        insights.append({
            "criterion_id":    str(r.criterion_id),
            "label":           crit.label if crit else "Unknown",
            "verdict":         r.verdict,
            "explanation":     r.explanation,
            "weight":          r.weight,
            "importance_level": importance,
            "bidder_file_id":  str(r.bidder_file_id) if r.bidder_file_id else None,
            "bidder_name":     bidder_name,
        })

    # Stable, human-friendly order: by bidder name, then criterion label,
    # then criterion_id (UUID) as a final tiebreak. Without this the list
    # would inherit the dict iteration order of `results`.
    insights.sort(key=lambda i: (
        (i["bidder_name"] or "").lower(),
        (i["label"]       or "").lower(),
        i["criterion_id"],
    ))
    return insights


async def generate_flags(
    db: AsyncSession, job_id: uuid_mod.UUID
) -> List[Dict[str, Any]]:
    """Detect quality and completeness issues in the evaluation."""
    results = await _get_all_results(db, job_id)
    flags: List[Dict[str, Any]] = []

    if not results:
        flags.append({
            "code":     "empty_evaluation",
            "message":  "No evaluation results found for this job.",
            "severity": "critical",
        })
        return flags

    crit_ids = [str(r.criterion_id) for r in results]
    crit_map = await _get_criteria_map(db, crit_ids)

    total         = len(results)
    unknown_count = sum(1 for r in results if r.verdict == "unknown")

    if total > 0 and (unknown_count / total) > 0.5:
        flags.append({
            "code":     "high_unknown_ratio",
            "message":  f"{unknown_count}/{total} evaluations have UNKNOWN verdict (>50% threshold).",
            "severity": "warning",
        })

    # Sort affected criterion ids so the flag payload is byte-identical
    # across runs (set iteration order is unstable in CPython).
    missing_threshold = sorted([
        cid for cid in set(crit_ids)
        if crit_map.get(cid) is not None and crit_map[cid].threshold_value is None
    ])
    if missing_threshold:
        flags.append({
            "code":              "missing_numeric_thresholds",
            "message":           f"{len(missing_threshold)} criteria have no numeric threshold defined.",
            "severity":          "info",
            "affected_criteria": missing_threshold,
        })

    return flags
