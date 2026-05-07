"""Inspect the most recent prod-sim job (use correct DB column names)."""
import sys, requests

BASE = "http://localhost:8000/api/v1"


def login():
    r = requests.post(f"{BASE}/auth/login",
                      json={"username": "officer", "password": "vajans2024"},
                      timeout=10)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main():
    h = login()
    jobs = requests.get(f"{BASE}/jobs/", headers=h, timeout=15).json()
    if isinstance(jobs, dict):
        jobs = jobs.get("data") or []
    sim_jobs = [j for j in jobs if str(j.get("title", "")).startswith("prod-sim-run1")]
    sim_jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    if not sim_jobs:
        print("no prod-sim jobs found")
        return 1
    job_id = sim_jobs[0]["id"]
    print(f"Inspecting job {job_id} ({sim_jobs[0]['title']})")

    crit = requests.get(f"{BASE}/analyze/{job_id}/criteria", headers=h, timeout=15).json()
    print(f"\n=== TENDER CRITERIA ({crit.get('total')}) ===")
    for c in (crit.get("data") or []):
        print(f"  {c.get('criterion_key'):30s}  type={c.get('criterion_type'):14s}  "
              f"mandatory={c.get('mandatory'):<5}  thr={c.get('threshold_value')} "
              f"{c.get('threshold_unit') or ''} op={c.get('operator')}")

    files = requests.get(f"{BASE}/files/job/{job_id}", headers=h, timeout=15).json()
    if isinstance(files, dict):
        files = files.get("data") or []
    fid_to_name = {str(f["id"]): f["original_name"] for f in files}
    cid_to_key  = {str(c["id"]): c["criterion_key"] for c in (crit.get("data") or [])}

    ext = requests.get(f"{BASE}/analyze/{job_id}/extractions", headers=h, timeout=20).json()
    rows = ext.get("data") or []

    print("\n=== EXTRACTIONS PER BIDDER ===")
    by_bidder = {}
    for r in rows:
        nm = fid_to_name.get(str(r.get("file_id")), "?")
        by_bidder.setdefault(nm, []).append(r)
    for nm in sorted(by_bidder):
        print(f"\n  {nm}")
        for r in by_bidder[nm]:
            ck = cid_to_key.get(str(r.get("criterion_id")), "?")
            pv = r.get("parsed_value")
            cn = r.get("extraction_confidence")
            nf = r.get("not_found")
            sn = (r.get("source_snippet") or "").strip().replace("\n", " ")
            page = r.get("page_number")
            print(f"    {ck:30s}  conf={cn}  not_found={nf}  page={page}")
            print(f"      parsed={pv!r}")
            if sn:
                print(f"      snip[:140]={sn[:140]!r}")

    ev = requests.get(f"{BASE}/analyze/{job_id}/evaluation", headers=h, timeout=15).json()
    print("\n=== EVALUATION SUMMARIES ===")
    for b in ev.get("bidders") or []:
        print(f"\n  {b.get('bidder_name')}: {b.get('final_status')} "
              f"score={b.get('final_score'):.3f}")
        print(f"    summary: {b.get('summary')}")
        print(f"    disq:   {b.get('disqualification_reasons')}")
        for r in b.get("results") or []:
            print(f"    {r.get('verdict'):8s}  {(r.get('explanation') or '')[:130]}  "
                  f"score={r.get('score')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
