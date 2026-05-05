import requests
import time
import json
import sys

BASE   = "http://localhost:8000/api/v1"
SAMPLE = "/home/sanju/vajans/data/sample"

results = []


def test(name, condition, details=""):
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"{status} — {name}")
    if not condition and details:
        print(f"       {details}")
    results.append(condition)
    return condition


# ── TEST 1: Health ─────────────────────────────────────────────────────────────
print("\n── Health checks ──")
try:
    r = requests.get("http://localhost:8000/api/health/ready", timeout=10)
    d = r.json()
    test("Backend health",      r.status_code == 200)
    test("Database connected",  d.get("checks", {}).get("database") == "ok",  str(d))
    test("Redis connected",     d.get("checks", {}).get("redis")    == "ok",  str(d))
except Exception as e:
    test("Backend reachable", False, str(e))
    test("Database connected", False, "Backend unreachable")
    test("Redis connected",    False, "Backend unreachable")

# ── TEST 2: Authentication ─────────────────────────────────────────────────────
print("\n── Authentication ──")
token = ""
try:
    r = requests.post(f"{BASE}/auth/login",
        json={"username": "officer", "password": "vajans2024"},
        timeout=10)
    test("Login works", r.status_code == 200, r.text[:200])
    token = r.json().get("access_token", "") if r.status_code == 200 else ""
except Exception as e:
    test("Login works", False, str(e))

headers = {"Authorization": f"Bearer {token}"} if token else {}

# ── TEST 3: Create job ─────────────────────────────────────────────────────────
print("\n── Job management ──")
job_id = ""
try:
    r = requests.post(f"{BASE}/jobs/",
        json={"title": "E2E Test Job", "created_by": "verifier", "metadata": {}},
        headers=headers, timeout=10)
    test("Create job", r.status_code == 201, r.text[:200])
    job_id = r.json().get("id", "") if r.status_code == 201 else ""
except Exception as e:
    test("Create job", False, str(e))

# ── TEST 4: Upload files ───────────────────────────────────────────────────────
print("\n── File uploads ──")
if job_id:
    for fname, ftype in [
        ("tender_crpf_2024.pdf",              "tender"),
        ("bidder_infratech_solutions.pdf",     "bidder"),
        ("bidder_buildquick_construction.pdf", "bidder"),
    ]:
        try:
            with open(f"{SAMPLE}/{fname}", "rb") as f:
                r = requests.post(f"{BASE}/files/upload",
                    data={"job_id": job_id, "file_type": ftype},
                    files={"file": (fname, f, "application/pdf")},
                    headers=headers, timeout=30)
            test(f"Upload {fname}", r.status_code == 201, r.text[:200])
        except FileNotFoundError:
            test(f"Upload {fname}", False, f"File not found: {SAMPLE}/{fname}")
        except Exception as e:
            test(f"Upload {fname}", False, str(e))

# ── TEST 5: Trigger pipeline ───────────────────────────────────────────────────
print("\n── Pipeline ──")
if job_id:
    try:
        r = requests.post(f"{BASE}/analyze/{job_id}", headers=headers, timeout=30)
        test("Trigger pipeline", r.status_code == 202, r.text[:200])
    except Exception as e:
        test("Trigger pipeline", False, str(e))

# ── TEST 6: Wait for completion ────────────────────────────────────────────────
print("\nWaiting for pipeline (90 seconds)...")
time.sleep(90)

print("\n── Job completion ──")
if job_id:
    try:
        r = requests.get(f"{BASE}/jobs/{job_id}", headers=headers, timeout=10)
        status_val = r.json().get("status", "")
        test("Job completed", status_val == "completed", f"Status: {status_val}")
    except Exception as e:
        test("Job completed", False, str(e))

# ── TEST 7: Evaluation results ─────────────────────────────────────────────────
print("\n── Evaluation results ──")
if job_id:
    try:
        r = requests.get(f"{BASE}/analyze/{job_id}/evaluation", headers=headers, timeout=10)
        test("Evaluation endpoint works", r.status_code == 200, r.text[:200])

        if r.status_code == 200:
            data    = r.json()
            bidders = data.get("bidders", [])
            test("Has 2 bidders", len(bidders) == 2, f"Found: {len(bidders)}")

            infratech  = next((b for b in bidders if "infratech"  in b.get("bidder_name", "").lower()), None)
            buildquick = next((b for b in bidders if "buildquick" in b.get("bidder_name", "").lower()), None)

            test("InfraTech bidder exists",  infratech  is not None)
            test("BuildQuick bidder exists", buildquick is not None)

            if infratech:
                test("InfraTech = QUALIFIED",
                     infratech.get("final_status") == "QUALIFIED",
                     f"Got: {infratech.get('final_status')} score:{infratech.get('final_score')}")
                test("InfraTech score > 70%",
                     (infratech.get("final_score") or 0) > 0.70,
                     f"Score: {infratech.get('final_score')}")

            if buildquick:
                test("BuildQuick = DISQUALIFIED",
                     buildquick.get("final_status") == "DISQUALIFIED",
                     f"Got: {buildquick.get('final_status')} score:{buildquick.get('final_score')}")
                test("BuildQuick score < 70%",
                     (buildquick.get("final_score") or 0) < 0.70,
                     f"Score: {buildquick.get('final_score')}")
                reasons = buildquick.get("disqualification_reasons", [])
                test("BuildQuick has failure reasons", len(reasons) > 0, f"Reasons: {reasons}")
    except Exception as e:
        test("Evaluation endpoint works", False, str(e))

# ── TEST 8: Determinism ────────────────────────────────────────────────────────
print("\n── Determinism ──")
if job_id:
    try:
        r1 = requests.get(f"{BASE}/analyze/{job_id}/evaluation", headers=headers, timeout=10)
        time.sleep(2)
        r2 = requests.get(f"{BASE}/analyze/{job_id}/evaluation", headers=headers, timeout=10)

        if r1.status_code == 200 and r2.status_code == 200:
            b1 = {b["bidder_name"]: b["final_status"] for b in r1.json().get("bidders", [])}
            b2 = {b["bidder_name"]: b["final_status"] for b in r2.json().get("bidders", [])}
            test("Deterministic outputs (same result twice)", b1 == b2,
                 f"Run1: {b1} Run2: {b2}")
        else:
            test("Deterministic outputs (same result twice)", False, "Could not fetch both runs")
    except Exception as e:
        test("Deterministic outputs (same result twice)", False, str(e))

# ── TEST 9: Audit trail ────────────────────────────────────────────────────────
print("\n── Audit trail ──")
if job_id:
    try:
        r = requests.get(f"{BASE}/analyze/{job_id}/audit", headers=headers, timeout=10)
        test("Audit trail works", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            data = r.json()
            test("Audit chain intact",
                 data.get("chain_valid", False) or data.get("chain_intact", False),
                 str(data)[:200])
    except Exception as e:
        test("Audit trail works", False, str(e))

# ── TEST 10: Dashboard data ────────────────────────────────────────────────────
print("\n── Dashboard endpoint ──")
if job_id:
    try:
        r = requests.get(f"{BASE}/analyze/{job_id}/dashboard", headers=headers, timeout=10)
        test("Dashboard endpoint works", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            data = r.json()
            test("Dashboard has summary",    "summary"    in data)
            test("Dashboard has comparison", "comparison" in data)
    except Exception as e:
        test("Dashboard endpoint works", False, str(e))

# ── TEST 11: Criteria endpoint ─────────────────────────────────────────────────
print("\n── Criteria endpoint ──")
if job_id:
    try:
        r = requests.get(f"{BASE}/analyze/{job_id}/criteria", headers=headers, timeout=10)
        test("Criteria endpoint works", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            count = r.json().get("total", 0)
            test("Has 6 criteria extracted", count == 6, f"Found: {count} criteria")
    except Exception as e:
        test("Criteria endpoint works", False, str(e))

# ── SUMMARY ────────────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r)
total  = len(results)
print(f"\n{'='*50}")
print(f"RESULTS: {passed}/{total} tests passed")
if passed == total:
    print("✓ SYSTEM FULLY VERIFIED — READY FOR DEMO")
else:
    print(f"✗ {total - passed} tests failed — fix before demo")
print("=" * 50)

sys.exit(0 if passed == total else 1)
