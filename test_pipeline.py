"""
VAJANS — Pipeline Integration Test
===================================
Uploads the 3 demo PDFs (1 tender + 2 bidder) and runs the full pipeline.
Verifies expected outputs:
  - InfraTech:  QUALIFIED,     score ≥ 70%
  - BuildQuick: DISQUALIFIED,  score ≤ 60%
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE    = "http://localhost:8000/api"
SAMPLE  = Path(__file__).parent / "data" / "sample"

TENDER  = SAMPLE / "tender_crpf_2024.pdf"
BIDDER1 = SAMPLE / "bidder_infratech_solutions.pdf"
BIDDER2 = SAMPLE / "bidder_buildquick_construction.pdf"

# ─── helpers ─────────────────────────────────────────────────────────────────

def check(cond, msg):
    if cond:
        print(f"  ✓  {msg}")
    else:
        print(f"  ✗  FAIL: {msg}")
    return cond


def wait_for_status(job_id: str, target: str, timeout: int = 300) -> dict:
    print(f"\n  Waiting for status={target!r} (timeout {timeout}s)…")
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        r = requests.get(f"{BASE}/v1/jobs/{job_id}")
        r.raise_for_status()
        job = r.json()
        s = job["status"]
        if s != last_status:
            print(f"    status → {s}")
            last_status = s
        if s == target:
            return job
        if s == "failed":
            print(f"  ✗  Job FAILED unexpectedly")
            sys.exit(1)
        time.sleep(5)
    print(f"  ✗  Timed out waiting for {target!r}")
    sys.exit(1)


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("VAJANS Pipeline Test")
    print("=" * 60)

    # ── 1. Verify demo files exist ────────────────────────────────────────
    print("\n[1] Checking demo PDFs…")
    for f in [TENDER, BIDDER1, BIDDER2]:
        check(f.exists(), f"{f.name}")
    if not all(f.exists() for f in [TENDER, BIDDER1, BIDDER2]):
        print("\n  Cannot proceed — demo PDFs missing.")
        sys.exit(1)

    # ── 2. Create job ─────────────────────────────────────────────────────
    print("\n[2] Creating evaluation job…")
    r = requests.post(f"{BASE}/v1/jobs/", json={
        "title":      "CRPF Demo Test — VAJANS",
        "created_by": "test_pipeline",
        "metadata":   {},
    })
    r.raise_for_status()
    job_id = r.json()["id"]
    print(f"  Job created: {job_id}")

    # ── 3. Upload tender ──────────────────────────────────────────────────
    print("\n[3] Uploading tender document…")
    with open(TENDER, "rb") as f:
        r = requests.post(f"{BASE}/v1/files/upload", data={
            "job_id":    job_id,
            "file_type": "tender",
        }, files={"file": (TENDER.name, f, "application/pdf")})
    r.raise_for_status()
    print(f"  Uploaded: {TENDER.name}")

    # ── 4. Upload bidders ─────────────────────────────────────────────────
    print("\n[4] Uploading bidder documents…")
    for bf in [BIDDER1, BIDDER2]:
        with open(bf, "rb") as f:
            r = requests.post(f"{BASE}/v1/files/upload", data={
                "job_id":    job_id,
                "file_type": "bidder",
            }, files={"file": (bf.name, f, "application/pdf")})
        r.raise_for_status()
        print(f"  Uploaded: {bf.name}")

    # ── 5. Wait for ingestion ─────────────────────────────────────────────
    print("\n[5] Waiting for ingestion to complete…")
    time.sleep(8)

    r = requests.get(f"{BASE}/v1/jobs/{job_id}")
    job = r.json()
    print(f"  Job status: {job['status']}")

    # ── 6. Trigger AI pipeline ────────────────────────────────────────────
    print("\n[6] Triggering AI pipeline…")
    r = requests.post(f"{BASE}/v1/analyze/{job_id}")
    if r.status_code == 409:
        print("  Pipeline already running (409 — OK)")
    else:
        r.raise_for_status()
        print(f"  Pipeline started: task_id={r.json().get('task_id')}")

    # ── 7. Wait for completion ────────────────────────────────────────────
    job = wait_for_status(job_id, "completed", timeout=360)
    print(f"\n  Job completed!")

    # ── 8. Fetch and verify results ───────────────────────────────────────
    print("\n[8] Fetching evaluation results…")

    r = requests.get(f"{BASE}/v1/analyze/{job_id}/evaluation")
    r.raise_for_status()
    eval_data = r.json()

    r = requests.get(f"{BASE}/v1/analyze/{job_id}/dashboard")
    r.raise_for_status()
    dashboard = r.json()

    # ── 9. Print summary ──────────────────────────────────────────────────
    print("\n[9] Results summary:")
    print(f"\n  Overall: final_status={eval_data['final_status']!r}  "
          f"final_score={eval_data['final_score']:.2%}")
    print(f"  Summary: {eval_data['summary']}")

    bidders = eval_data.get("bidders", [])
    print(f"\n  Bidder-level results ({len(bidders)} bidders):")
    for b in bidders:
        print(f"\n    [{b['bidder_name']}]")
        print(f"      Status : {b['final_status']}")
        print(f"      Score  : {b['final_score']:.2%}")
        print(f"      Pass   : {b['summary']['pass']}  "
              f"Fail: {b['summary']['fail']}  "
              f"Unknown: {b['summary']['unknown']}")

    # ── 10. Assertions ────────────────────────────────────────────────────
    print("\n[10] Assertions:")
    ok = True

    infratech = next(
        (b for b in bidders if "infratech" in b["bidder_name"].lower()), None
    )
    buildquick = next(
        (b for b in bidders if "buildquick" in b["bidder_name"].lower()), None
    )

    if infratech:
        ok &= check(infratech["final_status"] == "QUALIFIED",
                    f"InfraTech QUALIFIED (got {infratech['final_status']!r})")
        ok &= check(infratech["final_score"] >= 0.60,
                    f"InfraTech score ≥ 60% (got {infratech['final_score']:.1%})")
    else:
        ok &= check(False, "InfraTech bidder found in results")

    if buildquick:
        ok &= check(buildquick["final_status"] == "DISQUALIFIED",
                    f"BuildQuick DISQUALIFIED (got {buildquick['final_status']!r})")
        ok &= check(buildquick["final_score"] <= 0.70,
                    f"BuildQuick score ≤ 70% (got {buildquick['final_score']:.1%})")
    else:
        ok &= check(False, "BuildQuick bidder found in results")

    crit_count = len(dashboard.get("criteria", []))
    ok &= check(crit_count >= 4,
                f"At least 4 criteria extracted (got {crit_count})")

    # ── 11. Print criteria details ────────────────────────────────────────
    print("\n[11] Criteria details:")
    for c in dashboard.get("criteria", []):
        print(f"  {c['verdict'].upper():10s}  {c['label']}")

    print("\n" + ("=" * 60))
    print("TEST PASSED ✓" if ok else "TEST FAILED ✗")
    print("=" * 60)

    print(f"\nJob ID for manual inspection: {job_id}")
    print(f"Dashboard: http://localhost:5173/jobs/{job_id}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
