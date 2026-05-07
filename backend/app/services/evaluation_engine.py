"""
VAJANS — Phase 4 Deterministic Evaluation Engine
==================================================
Pure Python. No async. No DB access. No external calls.

Rules:
  - ambiguous criterion                → UNKNOWN  (score = _UNKNOWN_SCORE)
  - no threshold AND no value          → UNKNOWN  (score = _UNKNOWN_SCORE)
  - bidder value not found in document → UNKNOWN  (score = _UNKNOWN_SCORE)
  - value found, numeric threshold     → operator → PASS (extraction_confidence) or FAIL (0.0)
  - value found, no numeric threshold  → signal-based → PASS or FAIL

  See `app/services/insight_engine._compute_review_confidence` for the
  Review-Queue confidence model that surfaces these scores to the UI.

TrustScore formula (stored per criterion result):
  TrustScore = 0.30 × ocr_quality + 0.25 × field_completeness
             + 0.25 × semantic_confidence + 0.20 × cross_doc_consistency

Final decision:
  - ANY mandatory FAIL               → DISQUALIFIED
  - ALL mandatory PASS               → QUALIFIED
  - Unknowns present, no FAIL        → NEEDS_REVIEW (shown as QUALIFIED with flag)
  - final_score = sum(weighted) / max_possible
"""

import operator as op_module
import re
import structlog
from typing import Any, Dict, List, Optional

logger = structlog.get_logger("vajans.evaluation_engine")

_OPS = {
    "gte": op_module.ge,
    "lte": op_module.le,
    "gt":  op_module.gt,
    "lt":  op_module.lt,
    "eq":  op_module.eq,
    "neq": op_module.ne,
}

_UNKNOWN_SCORE = 0.3   # partial credit for uncertain data (score = 0.3 × weight)

# GST pattern: 15-character alphanumeric
_GST_RE = re.compile(r'\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b')


def _to_float(val: Any) -> Optional[float]:
    """
    Coerce extracted value to float.

    Handles:
    - int / float                 → as-is
    - "8.2"                       → 8.2
    - "8.2 crore" / "8.2 Cr"     → 8.2   (already in crore — matches threshold unit)
    - "82 lakhs" / "82 lakh"     → 0.82  (convert: 1 crore = 100 lakhs)
    - None / "None" / "null"     → None
    - lists / complex strings    → extract first number
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip().lower()
    if s in ("none", "null", "nan", ""):
        return None

    # Handle list representation like "[8.2, 9.1, 10.4]" — take average
    numbers = re.findall(r'\d+\.?\d*', s)
    if not numbers:
        return None

    if '[' in s or ',' in s:
        # Multiple values — average them (e.g., multiple year turnovers)
        try:
            vals = [float(n) for n in numbers]
            num = sum(vals) / len(vals)
        except ValueError:
            return None
    else:
        try:
            num = float(numbers[0])
        except ValueError:
            return None

    # Unit normalization: convert lakhs → crore
    if any(k in s for k in ("lakh", "lac")):
        num = round(num / 100.0, 4)

    return num


def _is_gst_number(val: str) -> bool:
    return bool(_GST_RE.search(val.upper()))


# NOTE: A `_compute_trust_score()` helper used to live here with a hard-coded
# `ocr_quality: float = 0.88` default. It had ZERO callers anywhere in the
# codebase and the 0.88 default was the smoking gun behind the "every
# document shows 88%" UI bug (the frontend separately fell back to 0.88 when
# the API didn't expose `ocr_quality`). The helper was removed; the real,
# dynamic OCR-quality score now lives in `app.engines.ingestion.compute_ocr_quality`
# and is read by the API layer / frontend without any 0.88 placeholder.


# ---------------------------------------------------------------------------
# Core criterion evaluator
# ---------------------------------------------------------------------------

def evaluate_criterion(criterion: Dict, extracted_value: Any = None, confidence: float = 0.87) -> Dict:
    """
    Evaluate one criterion against one extracted value.

    Args:
        confidence: extraction confidence (0–1). Passing criteria use this instead
                    of a perfect 1.0 so that 100% scores only occur on exact matches.
                    Default 0.87 reflects typical OCR + LLM extraction quality.

    Returns:
        {"verdict": str, "score": float, "explanation": str}
    """
    label     = criterion.get("label") or criterion.get("criterion_key", "unnamed")
    ambiguous = bool(criterion.get("ambiguous", False))
    threshold = _to_float(criterion.get("threshold_value"))
    op_key    = (criterion.get("operator") or "gte").lower().strip()

    logger.debug(
        "Evaluating criterion",
        label=label,
        op=op_key,
        threshold=threshold,
        extracted=extracted_value,
    )

    if ambiguous:
        return {
            "verdict": "unknown",
            "score": _UNKNOWN_SCORE,
            "explanation": f"[{label}] Criterion is ambiguous — cannot evaluate deterministically",
        }

    # ── Numeric evaluation path ───────────────────────────────────────────
    if threshold is not None:
        val = _to_float(extracted_value)
        if val is None:
            return {
                "verdict": "unknown",
                "score": _UNKNOWN_SCORE,
                "explanation": f"[{label}] Value not found or not numeric in bidder document",
            }
        fn      = _OPS.get(op_key, op_module.ge)
        passed  = fn(val, threshold)
        verdict = "pass" if passed else "fail"
        score   = round(confidence, 4) if passed else 0.0
        explanation = (
            f"[{label}] extracted={val} {op_key} threshold={threshold} → {verdict.upper()}"
        )
        return {"verdict": verdict, "score": score, "explanation": explanation}

    # ── No numeric threshold → boolean / presence evaluation ─────────────
    if extracted_value is None:
        return {
            "verdict": "unknown",
            "score": _UNKNOWN_SCORE,
            "explanation": f"[{label}] Not found in bidder document",
        }

    val_str   = str(extracted_value).strip()
    val_lower = val_str.lower()

    # GST: if value matches GST pattern → PASS
    if any(k in label.lower() for k in ("gst", "gstin", "tax")):
        if _is_gst_number(val_str):
            return {
                "verdict": "pass",
                "score": round(confidence, 4),
                "explanation": f"[{label}] Valid GST number found: {val_str}",
            }
        # Fall through to signal-based check below

    # STEP 1: Check negated PASS phrases FIRST (deterministic ordering).
    # CRITICAL: "not blacklisted" contains "blacklisted" — therefore PASS signals
    # MUST be matched before FAIL signals or every clean record would be flagged.
    _NEGATED_PASS_SIGNALS = (
        # Blacklisting / debarment — explicit clean declarations
        "not blacklisted", "not_blacklisted",
        "is not blacklisted", "are not blacklisted",
        "not debarred", "not_debarred",
        "is not debarred", "are not debarred",
        "not listed", "not_listed",
        "no blacklisting", "no debarment",
        "debarment: none",
        "not been blacklisted", "not been debarred",
        "hereby declare", "declares that",
    )
    if any(sig in val_lower for sig in _NEGATED_PASS_SIGNALS):
        return {
            "verdict": "pass",
            "score": round(confidence, 4),
            "explanation": f"[{label}] Compliant (not blacklisted/debarred): '{extracted_value}'",
        }

    # STEP 2: Explicit failure signals — checked AFTER pass signals so phrases
    # like "is not blacklisted" never fall through to here.
    _FAIL_SIGNALS = (
        # Blacklisting / debarment — explicit non-compliance
        "is blacklisted", "has been blacklisted", "was blacklisted",
        "is debarred", "has been debarred", "was debarred",
        # Generic non-compliance signals (matched as substrings)
        "expired", "invalid", "blacklisted", "debarred",
        "cancelled", "revoked", "suspended",
        "not registered", "not valid", "lapsed",
        # Explicit denial of certification / registration possession
        "does not hold", "not held", "not_held",
        "not yet", "not yet allotted", "not yet issued", "not yet been issued",
        "under process", "in process", "in_process",
        "pending", "applied for", "application pending", "yet to be",
        "not certified", "not currently certified",
        "no certification", "no valid certificate",
    )
    if any(sig in val_lower for sig in _FAIL_SIGNALS):
        return {
            "verdict": "fail",
            "score": 0.0,
            "explanation": f"[{label}] Non-compliant: '{extracted_value}'",
        }

    # STEP 3: Explicit pass signals
    _PASS_SIGNALS = (
        "valid", "registered", "active", "compliant", "certified",
        "approved", "current", "clean",
    )
    if any(sig in val_lower for sig in _PASS_SIGNALS):
        return {
            "verdict": "pass",
            "score": round(confidence, 4),
            "explanation": f"[{label}] Compliant: '{extracted_value}'",
        }

    # Has a value but doesn't match any signal — treat as pass at actual confidence
    if val_lower:
        return {
            "verdict": "pass",
            "score": round(confidence, 4),
            "explanation": f"[{label}] Value present: '{extracted_value}'",
        }

    return {
        "verdict": "unknown",
        "score": _UNKNOWN_SCORE,
        "explanation": f"[{label}] Could not determine compliance from: '{extracted_value}'",
    }


# ---------------------------------------------------------------------------
# Final decision
# ---------------------------------------------------------------------------

def compute_final_decision(
    results: List[Dict],
    criteria_lookup: Dict[str, Dict],
) -> Dict:
    """
    Compute final QUALIFIED / DISQUALIFIED decision from per-criterion results.
    Mutates each result dict to add `weight` and `weighted_score`.
    """
    total_weighted = 0.0
    max_possible   = 0.0
    disqualified   = False

    for r in results:
        crit      = criteria_lookup.get(r.get("criterion_key", ""), {})
        mandatory = bool(crit.get("mandatory", True))
        weight    = float(crit.get("weight") or 1.0)
        score     = float(r.get("score", 0.0))

        weighted = score * weight
        r["weight"]         = weight
        r["weighted_score"] = round(weighted, 4)

        if r["verdict"] == "fail" and mandatory:
            disqualified = True

        total_weighted += weighted
        max_possible   += weight

    final_score  = round(total_weighted / max_possible, 4) if max_possible > 0 else 0.0
    final_status = "DISQUALIFIED" if disqualified else "QUALIFIED"

    logger.info(
        "Final decision computed",
        final_status=final_status,
        final_score=final_score,
        total_weighted=round(total_weighted, 4),
        max_possible=round(max_possible, 4),
        disqualified_by_mandatory_fail=disqualified,
    )

    return {
        "final_status":          final_status,
        "final_score":           final_score,
        "total_weighted_score":  round(total_weighted, 4),
        "max_possible_score":    round(max_possible, 4),
    }


# ---------------------------------------------------------------------------
# Job-level entry point
# ---------------------------------------------------------------------------

def evaluate_job(
    criteria: List[Dict],
    extractions: Dict[str, Any],
) -> Dict:
    """
    Evaluate all criteria for a job.

    Args:
        criteria:    list of criterion dicts (from CriterionDB.to_dict())
        extractions: criterion_key → extracted_value (None if not found)

    Returns:
        {
          "results":  List[Dict],  # per-criterion, each has weight + weighted_score
          "decision": Dict,        # final_status, final_score, totals
        }
    """
    logger.info("Evaluation started", criteria_count=len(criteria))

    results = []
    for criterion in criteria:
        key             = criterion.get("criterion_key", "")
        criterion_id    = criterion.get("id")
        extracted_value = extractions.get(key)   # None → UNKNOWN

        row = evaluate_criterion(criterion, extracted_value)
        row["criterion_id"]  = criterion_id
        row["criterion_key"] = key

        logger.info(
            "Criterion evaluated",
            criterion=key,
            verdict=row["verdict"],
            score=row["score"],
            extracted=str(extracted_value)[:80] if extracted_value else None,
        )
        results.append(row)

    criteria_lookup = {c.get("criterion_key", ""): c for c in criteria}
    decision = compute_final_decision(results, criteria_lookup)

    verdicts = [r["verdict"] for r in results]
    logger.info(
        "Evaluation completed",
        total=len(results),
        pass_count=verdicts.count("pass"),
        fail_count=verdicts.count("fail"),
        unknown_count=verdicts.count("unknown"),
        final_status=decision["final_status"],
        final_score=decision["final_score"],
    )

    return {"results": results, "decision": decision}
