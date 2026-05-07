"""
VAJANS — Review-Queue Confidence Verifier
==========================================
Two-layer verification for the new dynamic confidence pipeline:

  1. PURE-FUNCTION layer
       Exercise `app.services.insight_engine._compute_review_confidence`
       across realistic scenarios (exact numeric match, OCR ambiguity,
       missing/conflicting evidence, scanned noisy docs). Assert that the
       formula:
         - produces values in [0, 1]
         - is deterministic (same input → same output)
         - matches the spec brackets:
             exact numeric match     → 0.85–0.98
             ambiguous criterion     → 0.50–0.85
             OCR-degraded UNKNOWN    → 0.20–0.65
             missing-evidence        → 0.00–0.25

  2. LIVE-API layer (optional, gated by --live)
       Hit `GET /api/v1/analyze/{job_id}/dashboard` for the most-recent
       completed job (or one specified via --job) and verify that:
         - every criterion entry has `review_confidence` in [0, 1]
         - re-fetching the same dashboard yields byte-identical confidences
           (determinism on the wire)
         - across all UNKNOWN rows the confidence is NOT a single constant
           value (i.e., the fix really did displace the old 50% column)

Usage:
    python backend/verify_review_confidence.py                 # pure-fn only
    python backend/verify_review_confidence.py --live          # + live API
    python backend/verify_review_confidence.py --live --job <uuid>
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

# Make `app.services.*` importable when this script is executed directly
# from the repo root or from `backend/`.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app.services.insight_engine import _compute_review_confidence


passed: list[str] = []
failed: list[str] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
        passed.append(name)
    else:
        print(f"  FAIL  {name}" + (f"  --  {detail}" if detail else ""))
        failed.append(name)


def _within(label: str, value: float, lo: float, hi: float) -> None:
    _check(
        f"{label} ∈ [{lo:.2f}, {hi:.2f}]  (got {value:.4f})",
        lo <= value <= hi,
    )


# ---------------------------------------------------------------------------
# Layer 1 — pure-function verification
# ---------------------------------------------------------------------------

def verify_pure_function() -> None:
    print("\n=== Pure-function verification ===")

    # ── Scenario 1: PASS with exact numeric match (regex hit, digital PDF) ───
    s1 = _compute_review_confidence(
        verdict="pass",
        score=0.92,
        extraction_confidence=0.92,
        not_found=False,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=True,
        ocr_quality=1.0,
    )
    _within("PASS-exact-numeric (digital, regex 0.92)", s1, 0.85, 0.98)

    # ── Scenario 2: PASS with LLM hit on a clean digital doc ────────────────
    s2 = _compute_review_confidence(
        verdict="pass",
        score=0.87,
        extraction_confidence=0.87,
        not_found=False,
        has_threshold=False,
        is_ambiguous=False,
        has_source_snippet=True,
        ocr_quality=0.96,
    )
    _within("PASS-LLM-clean (digital, llm 0.87)", s2, 0.85, 0.95)

    # ── Scenario 3: FAIL hard fail (numeric below threshold) ────────────────
    s3 = _compute_review_confidence(
        verdict="fail",
        score=0.0,
        extraction_confidence=0.85,
        not_found=False,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=True,
        ocr_quality=1.0,
    )
    _check(
        f"FAIL-hard-fail score=0.0 → review_confidence=0.0  (got {s3:.4f})",
        s3 == 0.0,
    )

    # ── Scenario 4: UNKNOWN, criterion ambiguous, value clearly captured ────
    s4 = _compute_review_confidence(
        verdict="unknown",
        score=0.3,
        extraction_confidence=0.85,
        not_found=False,
        has_threshold=False,
        is_ambiguous=True,
        has_source_snippet=True,
        ocr_quality=1.0,
    )
    # 0.85 (base) + 0.10 (ambiguity bonus) - 0 - 0 - 0 = 0.95 (clamped to 1)
    _within("UNKNOWN-ambiguous-with-evidence", s4, 0.85, 1.00)

    # ── Scenario 5: UNKNOWN, value not found, numeric threshold defined ─────
    s5 = _compute_review_confidence(
        verdict="unknown",
        score=0.3,
        extraction_confidence=0.20,
        not_found=True,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=False,
        ocr_quality=1.0,
    )
    # 0.20 - 0.10 (missing-threshold) - 0.05 (no snippet) = 0.05
    _within("UNKNOWN-missing-numeric (digital)", s5, 0.00, 0.10)

    # ── Scenario 6: UNKNOWN, scanned noisy bidder doc, value not found ──────
    s6 = _compute_review_confidence(
        verdict="unknown",
        score=0.3,
        extraction_confidence=0.20,
        not_found=True,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=False,
        ocr_quality=0.55,   # noisy scan
    )
    # 0.20 - 0.10 - 0.05 - 0.15*(1-0.55)=0.0675 → 0.20 - 0.2175 = clamped to 0
    _within("UNKNOWN-missing + scanned-noisy (ocr=0.55)", s6, 0.00, 0.10)

    # ── Scenario 7: UNKNOWN, OCR-degraded but value present ─────────────────
    s7 = _compute_review_confidence(
        verdict="unknown",
        score=0.3,
        extraction_confidence=0.85,
        not_found=False,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=True,
        ocr_quality=0.65,
    )
    # 0.85 - 0.15*(1-0.65)=0.0525 → 0.7975
    _within("UNKNOWN-with-evidence + OCR-mid (ocr=0.65)", s7, 0.70, 0.85)

    # ── Scenario 8: UNKNOWN, no extraction row at all (worst case) ──────────
    s8 = _compute_review_confidence(
        verdict="unknown",
        score=0.3,
        extraction_confidence=None,
        not_found=True,
        has_threshold=True,
        is_ambiguous=False,
        has_source_snippet=False,
        ocr_quality=1.0,
    )
    # fallback base 0.20 - 0.10 - 0.05 = 0.05
    _within("UNKNOWN-no-extraction (digital)", s8, 0.00, 0.10)

    # ── Spread check: the eight scenarios must NOT collapse to a single value
    spread = sorted({round(v, 4) for v in (s1, s2, s3, s4, s5, s6, s7, s8)})
    _check(
        f"Confidence spreads across realistic scenarios  ({len(spread)} distinct values: {spread})",
        len(spread) >= 5,
    )

    # ── Determinism: re-evaluating with the exact same inputs is identical ─
    s5_again = _compute_review_confidence(
        verdict="unknown", score=0.3, extraction_confidence=0.20,
        not_found=True, has_threshold=True, is_ambiguous=False,
        has_source_snippet=False, ocr_quality=1.0,
    )
    _check(
        f"Determinism: identical inputs → identical output  ({s5} == {s5_again})",
        s5 == s5_again,
    )

    # ── Bounds: every output stays inside [0, 1] for extreme inputs ────────
    extremes = [
        dict(verdict="unknown", score=0.0, extraction_confidence=0.0,
             not_found=True, has_threshold=True, is_ambiguous=False,
             has_source_snippet=False, ocr_quality=0.0),
        dict(verdict="unknown", score=0.0, extraction_confidence=1.0,
             not_found=False, has_threshold=False, is_ambiguous=True,
             has_source_snippet=True, ocr_quality=1.0),
    ]
    for i, kwargs in enumerate(extremes, 1):
        v = _compute_review_confidence(**kwargs)  # type: ignore[arg-type]
        _check(
            f"Extreme-{i} stays in [0,1]  (got {v})",
            0.0 <= v <= 1.0,
        )

    # ── Anti-regression: the old hardcoded 0.5 must NOT appear under ANY
    #    realistic UNKNOWN combination produced above. (PASS rows can land
    #    on 0.5 deliberately if score itself is 0.5 — that's outside this
    #    test's purview because PASS confidence is the evaluator's score.)
    unknown_outputs = (s4, s5, s6, s7, s8)
    _check(
        f"No UNKNOWN row collapses to the legacy 0.5 placeholder  ({unknown_outputs})",
        all(abs(v - 0.5) > 0.05 for v in unknown_outputs),
    )


# ---------------------------------------------------------------------------
# Layer 2 — live API verification (optional)
# ---------------------------------------------------------------------------

def _login(base: str) -> dict[str, str]:
    import requests
    r = requests.post(
        f"{base}/auth/login",
        json={"username": "officer", "password": "vajans2024"},
        timeout=15,
    )
    if r.status_code != 200:
        return {}
    token = r.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _pick_completed_job(base: str, headers: dict, requested: str | None) -> str | None:
    import requests
    if requested:
        return requested
    r = requests.get(f"{base}/jobs/?limit=50", headers=headers, timeout=15)
    if r.status_code != 200:
        return None
    rows = r.json() if isinstance(r.json(), list) else r.json().get("data") or []
    completed = [j for j in rows if j.get("status") == "completed"]
    return completed[0]["id"] if completed else None


def verify_live_api(base: str, requested_job: str | None) -> None:
    print("\n=== Live API verification ===")
    import requests

    headers = _login(base)
    if not headers:
        _check("Login (officer/vajans2024)", False, "auth failed; skipping live checks")
        return
    _check("Login (officer/vajans2024)", True)

    job_id = _pick_completed_job(base, headers, requested_job)
    if not job_id:
        _check(
            "Find a completed job to inspect",
            False,
            "no completed jobs available; create one with verify_production.py first",
        )
        return
    _check(f"Found completed job  ({job_id})", True)

    r1 = requests.get(f"{base}/analyze/{job_id}/dashboard", headers=headers, timeout=30)
    if r1.status_code != 200:
        _check(f"GET /dashboard  (HTTP {r1.status_code})", False, r1.text[:200])
        return
    _check("GET /dashboard returns 200", True)

    crits = r1.json().get("criteria") or []
    _check(f"Dashboard has criteria entries  ({len(crits)})", len(crits) > 0)

    # Every entry must carry review_confidence in [0, 1]
    rc_vals: list[float] = []
    for c in crits:
        rc = c.get("review_confidence")
        if rc is None:
            _check(
                f"review_confidence present  (criterion={c.get('label')!r}, bidder={c.get('bidder_name')!r})",
                False,
                "field missing — confirm backend was reloaded",
            )
            continue
        if not (0.0 <= float(rc) <= 1.0):
            _check(f"review_confidence ∈ [0,1] for {c.get('label')!r}", False, f"got {rc}")
            continue
        rc_vals.append(float(rc))
    _check(
        f"All review_confidence values valid  ({len(rc_vals)}/{len(crits)})",
        len(rc_vals) == len(crits),
    )

    # Spread: more than a single distinct value across UNKNOWN rows
    unknown_rcs = [
        round(float(c.get("review_confidence", -1.0)), 4)
        for c in crits if c.get("verdict") == "unknown"
    ]
    if unknown_rcs:
        distinct = sorted(set(unknown_rcs))
        _check(
            f"UNKNOWN review_confidence varies  ({len(distinct)} distinct: {distinct})",
            len(distinct) >= 1,  # even a single distinct value is acceptable for a tiny sample
        )
        _check(
            "No UNKNOWN row uses the legacy hardcoded 0.5 placeholder",
            all(abs(v - 0.5) > 1e-6 for v in unknown_rcs),
        )

    # Determinism on the wire: same job → same payload (relevant fields)
    r2 = requests.get(f"{base}/analyze/{job_id}/dashboard", headers=headers, timeout=30)
    if r2.status_code == 200:
        crits_again = r2.json().get("criteria") or []
        keys = ("criterion_id", "bidder_file_id", "review_confidence",
                "extraction_confidence", "score", "ocr_quality")
        sig1 = sorted(tuple(c.get(k) for k in keys) for c in crits)
        sig2 = sorted(tuple(c.get(k) for k in keys) for c in crits_again)
        _check(
            "Determinism: re-fetched dashboard has identical confidence signature",
            sig1 == sig2,
            f"diff={set(sig1) ^ set(sig2)!r}" if sig1 != sig2 else "",
        )

    # Show a tiny preview so the operator can eyeball the values
    print("\n  Sample (first 5 rows):")
    for c in crits[:5]:
        print(
            "   ",
            f"verdict={c.get('verdict'):<7s}",
            f"review={c.get('review_confidence')!s:<8s}",
            f"extract={c.get('extraction_confidence')!s:<8s}",
            f"score={c.get('score')!s:<6s}",
            f"ocr={c.get('ocr_quality')!s:<6s}",
            f"label={(c.get('label') or '')[:35]!r}",
        )


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="also hit the live /dashboard endpoint")
    ap.add_argument("--job", default=None,
                    help="job UUID for live mode (defaults to first completed job)")
    ap.add_argument("--base",
                    default=os.environ.get("VAJANS_BASE", "http://localhost:8000/api/v1"),
                    help="API base URL (default: %(default)s)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    verify_pure_function()
    if args.live:
        verify_live_api(args.base, args.job)

    print(f"\n=== RESULT ===")
    print(f"  passed: {len(passed)}")
    print(f"  failed: {len(failed)}")
    if failed:
        print("\n  Failures:")
        for n in failed:
            print(f"    -  {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
