import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LabelList, ReferenceLine,
} from "recharts";
import type { BidderEntry } from "../../services/types";
import { C } from "../../styles/tokens";

interface Props { bidders: BidderEntry[]; }

const GRAD_PASS    = "bidderGradPass";
const GRAD_FAIL    = "bidderGradFail";
const GRAD_REVIEW  = "bidderGradReview";

function gradId(b: { fail: number; unknown: number }): string {
  if (b.fail > 0)    return `url(#${GRAD_FAIL})`;
  if (b.unknown > 0) return `url(#${GRAD_REVIEW})`;
  return `url(#${GRAD_PASS})`;
}

function solidColor(b: { fail: number; unknown: number }): string {
  if (b.fail > 0)    return "#DC2626";
  if (b.unknown > 0) return "#D97706";
  return "#059669";
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const color = solidColor(d);
  return (
    <div style={{
      background: C.bgSecondary,
      border: `1px solid ${C.borderActive}`,
      borderRadius: 8,
      padding: "12px 16px",
      fontSize: 12,
      minWidth: 170,
      boxShadow: "0 12px 32px rgba(0,0,0,0.5)",
    }}>
      <div style={{
        fontWeight: 700, color: C.textPrimary, marginBottom: 10,
        paddingBottom: 8, borderBottom: `1px solid ${C.borderSubtle}`,
        fontSize: 13,
      }}>
        {d.name}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: C.textTertiary }}>Score</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color }}>{d.score}%</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: "#4ade80" }}>Passed</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", color: "#4ade80", fontWeight: 600 }}>{d.pass}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: "#f87171" }}>Failed</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", color: d.fail > 0 ? "#f87171" : C.textTertiary, fontWeight: 600 }}>{d.fail}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20 }}>
          <span style={{ color: "#fbbf24" }}>Under Review</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace", color: d.unknown > 0 ? "#fbbf24" : C.textTertiary, fontWeight: 600 }}>{d.unknown}</span>
        </div>
      </div>
    </div>
  );
};

export default function BidderBarChart({ bidders }: Props) {
  const data = bidders.map((b, i) => ({
    name:    (b.bidder_name || `Bidder ${i + 1}`).replace(/\.pdf$/i, ""),
    score:   Math.round(b.total_score * 100),
    pass:    b.pass,
    fail:    b.fail,
    unknown: b.unknown,
  }));

  const minWidth = Math.max(300, data.length * 90);

  return (
    <div style={{ width: "100%", overflowX: "auto", overflowY: "hidden" }}>
      <div style={{ minWidth }}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 28, right: 24, left: -14, bottom: 8 }} barCategoryGap="35%">
            <defs>
              <linearGradient id={GRAD_PASS} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#10B981" stopOpacity={1} />
                <stop offset="100%" stopColor="#059669" stopOpacity={0.7} />
              </linearGradient>
              <linearGradient id={GRAD_FAIL} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#F87171" stopOpacity={1} />
                <stop offset="100%" stopColor="#DC2626" stopOpacity={0.7} />
              </linearGradient>
              <linearGradient id={GRAD_REVIEW} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#FBBF24" stopOpacity={1} />
                <stop offset="100%" stopColor="#D97706" stopOpacity={0.7} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="2 4" stroke={C.borderSubtle} vertical={false} />

            <ReferenceLine
              y={75}
              stroke={C.borderActive}
              strokeDasharray="4 4"
              label={{ value: "Pass threshold", fill: C.textTertiary, fontSize: 9, position: "insideTopRight" }}
            />

            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: C.textTertiary }}
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

            <Bar dataKey="score" radius={[6, 6, 0, 0]} isAnimationActive animationDuration={700} animationEasing="ease-out">
              <LabelList
                dataKey="score"
                position="top"
                formatter={(v: any) => v != null ? `${v}%` : ""}
                style={{ fontSize: 11, fontWeight: 700, fill: C.textSecondary }}
              />
              {data.map((d, i) => (
                <Cell key={i} fill={gradId(d)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
