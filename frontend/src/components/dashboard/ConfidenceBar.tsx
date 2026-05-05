import React from "react";
import { Gauge } from "lucide-react";
import type { InsightSummary } from "../../services/types";

interface Props { summary: InsightSummary; }

export default function ConfidenceBar({ summary }: Props) {
  const { total_criteria, pass, fail, unknown } = summary;

  // Confidence = proportion of deterministically resolved criteria
  const resolved    = pass + fail;
  const confidence  = total_criteria > 0 ? resolved / total_criteria : 0;
  const pct         = Math.round(confidence * 100);

  const level  = pct >= 70 ? "High"   : pct >= 40 ? "Medium" : "Low";
  const label  = pct >= 70 ? "Auto Decision Reliable" : pct >= 40 ? "Needs Human Review" : "Low Evidence — Unreliable";
  const color  = pct >= 70 ? "#16a34a" : pct >= 40 ? "#d97706" : "#dc2626";
  const bg     = pct >= 70 ? "#f0fdf4" : pct >= 40 ? "#fffbeb" : "#fff1f2";
  const border = pct >= 70 ? "#bbf7d0" : pct >= 40 ? "#fde68a" : "#fecdd3";

  return (
    <div style={{
      background: bg, border: `1px solid ${border}`,
      borderRadius: 12, padding: "14px 18px",
      display: "flex", alignItems: "center", gap: 16,
    }}>
      <Gauge size={22} color={color} style={{ flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color }}>
            {level} Confidence — {label}
          </span>
          <span style={{ fontSize: 13, fontWeight: 800, color }}>{pct}%</span>
        </div>
        <div style={{ height: 6, background: "rgba(0,0,0,0.08)", borderRadius: 3, overflow: "hidden" }}>
          <div style={{
            height: "100%", width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}cc, ${color})`,
            borderRadius: 3, transition: "width 0.6s ease",
          }} />
        </div>
        <div style={{ fontSize: 11, color: "#64748b", marginTop: 5 }}>
          {resolved} of {total_criteria} criteria resolved deterministically
          {unknown > 0 && ` · ${unknown} require human judgment`}
        </div>
      </div>
    </div>
  );
}
