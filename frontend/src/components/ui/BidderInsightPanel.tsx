import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  Cell, PieChart, Pie, CartesianGrid, ReferenceLine,
} from "recharts";
import { X, CheckCircle2, XCircle } from "lucide-react";
import { analyzeApi } from "../../services/api";
import type { EvalResultRow } from "../../services/types";

// ── Chart card style ──────────────────────────────────────────────────────────

const CHART_CARD: React.CSSProperties = {
  background: "#111827",
  border: "1px solid #1E2A3B",
  borderRadius: 12,
  padding: 20,
  overflow: "hidden",
  width: "100%",
  boxSizing: "border-box",
};

// ── Main Component ────────────────────────────────────────────────────────────

interface Props {
  jobId:        string;
  bidderFileId: string | null;
  bidderName:   string;
  onClose:      () => void;
}

export default function BidderInsightPanel({ jobId, bidderFileId, bidderName, onClose }: Props) {
  const [activeSection, setActiveSection] = useState("overview");

  // ── Data fetching ────────────────────────────────────────────────────────────

  const { data: evalData, isLoading: evalLoading } = useQuery({
    queryKey: ["evaluation", jobId],
    queryFn: () => analyzeApi.getEvaluation(jobId),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  const { data: comparisonData } = useQuery({
    queryKey: ["comparison", jobId],
    queryFn: () => analyzeApi.getComparison(jobId),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  const { data: criteriaResp } = useQuery({
    queryKey: ["criteria", jobId],
    queryFn: () => analyzeApi.getCriteria(jobId),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  // ── Derived data ─────────────────────────────────────────────────────────────

  const detailMap = useMemo(
    () => Object.fromEntries((criteriaResp?.data ?? []).map((c) => [c.id, c])),
    [criteriaResp]
  );

  const thisBidder = useMemo(() => {
    if (!evalData?.bidders?.length) return null;
    if (bidderFileId) {
      const byId = evalData.bidders.find((b) => b.bidder_file_id === bidderFileId);
      if (byId) return byId;
    }
    return evalData.bidders.find((b) =>
      b.bidder_name === bidderName ||
      b.bidder_name.toLowerCase().includes(bidderName.toLowerCase()) ||
      bidderName.toLowerCase().includes(b.bidder_name.toLowerCase())
    ) ?? null;
  }, [evalData, bidderFileId, bidderName]);

  const thisResults: EvalResultRow[] = useMemo(() => {
    if (thisBidder?.results?.length) return thisBidder.results;
    if (!evalData?.results) return [];
    if (bidderFileId) return evalData.results.filter((r) => r.bidder_file_id === bidderFileId);
    return [];
  }, [thisBidder, evalData, bidderFileId]);

  const getAvg = (type: string) => {
    const rows = thisResults.filter(
      (r) => detailMap[r.criterion_id]?.criterion_type?.toLowerCase() === type
    );
    if (!rows.length) return 0;
    return Math.round(rows.reduce((s, r) => s + r.score * 100, 0) / rows.length);
  };

  const scores = useMemo(() => ({
    financial:     getAvg("financial"),
    technical:     getAvg("technical"),
    compliance:    getAvg("compliance"),
    certification: getAvg("certification"),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [thisResults, detailMap]);

  const passCount   = useMemo(() => thisResults.filter((r) => r.verdict === "pass").length,    [thisResults]);
  const failCount   = useMemo(() => thisResults.filter((r) => r.verdict === "fail").length,    [thisResults]);
  const reviewCount = useMemo(() => thisResults.filter((r) => r.verdict === "unknown").length, [thisResults]);
  const totalCount  = thisResults.length;
  const avgConf     = totalCount ? Math.round(thisResults.reduce((s, r) => s + r.score, 0) / totalCount * 100) : 0;

  const radarData = [
    { subject: "Financial",     score: scores.financial     },
    { subject: "Technical",     score: scores.technical     },
    { subject: "Compliance",    score: scores.compliance    },
    { subject: "Certification", score: scores.certification },
  ];

  const trustDist = useMemo(() => [
    { name: "High ≥85%",     value: thisResults.filter((r) => r.score >= 0.85).length,                  color: "#059669" },
    { name: "Medium 60–85%", value: thisResults.filter((r) => r.score >= 0.6 && r.score < 0.85).length, color: "#3B82F6" },
    { name: "Low <60%",      value: thisResults.filter((r) => r.score < 0.6).length,                     color: "#D97706" },
  ].filter((d) => d.value > 0), [thisResults]);

  const isQualified = failCount === 0 && totalCount > 0;

  const compBarData = useMemo(() => {
    const bidders = evalData?.bidders ?? [];
    if (bidders.length) {
      return bidders.map((b) => ({
        name:   b.bidder_name.replace(/\.(pdf|docx?)$/i, "").slice(0, 12),
        score:  Math.round(b.final_score * 100),
        isThis: b.bidder_file_id === bidderFileId || b.bidder_name === bidderName,
      }));
    }
    return (comparisonData?.bidders ?? []).map((b) => ({
      name:   b.bidder_name.replace(/\.(pdf|docx?)$/i, "").slice(0, 12),
      score:  Math.round(b.total_score * 100),
      isThis: b.bidder_name === bidderName,
    }));
  }, [evalData, comparisonData, bidderFileId, bidderName]);

  const criteriaBarData = useMemo(() =>
    thisResults.map((r) => ({
      label:   ((detailMap[r.criterion_id]?.label ?? r.criterion_id) as string).slice(0, 30),
      score:   Math.round(r.score * 100),
      verdict: r.verdict as string,
    })),
    [thisResults, detailMap]
  );

  const catCards = useMemo(() => {
    const cats = ["financial", "technical", "compliance", "certification"] as const;
    return cats.map((cat) => {
      const rows = thisResults.filter(
        (r) => detailMap[r.criterion_id]?.criterion_type?.toLowerCase() === cat
      );
      return {
        cat,
        label:  cat.charAt(0).toUpperCase() + cat.slice(1),
        score:  rows.length ? Math.round(rows.reduce((s, r) => s + r.score * 100, 0) / rows.length) : 0,
        pass:   rows.filter((r) => r.verdict === "pass").length,
        fail:   rows.filter((r) => r.verdict === "fail").length,
        review: rows.filter((r) => r.verdict === "unknown").length,
        total:  rows.length,
      };
    }).filter((c) => c.total > 0);
  }, [thisResults, detailMap]);

  const failedLabels = useMemo(() =>
    thisResults.filter((r) => r.verdict === "fail")
      .map((r) => detailMap[r.criterion_id]?.label ?? r.criterion_id).slice(0, 3),
    [thisResults, detailMap]
  );

  const accentBlue = "#3B82F6";

  // ── Render ──────────────────────────────────────────────────────────────────

  if (evalLoading) return (
    <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "#0B0F1A", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
      <div style={{ width: 40, height: 40, border: "3px solid #1E2A3B", borderTopColor: "#3B82F6", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      <div style={{ fontSize: 13, color: "#4B5563" }}>Loading analysis…</div>
    </div>
  );

  return (
    <div style={{
      position: "fixed", top: 0, left: 0,
      width: "100vw", height: "100vh",
      background: "#0B0F1A",
      zIndex: 9999,
      overflowY: "auto",
      overflowX: "hidden",
      display: "flex",
      flexDirection: "column",
    }}>

        {/* ── Sticky Header ── */}
        <div style={{
          background: "#111827", borderBottom: "1px solid #1E2A3B",
          padding: "0 32px", height: 64,
          position: "sticky", top: 0, zIndex: 10, flexShrink: 0,
          display: "flex", alignItems: "center", gap: 16,
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 700, color: "#F9FAFB", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {bidderName}
              </span>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 20,
                background: isQualified ? "#064E3B" : totalCount ? "#450A0A" : "#1F2937",
                color:      isQualified ? "#34D399" : totalCount ? "#F87171" : "#9CA3AF",
                border:     `1px solid ${isQualified ? "#059669" : totalCount ? "#DC2626" : "#374151"}`,
                letterSpacing: "0.06em", whiteSpace: "nowrap",
              }}>
                {isQualified ? "QUALIFIED" : totalCount ? "DISQUALIFIED" : "PENDING"}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#6B7280", marginTop: 2 }}>
              Bidder Analysis · {totalCount} criteria evaluated
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "#1F2937", border: "1px solid #374151", borderRadius: 8,
              color: "#9CA3AF", cursor: "pointer", padding: "6px 16px",
              display: "flex", alignItems: "center", gap: 6,
              fontSize: 13, fontWeight: 600, flexShrink: 0,
            }}
          >
            <X size={14} /> Close
          </button>
        </div>

        {/* ── Section Nav Bar ── */}
        <div style={{
          position: "sticky", top: 64, zIndex: 9,
          background: "#111827", borderBottom: "1px solid #1E2A3B",
          padding: "0 32px", display: "flex", alignItems: "center", gap: 4,
          height: 44, flexShrink: 0, overflowX: "auto",
        }}>
          {(["overview", "analysis", "criteria"] as const).map((id) => (
            <button
              key={id}
              onClick={() => {
                setActiveSection(id);
                document.getElementById(`panel-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}
              style={{
                background: activeSection === id ? "#1E3A5F" : "none",
                border: activeSection === id ? `1px solid ${accentBlue}40` : "1px solid transparent",
                borderRadius: 6, color: activeSection === id ? accentBlue : "#6B7280",
                cursor: "pointer", padding: "4px 14px",
                fontSize: 12, fontWeight: activeSection === id ? 600 : 400,
                transition: "color 0.15s, background 0.15s", whiteSpace: "nowrap",
              }}
            >
              {id === "overview" ? "Overview" : id === "analysis" ? "Analysis" : "Criteria"}
            </button>
          ))}
        </div>

        {/* ── Scrollable body ── */}
        <div style={{ padding: "28px 32px", maxWidth: 1440, margin: "0 auto", width: "100%", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 28 }}>

          {/* ─── B: METRIC CARDS ─── */}
          <div id="panel-overview" style={{ scrollMarginTop: 112 }}>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {([
                { label: "Pass",       value: passCount,     color: "#34D399" },
                { label: "Fail",       value: failCount,     color: "#F87171" },
                { label: "Review",     value: reviewCount,   color: "#FBBF24" },
                { label: "Confidence", value: `${avgConf}%`, color: accentBlue },
                { label: "Total",      value: totalCount,    color: "#9CA3AF" },
              ] as const).map((m) => (
                <div key={m.label} style={{ flex: "1 1 140px", ...CHART_CARD, padding: "16px 20px" }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#4B5563", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>{m.label}</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: m.color, fontFamily: "JetBrains Mono, monospace", lineHeight: 1 }}>{m.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ─── C: VERDICT BANNER ─── */}
          {totalCount > 0 && (
            <div style={{
              background: isQualified ? "#064E3B" : "#450A0A",
              border:     `1px solid ${isQualified ? "#059669" : "#DC2626"}`,
              borderRadius: 12, padding: "16px 24px",
              display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {isQualified ? <CheckCircle2 size={20} color="#34D399" /> : <XCircle size={20} color="#F87171" />}
                <span style={{ fontSize: 14, fontWeight: 700, color: isQualified ? "#34D399" : "#F87171" }}>
                  {isQualified ? "✓ Eligible Bidder — All criteria satisfied" : `✗ Not Eligible${failedLabels.length ? ` — ${failedLabels.join(", ")}` : ""}`}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {(["financial", "technical", "compliance", "certification"] as const).map((cat) => {
                  const v = scores[cat]; if (!v) return null;
                  return <span key={cat} style={{ fontSize: 11, fontWeight: 700, padding: "4px 10px", background: "rgba(0,0,0,0.3)", borderRadius: 20, color: v >= 80 ? "#34D399" : v >= 60 ? "#60A5FA" : "#F87171", border: "1px solid rgba(255,255,255,0.1)", textTransform: "capitalize" }}>{cat.slice(0, 5)}: {v}</span>;
                })}
              </div>
            </div>
          )}

          {/* ─── D: ANALYSIS HEADER ─── */}
          <div id="panel-analysis" style={{ scrollMarginTop: 112, paddingBottom: 10, borderBottom: "1px solid #1E2A3B" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#4B5563", letterSpacing: "0.12em", textTransform: "uppercase" }}>Analysis</div>
          </div>

          {/* ─── E: THREE CHARTS ─── */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, overflow: "hidden" }}>
            {/* Radar */}
            <div style={CHART_CARD}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#9CA3AF", marginBottom: 12 }}>Performance Radar</div>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData} margin={{ top: 12, right: 32, bottom: 12, left: 32 }}>
                  <PolarGrid stroke="#1E2A3B" />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#9CA3AF" }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name={bidderName} dataKey="score" stroke={accentBlue} fill={accentBlue} fillOpacity={0.25} dot={{ r: 3, fill: accentBlue } as any} />
                  <Tooltip contentStyle={{ background: "#1F2937", border: "1px solid #374151", borderRadius: 6, fontSize: 11 }} labelStyle={{ color: "#9CA3AF" }} itemStyle={{ color: "#F9FAFB" }} formatter={(v: any) => [`${v}`, "Score"]} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div style={CHART_CARD}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#9CA3AF", marginBottom: 12 }}>vs All Bidders</div>

              {compBarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={compBarData} margin={{ top: 4, right: 8, bottom: 40, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E2A3B" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#6B7280" }} angle={-35} textAnchor="end" interval={0} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#6B7280" }} width={28} />
                    <Tooltip contentStyle={{ background: "#1F2937", border: "1px solid #374151", borderRadius: 6, fontSize: 11 }} formatter={(v: any) => [`${v}`, "Score"]} />
                    <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={40}>
                      {compBarData.map((e, i) => <Cell key={i} fill={e.isThis ? accentBlue : "#374151"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 220, display: "flex", alignItems: "center", justifyContent: "center", color: "#4B5563", fontSize: 12 }}>No comparison data</div>
              )}
            </div>

            {/* Confidence Donut */}
            <div style={{ ...CHART_CARD, display: "flex", flexDirection: "column" }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#9CA3AF", marginBottom: 12 }}>Confidence Distribution</div>
              <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ flex: "0 0 160px", position: "relative" }}>
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={trustDist.length ? trustDist : [{ name: "—", value: 1, color: "#1F2937" }]} cx="50%" cy="50%" innerRadius={50} outerRadius={72} dataKey="value" strokeWidth={0} animationBegin={0} animationDuration={600}>
                        {(trustDist.length ? trustDist : [{ name: "—", value: 1, color: "#1F2937" }]).map((e, i) => <Cell key={i} fill={e.color} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: "#1F2937", border: "1px solid #374151", borderRadius: 6, fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#F9FAFB", fontFamily: "JetBrains Mono, monospace" }}>{totalCount}</div>
                    <div style={{ fontSize: 10, color: "#6B7280" }}>criteria</div>
                  </div>
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                  {trustDist.map((d) => (
                    <div key={d.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: "#6B7280" }}>{d.name}</span>
                      </div>
                      <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#F9FAFB", fontWeight: 600 }}>{totalCount ? Math.round(d.value / totalCount * 100) : 0}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* ─── F: CRITERIA ANALYSIS HEADER ─── */}
          <div id="panel-criteria" style={{ scrollMarginTop: 112, paddingBottom: 10, borderBottom: "1px solid #1E2A3B" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#4B5563", letterSpacing: "0.12em", textTransform: "uppercase" }}>Criteria Analysis</div>
          </div>

          {/* ─── G: SCORE vs THRESHOLD ─── */}
          {criteriaBarData.length > 0 && (
            <div style={CHART_CARD}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#9CA3AF", marginBottom: 16 }}>Score vs Threshold</div>
              <ResponsiveContainer width="100%" height={Math.max(200, criteriaBarData.length * 34)}>
                <BarChart layout="vertical" data={criteriaBarData} margin={{ top: 4, right: 48, bottom: 4, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2A3B" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#6B7280" }} />
                  <YAxis type="category" dataKey="label" tick={{ fontSize: 10, fill: "#9CA3AF" }} width={168} />
                  <Tooltip contentStyle={{ background: "#1F2937", border: "1px solid #374151", borderRadius: 6, fontSize: 11 }} formatter={(v: any) => [`${v}%`, "Score"]} />
                  <ReferenceLine x={85} stroke="#4B5563" strokeDasharray="4 4" label={{ value: "85%", position: "insideTopRight", fill: "#6B7280", fontSize: 10 }} />
                  <Bar dataKey="score" radius={[0, 4, 4, 0]} maxBarSize={20}>
                    {criteriaBarData.map((e, i) => (
                      <Cell key={i} fill={e.verdict === "pass" ? "#059669" : e.verdict === "fail" ? "#DC2626" : "#D97706"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ─── H: CATEGORY CARDS ─── */}
          {catCards.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
              {catCards.map((c) => (
                <div key={c.cat} style={CHART_CARD}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>{c.label}</div>
                  <div style={{ fontSize: 28, fontWeight: 800, fontFamily: "JetBrains Mono, monospace", lineHeight: 1, marginBottom: 10, color: c.score >= 80 ? "#34D399" : c.score >= 60 ? "#60A5FA" : "#F87171" }}>{c.score}</div>
                  <div style={{ height: 4, background: "#1F2937", borderRadius: 2, marginBottom: 10, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${c.score}%`, background: c.score >= 80 ? "#059669" : c.score >= 60 ? accentBlue : "#DC2626", borderRadius: 2, transition: "width 0.6s ease" }} />
                  </div>
                  <div style={{ display: "flex", gap: 12, fontSize: 11 }}>
                    <span style={{ color: "#34D399" }}>{c.pass} pass</span>
                    <span style={{ color: "#F87171" }}>{c.fail} fail</span>
                    {c.review > 0 && <span style={{ color: "#FBBF24" }}>{c.review} review</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div style={{ height: 40 }} />
        </div>
    </div>
  );
}

