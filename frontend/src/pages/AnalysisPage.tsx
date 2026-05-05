import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, CheckCircle2, XCircle, FileText, BookOpen, AlertCircle,
  TrendingUp, Target, Award, Activity,
} from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip,
  Cell, PieChart, Pie, CartesianGrid, ReferenceLine, Legend,
  Line, ComposedChart, Area,
} from "recharts";
import { analyzeApi } from "../services/api";
import type { EvalResultRow } from "../services/types";

// ── Theme-aware tokens ───────────────────────────────────────────────────────
const T = {
  bg:        "var(--bg-primary)",
  card:      "var(--card-bg)",
  cardAlt:   "var(--bg-tertiary)",
  border:    "var(--border-subtle)",
  borderHi:  "var(--border-active)",
  text:      "var(--text-primary)",
  textSub:   "var(--text-secondary)",
  textMute:  "var(--text-tertiary)",
  // SVG attributes do NOT resolve CSS vars — use neutral hexes that work in both themes
  grid:      "rgba(148, 163, 184, 0.2)",
  axis:      "#94A3B8",
  tipBg:     "var(--tooltip-bg)",
  tipBorder: "var(--tooltip-border)",
};

// Chart palette — same hue in both themes
const PALETTE = {
  blue:   "#3B82F6",
  green:  "#10B981",
  red:    "#EF4444",
  amber:  "#F59E0B",
  purple: "#8B5CF6",
  cyan:   "#06B6D4",
  pink:   "#EC4899",
  slate:  "#64748B",
};

const CARD: React.CSSProperties = {
  background:   T.card,
  border:       `1px solid ${T.border}`,
  borderRadius: 12,
  padding:      20,
  boxSizing:    "border-box",
  width:        "100%",
  minWidth:     0,      // critical: allow shrinking in grid/flex so Recharts can measure
  overflow:     "hidden",
};

// ── Measure-your-own-width hook — bypass Recharts ResponsiveContainer entirely ─
function useMeasuredWidth() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setW(el.getBoundingClientRect().width);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    // Also fire once after layout settles (framer-motion opacity transition)
    const t = window.setTimeout(measure, 250);
    return () => { ro.disconnect(); window.clearTimeout(t); };
  }, []);
  return { ref, width: w };
}

/**
 * MeasuredChart — provides a width-measured slot and passes explicit pixel
 * width+height to Recharts chart components, bypassing ResponsiveContainer.
 * This avoids the well-known "0-width on mount" issue in grid/animated layouts.
 */
function MeasuredChart({
  height, children,
}: {
  height: number;
  children: (w: number, h: number) => React.ReactNode;
}) {
  const { ref, width } = useMeasuredWidth();
  return (
    <div ref={ref} style={{ width: "100%", height, minWidth: 0, position: "relative" }}>
      {width > 0 ? children(width, height) : null}
    </div>
  );
}

const SECTION_TITLE: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: T.textMute,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  marginBottom: 14,
};

const CHART_TITLE: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: T.textSub,
  marginBottom: 14,
  display: "flex",
  alignItems: "center",
  gap: 8,
};

// Recharts tooltip with theme-aware styling
const tooltipStyle: React.CSSProperties = {
  background: T.tipBg,
  border:     `1px solid ${T.tipBorder}`,
  borderRadius: 8,
  fontSize:   12,
  color:      T.text,
  boxShadow:  "0 4px 12px rgba(0,0,0,0.15)",
};
const tooltipLabelStyle: React.CSSProperties = { color: T.textSub, fontWeight: 600 };
const tooltipItemStyle:  React.CSSProperties = { color: T.text };

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalysisPage() {
  const { jobId, bidderId } = useParams<{ jobId: string; bidderId: string }>();
  const navigate = useNavigate();

  const decodedBidderId = decodeURIComponent(bidderId || "");

  // ── Data fetching ─────────────────────────────────────────────────────────
  const { data: evalData, isLoading: evalLoading } = useQuery({
    queryKey: ["evaluation", jobId],
    queryFn: () => analyzeApi.getEvaluation(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  const { data: comparisonData } = useQuery({
    queryKey: ["comparison", jobId],
    queryFn: () => analyzeApi.getComparison(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  const { data: criteriaResp } = useQuery({
    queryKey: ["criteria", jobId],
    queryFn: () => analyzeApi.getCriteria(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  });

  // ── Resolve target bidder ─────────────────────────────────────────────────
  const thisBidder = useMemo(() => {
    if (!evalData?.bidders?.length) return null;
    const list = evalData.bidders;
    return (
      list.find((b) => b.bidder_file_id === decodedBidderId) ??
      list.find((b) => b.bidder_name === decodedBidderId) ??
      list.find(
        (b) =>
          b.bidder_name.toLowerCase().includes(decodedBidderId.toLowerCase()) ||
          decodedBidderId.toLowerCase().includes(b.bidder_name.toLowerCase())
      ) ??
      null
    );
  }, [evalData, decodedBidderId]);

  const bidderName = thisBidder?.bidder_name ?? decodedBidderId ?? "Bidder";

  // ── Criterion lookup map ──────────────────────────────────────────────────
  const detailMap = useMemo(
    () => Object.fromEntries((criteriaResp?.data ?? []).map((c) => [c.id, c])),
    [criteriaResp]
  );

  // ── This bidder's results ─────────────────────────────────────────────────
  const thisResults: EvalResultRow[] = useMemo(() => {
    if (thisBidder?.results?.length) return thisBidder.results;
    if (!evalData?.results) return [];
    if (thisBidder?.bidder_file_id) {
      return evalData.results.filter((r) => r.bidder_file_id === thisBidder.bidder_file_id);
    }
    return evalData.results;
  }, [thisBidder, evalData]);

  // ── Metrics ───────────────────────────────────────────────────────────────
  const passCount   = thisResults.filter((r) => r.verdict === "pass").length;
  const failCount   = thisResults.filter((r) => r.verdict === "fail").length;
  const reviewCount = thisResults.filter((r) => r.verdict === "unknown").length;
  const totalCount  = thisResults.length;
  const avgConf     = totalCount
    ? Math.round((thisResults.reduce((s, r) => s + r.score, 0) / totalCount) * 100)
    : 0;
  const totalScore  = thisBidder ? Math.round(thisBidder.final_score * 100) : avgConf;
  const isQualified = failCount === 0 && totalCount > 0;

  // ── Category scores ──────────────────────────────────────────────────────
  const getAvg = (type: string) => {
    const rows = thisResults.filter(
      (r) => detailMap[r.criterion_id]?.criterion_type?.toLowerCase() === type
    );
    if (!rows.length) return 0;
    return Math.round(rows.reduce((s, r) => s + r.score * 100, 0) / rows.length);
  };

  const radarData = useMemo(() => {
    const cats = [
      { key: "financial",     subject: "Financial"     },
      { key: "technical",     subject: "Technical"     },
      { key: "compliance",    subject: "Compliance"    },
      { key: "certification", subject: "Certification" },
      { key: "experience",    subject: "Experience"    },
      { key: "quality",       subject: "Quality"       },
    ];
    const data = cats
      .map((c) => ({ subject: c.subject, score: getAvg(c.key), threshold: 70 }))
      .filter((d) => d.score > 0);
    // If no categorized data, fall back to a synthetic distribution from results
    if (data.length === 0 && totalCount > 0) {
      return [
        { subject: "Pass Rate",  score: Math.round((passCount / totalCount) * 100), threshold: 70 },
        { subject: "Confidence", score: avgConf,                                      threshold: 70 },
        { subject: "Coverage",   score: Math.min(100, totalCount * 10),               threshold: 70 },
        { subject: "Consistency",score: Math.max(20, 100 - (failCount / Math.max(1, totalCount)) * 100), threshold: 70 },
      ];
    }
    return data;
  }, [thisResults, detailMap, totalCount, passCount, failCount, avgConf]);

  // ── Bidder comparison ────────────────────────────────────────────────────
  const compBarData = useMemo(() => {
    const list = evalData?.bidders ?? [];
    if (list.length) {
      return list
        .map((b) => ({
          name:   b.bidder_name.replace(/\.(pdf|docx?)$/i, "").slice(0, 16),
          score:  Math.round(b.final_score * 100),
          isThis: b.bidder_file_id === thisBidder?.bidder_file_id,
          pass:   b.summary.pass,
          fail:   b.summary.fail,
        }))
        .sort((a, b) => b.score - a.score);
    }
    return (comparisonData?.bidders ?? [])
      .map((b) => ({
        name:   b.bidder_name.replace(/\.(pdf|docx?)$/i, "").slice(0, 16),
        score:  Math.round(b.total_score * 100),
        isThis: b.bidder_name === bidderName,
        pass:   b.pass,
        fail:   b.fail,
      }))
      .sort((a, b) => b.score - a.score);
  }, [evalData, comparisonData, thisBidder, bidderName]);

  // ── Confidence distribution donut ────────────────────────────────────────
  const trustDist = useMemo(() => {
    const high = thisResults.filter((r) => r.score >= 0.85).length;
    const med  = thisResults.filter((r) => r.score >= 0.6 && r.score < 0.85).length;
    const low  = thisResults.filter((r) => r.score < 0.6).length;
    return [
      { name: "High (≥85%)",    value: high, color: PALETTE.green },
      { name: "Medium (60–85%)", value: med,  color: PALETTE.blue  },
      { name: "Low (<60%)",     value: low,  color: PALETTE.amber },
    ].filter((d) => d.value > 0);
  }, [thisResults]);

  // ── Score distribution histogram ─────────────────────────────────────────
  const scoreBuckets = useMemo(() => {
    const buckets = [
      { range: "0–20",   count: 0, fill: PALETTE.red    },
      { range: "20–40",  count: 0, fill: PALETTE.amber  },
      { range: "40–60",  count: 0, fill: "#FBBF24"      },
      { range: "60–80",  count: 0, fill: PALETTE.blue   },
      { range: "80–100", count: 0, fill: PALETTE.green  },
    ];
    thisResults.forEach((r) => {
      const pct = r.score * 100;
      if (pct < 20)       buckets[0].count++;
      else if (pct < 40)  buckets[1].count++;
      else if (pct < 60)  buckets[2].count++;
      else if (pct < 80)  buckets[3].count++;
      else                buckets[4].count++;
    });
    return buckets;
  }, [thisResults]);

  // ── Trend chart — cumulative score over criteria order ───────────────────
  const trendData = useMemo(() => {
    if (!thisResults.length) return [];
    let sum = 0;
    return thisResults.map((r, i) => {
      sum += r.score * 100;
      return {
        idx:        i + 1,
        label:      `C${i + 1}`,
        criterion:  (detailMap[r.criterion_id]?.label ?? r.criterion_id).slice(0, 24),
        score:      Math.round(r.score * 100),
        avg:        Math.round(sum / (i + 1)),
        threshold:  70,
      };
    });
  }, [thisResults, detailMap]);

  // ── Criteria detail rows (with evidence) ─────────────────────────────────
  const criteriaRows = useMemo(() => {
    return thisResults.map((r) => {
      const d = detailMap[r.criterion_id];
      return {
        id:          r.criterion_id,
        label:       d?.label ?? r.criterion_id,
        type:        d?.criterion_type ?? "—",
        mandatory:   d?.mandatory ?? false,
        verdict:     r.verdict,
        score:       Math.round(r.score * 100),
        threshold:   d?.threshold_value != null
                       ? `${d.threshold_value}${d.threshold_unit ?? ""}`
                       : "—",
        explanation: r.explanation,
        snippet:     d?.source_snippet ?? null,
        sourceDoc:   "Tender Document",
      };
    });
  }, [thisResults, detailMap]);

  const evidenceRows = useMemo(
    () => criteriaRows.filter((r) => r.snippet && r.snippet.trim().length > 0),
    [criteriaRows]
  );

  // ── Render guards ────────────────────────────────────────────────────────
  if (evalLoading) return <LoadingState />;

  // ── Render ───────────────────────────────────────────────────────────────
  const verdictColor = isQualified ? PALETTE.green : totalCount ? PALETTE.red : PALETTE.slate;

  return (
    <div style={{
      padding: "24px clamp(16px, 3vw, 32px)",
      maxWidth: 1600, margin: "0 auto", width: "100%", boxSizing: "border-box",
      display: "flex", flexDirection: "column", gap: 20,
      color: T.text,
    }}>
      {/* ─── Header ─── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <button
          onClick={() => navigate(`/jobs/${jobId}`)}
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            background: T.card, border: `1px solid ${T.border}`,
            color: T.textSub, padding: "8px 14px", borderRadius: 8,
            fontSize: 13, fontWeight: 500,
          }}
        >
          <ArrowLeft size={14} /> Back to Job
        </button>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: T.text, margin: 0 }}>
            Bidder Analysis
          </h1>
          <div style={{ fontSize: 13, color: T.textSub, marginTop: 4 }}>
            <span style={{ fontWeight: 600, color: T.text }}>{bidderName}</span>
            <span style={{ margin: "0 8px", color: T.textMute }}>·</span>
            {totalCount} criteria evaluated
          </div>
        </div>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "8px 16px", borderRadius: 24,
          background: isQualified
            ? "rgba(16,185,129,0.1)"
            : totalCount
              ? "rgba(239,68,68,0.1)"
              : "rgba(100,116,139,0.1)",
          border: `1px solid ${verdictColor}40`,
          color: verdictColor, fontSize: 12, fontWeight: 700, letterSpacing: "0.06em",
        }}>
          {isQualified
            ? <><CheckCircle2 size={14} /> QUALIFIED</>
            : totalCount
              ? <><XCircle size={14} /> DISQUALIFIED</>
              : <><AlertCircle size={14} /> PENDING</>}
        </div>
      </div>

      {/* ─── Metric cards row ─── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
        gap: 16,
      }}>
        <MetricCard icon={<Award size={16} />}     label="Total Score"  value={`${totalScore}`}     suffix="/100" color={verdictColor} />
        <MetricCard icon={<CheckCircle2 size={16}/>}label="Pass"         value={passCount}                          color={PALETTE.green} />
        <MetricCard icon={<XCircle size={16} />}    label="Fail"         value={failCount}                          color={PALETTE.red} />
        <MetricCard icon={<AlertCircle size={16}/>} label="Review"       value={reviewCount}                        color={PALETTE.amber} />
        <MetricCard icon={<Target size={16} />}     label="Confidence"   value={`${avgConf}`} suffix="%"            color={PALETTE.blue} />
        <MetricCard icon={<Activity size={16} />}   label="Total"        value={totalCount}                         color={PALETTE.slate} />
      </div>

      {/* ─── Charts grid: Radar + Comparison + Donut ─── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
        gap: 16,
      }}>
        {/* Performance Radar */}
        <div style={CARD}>
          <div style={CHART_TITLE}><Target size={14} /> Performance by Category</div>
          {radarData.length >= 3 ? (
            <MeasuredChart height={300}>{(w, h) => (
              <RadarChart width={w} height={h} data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                <PolarGrid stroke={T.grid} />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: T.axis }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar name={bidderName} dataKey="score"
                  stroke={PALETTE.blue} fill={PALETTE.blue} fillOpacity={0.3}
                  dot={{ r: 3, fill: PALETTE.blue, strokeWidth: 0 } as never}
                  isAnimationActive animationDuration={600} />
                <Radar name="Threshold" dataKey="threshold"
                  stroke={PALETTE.slate} fill="none" strokeDasharray="4 4" strokeWidth={1.5}
                  isAnimationActive={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} />
                <Legend wrapperStyle={{ fontSize: 11, color: T.textSub }} iconSize={10} />
              </RadarChart>
            )}</MeasuredChart>
          ) : <NoData height={300} />}
        </div>

        {/* Bidder Comparison */}
        <div style={CARD}>
          <div style={CHART_TITLE}><TrendingUp size={14} /> Bidder Comparison</div>
          {compBarData.length > 0 ? (
            <MeasuredChart height={300}>{(w, h) => (
              <BarChart width={w} height={h} data={compBarData} margin={{ top: 8, right: 8, bottom: 48, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.grid} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: T.axis }}
                  angle={-30} textAnchor="end" interval={0} height={48} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: T.axis }} width={36} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle}
                  formatter={(v: number) => [`${v}/100`, "Score"]} />
                <ReferenceLine y={70} stroke={PALETTE.amber} strokeDasharray="4 4"
                  label={{ value: "Threshold", position: "insideTopRight", fill: T.axis, fontSize: 10 }} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={48}
                  isAnimationActive animationDuration={600}>
                  {compBarData.map((e, i) => (
                    <Cell key={i} fill={e.isThis ? PALETTE.blue : PALETTE.slate}
                      fillOpacity={e.isThis ? 1 : 0.45} />
                  ))}
                </Bar>
              </BarChart>
            )}</MeasuredChart>
          ) : <NoData height={300} />}
        </div>

        {/* Confidence Donut */}
        <div style={CARD}>
          <div style={CHART_TITLE}><Activity size={14} /> Confidence Distribution</div>
          {trustDist.length > 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12, height: 300 }}>
              <div style={{ flex: "0 0 55%", position: "relative", height: "100%", minWidth: 0 }}>
                <MeasuredChart height={300}>{(w, h) => (
                  <PieChart width={w} height={h}>
                    <Pie data={trustDist} cx="50%" cy="50%"
                      innerRadius={60} outerRadius={90}
                      paddingAngle={2} dataKey="value" strokeWidth={0}
                      isAnimationActive animationDuration={600}>
                      {trustDist.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} />
                  </PieChart>
                )}</MeasuredChart>
                <div style={{
                  position: "absolute", inset: 0,
                  display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                  pointerEvents: "none",
                }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: T.text, fontFamily: "JetBrains Mono, monospace" }}>
                    {totalCount}
                  </div>
                  <div style={{ fontSize: 10, color: T.textMute, letterSpacing: "0.08em" }}>CRITERIA</div>
                </div>
              </div>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, paddingRight: 4 }}>
                {trustDist.map((d) => (
                  <div key={d.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 10, height: 10, borderRadius: 3, background: d.color }} />
                      <span style={{ color: T.textSub }}>{d.name}</span>
                    </div>
                    <span style={{ color: T.text, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" }}>
                      {d.value} <span style={{ color: T.textMute, fontWeight: 400 }}>
                        ({Math.round((d.value / totalCount) * 100)}%)
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : <NoData height={300} />}
        </div>
      </div>

      {/* ─── Trends + Score Distribution row ─── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)",
        gap: 16,
      }}>
        {/* Cumulative score trend */}
        <div style={{ ...CARD, minWidth: 0 }}>
          <div style={CHART_TITLE}><TrendingUp size={14} /> Score Progression Across Criteria</div>
          {trendData.length > 0 ? (
            <MeasuredChart height={320}>{(w, h) => (
              <ComposedChart width={w} height={h} data={trendData} margin={{ top: 16, right: 16, bottom: 8, left: -8 }}>
                <defs>
                  <linearGradient id="scoreArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor={PALETTE.blue} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={PALETTE.blue} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={T.grid} vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: T.axis }} interval="preserveStartEnd" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: T.axis }} width={36} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle}
                  labelFormatter={(_l, p) => p?.[0]?.payload?.criterion ?? ""}
                  formatter={(v: number, name: string) => [`${v}`, name]} />
                <ReferenceLine y={70} stroke={PALETTE.amber} strokeDasharray="4 4" />
                <Area type="monotone" dataKey="score" stroke={PALETTE.blue}
                  strokeWidth={2} fill="url(#scoreArea)"
                  dot={{ r: 3, fill: PALETTE.blue, strokeWidth: 0 } as never}
                  name="Score" isAnimationActive animationDuration={700} />
                <Line type="monotone" dataKey="avg" stroke={PALETTE.green}
                  strokeWidth={2} dot={false} name="Running Avg"
                  isAnimationActive animationDuration={700} />
                <Legend wrapperStyle={{ fontSize: 11, color: T.textSub }} iconSize={10} />
              </ComposedChart>
            )}</MeasuredChart>
          ) : <NoData height={320} />}
        </div>

        {/* Score histogram */}
        <div style={{ ...CARD, minWidth: 0 }}>
          <div style={CHART_TITLE}><Activity size={14} /> Score Distribution</div>
          {totalCount > 0 ? (
            <MeasuredChart height={320}>{(w, h) => (
              <BarChart width={w} height={h} data={scoreBuckets} margin={{ top: 16, right: 8, bottom: 8, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.grid} vertical={false} />
                <XAxis dataKey="range" tick={{ fontSize: 10, fill: T.axis }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: T.axis }} width={36} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle}
                  formatter={(v: number) => [`${v} criteria`, "Count"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={56}
                  isAnimationActive animationDuration={600}>
                  {scoreBuckets.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Bar>
              </BarChart>
            )}</MeasuredChart>
          ) : <NoData height={320} />}
        </div>
      </div>

      {/* ─── Criteria Performance (horizontal bars) ─── */}
      <div style={CARD}>
        <div style={CHART_TITLE}><Target size={14} /> Criteria Performance vs Threshold</div>
        {criteriaRows.length > 0 ? (
          <MeasuredChart height={Math.max(220, criteriaRows.length * 32)}>{(w, h) => (
            <BarChart width={w} height={h} layout="vertical" data={criteriaRows.slice(0, 20).map((r) => ({
              name:    r.label.length > 36 ? r.label.slice(0, 36) + "…" : r.label,
              score:   r.score,
              verdict: r.verdict,
            }))} margin={{ top: 8, right: 32, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={T.grid} horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: T.axis }} />
              <YAxis type="category" dataKey="name"
                tick={{ fontSize: 11, fill: T.textSub }} width={200} interval={0} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle}
                formatter={(v: number) => [`${v}/100`, "Score"]} />
              <ReferenceLine x={70} stroke={PALETTE.amber} strokeDasharray="4 4"
                label={{ value: "70", position: "top", fill: PALETTE.amber, fontSize: 10 }} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} maxBarSize={20}
                isAnimationActive animationDuration={600}>
                {criteriaRows.slice(0, 20).map((r, i) => (
                  <Cell key={i}
                    fill={r.verdict === "pass" ? PALETTE.green
                       : r.verdict === "fail" ? PALETTE.red
                       : PALETTE.amber} />
                ))}
              </Bar>
            </BarChart>
          )}</MeasuredChart>
        ) : <NoData height={220} />}
      </div>

      {/* ─── Source Evidence section ─── */}
      <div>
        <div style={SECTION_TITLE}>Source Evidence</div>
        <div style={{ ...CARD, padding: 0, overflow: "hidden" }}>
          {evidenceRows.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column" }}>
              {evidenceRows.slice(0, 12).map((r, i) => (
                <EvidenceCard key={r.id + i} row={r} isLast={i === Math.min(evidenceRows.length - 1, 11)} />
              ))}
              {evidenceRows.length > 12 && (
                <div style={{
                  padding: "12px 20px", textAlign: "center",
                  fontSize: 12, color: T.textMute, borderTop: `1px solid ${T.border}`,
                }}>
                  Showing 12 of {evidenceRows.length} evidence items
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: "60px 20px", textAlign: "center", color: T.textMute, fontSize: 13 }}>
              <FileText size={28} style={{ opacity: 0.3, marginBottom: 12 }} />
              <div>No evidence available</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>
                Source snippets are not yet extracted for this evaluation
              </div>
            </div>
          )}
        </div>
      </div>

      <div style={{ height: 24 }} />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricCard({
  icon, label, value, suffix, color,
}: {
  icon: React.ReactNode; label: string; value: string | number; suffix?: string; color: string;
}) {
  return (
    <div style={CARD}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 12,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 700, color: T.textMute,
          textTransform: "uppercase", letterSpacing: "0.1em",
        }}>{label}</div>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: `${color}1A`, color,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>{icon}</div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{
          fontSize: 26, fontWeight: 800, color, lineHeight: 1,
          fontFamily: "JetBrains Mono, monospace",
        }}>{value}</span>
        {suffix && (
          <span style={{ fontSize: 13, color: T.textMute, fontFamily: "JetBrains Mono, monospace" }}>
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}

function EvidenceCard({
  row, isLast,
}: {
  row: {
    id: string; label: string; verdict: string; score: number;
    explanation: string; snippet: string | null; sourceDoc: string;
    type: string; mandatory: boolean; threshold: string;
  };
  isLast: boolean;
}) {
  const vColor = row.verdict === "pass" ? PALETTE.green
              : row.verdict === "fail" ? PALETTE.red
              : PALETTE.amber;

  return (
    <div style={{
      padding: 20, borderBottom: isLast ? "none" : `1px solid ${T.border}`,
      display: "grid", gap: 14,
      gridTemplateColumns: "minmax(0, 1fr)",
    }}>
      {/* Top row: title + meta */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: T.text }}>{row.label}</span>
            {row.mandatory && (
              <span style={{
                fontSize: 9, fontWeight: 700,
                color: PALETTE.blue, background: `${PALETTE.blue}1A`,
                border: `1px solid ${PALETTE.blue}40`,
                padding: "2px 6px", borderRadius: 4, letterSpacing: "0.06em",
              }}>REQUIRED</span>
            )}
            <span style={{
              fontSize: 10, fontWeight: 600, color: T.textMute,
              background: T.cardAlt, padding: "2px 8px", borderRadius: 4,
              textTransform: "capitalize",
            }}>{row.type}</span>
          </div>
          <div style={{ fontSize: 11, color: T.textMute }}>
            Threshold: <span style={{ color: T.textSub, fontFamily: "JetBrains Mono, monospace" }}>{row.threshold}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: vColor,
              fontFamily: "JetBrains Mono, monospace", lineHeight: 1 }}>
              {row.score}<span style={{ fontSize: 11, color: T.textMute, fontWeight: 400 }}>/100</span>
            </div>
          </div>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: "4px 10px", borderRadius: 12,
            background: `${vColor}1A`, color: vColor,
            border: `1px solid ${vColor}40`,
            textTransform: "uppercase", letterSpacing: "0.06em",
          }}>{row.verdict}</span>
        </div>
      </div>

      {/* Source snippet */}
      {row.snippet && (
        <div>
          <div style={{
            fontSize: 10, fontWeight: 700, color: T.textMute,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
          }}>Source Snippet</div>
          <blockquote style={{
            margin: 0, padding: "10px 14px",
            borderLeft: `3px solid ${vColor}`,
            background: T.cardAlt, borderRadius: "0 6px 6px 0",
            fontSize: 12, lineHeight: 1.55,
            color: T.textSub,
            fontFamily: "JetBrains Mono, monospace",
          }}>
            “{row.snippet}”
          </blockquote>
          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              fontSize: 10, fontWeight: 700, color: PALETTE.blue,
              background: `${PALETTE.blue}1A`, border: `1px solid ${PALETTE.blue}40`,
              padding: "3px 8px", borderRadius: 4,
            }}>
              <BookOpen size={10} /> {row.sourceDoc}
            </span>
          </div>
        </div>
      )}

      {/* AI Reasoning */}
      <div>
        <div style={{
          fontSize: 10, fontWeight: 700, color: T.textMute,
          textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
        }}>AI Reasoning</div>
        <p style={{ fontSize: 12.5, color: T.textSub, lineHeight: 1.6, margin: 0 }}>
          {row.explanation || "No reasoning provided."}
        </p>
      </div>
    </div>
  );
}

function NoData({ height }: { height: number }) {
  return (
    <div style={{
      height, display: "flex", alignItems: "center", justifyContent: "center",
      color: T.textMute, fontSize: 12,
    }}>No data available</div>
  );
}

function LoadingState() {
  return (
    <div style={{
      padding: 48, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 16,
      minHeight: "60vh",
    }}>
      <div className="spin" style={{
        width: 40, height: 40,
        border: `3px solid ${T.border}`,
        borderTopColor: PALETTE.blue,
        borderRadius: "50%",
      }} />
      <div style={{ fontSize: 13, color: T.textSub }}>Loading analysis…</div>
    </div>
  );
}
