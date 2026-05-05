"""VAJANS — Phase 6 Comparison Engine"""

import uuid as uuid_mod
from typing import Any, Dict, List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vajans.comparison_engine")


async def compare_bidders(db: AsyncSession, job_id: uuid_mod.UUID) -> Dict[str, Any]:
    """
    Aggregate per-bidder scores and rankings from EvaluationResult rows.
    Returns per-bidder data including per-criterion verdicts for the matrix view.
    """
    from app.models.evaluation import EvaluationResult
    from app.models.file import File
    from app.models.result import CriterionDB

    logger.info("Computing bidder comparison", job_id=str(job_id))

    all_rows = (
        await db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.job_id == job_id)
            .order_by(EvaluationResult.created_at.asc())
        )
    ).scalars().all()

    if not all_rows:
        return {"bidders": [], "rankings": []}

    # Latest result per (bidder_file_id, criterion_id)
    latest: dict[tuple, Any] = {}
    for row in all_rows:
        key = (row.bidder_file_id, str(row.criterion_id))
        latest[key] = row

    # Load criteria info for determining DISQUALIFIED status
    # Deduplicate by criterion_key so the matrix shows no duplicate rows
    crit_ids_set = {str(row.criterion_id) for row in all_rows}
    all_crit_rows = (
        await db.execute(
            select(CriterionDB).where(
                CriterionDB.id.in_([uuid_mod.UUID(cid) for cid in crit_ids_set])
            )
        )
    ).scalars().all()
    # Deduplicate by criterion_key — keep the UUID that appears earliest
    seen_keys: dict[str, CriterionDB] = {}
    for c in all_crit_rows:
        if c.criterion_key not in seen_keys:
            seen_keys[c.criterion_key] = c
    # Build map by id (all IDs pointing to the canonical row)
    canonical_ids: dict[str, str] = {}  # old_id → canonical_id
    for c in all_crit_rows:
        canonical = seen_keys[c.criterion_key]
        canonical_ids[str(c.id)] = str(canonical.id)
    crit_map = {str(c.id): c for c in seen_keys.values()}

    # Group by bidder_file_id
    bidder_results: dict[Any, list] = {}
    for (bidder_uuid, _), row in latest.items():
        bidder_results.setdefault(bidder_uuid, []).append(row)

    # Collect unique file IDs for name lookup
    file_ids_set: dict[str, uuid_mod.UUID] = {}
    for row in all_rows:
        if row.bidder_file_id is not None:
            file_ids_set[str(row.bidder_file_id)] = row.bidder_file_id
    file_map: dict[str, str] = {}
    if file_ids_set:
        file_rows = (
            await db.execute(
                select(File).where(File.id.in_(list(file_ids_set.values())))
            )
        ).scalars().all()
        file_map = {str(f.id): f.original_name for f in file_rows}

    bidders: List[Dict[str, Any]] = []
    for bidder_uuid, rows in bidder_results.items():
        verdicts       = [r.verdict for r in rows]
        total_weighted = sum(r.weighted_score for r in rows)
        max_possible   = sum(r.weight for r in rows)
        total_score    = round(total_weighted / max_possible, 4) if max_possible > 0 else 0.0

        # Check if disqualified: any mandatory criterion fails
        is_disqualified = any(
            r.verdict == "fail"
            and crit_map.get(str(r.criterion_id)) is not None
            and crit_map[str(r.criterion_id)].mandatory
            for r in rows
        )

        # Build per-criterion verdict map for the matrix view
        criteria_verdicts = [
            {
                "criterion_id": str(r.criterion_id),
                "verdict": r.verdict,
                "score": r.score,
                "explanation": r.explanation,
            }
            for r in rows
        ]

        # Disqualification reasons (failed mandatory criteria)
        disq_reasons = [
            crit_map[str(r.criterion_id)].label
            for r in rows
            if r.verdict == "fail"
            and crit_map.get(str(r.criterion_id)) is not None
            and crit_map[str(r.criterion_id)].mandatory
        ]

        bidder_id_str = str(bidder_uuid) if bidder_uuid is not None else None
        bidder_name   = file_map.get(bidder_id_str, "Unassigned") if bidder_id_str else "Unassigned"

        bidders.append({
            "bidder_id":              bidder_id_str,
            "bidder_name":            bidder_name,
            "total_score":            total_score,
            "pass":                   verdicts.count("pass"),
            "fail":                   verdicts.count("fail"),
            "unknown":                verdicts.count("unknown"),
            "total_criteria":         len(rows),
            "is_disqualified":        is_disqualified,
            "disqualification_reason": ", ".join(disq_reasons) if disq_reasons else None,
            "criteria":               criteria_verdicts,
        })

    # Rank: disqualified bidders go to the bottom; within groups, sort by score desc
    bidders.sort(key=lambda b: (b["is_disqualified"], -b["total_score"], b["fail"]))

    rankings: List[Dict[str, Any]] = []
    eligible_rank   = 1
    ineligible_rank = 1
    for b in bidders:
        if b["is_disqualified"]:
            rankings.append({
                "rank":                    None,
                "bidder_id":               b["bidder_id"],
                "bidder_name":             b["bidder_name"],
                "total_score":             b["total_score"],
                "is_eligible":             False,
                "disqualification_reason": b["disqualification_reason"],
            })
            ineligible_rank += 1
        else:
            rankings.append({
                "rank":        eligible_rank,
                "bidder_id":   b["bidder_id"],
                "bidder_name": b["bidder_name"],
                "total_score": b["total_score"],
                "is_eligible": True,
                "disqualification_reason": None,
            })
            eligible_rank += 1

    return {"bidders": bidders, "rankings": rankings}
