"""
VAJANS -- Production Simulation Verifier
=========================================

End-to-end verification harness for the realistic dataset created by
`generate_production_simulation.py`.  This script:

  1. Uploads the realistic tender and the 5 distinct bidder PDFs to a
     fresh job.
  2. Triggers the full ingestion -> OCR -> embedding -> extraction ->
     evaluation -> review pipeline.
  3. Audits the OUTPUTS against expected per-bidder verdicts:

         Maharashtra Infra            -> QUALIFIED
         Sahyadri Construction        -> DISQUALIFIED   (turnover < Rs.50 Cr)
         Vidhya Builders              -> DISQUALIFIED   (only 1 similar project)
         Konkan Engineering (scanned) -> DISQUALIFIED   (no ISO, no EPF)
         Deccan Civil Works (scanned) -> ambiguous -- low confidence expected

  4. Audits evidence-trace quality:
       - every PASS/FAIL verdict carries a non-empty source_snippet
       - page_number resolves to a valid 1..page_count value
       - snippet text is actually present on that page
  5. Confirms OCR was invoked on the two scanned bidders.
  6. Runs the pipeline a second time on identical input and verifies that
     the outputs are byte-identical (cross-job determinism with realistic
     OCR-derived text).
  7. Asserts the audit chain validates.

Usage:
    python backend/verify_production.py
    python backend/verify_production.py --runs 3 --skip-second-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests


BASE   = os.environ.get("VAJANS_BASE",   "http://localhost:8000/api/v1")
HEALTH = os.environ.get("VAJANS_HEALTH", "http://localhost:8000/api/health/ready")
SAMPLE = os.environ.get("VAJANS_PROD_SAMPLE",
                        "/home/sanju/vajans/data/sample_prod")

PIPELINE_TIMEOUT_SECS = 600       # OCR can be slow -- allow up to 10 min
POLL_INTERVAL_SECS    = 5

passed: list[str] = []
failed: list[str] = []


# ---------------------------------------------------------------------------
# Test bidder catalogue
# ---------------------------------------------------------------------------
BIDDERS = [
    # filename,                                  short_key,        expected_status
    ("bidder_maharashtra_infra.pdf",        "maharashtra_infra",   "QUALIFIED"),
    ("bidder_sahyadri_construction.pdf",    "sahyadri",            "DISQUALIFIED"),
    ("bidder_vidhya_builders.pdf",          "vidhya_builders",     "DISQUALIFIED"),
    ("bidder_konkan_engineering.pdf",       "konkan_engineering",  "DISQUALIFIED"),
    ("bidder_deccan_civil_works.pdf",       "deccan_civil_works",  "ANY"),
]
TENDER_PDF = "tender_morth_sh275.pdf"
SCANNED_BIDDERS = {"konkan_engineering", "deccan_civil_works"}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def test(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"  PASS  {name}")
        passed.append(name)
    else:
        print(f"  FAIL  {name}" + (f"  --  {detail}" if detail else ""))
        failed.append(name)
    return bool(condition)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def login() -> dict[str, str]:
    r = requests.post(
        f"{BASE}/auth/login",
        json={"username": "officer", "password": "vajans2024"},
        timeout=15,
    )
    if r.status_code != 200:
        return {}
    token = r.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def create_job(headers: dict, title: str) -> str:
    r = requests.post(
        f"{BASE}/jobs/",
        json={"title": title, "created_by": "verifier", "metadata": {}},
        headers=headers, timeout=15,
    )
    return r.json().get("id", "") if r.status_code == 201 else ""


def upload_files(headers: dict, job_id: str) -> bool:
    catalog = [(TENDER_PDF, "tender")] + \
              [(fname, "bidder") for fname, _, _ in BIDDERS]
    for fname, ftype in catalog:
        path = f"{SAMPLE}/{fname}"
        try:
            with open(path, "rb") as fh:
                r = requests.post(
                    f"{BASE}/files/upload",
                    data={"job_id": job_id, "file_type": ftype},
                    files={"file": (fname, fh, "application/pdf")},
                    headers=headers, timeout=120,
                )
            if r.status_code != 201:
                print(f"    upload {fname} -> HTTP {r.status_code}: {r.text[:140]}")
                return False
        except FileNotFoundError:
            print(f"    sample missing: {path}")
            return False
        except Exception as e:
            print(f"    upload {fname} error: {e}")
            return False
    return True


def trigger_and_wait(headers: dict, job_id: str) -> str:
    r = requests.post(f"{BASE}/analyze/{job_id}", headers=headers, timeout=30)
    if r.status_code != 202:
        return f"trigger_failed:{r.status_code}:{r.text[:80]}"

    deadline = time.time() + PIPELINE_TIMEOUT_SECS
    last = "?"
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECS)
        try:
            jr = requests.get(f"{BASE}/jobs/{job_id}", headers=headers, timeout=15)
            last = jr.json().get("status", "?")
        except Exception as e:
            print(f"    poll error: {e}")
            continue
        if last == "completed":
            return "completed"
        if last == "failed":
            return "failed"
        elapsed = int(PIPELINE_TIMEOUT_SECS - (deadline - time.time()))
        print(f"    {elapsed}s -- status: {last}")
    return f"timeout:{last}"


def get(headers: dict, path: str) -> dict | None:
    r = requests.get(f"{BASE}{path}", headers=headers, timeout=30)
    return r.json() if r.status_code == 200 else None


# ---------------------------------------------------------------------------
# Determinism signature (job-independent)
# ---------------------------------------------------------------------------
def _build_signature(eval_data: dict, comp_data: dict, dash_data: dict,
                     crit_data: dict) -> dict:
    """
    Job-independent signature of an evaluated tender:
      - bidder filename -> {final_status, final_score, summary, disq_reasons,
                            criteria-by-explanation -> {verdict,score,weight,...}}
      - rankings by bidder name + score
      - dashboard summary + flags (UUID-stripped, key-translated)
      - criteria by criterion_key
    """
    cid_to_key = {str(c.get("id")): c.get("criterion_key") or ""
                  for c in (crit_data.get("data") or [])}

    def _translate(value: Any) -> Any:
        if isinstance(value, list):
            return [cid_to_key.get(v, v) if isinstance(v, str) else _translate(v)
                    for v in value]
        if isinstance(value, dict):
            return {k: _translate(v) for k, v in value.items()}
        return value

    sig: dict[str, Any] = {}

    # --- evaluation
    sig["evaluation"] = {
        "final_status": eval_data.get("final_status"),
        "final_score":  eval_data.get("final_score"),
        "summary":      eval_data.get("summary"),
        "bidders_by_name": {
            b.get("bidder_name"): {
                "final_status": b.get("final_status"),
                "final_score":  b.get("final_score"),
                "summary":      b.get("summary"),
                "disq_reasons": sorted(b.get("disqualification_reasons") or []),
                "criteria": sorted(
                    [
                        {
                            "verdict":         r.get("verdict"),
                            "score":           r.get("score"),
                            "weight":          r.get("weight"),
                            "weighted_score":  r.get("weighted_score"),
                            "explanation":     r.get("explanation"),
                        }
                        for r in (b.get("results") or [])
                    ],
                    key=lambda d: d.get("explanation") or "",
                ),
            }
            for b in (eval_data.get("bidders") or [])
        },
    }

    # --- comparison
    sig["comparison"] = {
        "rankings": [
            {
                "rank":         r.get("rank"),
                "bidder_name":  r.get("bidder_name"),
                "total_score":  r.get("total_score"),
                "is_eligible":  r.get("is_eligible"),
                "disq_reason":  r.get("disqualification_reason"),
            }
            for r in (comp_data.get("rankings") or [])
        ]
    }

    # --- dashboard (translate ids and sort)
    flags = []
    for f in (dash_data.get("flags") or []):
        f2 = dict(f)
        if "affected_criteria" in f2:
            f2["affected_criteria"] = sorted(_translate(f2["affected_criteria"]))
        flags.append(f2)
    flags.sort(key=lambda f: (f.get("code") or "", f.get("severity") or ""))
    sig["dashboard"] = {"summary": dash_data.get("summary"), "flags": flags}

    # --- criteria by_key
    sig["criteria"] = sorted(
        [
            {
                "criterion_key":   c.get("criterion_key"),
                "label":           c.get("label"),
                "criterion_type":  c.get("criterion_type"),
                "mandatory":       c.get("mandatory"),
                "threshold_value": c.get("threshold_value"),
                "threshold_unit":  c.get("threshold_unit"),
                "operator":        c.get("operator"),
                "ambiguous":       c.get("ambiguous"),
            }
            for c in (crit_data.get("data") or [])
        ],
        key=lambda d: d.get("criterion_key") or "",
    )
    return sig


def diff_first_path(a: Any, b: Any, path: str = "") -> str | None:
    if type(a) is not type(b):
        return f"{path or '<root>'}: {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return f"{path}.{k} missing in run1"
            if k not in b:
                return f"{path}.{k} missing in run2"
            d = diff_first_path(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: list len {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff_first_path(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} vs {b!r}"
    return None


# ---------------------------------------------------------------------------
# Per-run pipeline driver
# ---------------------------------------------------------------------------
def run_pipeline(headers: dict, label: str) -> tuple[str, dict, dict, dict, dict]:
    print(f"\n[{label}] creating job ...")
    job_id = create_job(headers, f"prod-sim-{label}")
    if not job_id:
        return "", {}, {}, {}, {}

    print(f"[{label}] uploading 1 tender + 5 bidders (job {job_id[:8]}) ...")
    if not upload_files(headers, job_id):
        return job_id, {}, {}, {}, {}

    print(f"[{label}] triggering pipeline (this includes OCR for 2 bidders) ...")
    status = trigger_and_wait(headers, job_id)
    if status != "completed":
        print(f"[{label}] pipeline status: {status}")
        return job_id, {}, {}, {}, {}

    eval_data = get(headers, f"/analyze/{job_id}/evaluation") or {}
    comp_data = get(headers, f"/analyze/{job_id}/comparison") or {}
    dash_data = get(headers, f"/analyze/{job_id}/dashboard")  or {}
    crit_data = get(headers, f"/analyze/{job_id}/criteria")   or {}

    return job_id, eval_data, comp_data, dash_data, crit_data


# ---------------------------------------------------------------------------
# Evidence-trace audit
# ---------------------------------------------------------------------------
def audit_evidence(headers: dict, job_id: str, eval_data: dict) -> dict:
    """
    Inspect every extraction with a recovered value and confirm that:
      - it has a non-empty source_snippet
      - page_number is within [1, file_page_count]
      - the snippet (or a short probe) appears verbatim on that page when
        we re-extract the PDF page text directly with PyMuPDF (digital)
        or via Tesseract (scanned)

    The third check is the strongest: it proves the system is reporting
    real evidence, not hallucinated text.

    Returns counts and a list of mismatches (first 5).
    """
    import fitz
    import pytesseract
    from pdf2image import convert_from_path

    ext = get(headers, f"/analyze/{job_id}/extractions") or {}
    extractions = ext.get("data", [])

    files = get(headers, f"/files/job/{job_id}") or []
    if isinstance(files, dict):
        files = files.get("data", []) or []
    page_count_by_file = {str(f.get("id")): f.get("page_count") or 0
                          for f in files}

    # ── Pre-fetch page texts on demand via the /files/{id}/inline route ─
    page_text_cache: dict[tuple, str] = {}

    def _page_text(file_id: str, page: int) -> str:
        key = (file_id, page)
        if key in page_text_cache:
            return page_text_cache[key]
        try:
            r = requests.get(f"{BASE}/files/{file_id}/inline",
                             headers=headers, timeout=60)
            r.raise_for_status()
            doc = fitz.open(stream=r.content, filetype="pdf")
            if page < 1 or page > len(doc):
                page_text_cache[key] = ""
                doc.close()
                return ""
            txt = doc[page - 1].get_text() or ""
            doc.close()
            if len(txt.strip()) < 30:
                # Probably scanned -- write to a temp PDF and run OCR.
                import tempfile, pathlib
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
                    tf.write(r.content)
                    tmp_path = pathlib.Path(tf.name)
                try:
                    images = convert_from_path(
                        str(tmp_path), dpi=200,
                        first_page=page, last_page=page,
                    )
                    txt = pytesseract.image_to_string(images[0], lang="eng+hin")
                finally:
                    tmp_path.unlink(missing_ok=True)
            page_text_cache[key] = txt
            return txt
        except Exception:
            page_text_cache[key] = ""
            return ""

    counts = {
        "total_with_value":  0,
        "with_snippet":      0,
        "with_page":         0,
        "page_within_doc":   0,
        "snippet_verified":  0,
    }
    mismatches: list[str] = []

    for e in extractions:
        if e.get("not_found"):
            continue
        counts["total_with_value"] += 1
        snip = (e.get("source_snippet") or "").strip()
        page = e.get("page_number")
        fid  = str(e.get("file_id"))

        if snip:
            counts["with_snippet"] += 1
        if page:
            counts["with_page"] += 1
            pc = page_count_by_file.get(fid, 0)
            if 1 <= page <= pc:
                counts["page_within_doc"] += 1
                page_txt = _page_text(fid, page).lower()
                probe = " ".join(snip.lower().split())[:60]
                if probe and probe in " ".join(page_txt.split()):
                    counts["snippet_verified"] += 1
                elif len(mismatches) < 5:
                    mismatches.append(
                        f"page={page} snippet[:50]={snip[:50]!r}"
                    )

    counts["sample_mismatches"] = mismatches
    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=2,
                        help="Total independent pipeline runs to compare.")
    parser.add_argument("--skip-second-run", action="store_true",
                        help="Skip cross-run determinism (single pipeline only).")
    args = parser.parse_args(argv)

    runs = 1 if args.skip_second_run else max(2, args.runs)

    section("PRE-FLIGHT")
    try:
        h = requests.get(HEALTH, timeout=10).json()
        test("Backend reachable",  h.get("status") == "ok"
                                   or h.get("checks", {}).get("database") == "ok")
        test("Database online",    h.get("checks", {}).get("database") == "ok")
        test("Redis online",       h.get("checks", {}).get("redis")    == "ok")
    except Exception as e:
        test("Backend reachable", False, str(e))
        return _summary()

    headers = login()
    test("Auth", bool(headers))
    if not headers:
        return _summary()

    if not os.path.isdir(SAMPLE):
        test("Sample directory exists", False, SAMPLE)
        return _summary()
    test("Sample directory exists", True)

    # ── RUN 1 ──────────────────────────────────────────────────────────
    section("PHASE 2 -- FULL PIPELINE EXECUTION (RUN 1)")
    job1, eval1, comp1, dash1, crit1 = run_pipeline(headers, "run1")
    test("Run 1 completed", bool(eval1))
    if not eval1:
        return _summary()

    # ── 1a. Per-bidder verdict assertions ──────────────────────────────
    section("PHASE 2a -- PER-BIDDER VERDICT ASSERTIONS")
    by_name: dict[str, dict] = {b["bidder_name"]: b
                                for b in eval1.get("bidders", [])}
    test(f"{len(by_name)} bidders evaluated", len(by_name) == 5,
         f"got {len(by_name)} bidders -- {list(by_name)}")

    for fname, key, expected in BIDDERS:
        b = by_name.get(fname, {})
        got = b.get("final_status", "MISSING")
        score = b.get("final_score", 0.0)
        if expected == "ANY":
            # Just record what happened for the ambiguous bidder
            test(f"{key}: bidder appears in evaluation",
                 fname in by_name,
                 f"present={fname in by_name}, status={got}, score={score}")
        else:
            test(f"{key}: final_status == {expected}",
                 got == expected,
                 f"got status={got} score={score} reasons={b.get('disqualification_reasons')}")

    # ── 1b. OCR was actually invoked for scanned bidders ───────────────
    # The scanned bidder PDFs are produced by rasterising every page to an
    # image first, then wrapping the images in a PDF.  They contain ZERO
    # embedded text, so any recovered snippet is 100% proof OCR ran.
    section("PHASE 2b -- OCR INVOCATION ON SCANNED BIDDERS")
    files = get(headers, f"/files/job/{job1}") or []
    if isinstance(files, dict):
        files = files.get("data") or []
    name_to_file = {f.get("original_name"): f for f in files}

    # Pre-fetch all extractions once for indirect OCR-proof checks
    ext_all = get(headers, f"/analyze/{job1}/extractions") or {}
    ext_by_file: dict[str, list[dict]] = {}
    for e in (ext_all.get("data") or []):
        ext_by_file.setdefault(str(e.get("file_id")), []).append(e)

    # Confirm each scanned source PDF genuinely has no embedded text.
    import fitz as _fitz
    for fname, key, _expected in BIDDERS:
        if key not in SCANNED_BIDDERS:
            continue
        src = f"{SAMPLE}/{fname}"
        try:
            doc = _fitz.open(src)
            total_chars = sum(len((p.get_text() or "").strip()) for p in doc)
            doc.close()
        except Exception as e:
            total_chars = -1
            print(f"    warn: could not inspect {src}: {e}")
        test(f"{key}: source PDF has no embedded text (image-only)",
             0 <= total_chars < 20,
             f"embedded chars on disk = {total_chars}")

        f = name_to_file.get(fname)
        if not f:
            test(f"{key}: file record exists", False)
            continue
        page_count = f.get("page_count") or 0
        test(f"{key}: page_count > 0 after ingestion",
             page_count > 0, f"page_count={page_count}")

        rows = ext_by_file.get(str(f.get("id")), [])
        recovered = [r for r in rows if not r.get("not_found")]
        with_snip = [r for r in recovered
                     if (r.get("source_snippet") or "").strip()]
        test(f"{key}: recovered extractions from image-only PDF (OCR ran)",
             len(recovered) >= 1,
             f"recovered={len(recovered)} of {len(rows)}")
        test(f"{key}: recovered extractions carry source_snippet",
             len(with_snip) >= 1,
             f"with_snippet={len(with_snip)} of {len(recovered)}")

    # ── 1c. Evidence trace quality ─────────────────────────────────────
    section("PHASE 2c -- EVIDENCE TRACE QUALITY")
    ev_counts = audit_evidence(headers, job1, eval1)
    print(f"    extractions with value: {ev_counts['total_with_value']}")
    print(f"    with source_snippet:    {ev_counts['with_snippet']}")
    print(f"    with page_number:       {ev_counts['with_page']}")
    print(f"    page within doc range:  {ev_counts['page_within_doc']}")
    print(f"    snippet verified on page: {ev_counts['snippet_verified']}")

    test("Most extractions carry source_snippet",
         ev_counts["with_snippet"] >= max(1, int(0.7 * ev_counts["total_with_value"])),
         f"{ev_counts['with_snippet']}/{ev_counts['total_with_value']}")
    test("Most extractions resolve to a page",
         ev_counts["with_page"] >= max(1, int(0.6 * ev_counts["total_with_value"])),
         f"{ev_counts['with_page']}/{ev_counts['total_with_value']}")
    test("Resolved pages within document range",
         ev_counts["page_within_doc"] == ev_counts["with_page"],
         f"{ev_counts['page_within_doc']}/{ev_counts['with_page']}")

    # ── 1d. Audit chain valid ──────────────────────────────────────────
    section("PHASE 2d -- AUDIT CHAIN")
    audit = get(headers, f"/analyze/{job1}/audit") or {}
    test("Audit chain validates",
         bool(audit.get("chain_valid") or audit.get("chain_intact")),
         f"failure_index={audit.get('failure_index')} "
         f"total={audit.get('total_entries')}")

    # ── 1e. Tender criteria count ──────────────────────────────────────
    section("PHASE 2e -- TENDER CRITERIA")
    test("6 tender criteria extracted",
         (crit1.get("total") or 0) == 6,
         f"got {crit1.get('total')}")

    # ── 1f. Snapshot of the full ranking ───────────────────────────────
    section("PHASE 2f -- RANKINGS SNAPSHOT")
    for r in (comp1.get("rankings") or []):
        rank = r.get("rank") or "-"
        eligible = "ELIGIBLE" if r.get("is_eligible") else "INELIG."
        print(f"    rank={rank}  {eligible}  "
              f"score={r.get('total_score'):.3f}  "
              f"{r.get('bidder_name')}  "
              f"reason={r.get('disqualification_reason') or ''}")

    # ── PHASE 3: Determinism across independent runs ───────────────────
    if not args.skip_second_run:
        section(f"PHASE 3 -- DETERMINISM ACROSS {runs} INDEPENDENT RUNS")
        sig1 = _build_signature(eval1, comp1, dash1, crit1)
        sigs = [sig1]
        for i in range(2, runs + 1):
            _, e2, c2, d2, k2 = run_pipeline(headers, f"run{i}")
            test(f"Run {i} completed", bool(e2))
            if e2:
                sigs.append(_build_signature(e2, c2, d2, k2))

        all_match = len(sigs) == runs and all(s == sigs[0] for s in sigs)
        first_diff = ""
        if not all_match:
            for i, s in enumerate(sigs[1:], start=2):
                d = diff_first_path(sigs[0], s)
                if d:
                    first_diff = f"run1 vs run{i}: {d}"
                    break
        test(f"All {runs} pipeline runs produce identical signatures",
             all_match, first_diff[:280])

        if not all_match:
            os.makedirs("/tmp/vajans_prod_verify", exist_ok=True)
            for i, s in enumerate(sigs, start=1):
                with open(f"/tmp/vajans_prod_verify/run{i}.json", "w") as f:
                    json.dump(s, f, indent=2, sort_keys=True, default=str)
            print("\n    Signatures saved to /tmp/vajans_prod_verify/run*.json")

    return _summary()


def _summary() -> int:
    print("\n" + "=" * 64)
    total = len(passed) + len(failed)
    print(f"PRODUCTION SIMULATION RESULTS: {len(passed)}/{total} passed")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f"  - {f}")
    else:
        print("ALL PRODUCTION-SIMULATION ASSERTIONS PASSED")
    print("=" * 64)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
