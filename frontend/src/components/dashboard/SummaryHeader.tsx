import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { InsightSummary } from "../../services/types";

interface Props { summary: InsightSummary; }

export default function SummaryHeader({ summary }: Props) {
  const pct = Math.round(summary.final_score * 100);
  const qualified = summary.final_status !== "DISQUALIFIED";

  const tiles = [
    {
      label: "Total Criteria", value: summary.total_criteria,
      color: "#1e40af", bg: "#eff6ff", icon: <Minus size={16} color="#1e40af" />,
    },
    {
      label: "Passed", value: summary.pass,
      color: "#16a34a", bg: "#f0fdf4", icon: <TrendingUp size={16} color="#16a34a" />,
    },
    {
      label: "Failed", value: summary.fail,
      color: "#dc2626", bg: "#fff1f2", icon: <TrendingDown size={16} color="#dc2626" />,
    },
    {
      label: "Needs Review", value: summary.unknown,
      color: "#d97706", bg: "#fffbeb", icon: <Minus size={16} color="#d97706" />,
    },
  ];

  return (
    <div style={{
      display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap",
    }}>
      {/* Score tile */}
      <div style={{
        background: qualified
          ? "linear-gradient(135deg,#1e40af,#2563eb)"
          : "linear-gradient(135deg,#991b1b,#dc2626)",
        borderRadius: 14, padding: "18px 22px",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
        minWidth: 130, color: "#fff",
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, opacity: 0.7 }}>FINAL SCORE</div>
        <div style={{ fontSize: 38, fontWeight: 900, lineHeight: 1 }}>{pct}%</div>
        <div style={{
          fontSize: 11, fontWeight: 700, marginTop: 6,
          background: "rgba(255,255,255,0.15)", borderRadius: 6,
          padding: "3px 8px", display: "inline-block",
        }}>
          {summary.final_status}
        </div>
      </div>

      {/* Metric tiles */}
      {tiles.map(({ label, value, color, bg, icon }) => (
        <div key={label} style={{
          background: bg, borderRadius: 12, padding: "14px 18px",
          display: "flex", flexDirection: "column", gap: 6, flex: "1 1 90px",
          border: `1px solid ${color}22`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600 }}>{label}</span>
            {icon}
          </div>
          <div style={{ fontSize: 30, fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
          <div style={{
            height: 4, background: "rgba(0,0,0,0.07)", borderRadius: 2, overflow: "hidden",
          }}>
            <div style={{
              height: "100%",
              width: summary.total_criteria > 0
                ? `${(value / summary.total_criteria) * 100}%`
                : "0%",
              background: color, borderRadius: 2, transition: "width 0.5s",
            }} />
          </div>
        </div>
      ))}
    </div>
  );
}
