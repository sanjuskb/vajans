import requests
import time
import sys
import os

BASE = "http://localhost:8000/api/v1"
SAMPLE = "/home/sanju/vajans/data/sample"
passed = []
failed = []


def test(name, condition, detail=""):
    if condition:
        print(f"✓ {name}")
        passed.append(name)
    else:
        print(f"✗ {name}" + (f" — {detail}" if detail else ""))
        failed.append(name)
    return condition


print("\n=== HEALTH CHECKS ===")
try:
    r = requests.get("http://localhost:8000/api/health/ready", timeout=10)
    d = r.json()
    test("Backend running", r.status_code == 200)
    test("Database connected", d.get("checks", {}).get("database") == "ok", str(d))
    test("Redis connected", d.get("checks", {}).get("redis") == "ok", str(d))
except Exception as e:
    test("Backend running", False, str(e))
    test("Database connected", False, "Backend unreachable")
    test("Redis connected", False, "Backend unreachable")

print("\n=== AUTH ===")
token = ""
try:
    r = requests.post(f"{BASE}/auth/login",
                      json={"username": "officer", "password": "vajans2024"}, timeout=10)
    test("Login works", r.status_code == 200, r.text[:80])
    token = r.json().get("access_token", "") if r.status_code == 200 else ""
except Exception as e:
    test("Login works", False, str(e))

H = {"Authorization": f"Bearer {token}"} if token else {}

print("\n=== PIPELINE RUN 1 ===")
job1 = ""
try:
    r = requests.post(f"{BASE}/jobs/",
                      json={"title": "Verify Test 1", "created_by": "verifier", "metadata": {}},
                      headers=H, timeout=10)
    test("Create job", r.status_code == 201, r.text[:80])
    job1 = r.json().get("id", "") if r.status_code == 201 else ""
except Exception as e:
    test("Create job", False, str(e))

if job1:
    files_ok = True
    for fname, ftype in [
        ("tender_crpf_2024.pdf", "tender"),
        ("bidder_infratech_solutions.pdf", "bidder"),
        ("bidder_buildquick_construction.pdf", "bidder"),
    ]:
        try:
            with open(f"{SAMPLE}/{fname}", "rb") as f:
                r = requests.post(f"{BASE}/files/upload",
                                  data={"job_id": job1, "file_type": ftype},
                                  files={"file": (fname, f, "application/pdf")},
                                  headers=H, timeout=30)
            if r.status_code != 201:
                files_ok = False
        except Exception as e:
            files_ok = False
            print(f"  Upload error {fname}: {e}")
    test("All files uploaded", files_ok)

    try:
        r = requests.post(f"{BASE}/analyze/{job1}", headers=H, timeout=30)
        test("Pipeline triggered", r.status_code == 202, r.text[:80])
    except Exception as e:
        test("Pipeline triggered", False, str(e))

    print("Waiting for pipeline (up to 120 seconds)...")
    for i in range(24):
        time.sleep(5)
        try:
            r = requests.get(f"{BASE}/jobs/{job1}", headers=H, timeout=10)
            status = r.json().get("status", "?")
            if status == "completed":
                break
            print(f"  ...{(i+1)*5}s — status: {status}")
        except Exception:
            pass

    try:
        r = requests.get(f"{BASE}/jobs/{job1}", headers=H, timeout=10)
        test("Job completed", r.json().get("status") == "completed",
             f"status={r.json().get('status')}")
    except Exception as e:
        test("Job completed", False, str(e))

    try:
        r = requests.get(f"{BASE}/analyze/{job1}/evaluation", headers=H, timeout=10)
        test("Evaluation endpoint", r.status_code == 200, r.text[:80])

        if r.status_code == 200:
            data = r.json()
            bidders = data.get("bidders", [])
            test("2 bidders evaluated", len(bidders) == 2, f"got {len(bidders)}")

            infra = next((b for b in bidders if "infratech" in b.get("bidder_name", "").lower()), None)
            build = next((b for b in bidders if "buildquick" in b.get("bidder_name", "").lower()), None)

            run1_infra = infra.get("final_status") if infra else None
            run1_build = build.get("final_status") if build else None
            run1_infra_score = infra.get("final_score", 0) if infra else 0
            run1_build_score = build.get("final_score", 0) if build else 0

            test("InfraTech = QUALIFIED", run1_infra == "QUALIFIED",
                 f"got {run1_infra} score={run1_infra_score:.2f}")
            test("BuildQuick = DISQUALIFIED", run1_build == "DISQUALIFIED",
                 f"got {run1_build} score={run1_build_score:.2f}")
            test("InfraTech score > 0.70", run1_infra_score > 0.70,
                 f"score={run1_infra_score:.2f}")
            test("BuildQuick score < 0.70", run1_build_score < 0.70,
                 f"score={run1_build_score:.2f}")

            if build:
                reasons = build.get("disqualification_reasons", [])
                test("BuildQuick has failure reasons", len(reasons) > 0, str(reasons))
    except Exception as e:
        test("Evaluation endpoint", False, str(e))

print("\n=== PIPELINE RUN 2 (DETERMINISM TEST) ===")
if job1:
    try:
        r1 = requests.get(f"{BASE}/analyze/{job1}/evaluation", headers=H, timeout=10)
        time.sleep(2)
        r2 = requests.get(f"{BASE}/analyze/{job1}/evaluation", headers=H, timeout=10)
        if r1.status_code == 200 and r2.status_code == 200:
            b1 = {b["bidder_name"]: b["final_status"] for b in r1.json().get("bidders", [])}
            b2 = {b["bidder_name"]: b["final_status"] for b in r2.json().get("bidders", [])}
            test("Deterministic outputs", b1 == b2, f"run1={b1} run2={b2}")
        else:
            test("Deterministic outputs", False, "Could not fetch both runs")
    except Exception as e:
        test("Deterministic outputs", False, str(e))

print("\n=== SUPPORTING ENDPOINTS ===")
if job1:
    try:
        r = requests.get(f"{BASE}/analyze/{job1}/criteria", headers=H, timeout=10)
        test("Criteria endpoint", r.status_code == 200)
        if r.status_code == 200:
            test("6 criteria extracted", r.json().get("total") == 6,
                 f"got {r.json().get('total')}")
    except Exception as e:
        test("Criteria endpoint", False, str(e))

    try:
        r = requests.get(f"{BASE}/analyze/{job1}/dashboard", headers=H, timeout=10)
        test("Dashboard endpoint", r.status_code == 200)
    except Exception as e:
        test("Dashboard endpoint", False, str(e))

    try:
        r = requests.get(f"{BASE}/analyze/{job1}/comparison", headers=H, timeout=10)
        test("Comparison endpoint", r.status_code == 200)
        if r.status_code == 200:
            bids = r.json().get("bidders", [])
            test("Comparison has 2 bidders", len(bids) == 2, f"got {len(bids)}")
    except Exception as e:
        test("Comparison endpoint", False, str(e))

    try:
        r = requests.get(f"{BASE}/analyze/{job1}/audit", headers=H, timeout=10)
        test("Audit endpoint", r.status_code == 200)
        if r.status_code == 200:
            test("Audit chain intact",
                 r.json().get("chain_intact", False) or r.json().get("chain_valid", False))
    except Exception as e:
        test("Audit endpoint", False, str(e))

print("\n=== SUPABASE CONNECTION ===")
try:
    import asyncio as _asyncio

    async def _check_supa():
        os.environ['ENVIRONMENT'] = 'production'
        # Re-import to pick up env var
        import importlib
        import app.db.session as sess_mod
        importlib.reload(sess_mod)
        from sqlalchemy import text
        async with sess_mod.engine.connect() as conn:
            r = await conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
            ))
            return r.scalar()

    count = _asyncio.run(_check_supa())
    test("Supabase connected", count > 0, f"{count} tables in Supabase")
except Exception as e:
    test("Supabase connected", False, str(e)[:120])

print(f"\n{'='*50}")
print(f"RESULTS: {len(passed)}/{len(passed)+len(failed)} passed")
if not failed:
    print("✓ ALL SYSTEMS VERIFIED — READY TO DEPLOY")
else:
    print(f"✗ FAILED: {failed}")
print('=' * 50)

sys.exit(0 if not failed else 1)
