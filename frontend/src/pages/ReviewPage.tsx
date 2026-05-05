import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ClipboardCheck, Filter, ChevronRight, User, CheckCircle2 } from "lucide-react";
import { C, SP } from "../styles/tokens";
import { jobsApi, analyzeApi } from "../services/api";
import Badge from "../components/ui/Badge";
import TrustBar from "../components/ui/TrustBar";
import { CardSkeleton } from "../components/ui/Card";
import type { Job } from "../services/types";

interface ReviewItem {
  jobId: string;
  jobTitle: string;
  criterionId: string;
  criterionLabel: string;
  verdict: string;
  explanation: string;
  importance: string;
  score: number;
  escalatedAt: string;
}

function timeAgo(date: string): string {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ReviewPage() {
  const navigate = useNavigate();
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [jobFilter,      setJobFilter]      = useState("all");
  const [assignedOnly,   setAssignedOnly]   = useState(false);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list(0, 100),
  });

  const completedJobs = (jobs as Job[]).filter((j) => j.status === "completed");

  const { data: allItems = [], isLoading: itemsLoading } = useQuery({
    queryKey: ["review-queue", completedJobs.map((j) => j.id).join(",")],
    queryFn: async (): Promise<ReviewItem[]> => {
      const items: ReviewItem[] = [];
      for (const job of completedJobs) {
        try {
          const dash = await analyzeApi.getDashboard(job.id);
          for (const c of dash.criteria) {
            if (c.verdict === "unknown") {
              items.push({
                jobId:          job.id,
                jobTitle:       job.title,
                criterionId:    c.criterion_id,
                criterionLabel: c.label,
                verdict:        c.verdict,
                explanation:    c.explanation,
                importance:     c.importance_level,
                score:          0.5,
                escalatedAt:    job.updated_at,
              });
            }
          }
        } catch { /* skip failed */ }
      }
      return items;
    },
    enabled: completedJobs.length > 0,
    staleTime: 60_000,
  });

  const filtered = allItems.filter((item) => {
    const mp = priorityFilter === "all" ? true
      : priorityFilter === "high"   ? item.importance === "high"
      : priorityFilter === "normal" ? item.importance === "medium"
      : item.importance === "low";
    const mj = jobFilter === "all" || item.jobId === jobFilter;
    return mp && mj;
  });

  type PriorityBadge = "high" | "normal" | "low";
  const priorityVariant = (imp: string): PriorityBadge => {
    if (imp === "high")   return "high";
    if (imp === "medium") return "normal";
    return "low";
  };

  const PRIORITY_FILTERS = [
    { id: "all",    label: "All" },
    { id: "high",   label: "High" },
    { id: "normal", label: "Normal" },
    { id: "low",    label: "Low" },
  ];

  const loading = isLoading || itemsLoading;

  return (
    <div className="fade-in">

      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: SP.xl }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: SP.md, marginBottom: SP.xs }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary }}>Review Queue</h2>
            {allItems.length > 0 && (
              <span style={{
                background: C.failBg, color: C.failText,
                borderRadius: 9999, fontSize: 11, fontWeight: 700,
                padding: "2px 9px",
              }}>
                {allItems.length} pending
              </span>
            )}
          </div>
          <p style={{ fontSize: 13, color: C.textTertiary }}>
            Criteria requiring human review across all active evaluations
          </p>
        </div>

        {/* "Assigned to me" toggle */}
        <label style={{ display: "flex", alignItems: "center", gap: SP.sm, cursor: "pointer", userSelect: "none" }}>
          <div
            onClick={() => setAssignedOnly(v => !v)}
            style={{
              width: 36, height: 20, borderRadius: 10,
              background: assignedOnly ? C.accent : C.bgTertiary,
              border: `1px solid ${assignedOnly ? C.accent : C.borderActive}`,
              position: "relative", cursor: "pointer", transition: "background 0.18s",
              flexShrink: 0,
            }}
          >
            <div style={{
              position: "absolute", top: 2, left: assignedOnly ? 17 : 2,
              width: 14, height: 14, borderRadius: "50%",
              background: "#fff", transition: "left 0.18s",
              boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
            }} />
          </div>
          <User size={13} color={C.textSecondary} />
          <span style={{ fontSize: 13, color: C.textSecondary }}>Assigned to me</span>
        </label>
      </div>

      {/* ── Filter bar ── */}
      <div style={{ display: "flex", gap: SP.sm, marginBottom: SP.xl, alignItems: "center", flexWrap: "wrap" }}>
        <Filter size={13} color={C.textTertiary} />

        <div style={{ display: "flex", gap: SP.xs }}>
          {PRIORITY_FILTERS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setPriorityFilter(id)}
              style={{
                padding: "4px 12px", borderRadius: 6, border: "none", cursor: "pointer",
                fontSize: 12, fontWeight: 500,
                background: priorityFilter === id ? C.accent : C.bgTertiary,
                color: priorityFilter === id ? "#fff" : C.textSecondary,
                transition: "background 0.12s",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: C.borderSubtle }} />

        <select
          value={jobFilter}
          onChange={(e) => setJobFilter(e.target.value)}
          style={{ padding: "5px 10px", borderRadius: 6, fontSize: 12, minWidth: 160 }}
        >
          <option value="all">All Jobs</option>
          {completedJobs.map((j) => (
            <option key={j.id} value={j.id}>{j.title}</option>
          ))}
        </select>

        {filtered.length !== allItems.length && (
          <span style={{ fontSize: 12, color: C.textTertiary, marginLeft: SP.xs }}>
            {filtered.length} of {allItems.length} shown
          </span>
        )}
      </div>

      {/* ── Queue content ── */}
      {loading ? (
        <CardSkeleton lines={8} />
      ) : allItems.length === 0 ? (
        /* All clear */
        <div style={{
          background: C.bgSecondary, border: `1px solid ${C.passSolid}30`,
          borderRadius: 8, padding: `${SP.xl4}px ${SP.xl2}px`,
          textAlign: "center",
        }}>
          <CheckCircle2 size={44} color={C.passSolid} style={{ margin: "0 auto", opacity: 0.7 }} />
          <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary, marginTop: SP.lg, marginBottom: SP.sm }}>
            All cases reviewed
          </div>
          <p style={{ fontSize: 14, color: C.textTertiary, maxWidth: 360, margin: "0 auto" }}>
            No pending review items across all evaluations. Complete new evaluations to populate the queue.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ padding: SP.xl2, textAlign: "center", color: C.textTertiary, fontSize: 14 }}>
          <ClipboardCheck size={32} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
          No items match this filter.
        </div>
      ) : (
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden" }}>
          <table>
            <thead>
              <tr style={{ background: C.bgPrimary }}>
                {["Priority","Criterion","Escalation Reason","Confidence","Job","Escalated","Action"].map((h) => (
                  <th key={h} style={{
                    padding: `${SP.sm}px ${SP.lg}px`,
                    textAlign: "left", fontSize: 11, fontWeight: 600,
                    color: C.textTertiary, textTransform: "uppercase",
                    letterSpacing: "0.05em", whiteSpace: "nowrap",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr
                  key={`${item.jobId}-${item.criterionId}`}
                  style={{ borderBottom: `1px solid ${C.borderSubtle}`, cursor: "pointer" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = C.bgHover)}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                  onClick={() => navigate(`/jobs/${item.jobId}`)}
                >
                  <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                    <Badge variant={priorityVariant(item.importance)} />
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px`, maxWidth: 180 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.criterionLabel}
                    </div>
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px`, maxWidth: 220 }}>
                    <div style={{
                      fontSize: 12, color: C.uncertainText, lineHeight: 1.4,
                      overflow: "hidden", display: "-webkit-box",
                      WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as const,
                    }}>
                      {item.explanation}
                    </div>
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px`, minWidth: 80 }}>
                    <TrustBar value={item.score} showLabel />
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px`, maxWidth: 140 }}>
                    <div style={{ fontSize: 12, color: C.accentText, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.jobTitle}
                    </div>
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 11, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", whiteSpace: "nowrap" }}>
                    {timeAgo(item.escalatedAt)}
                  </td>
                  <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                    <button
                      style={{
                        display: "flex", alignItems: "center", gap: 4,
                        background: "none",
                        border: `1px solid ${C.borderActive}`,
                        borderRadius: 5, padding: "4px 10px",
                        color: C.accentText, cursor: "pointer", fontSize: 12,
                        transition: "border-color 0.12s",
                      }}
                      onClick={(e) => { e.stopPropagation(); navigate(`/jobs/${item.jobId}`); }}
                    >
                      Review <ChevronRight size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
