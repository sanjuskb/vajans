import React, { useMemo, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Activity, CheckCircle, Clock, Search,
  ChevronRight, FileText, BarChart2, PieChart,
} from "lucide-react";
import { jobsApi, analyzeApi, analyticsApi } from "../services/api";
import { CardSkeleton } from "../components/ui/Card";
import type { Job, TimelinePoint, VerdictBucket } from "../services/types";
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

// ---------------------------------------------------------------------------
// AreaChart — Evaluations Over Time
// ---------------------------------------------------------------------------

const CHART_W = 480;
const CHART_H = 140;
const PAD = { top: 16, right: 16, bottom: 32, left: 40 };

function niceMax(v: number): number {
  if (v === 0) return 5;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  return Math.ceil(v / mag) * mag;
}

function AreaChart({ points }: { points: TimelinePoint[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const maxY = useMemo(() => niceMax(Math.max(...points.map((p) => p.count))), [points]);

  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;
  const n = points.length;

  const xOf = (i: number) => n < 2 ? innerW / 2 : (i / (n - 1)) * innerW;
  const yOf = (v: number) => innerH - (v / maxY) * innerH;

  // Smooth cubic bezier area path
  const linePts = points.map((p, i) => ({ x: xOf(i), y: yOf(p.count) }));

  function smoothPath(pts: { x: number; y: number }[]): string {
    if (pts.length === 0) return "";
    if (pts.length === 1) return `M ${pts[0].x} ${pts[0].y}`;
    let d = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const cp1x = pts[i].x + (pts[i + 1].x - pts[i].x) * 0.45;
      const cp1y = pts[i].y;
      const cp2x = pts[i + 1].x - (pts[i + 1].x - pts[i].x) * 0.45;
      const cp2y = pts[i + 1].y;
      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${pts[i + 1].x} ${pts[i + 1].y}`;
    }
    return d;
  }

  const linePath = smoothPath(linePts);
  const areaPath = linePts.length
    ? `${linePath} L ${linePts[linePts.length - 1].x} ${innerH} L ${linePts[0].x} ${innerH} Z`
    : "";

  const yTicks = [0, Math.round(maxY / 2), maxY];

  const formatDay = (iso: string) => {
    const d = new Date(iso + "T00:00:00Z");
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "UTC" });
  };

  const isEmpty = points.every((p) => p.count === 0);

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGRectElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const step = innerW / (n - 1);
    const idx = Math.max(0, Math.min(n - 1, Math.round(relX / step)));
    setHoverIdx(idx);
  }, [n, innerW]);

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        style={{ width: "100%", overflow: "visible" }}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="#3B82F6" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {/* Horizontal grid lines */}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={0} y1={yOf(tick)} x2={innerW} y2={yOf(tick)}
                stroke="rgba(255,255,255,0.06)" strokeWidth={1}
              />
              <text
                x={-6} y={yOf(tick) + 4}
                fill="rgba(255,255,255,0.35)" fontSize={10}
                textAnchor="end" fontFamily="JetBrains Mono, monospace"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* Area fill */}
          {!isEmpty && <path d={areaPath} fill="url(#areaGrad)" />}

          {/* Line */}
          {!isEmpty && (
            <path d={linePath} fill="none" stroke="#3B82F6" strokeWidth={2} strokeLinejoin="round" />
          )}

          {/* Data point dots */}
          {linePts.map((pt, i) => (
            <circle
              key={i}
              cx={pt.x} cy={pt.y} r={hoverIdx === i ? 4 : 2.5}
              fill={hoverIdx === i ? "#fff" : "#3B82F6"}
              stroke={hoverIdx === i ? "#3B82F6" : "none"}
              strokeWidth={hoverIdx === i ? 2 : 0}
              style={{ transition: "r 0.1s" }}
            />
          ))}

          {/* Hover crosshair */}
          {hoverIdx !== null && (
            <line
              x1={linePts[hoverIdx].x} y1={0}
              x2={linePts[hoverIdx].x} y2={innerH}
              stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="3 3"
            />
          )}

          {/* X-axis labels */}
          {points.map((p, i) => {
            const showEvery = n <= 7 ? 1 : n <= 14 ? 2 : 3;
            if (i % showEvery !== 0 && i !== n - 1) return null;
            return (
              <text
                key={i}
                x={xOf(i)} y={innerH + 18}
                fill={hoverIdx === i ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.35)"}
                fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
              >
                {formatDay(p.date)}
              </text>
            );
          })}

          {/* Invisible interaction overlay */}
          <rect
            x={0} y={0} width={innerW} height={innerH}
            fill="transparent"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIdx(null)}
          />
        </g>
      </svg>

      {/* Tooltip */}
      {hoverIdx !== null && (
        <div style={{
          position: "absolute",
          top: 0,
          left: `calc(${(PAD.left + (hoverIdx / (n - 1)) * (CHART_W - PAD.left - PAD.right)) / CHART_W * 100}% + 8px)`,
          pointerEvents: "none",
          background: "rgba(15,23,42,0.95)",
          border: "1px solid rgba(59,130,246,0.4)",
          borderRadius: 6,
          padding: "6px 10px",
          fontSize: 12,
          color: C.textPrimary,
          whiteSpace: "nowrap",
          zIndex: 10,
          boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
        }}>
          <div style={{ fontWeight: 600, color: "#3B82F6" }}>{points[hoverIdx].count} evaluations</div>
          <div style={{ color: C.textTertiary, marginTop: 2, fontSize: 11 }}>
            {formatDay(points[hoverIdx].date)}
          </div>
        </div>
      )}

      {/* Empty state overlay */}
      {isEmpty && (
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          pointerEvents: "none",
          gap: 6,
        }}>
          <BarChart2 size={28} color="rgba(255,255,255,0.12)" />
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)" }}>No evaluations yet</div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DonutChart — Verdict Distribution
// ---------------------------------------------------------------------------

const DONUT_R = 52;
const DONUT_SW = 22;
const DONUT_SIZE = (DONUT_R + DONUT_SW) * 2 + 8;
const CX = DONUT_SIZE / 2;
const CIRC = 2 * Math.PI * DONUT_R;

function DonutChart({ total, buckets }: { total: number; buckets: VerdictBucket[] }) {
  const [hoverId, setHoverId] = useState<string | null>(null);

  // Compute arcs: offset builds up as we go
  const arcs = useMemo(() => {
    let offset = 0; // starts at top (rotated -90deg via transform)
    return buckets.map((b) => {
      const frac = total > 0 ? b.count / total : 0;
      const dash = frac * CIRC;
      const gap  = CIRC - dash;
      const thisOffset = offset;
      offset += dash;
      return { ...b, dash, gap, offset: thisOffset, frac };
    });
  }, [buckets, total]);

  const hovered = hoverId ? buckets.find((b) => b.verdict === hoverId) : null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 28, flexWrap: "wrap" }}>
      {/* SVG donut */}
      <div style={{ position: "relative", flexShrink: 0 }}>
        <svg width={DONUT_SIZE} height={DONUT_SIZE}>
          {/* Track ring */}
          <circle
            cx={CX} cy={CX} r={DONUT_R}
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={DONUT_SW}
          />
          {/* Segments */}
          {total === 0 ? (
            <circle
              cx={CX} cy={CX} r={DONUT_R}
              fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={DONUT_SW}
              strokeDasharray={`${CIRC * 0.98} ${CIRC * 0.02}`}
              strokeDashoffset={CIRC * 0.25}
            />
          ) : (
            arcs.map((arc) => (
              <circle
                key={arc.verdict}
                cx={CX} cy={CX} r={DONUT_R}
                fill="none"
                stroke={arc.color}
                strokeWidth={hoverId === arc.verdict ? DONUT_SW + 4 : DONUT_SW}
                strokeDasharray={`${arc.dash - 2} ${arc.gap + 2}`}
                strokeDashoffset={CIRC * 0.25 - arc.offset}
                strokeLinecap="round"
                style={{ cursor: "pointer", transition: "stroke-width 0.15s" }}
                onMouseEnter={() => setHoverId(arc.verdict)}
                onMouseLeave={() => setHoverId(null)}
              />
            ))
          )}
        </svg>
        {/* Centre label */}
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          pointerEvents: "none",
        }}>
          {hovered ? (
            <>
              <div style={{ fontSize: 20, fontWeight: 700, color: hovered.color, lineHeight: 1 }}>
                {hovered.count}
              </div>
              <div style={{ fontSize: 10, color: C.textTertiary, marginTop: 3, textAlign: "center", maxWidth: 64 }}>
                {hovered.label}
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 22, fontWeight: 800, color: C.textPrimary, lineHeight: 1 }}>
                {total}
              </div>
              <div style={{ fontSize: 10, color: C.textTertiary, marginTop: 3 }}>total</div>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div style={{ flex: 1, minWidth: 120, display: "flex", flexDirection: "column", gap: 12 }}>
        {total === 0 ? (
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", display: "flex", flexDirection: "column", alignItems: "center", gap: 6, padding: "12px 0" }}>
            <PieChart size={24} color="rgba(255,255,255,0.12)" />
            <span>No evaluations yet</span>
          </div>
        ) : (
          buckets.map((b) => {
            const pct = total > 0 ? Math.round((b.count / total) * 100) : 0;
            return (
              <div
                key={b.verdict}
                style={{
                  display: "flex", alignItems: "center", gap: 10, cursor: "default",
                  opacity: hoverId && hoverId !== b.verdict ? 0.45 : 1,
                  transition: "opacity 0.15s",
                }}
                onMouseEnter={() => setHoverId(b.verdict)}
                onMouseLeave={() => setHoverId(null)}
              >
                <div style={{
                  width: 10, height: 10, borderRadius: 2, background: b.color, flexShrink: 0,
                }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>
                    {b.label}
                  </div>
                  <div style={{ fontSize: 11, color: C.textTertiary }}>
                    {b.count} · {pct}%
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
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

  // ── Analytics queries (independent of any specific job) ──────────────────
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ["analytics-timeline"],
    queryFn: () => analyticsApi.getTimeline(7),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  const { data: verdicts, isLoading: verdictsLoading } = useQuery({
    queryKey: ["analytics-verdicts"],
    queryFn: () => analyticsApi.getVerdicts(),
    staleTime: 60_000,
    refetchInterval: 120_000,
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

      {/* ── Review Queue preview ── */}
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
                      color: C.uncertainText, background: C.uncertainBg,
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
                          background: "none", border: `1px solid ${C.uncertainSolid}`,
                          borderRadius: 6, color: C.uncertainText,
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

      {/* ── Analytics: 2-column grid ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SP.md }}>

        {/* Graph 1 — Evaluations Over Time */}
        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--border-subtle)",
          borderRadius: 12,
          padding: "20px 24px",
        }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>Evaluations Over Time</div>
              <div style={{ fontSize: 11, color: C.textTertiary, marginTop: 3 }}>Criterion evaluations · last 7 days</div>
            </div>
            <BarChart2 size={16} color={C.textTertiary} style={{ marginTop: 2 }} />
          </div>
          {timelineLoading ? (
            <div className="skeleton" style={{ height: CHART_H, borderRadius: 6 }} />
          ) : (
            <AreaChart points={timeline?.points ?? []} />
          )}
        </div>

        {/* Graph 2 — Verdict Distribution */}
        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--border-subtle)",
          borderRadius: 12,
          padding: "20px 24px",
        }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>Verdict Distribution</div>
              <div style={{ fontSize: 11, color: C.textTertiary, marginTop: 3 }}>Criterion-level outcomes · all evaluations</div>
            </div>
            <PieChart size={16} color={C.textTertiary} style={{ marginTop: 2 }} />
          </div>
          {verdictsLoading ? (
            <div className="skeleton" style={{ height: CHART_H + 20, borderRadius: 6 }} />
          ) : (
            <DonutChart
              total={verdicts?.total ?? 0}
              buckets={verdicts?.buckets ?? []}
            />
          )}
        </div>

      </div>

    </div>
  );
}
