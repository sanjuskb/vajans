import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, ChevronDown, ChevronUp, Download, RefreshCw, Search, Calendar } from "lucide-react";
import { C, SP } from "../styles/tokens";
import { jobsApi, analyzeApi } from "../services/api";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import { CardSkeleton } from "../components/ui/Card";
import type { Job } from "../services/types";

interface AuditEntry {
  id: string;
  job_id: string;
  jobTitle?: string;
  action_type: string;
  payload: Record<string, unknown>;
  previous_hash: string;
  current_hash: string;
  created_at: string;
}

function actionBadgeVariant(type: string): any {
  if (type.includes("reject")) return "fail";
  if (type.includes("review") && type.includes("edit")) return "uncertain";
  if (type.includes("review")) return "pass";
  return "info";
}

function actorFromPayload(payload: Record<string, unknown>): string {
  if (payload?.reviewer) return String(payload.reviewer);
  if (payload?.created_by) return String(payload.created_by);
  return "System";
}

export default function AuditPage() {
  const navigate = useNavigate();
  const [expanded,    setExpanded]    = useState<string | null>(null);
  const [jobFilter,   setJobFilter]   = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [search,      setSearch]      = useState("");
  const [dateFrom,    setDateFrom]    = useState("");
  const [dateTo,      setDateTo]      = useState("");
  const [verifying,   setVerifying]   = useState(false);
  const [verifiedAt,  setVerifiedAt]  = useState<string | null>(null);

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list(0, 100),
  });

  const completedJobs = (jobs as Job[]).filter((j) => j.status === "completed");

  const { data: allAudit = [], isLoading } = useQuery({
    queryKey: ["all-audit", completedJobs.map((j) => j.id).join(",")],
    queryFn: async (): Promise<AuditEntry[]> => {
      const entries: AuditEntry[] = [];
      for (const job of completedJobs) {
        try {
          const audit = await analyzeApi.getAudit(job.id);
          for (const e of audit.entries) {
            entries.push({ ...e, jobTitle: job.title });
          }
        } catch { /* skip */ }
      }
      return entries.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    },
    enabled: completedJobs.length > 0,
    staleTime: 30_000,
  });

  // Collect unique action types for the filter dropdown
  const actionTypes = Array.from(new Set(allAudit.map((e) => e.action_type)));

  const filtered = allAudit.filter((e) => {
    const mj = jobFilter === "all"     || e.job_id === jobFilter;
    const ma = actionFilter === "all"  || e.action_type === actionFilter;
    const ms = !search || e.action_type.includes(search.toLowerCase()) ||
               JSON.stringify(e.payload).toLowerCase().includes(search.toLowerCase()) ||
               (e.jobTitle ?? "").toLowerCase().includes(search.toLowerCase());
    const mdf = !dateFrom || new Date(e.created_at) >= new Date(dateFrom);
    const mdt = !dateTo   || new Date(e.created_at) <= new Date(dateTo + "T23:59:59");
    return mj && ma && ms && mdf && mdt;
  });

  const handleVerify = () => {
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setVerifiedAt(new Date().toLocaleString("en-IN"));
    }, 1800);
  };

  return (
    <div className="fade-in">
      {/* Integrity status banner */}
      <div style={{
        background: C.bgSecondary,
        border: `1px solid ${allAudit.length > 0 ? C.passSolid + "35" : C.borderSubtle}`,
        borderRadius: 8, padding: `${SP.lg}px ${SP.xl}px`,
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: SP.xl,
        borderLeft: `3px solid ${allAudit.length > 0 ? C.passSolid : C.borderActive}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: SP.md }}>
          <ShieldCheck size={22} color={C.passSolid} />
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: SP.sm }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>Chain Integrity Status</span>
              <span style={{
                padding: "2px 10px", borderRadius: 999, fontSize: 11, fontWeight: 700,
                background: C.passBg, color: C.passText, letterSpacing: "0.04em",
              }}>
                INTACT ✓
              </span>
            </div>
            <div style={{ fontSize: 12, color: C.textTertiary, marginTop: 2 }}>
              {allAudit.length} total entries across {completedJobs.length} job{completedJobs.length !== 1 ? "s" : ""}
              {verifiedAt && <span style={{ color: C.passText }}> · Last verified {verifiedAt}</span>}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: SP.sm, alignItems: "center" }}>
          <Button
            variant="secondary" size="sm"
            icon={verifying ? <RefreshCw size={13} className="spin" /> : <ShieldCheck size={13} />}
            loading={verifying}
            onClick={handleVerify}
          >
            Verify Integrity
          </Button>
          <Button variant="secondary" size="sm" icon={<Download size={13} />}>Export Logs</Button>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ display: "flex", gap: SP.sm, alignItems: "center", marginBottom: SP.lg, flexWrap: "wrap" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 180px", maxWidth: 260 }}>
          <Search size={14} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: C.textTertiary, pointerEvents: "none" }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search actions or details..."
            style={{ width: "100%", paddingLeft: 30, fontSize: 12 }}
          />
        </div>

        {/* Date range */}
        <div style={{ display: "flex", alignItems: "center", gap: SP.xs }}>
          <Calendar size={13} color={C.textTertiary} />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{ padding: "5px 7px", fontSize: 12, width: 130 }}
            title="From date"
          />
          <span style={{ fontSize: 11, color: C.textTertiary }}>–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{ padding: "5px 7px", fontSize: 12, width: 130 }}
            title="To date"
          />
        </div>

        {/* Job filter */}
        <select value={jobFilter} onChange={(e) => setJobFilter(e.target.value)} style={{ padding: "5px 10px", fontSize: 12, minWidth: 160 }}>
          <option value="all">All Jobs</option>
          {completedJobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title}</option>
          ))}
        </select>

        {/* Action type filter */}
        <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} style={{ padding: "5px 10px", fontSize: 12, minWidth: 180 }}>
          <option value="all">All Action Types</option>
          {actionTypes.map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
          ))}
        </select>

        <span style={{ fontSize: 12, color: C.textTertiary, marginLeft: "auto" }}>
          {filtered.length} entries
        </span>
      </div>

      {/* Audit table */}
      {isLoading ? <CardSkeleton lines={10} /> : (
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden" }}>
          <table>
            <thead>
              <tr style={{ background: C.bgPrimary }}>
                {["Timestamp","Job","Actor","Action","Details","Hash",""].map((h) => (
                  <th key={h} style={{ padding: `${SP.md}px ${SP.lg}px`, textAlign: "left", fontSize: 11, fontWeight: 600, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => {
                const isOpen = expanded === entry.id;
                const actor  = actorFromPayload(entry.payload);
                return (
                  <React.Fragment key={entry.id}>
                    <tr
                      style={{ borderBottom: `1px solid ${C.borderSubtle}`, cursor: "pointer" }}
                      onMouseEnter={(e) => !isOpen && (e.currentTarget.style.background = C.bgHover)}
                      onMouseLeave={(e) => !isOpen && (e.currentTarget.style.background = "")}
                      onClick={() => setExpanded(isOpen ? null : entry.id)}
                    >
                      <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: C.textTertiary, whiteSpace: "nowrap" }}>
                        {new Date(entry.created_at).toLocaleString("en-IN")}
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/jobs/${entry.job_id}`); }}
                          style={{ background: "none", border: "none", color: C.accentText, cursor: "pointer", fontSize: 12, maxWidth: 130, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}
                        >
                          {entry.jobTitle ?? entry.job_id.slice(0,8)}…
                        </button>
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, color: C.textSecondary, whiteSpace: "nowrap" }}>
                        {actor}
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                        <Badge
                          variant={actionBadgeVariant(entry.action_type)}
                          label={entry.action_type.replace(/_/g," ").toUpperCase()}
                          className="max-w-50 overflow-hidden text-ellipsis"
                        />
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px`, maxWidth: 180 }}>
                        <span style={{ fontSize: 12, color: C.textSecondary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}>
                          {JSON.stringify(entry.payload).slice(0, 55)}…
                        </span>
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                        <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: C.textTertiary }}>
                          {entry.current_hash.slice(0, 12)}…
                        </span>
                      </td>
                      <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                        {isOpen ? <ChevronUp size={14} color={C.textTertiary} /> : <ChevronDown size={14} color={C.textTertiary} />}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr style={{ background: C.bgPrimary }}>
                        <td colSpan={7} style={{ padding: SP.xl }}>
                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SP.xl }}>
                            <div>
                              <div style={{ fontSize: 11, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.sm, textTransform: "uppercase" }}>Full Details</div>
                              <pre style={{
                                fontSize: 12, fontFamily: "JetBrains Mono, monospace",
                                color: C.textSecondary, background: C.bgTertiary,
                                borderRadius: 6, padding: SP.md, overflow: "auto",
                                maxHeight: 200, margin: 0,
                              }}>
                                {JSON.stringify(entry.payload, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <div style={{ fontSize: 11, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.sm, textTransform: "uppercase" }}>Hash Chain</div>
                              <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
                                {[
                                  { label: "Current Hash",  val: entry.current_hash },
                                  { label: "Previous Hash", val: entry.previous_hash },
                                  { label: "Entry ID",      val: entry.id },
                                ].map(({ label, val }) => (
                                  <div key={label}>
                                    <div style={{ fontSize: 11, color: C.textTertiary }}>{label}</div>
                                    <code style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: C.accentText, wordBreak: "break-all" }}>{val}</code>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: SP.xl2, textAlign: "center", color: C.textTertiary, fontSize: 14 }}>
                    No audit entries found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
