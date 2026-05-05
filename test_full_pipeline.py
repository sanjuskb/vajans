"""
VAJANS — Full Pipeline End-to-End Test
=======================================
Tests the complete pipeline from file upload through evaluation.

Usage (run from ~/vajans/backend/):
  python3 ../test_full_pipeline.py
  python3 ../test_full_pipeline.py --run-twice   # determinism check

Expected outcomes:
  InfraTech Solutions:   QUALIFIED,    score ~82%, 6 pass, 0 fail
  BuildQuick Construction: DISQUALIFIED, score ~45%, 3 pass, 3 fail
  Fail reasons (BuildQuick): Turnover, Projects, ISO expired
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

BASE_URL = os.getenv("VAJANS_API_URL", "http://localhost:8000/api/v1")
SAMPLE_DIR = Path(__file__).parent / "data" / "sample"

TENDER_FILE  = SAMPLE_DIR / "tender_crpf_2024.pdf"
INFRATECH    = SAMPLE_DIR / "bidder_infratech_solutions.pdf"
BUILDQUICK   = SAMPLE_DIR / "bidder_buildquick_construction.pdf"

TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def log(msg: str):
    print(f"  {msg}", flush=True)


def step(msg: str):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}", flush=True)


def assert_eq(label: str, actual, expected):
    if actual != expected:
        print(f"\n  ✗ ASSERT FAILED: {label}")
        print(f"    Expected: {expected!r}")
        print(f"    Actual:   {actual!r}")
        return False
    print(f"  ✓ {label}: {actual!r}")
    return True


def assert_gte(label: str, actual: float, minimum: float):
    if actual < minimum:
        print(f"\n  ✗ ASSERT FAILED: {label}")
        print(f"    Expected: >= {minimum}")
        print(f"    Actual:   {actual}")
        return False
    print(f"  ✓ {label}: {actual:.4f} >= {minimum}")
    return True


def assert_lte(label: str, actual: float, maximum: float):
    if actual > maximum:
        print(f"\n  ✗ ASSERT FAILED: {label}")
        print(f"    Expected: <= {maximum}")
        print(f"    Actual:   {actual}")
        return False
    print(f"  ✓ {label}: {actual:.4f} <= {maximum}")
    return True


def assert_contains_any(label: str, text: str, patterns: list[str]):
    text_lower = text.lower()
    for p in patterns:
        if p.lower() in text_lower:
            print(f"  ✓ {label}: found '{p}' in '{text[:60]}'")
            return True
    print(f"\n  ✗ ASSERT FAILED: {label}")
    print(f"    Expected one of: {patterns}")
    print(f"    In text: '{text}'")
    return False


def run_test(run_number: int = 1) -> dict:
    """Run one full pipeline test. Returns result dict for comparison."""
    step(f"RUN #{run_number}: Full Pipeline Test")

    client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)

    # ── Step 1: Create job ──────────────────────────────────────────────────
    log("Creating job...")
    r = client.post("/jobs/", json={
        "title": f"CRPF Construction Tender - Final Test (Run {run_number})",
        "created_by": "test_script",
        "metadata": {"test_run": run_number},
    })
    r.raise_for_status()
    job_id = r.json()["id"]
    log(f"Job created: {job_id}")

    # ── Step 2: Upload files ────────────────────────────────────────────────
    def upload_file(filepath: Path, file_type: str) -> str:
        with open(filepath, "rb") as fh:
            r = client.post(
                "/files/upload",
                data={"job_id": job_id, "file_type": file_type},
                files={"file": (filepath.name, fh, "application/pdf")},
            )
        r.raise_for_status()
        return r.json()["id"]

    log("Uploading tender document...")
    upload_file(TENDER_FILE, "tender")
    log("Tender uploaded.")

    log("Uploading InfraTech bidder document...")
    infratech_file_id = upload_file(INFRATECH, "bidder")
    log(f"InfraTech uploaded: {infratech_file_id}")

    log("Uploading BuildQuick bidder document...")
    buildquick_file_id = upload_file(BUILDQUICK, "bidder")
    log(f"BuildQuick uploaded: {buildquick_file_id}")

    # ── Step 3: Wait for ingestion ──────────────────────────────────────────
    log("Waiting for ingestion to complete...")
    max_wait = 120
    elapsed  = 0
    while elapsed < max_wait:
        r = client.get(f"/files/job/{job_id}")
        r.raise_for_status()
        files = r.json()
        all_done = all(
            f["status"] in ("processed", "failed")
            for f in files
            if f["file_type"] == "tender"
        )
        if all_done:
            log("Ingestion complete.")
            break
        time.sleep(5)
        elapsed += 5

    # ── Step 4: Trigger AI pipeline ─────────────────────────────────────────
    log("Triggering AI pipeline...")
    r = client.post(f"/analyze/{job_id}")
    if r.status_code not in (200, 202):
        log(f"Pipeline trigger returned {r.status_code}: {r.text[:200]}")
        if r.status_code == 409 and "already" in r.text.lower():
            log("Pipeline already running or completed — OK")
        else:
            r.raise_for_status()

    # ── Step 5: Poll until COMPLETED ────────────────────────────────────────
    log("Polling job status until COMPLETED (max 3 minutes)...")
    max_wait = 180
    elapsed  = 0
    while elapsed < max_wait:
        r = client.get(f"/jobs/{job_id}")
        r.raise_for_status()
        job = r.json()
        status = job["status"]
        log(f"  [{elapsed:3d}s] Status: {status}")

        if status == "completed":
            log("Pipeline COMPLETED.")
            break
        if status == "failed":
            log("Pipeline FAILED.")
            sys.exit(1)
        time.sleep(10)
        elapsed += 10
    else:
        log("TIMEOUT waiting for pipeline completion.")
        sys.exit(1)

    # ── Step 6: Fetch evaluation results ────────────────────────────────────
    log("Fetching evaluation results...")
    r = client.get(f"/analyze/{job_id}/evaluation")
    r.raise_for_status()
    eval_data = r.json()

    # ── Step 7: Print raw results ────────────────────────────────────────────
    print("\n--- EVALUATION RESULTS ---")
    print(f"  Job ID:       {job_id}")
    print(f"  Final status: {eval_data.get('final_status')}")
    print(f"  Final score:  {eval_data.get('final_score')}")
    print(f"  Summary:      {eval_data.get('summary')}")
    print(f"  Bidders:")
    for b in eval_data.get("bidders", []):
        print(f"    • {b.get('bidder_name')}")
        print(f"      Status: {b.get('final_status')}")
        print(f"      Score:  {b.get('final_score')}")
        s = b.get("summary", {})
        print(f"      Pass: {s.get('pass')}  Fail: {s.get('fail')}  Unknown: {s.get('unknown')}")

    # ── Step 8: Assertions ───────────────────────────────────────────────────
    step("ASSERTIONS")
    failures = 0

    bidders = eval_data.get("bidders", [])
    if len(bidders) < 2:
        print(f"  ✗ ASSERT FAILED: expected 2 bidders, got {len(bidders)}")
        sys.exit(1)

    # Find bidders by name
    infratech_result  = next(
        (b for b in bidders if "infratech" in b.get("bidder_name", "").lower()), None
    )
    buildquick_result = next(
        (b for b in bidders if "buildquick" in b.get("bidder_name", "").lower()), None
    )

    if infratech_result is None:
        print("  ✗ Could not find InfraTech in results")
        failures += 1
    else:
        print("\n  InfraTech Solutions:")
        if not assert_eq("  Final status", infratech_result["final_status"], "QUALIFIED"):
            failures += 1
        if not assert_gte("  Score",        infratech_result["final_score"], 0.70):
            failures += 1
        if not assert_lte("  Score",        infratech_result["final_score"], 1.00):
            failures += 1
        si = infratech_result.get("summary", {})
        if not assert_eq("  Pass count", si.get("pass"), 6):
            failures += 1
        if not assert_eq("  Fail count", si.get("fail"), 0):
            failures += 1

    if buildquick_result is None:
        print("  ✗ Could not find BuildQuick in results")
        failures += 1
    else:
        print("\n  BuildQuick Construction:")
        if not assert_eq("  Final status", buildquick_result["final_status"], "DISQUALIFIED"):
            failures += 1
        if not assert_lte("  Score",        buildquick_result["final_score"], 0.65):
            failures += 1
        sb = buildquick_result.get("summary", {})
        fail_count = sb.get("fail", 0)
        if fail_count < 3:
            print(f"  ✗ BuildQuick fail count: expected >=3, got {fail_count}")
            failures += 1
        else:
            print(f"  ✓ BuildQuick fail count: {fail_count} (>=3)")

        # Check disqualification reasons via comparison endpoint
        r2 = client.get(f"/analyze/{job_id}/comparison")
        if r2.status_code == 200:
            comp = r2.json()
            bq_comp = next(
                (b for b in comp.get("bidders", [])
                 if "buildquick" in b.get("bidder_name", "").lower()),
                None,
            )
            if bq_comp:
                disq_reason = bq_comp.get("disqualification_reason", "") or ""
                print(f"\n  BuildQuick disqualification reason: {disq_reason}")
                if not disq_reason:
                    # Check criteria verdicts
                    crits = bq_comp.get("criteria", [])
                    fail_labels = [
                        c.get("explanation", "") for c in crits
                        if c.get("verdict") == "fail"
                    ]
                    print(f"  Failed criteria explanations: {fail_labels}")

    # ── Step 9: Criteria deduplication check ────────────────────────────────
    print("\n  Criteria deduplication:")
    r3 = client.get(f"/analyze/{job_id}/criteria")
    if r3.status_code == 200:
        crit_data = r3.json()
        total_crit = crit_data.get("total", 0)
        keys = [c["criterion_key"] for c in crit_data.get("data", [])]
        unique_keys = set(keys)
        if len(keys) != len(unique_keys):
            print(f"  ✗ Duplicate criteria found! Total: {len(keys)}, Unique: {len(unique_keys)}")
            print(f"     Duplicates: {[k for k in keys if keys.count(k) > 1]}")
            failures += 1
        else:
            print(f"  ✓ No duplicate criteria: {total_crit} unique criteria")

    # ── Step 10: Return result for determinism comparison ──────────────────
    result = {
        "job_id":    job_id,
        "bidders":   [
            {
                "name":   b.get("bidder_name"),
                "status": b.get("final_status"),
                "score":  round(b.get("final_score", 0), 2),
                "pass":   b.get("summary", {}).get("pass"),
                "fail":   b.get("summary", {}).get("fail"),
            }
            for b in sorted(bidders, key=lambda x: x.get("bidder_name", ""))
        ],
    }

    if failures == 0:
        print(f"\n  ✓ ALL ASSERTIONS PASSED for Run #{run_number}")
    else:
        print(f"\n  ✗ {failures} ASSERTION(S) FAILED for Run #{run_number}")

    return result


def compare_runs(r1: dict, r2: dict) -> bool:
    """Compare two run results for determinism."""
    step("DETERMINISM CHECK")
    # Compare bidder verdicts (ignore job_id which is always different)
    b1 = {b["name"]: b for b in r1["bidders"]}
    b2 = {b["name"]: b for b in r2["bidders"]}

    all_match = True
    for name in b1:
        if name not in b2:
            print(f"  ✗ Bidder '{name}' missing in Run 2")
            all_match = False
            continue
        d1, d2 = b1[name], b2[name]
        for field in ("status", "score", "pass", "fail"):
            if d1[field] != d2[field]:
                print(f"  ✗ MISMATCH for '{name}' field '{field}': "
                      f"Run 1={d1[field]!r}  Run 2={d2[field]!r}")
                all_match = False
            else:
                print(f"  ✓ '{name}'.{field}: {d1[field]!r} == {d2[field]!r}")

    if all_match:
        print("\n  ✓ DETERMINISM CONFIRMED: Both runs produce identical verdicts.")
    else:
        print("\n  ✗ NON-DETERMINISM DETECTED: Runs differ. Check extraction caching.")

    return all_match


def main():
    parser = argparse.ArgumentParser(description="VAJANS full pipeline test")
    parser.add_argument("--run-twice", action="store_true",
                        help="Run the test twice to check determinism")
    args = parser.parse_args()

    # Verify sample files exist
    for p in (TENDER_FILE, INFRATECH, BUILDQUICK):
        if not p.exists():
            print(f"ERROR: Sample file not found: {p}")
            print("Run: python3 data/generate_demo_data.py")
            sys.exit(1)

    r1 = run_test(run_number=1)

    if args.run_twice:
        r2 = run_test(run_number=2)
        compare_runs(r1, r2)

    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
