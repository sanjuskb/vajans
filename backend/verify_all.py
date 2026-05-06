"""
VAJANS — End-to-End Verification + Determinism Probe
=====================================================

Runs the entire pipeline against the canonical sample documents and asserts:

  1. Health, auth, and supporting endpoints all work.
  2. InfraTech is QUALIFIED, BuildQuick is DISQUALIFIED for the CRPF tender.
  3. The same job answers the evaluation/comparison/dashboard/audit endpoints
     IDENTICALLY across N repeated reads (read-side determinism).
  4. Two separate jobs ingesting the SAME tender + bidder PDFs produce the
     same final outputs (pipeline-side determinism across re-runs).
  5. The audit chain validates.
  6. Supabase production connection works.

Exits non-zero on any failure.

Usage:
  python backend/verify_all.py                 # full run
  python backend/verify_all.py --quick         # skip the second pipeline run
  python backend/verify_all.py --pipeline-runs 3   # determinism over N runs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE   = os.environ.get("VAJANS_BASE", "http://localhost:8000/api/v1")
HEALTH = os.environ.get("VAJANS_HEALTH", "http://localhost:8000/api/health/ready")
SAMPLE = os.environ.get("VAJANS_SAMPLE", "/home/sanju/vajans/data/sample")

PIPELINE_TIMEOUT_SECS = 300        # max wait for one pipeline run
POLL_INTERVAL_SECS    = 5

passed: list[str] = []
failed: list[str] = []


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
        headers=headers,
        timeout=15,
    )
    if r.status_code != 201:
        return ""
    return r.json().get("id", "")


def upload_files(headers: dict, job_id: str) -> bool:
    files = [
        ("tender_crpf_2024.pdf",              "tender"),
        ("bidder_infratech_solutions.pdf",    "bidder"),
        ("bidder_buildquick_construction.pdf","bidder"),
    ]
    for fname, ftype in files:
        path = f"{SAMPLE}/{fname}"
        try:
            with open(path, "rb") as f:
                r = requests.post(
                    f"{BASE}/files/upload",
                    data={"job_id": job_id, "file_type": ftype},
                    files={"file": (fname, f, "application/pdf")},
                    headers=headers,
                    timeout=60,
                )
            if r.status_code != 201:
                print(f"    upload {fname} -> {r.status_code} {r.text[:120]}")
                return False
        except FileNotFoundError:
            print(f"    sample file missing: {path}")
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
    last_status = "?"
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECS)
        try:
            jr = requests.get(f"{BASE}/jobs/{job_id}", headers=headers, timeout=15)
            last_status = jr.json().get("status", "?")
            if last_status == "completed":
                return "completed"
            if last_status == "failed":
                return "failed"
        except Exception as e:
            print(f"    poll error: {e}")
        elapsed = int(PIPELINE_TIMEOUT_SECS - (deadline - time.time()))
        print(f"    {elapsed}s -- status: {last_status}")
    return f"timeout:{last_status}"


def fetch_evaluation(headers: dict, job_id: str) -> dict | None:
    r = requests.get(f"{BASE}/analyze/{job_id}/evaluation", headers=headers, timeout=15)
    return r.json() if r.status_code == 200 else None


def fetch_comparison(headers: dict, job_id: str) -> dict | None:
    r = requests.get(f"{BASE}/analyze/{job_id}/comparison", headers=headers, timeout=15)
    return r.json() if r.status_code == 200 else None


def fetch_dashboard(headers: dict, job_id: str) -> dict | None:
    r = requests.get(f"{BASE}/analyze/{job_id}/dashboard", headers=headers, timeout=15)
    return r.json() if r.status_code == 200 else None


def fetch_criteria(headers: dict, job_id: str) -> dict | None:
    r = requests.get(f"{BASE}/analyze/{job_id}/criteria", headers=headers, timeout=15)
    return r.json() if r.status_code == 200 else None


def fetch_audit(headers: dict, job_id: str) -> dict | None:
    r = requests.get(f"{BASE}/analyze/{job_id}/audit", headers=headers, timeout=15)
    return r.json() if r.status_code == 200 else None


# ---------------------------------------------------------------------------
# Determinism comparison
# ---------------------------------------------------------------------------
# Fields whose value depends on the JOB itself (id, timestamps, FK ids) and
# therefore legitimately differ between independent pipeline runs.  We strip
# them before comparing two jobs.
_JOB_VARIANT_FIELDS = {
    "id",
    "job_id",
    "criterion_id",
    "tender_file_id",
    "file_id",
    "bidder_file_id",
    "bidder_id",
    "previous_hash",
    "current_hash",
    "created_at",
    "updated_at",
    "evaluated_at",
    "task_id",
}


def _canonicalise(obj: Any, *, drop_job_specific: bool) -> Any:
    """Recursively strip job-specific fields and sort dict keys."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if drop_job_specific and k in _JOB_VARIANT_FIELDS:
                continue
            out[k] = _canonicalise(v, drop_job_specific=drop_job_specific)
        return dict(sorted(out.items()))
    if isinstance(obj, list):
        return [_canonicalise(x, drop_job_specific=drop_job_specific) for x in obj]
    return obj


def diff_first_path(a: Any, b: Any, path: str = "") -> str | None:
    """Return a textual path to the first difference, or None if identical."""
    if type(a) is not type(b):
        return f"{path or '<root>'}: type {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            if k not in a:
                return f"{path}.{k} missing in run1"
            if k not in b:
                return f"{path}.{k} missing in run2"
            d = diff_first_path(a[k], b[k], f"{path}.{k}")
            if d is not None:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: list len {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff_first_path(x, y, f"{path}[{i}]")
            if d is not None:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} vs {b!r}"
    return None


def signature_for_run(eval_data: dict, comp_data: dict | None,
                      dash_data: dict | None, crit_data: dict | None) -> dict:
    """
    Build a JOB-INDEPENDENT signature that captures every value an external
    user would observe, MINUS values that necessarily change with the job
    UUID (ids, timestamps).  Two runs with identical input must produce
    identical signatures.
    """
    sig: dict[str, Any] = {}

    # Build a map criterion_id -> criterion_key so we can translate any
    # UUIDs that appear inside list payloads (e.g. dashboard.flags) into
    # stable, data-derived keys.  Without this, two independent jobs would
    # always disagree on `affected_criteria` even though their semantic
    # content is identical.
    cid_to_key: dict[str, str] = {}
    if crit_data:
        for c in (crit_data.get("data") or []):
            cid_to_key[str(c.get("id"))] = c.get("criterion_key") or ""

    def _translate_ids(value: Any) -> Any:
        if isinstance(value, list):
            return [cid_to_key.get(v, v) if isinstance(v, str) else _translate_ids(v)
                    for v in value]
        if isinstance(value, dict):
            return {k: _translate_ids(v) for k, v in value.items()}
        return value

    if eval_data:
        sig["evaluation"] = {
            "final_status": eval_data.get("final_status"),
            "final_score":  eval_data.get("final_score"),
            "summary":      eval_data.get("summary"),
            # Per-bidder data, keyed by bidder name for stability
            "bidders": {
                b.get("bidder_name"): {
                    "final_status": b.get("final_status"),
                    "final_score":  b.get("final_score"),
                    "summary":      b.get("summary"),
                    "disq_reasons": sorted(b.get("disqualification_reasons") or []),
                    # Per-criterion -- key by criterion explanation (data-derived)
                    "criteria": sorted(
                        [
                            {
                                "verdict":       r.get("verdict"),
                                "score":         r.get("score"),
                                "weight":        r.get("weight"),
                                "weighted_score": r.get("weighted_score"),
                                "explanation":   r.get("explanation"),
                            }
                            for r in (b.get("results") or [])
                        ],
                        key=lambda d: d.get("explanation") or "",
                    ),
                }
                for b in (eval_data.get("bidders") or [])
            },
        }

    if comp_data:
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
            ],
            "bidders_by_name": {
                b.get("bidder_name"): {
                    "total_score":     b.get("total_score"),
                    "pass":            b.get("pass"),
                    "fail":            b.get("fail"),
                    "unknown":         b.get("unknown"),
                    "is_disqualified": b.get("is_disqualified"),
                    # Sort by explanation to drop criterion_id dependency
                    "criteria": sorted(
                        [
                            {
                                "verdict":     c.get("verdict"),
                                "score":       c.get("score"),
                                "explanation": c.get("explanation"),
                            }
                            for c in (b.get("criteria") or [])
                        ],
                        key=lambda d: d.get("explanation") or "",
                    ),
                }
                for b in (comp_data.get("bidders") or [])
            },
        }

    if dash_data:
        # Flags carry `affected_criteria` (UUIDs) which differ per job.
        # Translate to criterion_keys + sort so the comparison is semantic.
        flags_normalised = []
        for f in (dash_data.get("flags") or []):
            f_copy = dict(f)
            if "affected_criteria" in f_copy:
                translated = _translate_ids(f_copy["affected_criteria"])
                f_copy["affected_criteria"] = sorted(translated)
            flags_normalised.append(f_copy)
        flags_normalised.sort(
            key=lambda f: (f.get("code") or "", f.get("severity") or "")
        )
        sig["dashboard"] = {
            "summary": dash_data.get("summary"),
            "flags":   flags_normalised,
        }

    if crit_data:
        sig["criteria"] = {
            "total": crit_data.get("total"),
            "by_key": sorted(
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
            ),
        }

    return _canonicalise(sig, drop_job_specific=True)


# ---------------------------------------------------------------------------
# Pipeline run wrapper
# ---------------------------------------------------------------------------
def run_pipeline(headers: dict, label: str) -> tuple[str, dict]:
    """
    Create a job, upload all 3 sample files, trigger, wait, and collect
    every relevant API response.  Returns (job_id, signature).
    """
    print(f"\n[{label}] creating job ...")
    job_id = create_job(headers, f"verify-{label}")
    if not job_id:
        return "", {}

    print(f"[{label}] uploading files (job {job_id[:8]}) ...")
    if not upload_files(headers, job_id):
        return job_id, {}

    print(f"[{label}] triggering pipeline ...")
    status = trigger_and_wait(headers, job_id)
    if status != "completed":
        print(f"[{label}] pipeline did not complete: {status}")
        return job_id, {}

    print(f"[{label}] pipeline complete -- fetching outputs ...")
    eval_data = fetch_evaluation(headers, job_id)
    comp_data = fetch_comparison(headers, job_id)
    dash_data = fetch_dashboard(headers, job_id)
    crit_data = fetch_criteria(headers, job_id)

    sig = signature_for_run(eval_data, comp_data, dash_data, crit_data)
    return job_id, sig


# ---------------------------------------------------------------------------
# Main verification flow
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick", action="store_true",
        help="Run only one pipeline (skip cross-run determinism).",
    )
    parser.add_argument(
        "--pipeline-runs", type=int, default=2,
        help="Number of independent pipeline runs to compare (default 2).",
    )
    parser.add_argument(
        "--repeat-reads", type=int, default=5,
        help="How many times to re-read endpoints for read-side determinism.",
    )
    args = parser.parse_args(argv)

    runs = 1 if args.quick else max(2, args.pipeline_runs)

    # ── HEALTH ──────────────────────────────────────────────────────────
    section("HEALTH CHECKS")
    try:
        r = requests.get(HEALTH, timeout=10)
        d = r.json()
        test("Backend running",        r.status_code == 200, str(d)[:120])
        test("Database connected",     d.get("checks", {}).get("database") == "ok", str(d))
        test("Redis connected",        d.get("checks", {}).get("redis") == "ok",    str(d))
    except Exception as e:
        test("Backend running",    False, str(e))
        test("Database connected", False, "backend unreachable")
        test("Redis connected",    False, "backend unreachable")
        return _summary()

    # ── AUTH ────────────────────────────────────────────────────────────
    section("AUTH")
    headers = login()
    test("Login works", bool(headers), "no token returned")
    if not headers:
        return _summary()

    # ── PRIMARY PIPELINE RUN (job1) ─────────────────────────────────────
    section("PIPELINE RUN 1")
    job1, sig1 = run_pipeline(headers, "run1")
    test("Run 1 created job",  bool(job1))
    test("Run 1 produced data", bool(sig1))

    if not sig1:
        return _summary()

    eval1 = sig1.get("evaluation", {}).get("bidders", {})
    infra1 = next((v for k, v in eval1.items() if "infratech" in (k or "").lower()), {})
    build1 = next((v for k, v in eval1.items() if "buildquick" in (k or "").lower()), {})

    test(
        "InfraTech = QUALIFIED",
        infra1.get("final_status") == "QUALIFIED",
        f"got {infra1.get('final_status')} score={infra1.get('final_score')}",
    )
    test(
        "BuildQuick = DISQUALIFIED",
        build1.get("final_status") == "DISQUALIFIED",
        f"got {build1.get('final_status')} score={build1.get('final_score')}",
    )
    test(
        "InfraTech score > 0.70",
        (infra1.get("final_score") or 0) > 0.70,
        f"score={infra1.get('final_score')}",
    )
    test(
        "BuildQuick score < 0.70",
        (build1.get("final_score") or 0) < 0.70,
        f"score={build1.get('final_score')}",
    )
    test(
        "BuildQuick has failure reasons",
        len(build1.get("disq_reasons") or []) > 0,
        str(build1.get("disq_reasons")),
    )

    # ── SUPPORTING ENDPOINTS ────────────────────────────────────────────
    section("SUPPORTING ENDPOINTS")
    crit = fetch_criteria(headers, job1)
    test("Criteria endpoint", crit is not None)
    if crit:
        test("Criteria count == 6", crit.get("total") == 6, f"got {crit.get('total')}")

    dash = fetch_dashboard(headers, job1)
    test("Dashboard endpoint", dash is not None)
    if dash:
        test("Dashboard has summary",    "summary"    in dash)
        test("Dashboard has comparison", "comparison" in dash)

    comp = fetch_comparison(headers, job1)
    test("Comparison endpoint", comp is not None)
    if comp:
        test(
            "Comparison has 2 bidders",
            len(comp.get("bidders") or []) == 2,
            f"got {len(comp.get('bidders') or [])}",
        )

    audit = fetch_audit(headers, job1)
    test("Audit endpoint", audit is not None)
    if audit:
        test(
            "Audit chain valid",
            bool(audit.get("chain_valid") or audit.get("chain_intact")),
            f"failure_index={audit.get('failure_index')}",
        )

    # ── READ-SIDE DETERMINISM ───────────────────────────────────────────
    # Same DB state, multiple reads -- the API must return byte-identical
    # signatures.  Catches dict-iteration / ORDER BY issues.
    section("READ-SIDE DETERMINISM (same job, repeated reads)")
    read_sigs = []
    for i in range(args.repeat_reads):
        e = fetch_evaluation(headers, job1)
        c = fetch_comparison(headers, job1)
        d = fetch_dashboard(headers, job1)
        k = fetch_criteria(headers, job1)
        read_sigs.append(signature_for_run(e, c, d, k))
        time.sleep(0.5)

    all_reads_match = all(s == read_sigs[0] for s in read_sigs)
    test(
        f"All {args.repeat_reads} repeated reads identical",
        all_reads_match,
        diff_first_path(read_sigs[0], next(
            (s for s in read_sigs if s != read_sigs[0]), read_sigs[0]
        )) or "",
    )

    # ── PIPELINE-SIDE DETERMINISM (independent runs) ────────────────────
    if not args.quick and runs >= 2:
        section(f"PIPELINE-SIDE DETERMINISM ({runs} independent runs)")
        sigs = [sig1]
        for i in range(2, runs + 1):
            _, sig_i = run_pipeline(headers, f"run{i}")
            sigs.append(sig_i)

        all_runs_match = all(s == sigs[0] for s in sigs)
        first_diff = ""
        if not all_runs_match:
            for i, s in enumerate(sigs[1:], start=2):
                d = diff_first_path(sigs[0], s)
                if d:
                    first_diff = f"run1 vs run{i}: {d}"
                    break
        test(
            f"All {runs} pipeline runs produce identical outputs",
            all_runs_match,
            first_diff[:300],
        )

        if not all_runs_match:
            os.makedirs("/tmp/vajans_verify", exist_ok=True)
            for i, s in enumerate(sigs, start=1):
                with open(f"/tmp/vajans_verify/run{i}.json", "w") as f:
                    json.dump(s, f, indent=2, sort_keys=True, default=str)
            print("\n  Signatures saved to /tmp/vajans_verify/run*.json for inspection")

    # ── SUPABASE CONNECTION (production env) ────────────────────────────
    section("SUPABASE CONNECTION")
    try:
        # Run in a subprocess so the production engine creation does not
        # disturb the development engine in this Python process.
        import subprocess
        check_code = (
            "import os, asyncio;"
            "os.environ['ENVIRONMENT']='production';"
            "from sqlalchemy.ext.asyncio import create_async_engine;"
            "from sqlalchemy import text;"
            "from app.db.session import _build_engine_url, _build_connect_args;"
            "\nasync def run():\n"
            "    eng = create_async_engine(_build_engine_url(),"
            " connect_args=_build_connect_args());\n"
            "    async with eng.connect() as conn:\n"
            "        r = await conn.execute(text("
            "\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'\"));\n"
            "        print(r.scalar());\n"
            "    await eng.dispose()\n"
            "asyncio.run(run())"
        )
        result = subprocess.run(
            [sys.executable, "-c", check_code],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=45,
            env={**os.environ, "ENVIRONMENT": "production"},
        )
        out = (result.stdout or "").strip()
        try:
            tcount = int(out.splitlines()[-1])
        except Exception:
            tcount = 0
        test(
            "Supabase reachable",
            tcount > 0,
            f"tables={tcount} stderr={result.stderr[:160]}",
        )
    except Exception as e:
        test("Supabase reachable", False, str(e)[:160])

    return _summary()


def _summary() -> int:
    print("\n" + "=" * 60)
    total = len(passed) + len(failed)
    print(f"RESULTS: {len(passed)}/{total} passed")
    if not failed:
        print("ALL SYSTEMS VERIFIED -- DETERMINISTIC AND READY TO DEPLOY")
    else:
        print("FAILED:")
        for f in failed:
            print(f"  - {f}")
    print("=" * 60)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
