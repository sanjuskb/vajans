"""
VAJANS — Analytics API Endpoints

Provides production-grade aggregations for the Dashboard analytics section:

  GET /v1/analytics/timeline?days=7
      Evaluation-result counts grouped by UTC day for the last `days` days.
      Powers the "Evaluations Over Time" area chart.

  GET /v1/analytics/verdicts
      Criterion-level verdict distribution across all evaluation results.
      Powers the "Verdict Distribution" donut chart.

Both endpoints perform a single SQL query each, return deterministic JSON,
and handle the zero-data state gracefully.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.evaluation import EvaluationResult

router = APIRouter(prefix="/analytics")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# GET /v1/analytics/timeline
# ---------------------------------------------------------------------------

@router.get("/timeline")
async def evaluation_timeline(
    days: int = Query(default=7, ge=1, le=90, description="Number of past days to include"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the number of criterion-level evaluation results completed for each
    of the last `days` UTC days (inclusive of today).

    Response shape:
        {
          "days": 7,
          "points": [
            {"date": "2026-05-01", "count": 12},
            {"date": "2026-05-02", "count": 0},
            ...
          ]
        }

    Zero-fill: days with no evaluations are always present so the chart
    never has gaps on the X-axis.
    """
    today = _today_utc()
    since = today - timedelta(days=days - 1)

    # Single aggregate query: group evaluation_results by calendar date (UTC)
    rows = (await db.execute(
        select(
            func.date(EvaluationResult.created_at).label("day"),
            func.count(EvaluationResult.id).label("cnt"),
        )
        .where(EvaluationResult.created_at >= datetime(since.year, since.month, since.day,
                                                        tzinfo=timezone.utc))
        .group_by(func.date(EvaluationResult.created_at))
        .order_by(func.date(EvaluationResult.created_at))
    )).all()

    # Index by date string
    by_day: dict[str, int] = {str(r.day): int(r.cnt) for r in rows}

    # Zero-fill the full window so the frontend never needs to handle gaps
    points = []
    cursor = since
    while cursor <= today:
        ds = cursor.isoformat()
        points.append({"date": ds, "count": by_day.get(ds, 0)})
        cursor += timedelta(days=1)

    return {"days": days, "points": points}


# ---------------------------------------------------------------------------
# GET /v1/analytics/verdicts
# ---------------------------------------------------------------------------

_VERDICT_LABELS: dict[str, str] = {
    "pass":    "Qualified",
    "fail":    "Disqualified",
    "unknown": "Review Required",
}

# Ordered for deterministic chart rendering
_VERDICT_ORDER = ["pass", "fail", "unknown"]

# Enterprise palette — neutral, readable on dark backgrounds, no alarm red.
# These exact hex values are serialised to the frontend so the chart colours
# are driven by the backend contract (single source of truth).
_VERDICT_COLORS: dict[str, str] = {
    "pass":    "#22C55E",   # emerald-500 — qualified
    "fail":    "#F97316",   # orange-500  — disqualified (not alarm-red)
    "unknown": "#A78BFA",   # violet-400  — review required
}


@router.get("/verdicts")
async def verdict_distribution(db: AsyncSession = Depends(get_db)):
    """
    Return criterion-level verdict counts across all evaluation results.

    Response shape:
        {
          "total": 75,
          "buckets": [
            {"verdict": "pass",    "label": "Qualified",        "count": 42, "color": "#22C55E"},
            {"verdict": "fail",    "label": "Disqualified",     "count": 18, "color": "#F97316"},
            {"verdict": "unknown", "label": "Review Required",  "count": 15, "color": "#A78BFA"},
          ]
        }

    Only buckets with at least 1 result are present unless total == 0, in
    which case all three buckets are returned with count 0 so the frontend
    can show a meaningful empty-state donut.
    """
    rows = (await db.execute(
        select(
            EvaluationResult.verdict,
            func.count(EvaluationResult.id).label("cnt"),
        )
        .group_by(EvaluationResult.verdict)
    )).all()

    by_verdict: dict[str, int] = {r.verdict: int(r.cnt) for r in rows}
    total = sum(by_verdict.values())

    buckets = []
    for v in _VERDICT_ORDER:
        cnt = by_verdict.get(v, 0)
        if total == 0 or cnt > 0:
            buckets.append({
                "verdict": v,
                "label":   _VERDICT_LABELS.get(v, v.title()),
                "count":   cnt,
                "color":   _VERDICT_COLORS.get(v, "#64748B"),
            })

    return {"total": total, "buckets": buckets}
