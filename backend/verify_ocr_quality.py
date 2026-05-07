"""
VAJANS — OCR Quality Verifier
==============================

Two-layer verification for the dynamic OCR-quality pipeline:

  1. PURE-FUNCTION layer
       Constructs synthetic `PageText` fixtures and exercises
       `app.engines.ingestion.compute_ocr_quality` across every realistic
       scenario the user listed:
         - clean digital PDFs           → 0.95–1.00
         - mixed digital (some empty)   → 0.80–0.95
         - high-quality scans           → 0.80–0.95
         - noisy / skewed scans         → 0.55–0.80
         - blurry / low-text scans      → 0.30–0.55
         - unreadable                   → 0.00–0.30
       Also asserts:
         - determinism (identical inputs → identical output)
         - bounds (output ∈ [0, 1] for every input)
         - anti-regression (no scenario collapses to 0.88 / 0.5)

  2. LIVE-API layer (gated by --live)
       Hits `GET /api/v1/files/job/{job_id}` for the most-recent completed
       job (or one specified via --job) and verifies that:
         - every file carries an `ocr_quality` value (or NULL pre-ingest)
         - values are in [0, 1]
         - re-fetching produces an identical `ocr_quality` per file
           (determinism on the wire)
         - across all processed files the values vary (i.e., the fix
           displaced the constant-88% column)
         - digital vs scanned files are meaningfully different
           (digital ≥ 0.92, scanned can be lower)
         - NO file is exactly 0.88

Usage:
    python backend/verify_ocr_quality.py
    python backend/verify_ocr_quality.py --live
    python backend/verify_ocr_quality.py --live --job <uuid>
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

# Make `app.engines.*` importable when this script is executed directly
# from the repo root or from `backend/`.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app.engines.ingestion import (   # noqa: E402
    DocumentKind,
    PageText,
    compute_ocr_quality,
    ocr_quality_breakdown,
)


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


def _digital_pages(n: int, *, empty_idx: list[int] | None = None,
                   short_idx: list[int] | None = None) -> list[PageText]:
    """Build synthetic digital pages. ocr_confidence/sharpness stay at 1.0."""
    empty_idx = set(empty_idx or [])
    short_idx = set(short_idx or [])
    pages = []
    for i in range(1, n + 1):
        if i in empty_idx:
            text = ""
        elif i in short_idx:
            text = "Short page header only."           # ~24 chars
        else:
            text = "x" * 1500                          # density saturation
        pages.append(PageText(
            page_number=i, text=text,
            ocr_confidence=1.0,
            text_density=min(1.0, len(text.strip()) / 1500.0),
            sharpness=1.0,
            skew_abs_deg=0.0,
            is_empty=not text.strip(),
        ))
    return pages


def _scanned_pages(n: int, *, conf: float, sharpness: float = 1.0,
                   skew: float = 0.0, density: float = 1.0,
                   empty_idx: list[int] | None = None) -> list[PageText]:
    """Build synthetic scanned pages with controlled signal levels."""
    empty_idx = set(empty_idx or [])
    pages = []
    for i in range(1, n + 1):
        if i in empty_idx:
            # Match the failed-page record produced by `extract_scanned_pdf`'s
            # exception handler: zero confidence, zero density, zero sharpness
            # (a truly unreadable page has no measurable detail), zero skew.
            pages.append(PageText(
                page_number=i, text="",
                ocr_confidence=0.0,
                text_density=0.0,
                sharpness=0.0,
                skew_abs_deg=0.0,
                is_empty=True,
            ))
            continue
        # Use enough text that low_density_ratio doesn't fire (>100 chars).
        text = "OCR text " * 200            # ~1800 chars
        pages.append(PageText(
            page_number=i, text=text,
            ocr_confidence=conf,
            text_density=density,
            sharpness=sharpness,
            skew_abs_deg=skew,
            is_empty=False,
        ))
    return pages


# ---------------------------------------------------------------------------
# Layer 1 — pure-function verification
# ---------------------------------------------------------------------------

def verify_pure_function() -> None:
    print("\n=== Pure-function verification ===")

    # ── Scenario 1: clean digital PDF (5 dense pages) ──────────────────────
    s1 = compute_ocr_quality(_digital_pages(5), kind=DocumentKind.DIGITAL)
    _within("Clean-digital (5 dense pages)", s1, 0.95, 1.00)

    # ── Scenario 2: digital with one empty + one short page ────────────────
    s2 = compute_ocr_quality(
        _digital_pages(5, empty_idx=[3], short_idx=[4]),
        kind=DocumentKind.DIGITAL,
    )
    _within("Mixed-digital (1 empty + 1 short page)", s2, 0.80, 0.95)

    # ── Scenario 3: high-quality scan ──────────────────────────────────────
    s3 = compute_ocr_quality(
        _scanned_pages(5, conf=0.92, sharpness=0.95, skew=0.5, density=0.95),
        kind=DocumentKind.SCANNED,
    )
    _within("High-quality scan (conf=.92, sharp=.95, skew=.5)", s3, 0.80, 0.95)

    # ── Scenario 4: noisy / skewed scan ────────────────────────────────────
    s4 = compute_ocr_quality(
        _scanned_pages(5, conf=0.70, sharpness=0.55, skew=4.0, density=0.65),
        kind=DocumentKind.SCANNED,
    )
    _within("Noisy / skewed scan (conf=.70, skew=4°)", s4, 0.55, 0.80)

    # ── Scenario 5: blurry / low-text scan ─────────────────────────────────
    s5 = compute_ocr_quality(
        _scanned_pages(5, conf=0.45, sharpness=0.20, skew=2.5, density=0.30),
        kind=DocumentKind.SCANNED,
    )
    _within("Blurry low-text scan (conf=.45, sharp=.20)", s5, 0.30, 0.55)

    # ── Scenario 6: unreadable ─────────────────────────────────────────────
    s6 = compute_ocr_quality(
        _scanned_pages(5, conf=0.05, sharpness=0.05, skew=8.0, density=0.05,
                       empty_idx=[1, 3, 5]),
        kind=DocumentKind.SCANNED,
    )
    _within("Unreadable (most pages empty + heavy blur)", s6, 0.00, 0.30)

    # ── Scenario 7: scanned but ALL pages empty ────────────────────────────
    s7 = compute_ocr_quality(
        _scanned_pages(3, conf=0.0, density=0.0, empty_idx=[1, 2, 3]),
        kind=DocumentKind.SCANNED,
    )
    _within("Fully empty scan", s7, 0.00, 0.20)

    # ── Spread: every scenario above must produce a distinct value ─────────
    spread = sorted({round(v, 4) for v in (s1, s2, s3, s4, s5, s6, s7)})
    _check(
        f"OCR quality spreads across realistic scenarios  ({len(spread)} distinct values: {spread})",
        len(spread) >= 6,
    )

    # ── Determinism: identical inputs → identical output ───────────────────
    s3_again = compute_ocr_quality(
        _scanned_pages(5, conf=0.92, sharpness=0.95, skew=0.5, density=0.95),
        kind=DocumentKind.SCANNED,
    )
    _check(
        f"Determinism: identical inputs → identical output  ({s3} == {s3_again})",
        s3 == s3_again,
    )

    # ── Bounds: extreme inputs stay in [0, 1] ──────────────────────────────
    extremes = [
        # Everything zero
        _scanned_pages(3, conf=0.0, sharpness=0.0, skew=10.0, density=0.0),
        # Everything saturated
        _scanned_pages(3, conf=1.0, sharpness=1.0, skew=0.0, density=1.0),
    ]
    for i, pages in enumerate(extremes, 1):
        v = compute_ocr_quality(pages, kind=DocumentKind.SCANNED)
        _check(f"Extreme-{i} stays in [0,1]  (got {v})", 0.0 <= v <= 1.0)

    # ── Anti-regression: no realistic scenario equals the legacy 0.88 ──────
    realistic = (s1, s2, s3, s4, s5, s6, s7)
    _check(
        f"No realistic scenario collapses to legacy 0.88 placeholder  ({realistic})",
        all(abs(v - 0.88) > 0.02 for v in realistic),
    )

    # ── Branch inference: scanned-looking pages without explicit kind ──────
    s_inferred = compute_ocr_quality(
        _scanned_pages(3, conf=0.92, sharpness=0.95, skew=0.5, density=0.95),
        kind=None,
    )
    _check(
        f"Branch auto-inference picks scanned when any conf<1.0  (got {s_inferred})",
        s_inferred < s3 + 0.01 and s_inferred > s3 - 0.01,
    )

    # ── Breakdown sanity ───────────────────────────────────────────────────
    bd = ocr_quality_breakdown(_scanned_pages(5, conf=0.70, sharpness=0.55,
                                              skew=4.0, density=0.65))
    _check(
        f"ocr_quality_breakdown returns full per-signal payload  (keys={sorted(bd)})",
        {"branch", "mean_ocr_confidence", "mean_text_density",
         "mean_sharpness", "mean_skew_abs_deg", "empty_page_ratio",
         "low_density_page_ratio", "coverage", "knees"}.issubset(bd),
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

    r1 = requests.get(f"{base}/files/job/{job_id}", headers=headers, timeout=20)
    if r1.status_code != 200:
        _check(f"GET /files/job  (HTTP {r1.status_code})", False, r1.text[:200])
        return
    _check("GET /files/job returns 200", True)

    files = r1.json()
    _check(f"/files/job returns at least one file  ({len(files)})", len(files) > 0)

    processed = [f for f in files if f.get("status") == "processed"]
    _check(f"Found processed files  ({len(processed)})", len(processed) > 0)

    # Every processed file must carry a real ocr_quality in [0, 1]
    bad: list[str] = []
    oqs: list[float] = []
    for f in processed:
        oq = f.get("ocr_quality")
        if oq is None:
            bad.append(f"{f.get('original_name')}: ocr_quality is null after processing")
            continue
        try:
            v = float(oq)
        except (TypeError, ValueError):
            bad.append(f"{f.get('original_name')}: ocr_quality not numeric ({oq!r})")
            continue
        if not (0.0 <= v <= 1.0):
            bad.append(f"{f.get('original_name')}: ocr_quality out of range ({v})")
            continue
        oqs.append(v)
    _check(
        f"All processed files carry ocr_quality ∈ [0, 1]  ({len(oqs)}/{len(processed)})",
        not bad,
        "; ".join(bad[:3]) if bad else "",
    )

    # No file may have the legacy 0.88 placeholder
    eq_088 = [f.get("original_name") for f in processed
              if f.get("ocr_quality") is not None
              and abs(float(f["ocr_quality"]) - 0.88) < 1e-6]
    _check(
        "No processed file equals the legacy 0.88 placeholder",
        not eq_088,
        f"offenders: {eq_088}" if eq_088 else "",
    )

    # Spread: at least 2 distinct values across processed files (sample size
    # permitting) — this is the user's central complaint
    distinct = sorted({round(v, 4) for v in oqs})
    _check(
        f"OCR quality varies across processed files  ({len(distinct)} distinct: {distinct})",
        len(distinct) >= 2 if len(processed) >= 2 else True,
    )

    # Digital vs scanned: digital files should typically be ≥ 0.92
    digital  = [f for f in processed if f.get("document_kind") == "digital"]
    scanned  = [f for f in processed if f.get("document_kind") == "scanned"]
    if digital:
        digital_min = min(float(f["ocr_quality"]) for f in digital)
        _check(
            f"Digital files score \u2265 0.92  (min={digital_min:.4f}, n={len(digital)})",
            digital_min >= 0.92,
        )
    if scanned and digital:
        # Scanned can be either above or below digital depending on quality;
        # the meaningful assertion is that the means are detectably distinct
        mean_digital = sum(float(f["ocr_quality"]) for f in digital)  / len(digital)
        mean_scanned = sum(float(f["ocr_quality"]) for f in scanned) / len(scanned)
        _check(
            f"Digital vs scanned means differ \u2265 0.005  "
            f"(digital={mean_digital:.4f}, scanned={mean_scanned:.4f})",
            abs(mean_digital - mean_scanned) >= 0.005,
        )

    # Determinism on the wire
    r2 = requests.get(f"{base}/files/job/{job_id}", headers=headers, timeout=20)
    if r2.status_code == 200:
        again = {str(f["id"]): f.get("ocr_quality") for f in r2.json()}
        same  = all(again.get(str(f["id"])) == f.get("ocr_quality") for f in files)
        _check("Determinism: re-fetched /files/job has identical ocr_quality per file", same)

    # Show a tiny preview
    print("\n  Sample (per file):")
    for f in processed[:8]:
        oq = f.get("ocr_quality")
        oq_str = f"{float(oq):.4f}" if oq is not None else "—"
        print(
            "   ",
            f"kind={f.get('document_kind') or '?':<8s}",
            f"ocr={oq_str:<8s}",
            f"pages={f.get('page_count')!s:<4s}",
            f"name={f.get('original_name')!r}",
        )


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="also hit the live /files/job endpoint")
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
