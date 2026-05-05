import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LabelList, ReferenceLine,
} from "recharts";
import type { CriterionInsight } from "../../services/types";
import { C } from "../../styles/tokens";

interface Props { criteria: CriterionInsight[]; }

function scoreColor(score: number, verdict: string): string {
  if (verdict === "fail")    return "#DC2626";
  if (verdict === "unknown") return "#D97706";
  if (score >= 0.85)         return "#10B981";
  if (score >= 0.70)         return "#059669";
  return "#34D399";
}

function gradKey(verdict: string, score: number): string {
  if (verdict === "fail")    return "scoreGradFail";
  if (verdict === "unknown") return "scoreGradReview";
  if (score >= 0.85)         return "scoreGradPassHigh";
  return "scoreGradPassMid";
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const color = scoreColor(d.rawScore, d.verdict);
  return (
    <div style={{
      background: C.bgSecondary,
      border: `1px solid ${C.borderActive}`,
      borderRadius: 8,
      padding: "12px 16px",
      fontSize: 12,
      minWidth: 180,
      boxShadow: "0 12px 32px rgba(0,0,0,0.5)",
    }}>
      <div style={{
        fontWeight: 700, color: C.textPrimary, marginBottom: 8,
        paddingBottom: 6, borderBottom: `1px solid ${C.borderSubtle}`,
      }}>
        {d.fullName}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: C.textTertiary }}>Confidence</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color }}>{d.pct}%</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: C.textTertiary }}>Verdict</span>
          <span style={{
            fontFamily: "JetBrains Mono, monospace", fontWeight: 700,
            color: d.verdict === "pass" ? "#4ade80" : d.verdict === "fail" ? "#f87171" : "#fbbf24",
            textTransform: "uppercase",
          }}>{d.verdict}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: C.textTertiary }}>Weight</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", color: C.textSecondary }}>{d.weight.toFixed(1)}×</span>
        </div>
      </div>
    </div>
  );
};

export default function ScoreBarChart({ criteria }: Props) {
  const data = criteria.map((c) => {
    const rawScore = c.verdict === "pass" ? 0.87 : c.verdict === "fail" ? 0 : 0.3;
    const pct = Math.round(rawScore * 100);
    return {
      name:     c.label.length > 16 ? c.label.slice(0, 14) + "…" : c.label,
      fullName: c.label,
      pct,
      rawScore,
      verdict:  c.verdict,
      weight:   c.weight,
    };
  });

  return (
    <div style={{ width: "100%", overflowX: "auto", overflowY: "hidden" }}>
      <div style={{ minWidth: Math.max(300, data.length * 64) }}>
        <ResponsiveContainer width="100%" height={230}>
          <BarChart data={data} margin={{ top: 24, right: 16, left: -16, bottom: 50 }} barCategoryGap="30%">
            <defs>
              <linearGradient id="scoreGradPassHigh" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#10B981" stopOpacity={1} />
                <stop offset="100%" stopColor="#059669" stopOpacity={0.6} />
              </linearGradient>
              <linearGradient id="scoreGradPassMid" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#34D399" stopOpacity={1} />
                <stop offset="100%" stopColor="#059669" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="scoreGradFail" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#F87171" stopOpacity={1} />
                <stop offset="100%" stopColor="#DC2626" stopOpacity={0.6} />
              </linearGradient>
              <linearGradient id="scoreGradReview" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#FBBF24" stopOpacity={1} />
                <stop offset="100%" stopColor="#D97706" stopOpacity={0.5} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="2 4" stroke={C.borderSubtle} vertical={false} />

            <ReferenceLine
              y={85}
              stroke={C.passSolid}
              strokeDasharray="4 3"
              label={{ value: "85%", fill: C.passText, fontSize: 9, position: "insideTopRight" }}
            />

            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: C.textTertiary }}
              interval={0}
              angle={-35}
              textAnchor="end"
              height={55}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 10, fill: C.textTertiary }}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip content={<CustomTooltip />} cursor={{ fill: `${C.borderSubtle}50`, radius: 4 }} />

            <Bar dataKey="pct" radius={[4, 4, 0, 0]} isAnimationActive animationDuration={700} animationEasing="ease-out">
              <LabelList
                dataKey="pct"
                position="top"
                formatter={(v: any) => v != null ? `${v}%` : ""}
                style={{ fontSize: 9, fontWeight: 700, fill: C.textTertiary }}
              />
              {data.map((d, i) => (
                <Cell key={i} fill={`url(#${gradKey(d.verdict, d.rawScore)})`} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
