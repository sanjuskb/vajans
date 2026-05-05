import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Activity, CheckCircle, Clock, Search,
  ChevronRight, FileText,
} from "lucide-react";
import { jobsApi, analyzeApi } from "../services/api";
import { CardSkeleton } from "../components/ui/Card";
import type { Job } from "../services/types";
import { C, SP } from "../styles/tokens";
import { useStore } from "../store/useStore";
import Badge from "../components/ui/Badge";

// ── Metric Card ────────────────────────────────────────────────────────────────
function MetricCard({
  icon, iconColor, iconBg, value, label, subtitle, subtitleColor, numberColor,
}: {
  icon: React.ReactNode;
  iconColor: string;
  iconBg: string;
  value: string | number;
  label: string;
  subtitle?: string;
  subtitleColor?: string;
  numberColor?: string;
}) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--border-subtle)",
      borderRadius: 12,
      padding: "20px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 10,
        background: iconBg,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
        color: iconColor,
      }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 28, fontWeight: 700, lineHeight: 1,
          color: numberColor || C.textPrimary,
        }}>
          {value}
        </div>
        <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>{label}</div>
        {subtitle && (
          <div style={{ fontSize: 12, color: subtitleColor || C.textTertiary, marginTop: 2 }}>
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--border-subtle)",
      borderRadius: 12,
      padding: "20px 24px",
      display: "flex", alignItems: "center", gap: 16,
    }}>
      <div className="skeleton" style={{ width: 48, height: 48, borderRadius: 10, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div className="skeleton" style={{ height: 28, width: "55%", marginBottom: 8, borderRadius: 4 }} />
        <div className="skeleton" style={{ height: 13, width: "80%", borderRadius: 4 }} />
      </div>
    </div>
  );
}

function statusVariant(s: string): any {
  const m: Record<string, string> = {
    completed: "completed", failed: "failed",
    ingesting: "processing", extracting: "processing", evaluating: "processing",
    pending: "pending",
  };
  return m[s] ?? "draft";
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useStore();

  const { data: jobs = [], isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list(0, 100),
    refetchInterval: 30_000,
  });

  const all          = jobs as Job[];
  const activeJobs   = all.filter((j) => ["ingesting", "extracting", "evaluating"].includes(j.status));
  const completedAll = all.filter((j) => j.status === "completed");
  const recentJobs   = [...all].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5);
  const latestCompletedId = completedAll[0]?.id ?? null;

  // Avg processing time for completed jobs (ms → minutes)
  const avgProcMs = completedAll.length > 0
    ? completedAll.reduce((s, j) => s + (new Date(j.updated_at).getTime() - new Date(j.created_at).getTime()), 0) / completedAll.length
    : 0;
  const avgProcMin = Math.floor(avgProcMs / 60000);
  const avgProcSec = Math.floor((avgProcMs % 60000) / 1000);
  const avgProcLabel = avgProcMs > 0 ? `${avgProcMin}m ${avgProcSec}s` : "—";

  // Reviews for latest completed job (for pending reviews count + queue preview)
  const { data: reviewsResp } = useQuery({
    queryKey: ["reviews-dash", latestCompletedId],
    queryFn: () => analyzeApi.getReviews(latestCompletedId!),
    enabled: !!latestCompletedId,
    staleTime: 60_000,
  });

  const { data: criteriaResp } = useQuery({
    queryKey: ["criteria-dash", latestCompletedId],
    queryFn: () => analyzeApi.getCriteria(latestCompletedId!),
    enabled: !!latestCompletedId,
    staleTime: 120_000,
  });

  const reviews = reviewsResp?.data ?? [];
  // Pending reviews = criteria that need review (verdict unknown) with no existing review action
  const reviewedIds = new Set(reviews.map((r: any) => r.criterion_id));
  const allCriteriaData = criteriaResp?.data ?? [];
  const pendingReviewItems = allCriteriaData
    .filter((c: any) => c.verdict === "unknown" && !reviewedIds.has(c.criterion_id))
    .slice(0, 5);
  const pendingReviewCount = pendingReviewItems.length;

  if (jobsLoading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: SP.xl }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: SP.md }}>
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <CardSkeleton lines={6} />
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: SP.xl }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: SP.md }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: C.textPrimary, margin: 0 }}>
            Dashboard
          </h1>
          <div style={{ fontSize: 13, color: C.textSecondary, marginTop: 4 }}>
            Overview of tender evaluation status
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: "50%",
            background: "#7C3AED",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 700, color: "#fff", flexShrink: 0,
          }}>
            {user?.username ? user.username.slice(0, 2).toUpperCase() : "PO"}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, lineHeight: 1.3 }}>
              {user?.username ?? "Procurement Officer"}
            </div>
            <div style={{ fontSize: 11, color: C.textTertiary }}>
              {user?.role ? user.role.charAt(0).toUpperCase() + user.role.slice(1) : "Officer"}
            </div>
          </div>
        </div>
      </div>

      {/* ── 4 Metric Cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: SP.md }}>
        <MetricCard
          icon={<Activity size={20} />}
          iconColor="#3B82F6" iconBg="rgba(59,130,246,0.15)"
          value={activeJobs.length}
          label="Active Jobs"
          subtitle={activeJobs.length > 0 ? "Pipeline running" : "No active pipelines"}
          subtitleColor={activeJobs.length > 0 ? "#3B82F6" : C.textTertiary}
          numberColor={activeJobs.length > 0 ? "#3B82F6" : C.textPrimary}
        />
        <MetricCard
          icon={<CheckCircle size={20} />}
          iconColor="#059669" iconBg="rgba(5,150,105,0.15)"
          value={completedAll.length}
          label="Completed"
          subtitle={completedAll.length > 0 ? "Evaluations done" : "No completed jobs yet"}
          subtitleColor="#059669"
        />
        <MetricCard
          icon={<Search size={20} />}
          iconColor="#D97706" iconBg="rgba(217,119,6,0.15)"
          value={pendingReviewCount}
          label="Pending Reviews"
          subtitle={pendingReviewCount > 0 ? "Requires human review" : "All clear"}
          subtitleColor={pendingReviewCount > 0 ? "#D97706" : "#059669"}
          numberColor={pendingReviewCount > 0 ? "#D97706" : C.textPrimary}
        />
        <MetricCard
          icon={<Clock size={20} />}
          iconColor="#7C3AED" iconBg="rgba(124,58,237,0.15)"
          value={avgProcLabel}
          label="Avg Processing Time"
          subtitle={completedAll.length > 0 ? `Based on ${completedAll.length} jobs` : "No data yet"}
          subtitleColor={C.textTertiary}
        />
      </div>

      {/* ── Recent Jobs Table ── */}
      <div style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 12,
        overflow: "hidden",
      }}>
        <div style={{
          padding: "16px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary }}>
            Recent Jobs
          </div>
          <button
            onClick={() => navigate("/jobs")}
            style={{
              background: "none",
              border: "1px solid var(--border-subtle)",
              borderRadius: 6, color: C.accentText,
              cursor: "pointer", fontSize: 12,
              padding: "5px 12px",
            }}
          >
            View All →
          </button>
        </div>

        {recentJobs.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: C.textTertiary, fontSize: 13 }}>
            <FileText size={32} color={C.textTertiary} style={{ marginBottom: 8 }} />
            <div>No jobs yet. <button onClick={() => navigate("/jobs?new=true")} style={{ background: "none", border: "none", color: C.accentText, cursor: "pointer", fontSize: 13 }}>Create your first evaluation →</button></div>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--table-header)", borderBottom: "2px solid var(--border-subtle)" }}>
                {["Job Title", "Status", "Created", "Action"].map((h) => (
                  <th key={h} style={{
                    padding: "12px 16px", textAlign: "left",
                    fontSize: 11, fontWeight: 700, color: C.textTertiary,
                    textTransform: "uppercase", letterSpacing: "0.05em",
                    whiteSpace: "nowrap",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentJobs.map((job) => (
                <tr
                  key={job.id}
                  style={{ background: "var(--table-row)", borderBottom: "1px solid var(--border-subtle)", cursor: "pointer" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--table-row-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "var(--table-row)")}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                >
                  <td style={{ padding: "14px 16px" }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>
                      {job.title}
                    </div>
                    <div style={{ fontSize: 11, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>
                      {job.id.slice(0, 8)}…
                    </div>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <Badge variant={statusVariant(job.status)} dot />
                  </td>
                  <td style={{ padding: "14px 16px", fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                    {new Date(job.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/jobs/${job.id}`); }}
                      style={{
                        background: "none", border: "1px solid var(--border-subtle)",
                        borderRadius: 6, color: C.accentText,
                        cursor: "pointer", fontSize: 12, padding: "4px 10px",
                        display: "flex", alignItems: "center", gap: 4,
                      }}
                    >
                      View <ChevronRight size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Review Queue Preview ── */}
      <div style={{
        background: "var(--card-bg)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 12,
        overflow: "hidden",
      }}>
        <div style={{
          padding: "16px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary }}>
            Review Queue
          </div>
          {latestCompletedId && (
            <button
              onClick={() => navigate(`/jobs/${latestCompletedId}`)}
              style={{
                background: "none",
                border: "1px solid var(--border-subtle)",
                borderRadius: 6, color: C.accentText,
                cursor: "pointer", fontSize: 12,
                padding: "5px 12px",
              }}
            >
              View Details →
            </button>
          )}
        </div>

        {pendingReviewItems.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: C.textTertiary, fontSize: 13 }}>
            <CheckCircle size={28} color="#059669" style={{ marginBottom: 8 }} />
            <div style={{ color: "#059669", fontWeight: 600 }}>All clear — no pending reviews</div>
            <div style={{ marginTop: 4, color: C.textTertiary, fontSize: 12 }}>
              {completedAll.length === 0 ? "Run a pipeline to see reviews" : "All criteria have been resolved"}
            </div>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--table-header)", borderBottom: "2px solid var(--border-subtle)" }}>
                {["Criterion", "Escalation Reason", "Job", "Action"].map((h) => (
                  <th key={h} style={{
                    padding: "12px 16px", textAlign: "left",
                    fontSize: 11, fontWeight: 700, color: C.textTertiary,
                    textTransform: "uppercase", letterSpacing: "0.05em",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pendingReviewItems.map((c: any, i: number) => (
                <tr
                  key={`${c.criterion_id}_${i}`}
                  style={{ background: "var(--table-row)", borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td style={{ padding: "12px 16px", fontSize: 13, color: C.textPrimary, fontWeight: 500 }}>
                    {c.label || c.criterion_id}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: "#FCD34D", background: "#451A03",
                      padding: "2px 8px", borderRadius: 4,
                    }}>
                      Low AI confidence — review required
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 12, color: C.textTertiary }}>
                    {completedAll[0]?.title?.slice(0, 30) ?? "—"}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    {latestCompletedId && (
                      <button
                        onClick={() => navigate(`/jobs/${latestCompletedId}`)}
                        style={{
                          background: "none", border: "1px solid #D97706",
                          borderRadius: 6, color: "#FCD34D",
                          cursor: "pointer", fontSize: 12, padding: "4px 10px",
                        }}
                      >
                        Review →
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}
