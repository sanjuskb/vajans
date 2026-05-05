"""
VAJANS — Phase 5 Review Engine
================================
Human-in-the-loop review logic.

Rules:
- APPROVE  → keep original EvaluationResult as-is, no new row
- EDIT     → re-evaluate criterion with reviewer-supplied value, append new EvaluationResult
- REJECT   → force verdict=fail, append new EvaluationResult

Invariants:
- Original EvaluationResult rows are NEVER overwritten
- ReviewAction records are NEVER overwritten
- recalculate_job_decision uses the LATEST EvaluationResult per criterion
"""

import uuid as uuid_mod
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts.schemas import ReviewerAction

logger = structlog.get_logger("vajans.review_engine")


async def apply_review_action(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
    criterion_id: uuid_mod.UUID,
    evaluation_result_id: Optional[uuid_mod.UUID],
    reviewer_action: ReviewerAction,
    original_value: Optional[str],
    updated_value: Optional[str],
    reason: str,
    actor: str = "reviewer",
) -> "ReviewAction":  # noqa: F821
    """
    Record a review decision and apply its effect.

    1. Append an immutable ReviewAction row.
    2. If EDIT or REJECT: append a new EvaluationResult (never overwrite).
    3. Log the action to the cryptographic audit chain.
    4. Return the ReviewAction.
    """
    from app.models.review import ReviewAction
    from app.services.audit_logger import log_action

    # 1. Append ReviewAction (immutable)
    review = ReviewAction(
        job_id=job_id,
        criterion_id=criterion_id,
        evaluation_result_id=evaluation_result_id,
        reviewer_action=reviewer_action,
        original_value=original_value,
        updated_value=updated_value,
        reason=reason,
    )
    db.add(review)

    logger.info(
        "Review action recorded",
        job_id=str(job_id),
        criterion_id=str(criterion_id),
        action=reviewer_action.value,
        actor=actor,
    )

    # 2. Apply effect (EDIT / REJECT create new EvaluationResult)
    new_result_id: Optional[str] = None
    if reviewer_action in (ReviewerAction.EDIT, ReviewerAction.REJECT):
        if evaluation_result_id is None:
            raise ValueError(
                f"evaluation_result_id is required for action={reviewer_action.value}"
            )
        new_result = await _apply_verdict_change(
            db=db,
            job_id=job_id,
            criterion_id=criterion_id,
            original_result_id=evaluation_result_id,
            reviewer_action=reviewer_action,
            updated_value=updated_value,
        )
        new_result_id = str(new_result.id)

    # 3. Log to audit chain
    await log_action(
        db=db,
        job_id=job_id,
        action_type="review_action",
        payload={
            "actor":                actor,
            "reviewer_action":      reviewer_action.value,
            "criterion_id":         str(criterion_id),
            "evaluation_result_id": str(evaluation_result_id) if evaluation_result_id else None,
            "new_result_id":        new_result_id,
            "original_value":       original_value,
            "updated_value":        updated_value,
            "reason":               reason,
        },
    )

    return review


async def _apply_verdict_change(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
    criterion_id: uuid_mod.UUID,
    original_result_id: uuid_mod.UUID,
    reviewer_action: ReviewerAction,
    updated_value: Optional[str],
) -> "EvaluationResult":  # noqa: F821
    """
    Create a new EvaluationResult based on reviewer decision.
    The original row is never touched.
    """
    from app.models.evaluation import EvaluationResult
    from app.models.result import CriterionDB
    from app.services.evaluation_engine import evaluate_criterion

    original = await db.get(EvaluationResult, original_result_id)
    if not original:
        raise ValueError(f"EvaluationResult {original_result_id} not found")

    if reviewer_action == ReviewerAction.REJECT:
        new_verdict = "fail"
        new_score   = 0.0
        explanation = f"Reviewer REJECTED this criterion. Reason: {updated_value or 'not provided'}"

    elif reviewer_action == ReviewerAction.EDIT:
        # Re-run deterministic evaluation with the reviewer-supplied value
        criterion_row = await db.get(CriterionDB, criterion_id)
        if criterion_row is None:
            raise ValueError(f"CriterionDB {criterion_id} not found")

        if criterion_row.threshold_value is None:
            logger.info(
                "Reviewer override applied for non-threshold criterion",
                criterion_id=str(criterion_id),
            )
            new_verdict = "pass"
            new_score   = 1.0
            explanation = f"Reviewer override applied with value={updated_value}"
        else:
            criterion_dict = criterion_row.to_dict()
            eval_result    = evaluate_criterion(criterion_dict, updated_value)

            new_verdict = eval_result["verdict"]
            new_score   = eval_result["score"]
            explanation = (
                f"Reviewer provided updated value={updated_value!r}. "
                f"Re-evaluated: {eval_result['explanation']}"
            )
    else:
        raise ValueError(f"Unexpected reviewer_action={reviewer_action}")

    new_id = uuid_mod.uuid4()
    new_result = EvaluationResult(
        id=new_id,
        job_id=job_id,
        criterion_id=criterion_id,
        bidder_file_id=original.bidder_file_id,
        verdict=new_verdict,
        score=new_score,
        weight=original.weight,
        weighted_score=round(new_score * original.weight, 4),
        explanation=explanation,
    )
    db.add(new_result)

    logger.info(
        "New EvaluationResult appended after review",
        job_id=str(job_id),
        criterion_id=str(criterion_id),
        old_verdict=original.verdict,
        new_verdict=new_verdict,
        new_score=new_score,
    )
    return new_result


async def recalculate_job_decision(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
) -> dict[str, Any]:
    """
    Recompute the final QUALIFIED/DISQUALIFIED decision using the LATEST
    EvaluationResult per criterion (original + any review overrides).

    Returns a summary dict — does NOT update the Job row (read-only query).
    """
    from app.models.evaluation import EvaluationResult
    from app.models.result import CriterionDB

    all_rows = (
        await db.execute(
            select(EvaluationResult)
            .where(EvaluationResult.job_id == job_id)
            .order_by(EvaluationResult.created_at.asc())
        )
    ).scalars().all()

    if not all_rows:
        return {"final_status": "PENDING", "final_score": 0.0, "total_criteria": 0}

    # Keep only the latest result per criterion (last wins)
    latest: dict[str, EvaluationResult] = {}
    for row in all_rows:
        latest[str(row.criterion_id)] = row

    # Fetch mandatory flags for the criteria
    crit_rows = (
        await db.execute(
            select(CriterionDB).where(
                CriterionDB.id.in_(
                    [uuid_mod.UUID(cid) for cid in latest]
                )
            )
        )
    ).scalars().all()
    crit_map = {str(c.id): c for c in crit_rows}

    disqualified = any(
        row.verdict == "fail"
        and crit_map.get(str(row.criterion_id)) is not None
        and crit_map[str(row.criterion_id)].mandatory
        for row in latest.values()
    )

    total_weighted = sum(r.weighted_score for r in latest.values())
    max_possible   = sum(r.weight for r in latest.values())
    final_score    = round(total_weighted / max_possible, 4) if max_possible > 0 else 0.0
    final_status   = "DISQUALIFIED" if disqualified else "QUALIFIED"

    verdicts = [r.verdict for r in latest.values()]
    summary = {
        "final_status":  final_status,
        "final_score":   final_score,
        "total_criteria": len(latest),
        "pass":          verdicts.count("pass"),
        "fail":          verdicts.count("fail"),
        "unknown":       verdicts.count("unknown"),
    }

    logger.info("Job decision recalculated", job_id=str(job_id), **summary)
    return summary
