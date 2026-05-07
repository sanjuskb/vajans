"""VAJANS — Phase 6 Insight Engine"""

import uuid as uuid_mod
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vajans.insight_engine")


# ---------------------------------------------------------------------------
# Review-Queue confidence model
# ---------------------------------------------------------------------------
# Goal: produce a deterministic, per-row "how confident is the system in the
# data it observed for this criterion" score in [0, 1].  Surfaced as the
# Confidence column in the Review Queue and as the per-criterion trust bar
# on JobDetailPage.  Two regimes:
#
#   verdict in {pass, fail}  → trust the evaluator's score directly.
#       The evaluator already multiplies the verdict by the extraction
#       confidence (0.85–0.95 for clear hits, 0.0 for fail), so it is the
#       most informative single number we have.
#
#   verdict == unknown       → composite signal that captures *why* the
#       criterion was escalated.  Higher values = "we observed clear
#       evidence that explains the escalation"; lower values = "we have
#       very little data to go on".  Inputs:
#         base                = extraction_confidence (0.20 if not_found)
#         + 0.10              if criterion.ambiguous (we know why we escalated)
#         - 0.10              if numeric threshold was defined yet value
#                                is not_found (a real evidence gap)
#         - 0.05              if no source_snippet captured (zero evidence)
#         - 0.15 × (1 - ocr)  scanned-doc penalty (max -15%)
#       clamped to [0, 1] and rounded to 4 decimals.
#
# All inputs are read from existing DB columns; no new tables are required.
# ---------------------------------------------------------------------------

_AMBIGUITY_BONUS                  = 0.10
_MISSING_THRESHOLD_PENALTY        = 0.10
_NO_EVIDENCE_PENALTY              = 0.05
_OCR_PENALTY_WEIGHT               = 0.15
_DEFAULT_OCR_QUALITY              = 1.0   # unknown = treat as digital
_FALLBACK_NOT_FOUND_CONFIDENCE    = 0.20  # mirrors extraction.py


def _compute_review_confidence(
    *,
    verdict: str,
    score: float,
    extraction_confidence: Optional[float],
    not_found: bool,
    has_threshold: bool,
    is_ambiguous: bool,
    has_source_snippet: bool,
    ocr_quality: float,
) -> float:
    """
    Pure, deterministic. Same inputs → same output. See module docstring.
    """
    # PASS / FAIL: evaluator score already encodes extraction confidence
    if verdict in ("pass", "fail"):
        return round(max(0.0, min(1.0, float(score))), 4)

    # UNKNOWN regime — composite signal
    base = extraction_confidence if extraction_confidence is not None else _FALLBACK_NOT_FOUND_CONFIDENCE
    confidence = float(base)

    if is_ambiguous:
        confidence += _AMBIGUITY_BONUS

    if has_threshold and not_found:
        confidence -= _MISSING_THRESHOLD_PENALTY

    if not has_source_snippet:
        confidence -= _NO_EVIDENCE_PENALTY

    confidence -= _OCR_PENALTY_WEIGHT * (1.0 - max(0.0, min(1.0, float(ocr_quality))))

    return round(max(0.0, min(1.0, confidence)), 4)


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


async def _load_extraction_lookup(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
) -> Dict[Tuple[str, str], Any]:
    """
    Build a (bidder_file_id, criterion_id) → ExtractionResultDB lookup.

    When multiple extraction rows exist for the same key (re-runs, retries),
    the highest-confidence row wins; ties broken by oldest row + lowest id
    so the chosen row is byte-stable across pipeline restarts.
    """
    from app.models.result import ExtractionResultDB

    rows = (await db.execute(
        select(ExtractionResultDB)
        .where(ExtractionResultDB.job_id == job_id)
        .order_by(
            ExtractionResultDB.extraction_confidence.desc(),
            ExtractionResultDB.created_at.asc(),
            ExtractionResultDB.id.asc(),
        )
    )).scalars().all()

    lookup: Dict[Tuple[str, str], Any] = {}
    for row in rows:
        key = (str(row.file_id), str(row.criterion_id))
        if key not in lookup:           # first hit = best confidence
            lookup[key] = row
    return lookup


async def _load_ocr_quality_per_file(
    db: AsyncSession,
    job_id: uuid_mod.UUID,
) -> Dict[str, float]:
    """
    Per-bidder-file OCR quality score, sourced from the INGESTION_DONE
    audit log entry written by `worker/tasks/ingestion.py`. Returns
    {file_id_str: ocr_quality} with values in [0, 1]. Files whose audit
    entry is missing are absent from the dict — callers should treat
    missing as digital (1.0).
    """
    from app.models.audit import AuditLog
    from shared.contracts.schemas import AuditAction

    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.job_id == job_id)
        .where(AuditLog.action == AuditAction.INGESTION_DONE)
        # Latest ingestion result wins (handles re-ingestions deterministically).
        .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    )).scalars().all()

    ocr_map: Dict[str, float] = {}
    for row in rows:
        if row.file_id is None or not isinstance(row.details, dict):
            continue
        raw = row.details.get("ocr_quality")
        if raw is None:
            continue
        try:
            ocr_map[str(row.file_id)] = float(raw)
        except (TypeError, ValueError):
            continue
    return ocr_map


async def generate_criterion_insights(
    db: AsyncSession, job_id: uuid_mod.UUID
) -> List[Dict[str, Any]]:
    """
    Return per-criterion insight details.
    For multi-bidder jobs, returns one insight entry per (bidder × criterion) pair,
    with bidder context included.

    Each entry now carries the data the Review Queue needs to render a real
    confidence signal:
      score                  — evaluator score (already in DB)
      extraction_confidence  — per-bidder-per-criterion extraction signal
      ocr_quality            — per-bidder OCR quality (digital ≈ 1.0)
      review_confidence      — deterministic composite, see _compute_review_confidence
      source_snippet         — evidence text (or None)
      page_number            — best-effort page resolution
      extracted_value        — parsed value (string form) or None
      not_found              — extraction missed it
      ambiguous              — criterion flagged as ambiguous
      has_threshold          — criterion has a numeric threshold
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

    extraction_lookup = await _load_extraction_lookup(db, job_id)
    ocr_quality_map   = await _load_ocr_quality_per_file(db, job_id)

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

        bidder_file_id_str = str(r.bidder_file_id) if r.bidder_file_id else ""
        bidder_name = file_map.get(bidder_file_id_str, "") if bidder_file_id_str else ""

        # Look up the matching extraction row for this (bidder, criterion)
        extraction_row = extraction_lookup.get(
            (bidder_file_id_str, str(r.criterion_id))
        )
        if extraction_row is not None:
            extraction_confidence = float(extraction_row.extraction_confidence)
            not_found             = bool(extraction_row.not_found)
            source_snippet        = extraction_row.source_snippet
            page_number           = extraction_row.page_number
            extracted_value       = extraction_row.parsed_value
        else:
            extraction_confidence = None
            not_found             = True
            source_snippet        = None
            page_number           = None
            extracted_value       = None

        ocr_quality = ocr_quality_map.get(bidder_file_id_str, _DEFAULT_OCR_QUALITY)

        is_ambiguous   = bool(crit.ambiguous) if crit is not None else False
        has_threshold  = bool(crit and crit.threshold_value is not None)
        has_snippet    = bool(source_snippet and source_snippet.strip())

        review_confidence = _compute_review_confidence(
            verdict=r.verdict,
            score=float(r.score),
            extraction_confidence=extraction_confidence,
            not_found=not_found,
            has_threshold=has_threshold,
            is_ambiguous=is_ambiguous,
            has_source_snippet=has_snippet,
            ocr_quality=ocr_quality,
        )

        insights.append({
            "criterion_id":          str(r.criterion_id),
            "label":                 crit.label if crit else "Unknown",
            "verdict":               r.verdict,
            "explanation":           r.explanation,
            "weight":                r.weight,
            "importance_level":      importance,
            "bidder_file_id":        bidder_file_id_str or None,
            "bidder_name":           bidder_name,
            # Real signals — replace any frontend hardcoded 0.5 with these.
            "score":                 round(float(r.score), 4),
            "extraction_confidence": (
                round(extraction_confidence, 4) if extraction_confidence is not None else None
            ),
            "ocr_quality":           round(float(ocr_quality), 4),
            "review_confidence":     review_confidence,
            "source_snippet":        source_snippet,
            "page_number":           page_number,
            "extracted_value":       extracted_value,
            "not_found":             not_found,
            "ambiguous":             is_ambiguous,
            "has_threshold":         has_threshold,
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
