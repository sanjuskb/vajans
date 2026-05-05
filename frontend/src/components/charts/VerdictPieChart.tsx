import React from "react";
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { InsightSummary } from "../../services/types";
import { C } from "../../styles/tokens";

const VERDICT_COLORS: Record<string, string> = {
  Pass:    "#10B981",
  Fail:    "#F87171",
  Unknown: "#FBBF24",
};

const VERDICT_BG: Record<string, string> = {
  Pass:    C.passBg,
  Fail:    C.failBg,
  Unknown: C.uncertainBg,
};

interface Props { summary: InsightSummary; }

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  const color = VERDICT_COLORS[d.name] ?? C.neutral;
  return (
    <div style={{
      background: C.bgSecondary,
      border: `1px solid ${C.borderActive}`,
      borderRadius: 8,
      padding: "10px 14px",
      fontSize: 12,
      boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: C.textPrimary, marginBottom: 4 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" }} />
        {d.name}
      </div>
      <div style={{ fontFamily: "JetBrains Mono, monospace", color }}>
        {d.value} criteria
      </div>
      <div style={{ color: C.textTertiary, fontSize: 11 }}>
        {Math.round((d.value / d.payload.total) * 100)}% of total
      </div>
    </div>
  );
};

const CustomLegend = ({ payload, total }: any) => (
  <div style={{ display: "flex", justifyContent: "center", gap: 20, flexWrap: "wrap" }}>
    {(payload ?? []).map((entry: any) => {
      const color = VERDICT_COLORS[entry.value] ?? C.neutral;
      const bg    = VERDICT_BG[entry.value]    ?? C.bgTertiary;
      const count = entry.payload?.value ?? 0;
      const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
      return (
        <div key={entry.value} style={{
          display: "flex", alignItems: "center", gap: 8,
          background: bg, borderRadius: 6, padding: "4px 10px",
          border: `1px solid ${color}30`,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block", flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: C.textSecondary }}>{entry.value}</span>
          <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color }}>{count}</span>
          <span style={{ fontSize: 10, color: C.textTertiary }}>({pct}%)</span>
        </div>
      );
    })}
  </div>
);

export default function VerdictPieChart({ summary }: Props) {
  const entries = [
    { name: "Pass",    value: summary.pass },
    { name: "Fail",    value: summary.fail },
    { name: "Unknown", value: summary.unknown },
  ].filter((d) => d.value > 0);

  if (entries.length === 0) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 220, color: C.textTertiary, fontSize: 13 }}>
        No verdict data
      </div>
    );
  }

  const total = entries.reduce((s, d) => s + d.value, 0);
  const entriesWithTotal = entries.map((e) => ({ ...e, total }));

  const passRate = total > 0 ? Math.round((summary.pass / total) * 100) : 0;
  const passColor = passRate >= 70 ? C.passSolid : passRate >= 40 ? C.uncertainSolid : C.failSolid;

  const renderInnerLabel = () => (
    <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle">
      <tspan x="50%" dy="-8" style={{ fontSize: 22, fontWeight: 800, fill: passColor, fontFamily: "JetBrains Mono, monospace" }}>
        {passRate}%
      </tspan>
      <tspan x="50%" dy="18" style={{ fontSize: 10, fill: C.textTertiary }}>
        pass rate
      </tspan>
    </text>
  );

  const renderSliceLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, value }: any) => {
    const RADIAN = Math.PI / 180;
    const r = innerRadius + (outerRadius - innerRadius) * 0.62;
    const x = cx + r * Math.cos(-midAngle * RADIAN);
    const y = cy + r * Math.sin(-midAngle * RADIAN);
    const pct = Math.round((value / total) * 100);
    if (pct < 10) return null;
    return (
      <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central"
        style={{ fontSize: 11, fontWeight: 700 }}>
        {pct}%
      </text>
    );
  };

  return (
    <div style={{ width: "100%", overflow: "hidden" }}>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={entriesWithTotal}
            cx="50%" cy="46%"
            innerRadius={52} outerRadius={82}
            paddingAngle={3}
            dataKey="value"
            labelLine={false}
            label={renderSliceLabel}
            isAnimationActive
            animationBegin={0}
            animationDuration={700}
            animationEasing="ease-out"
          >
            {entriesWithTotal.map((d) => (
              <Cell key={d.name} fill={VERDICT_COLORS[d.name] ?? C.neutral} strokeWidth={0} />
            ))}
          </Pie>
          {renderInnerLabel()}
          <Tooltip content={<CustomTooltip />} />
          <Legend
            iconType="circle"
            iconSize={0}
            content={<CustomLegend total={total} />}
            wrapperStyle={{ paddingTop: 8 }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
