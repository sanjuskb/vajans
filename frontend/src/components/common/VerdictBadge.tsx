import React from "react";
import type { Verdict } from "../../services/types";

const cfg: Record<Verdict, { bg: string; color: string; label: string }> = {
  pass:    { bg: "#dcfce7", color: "#16a34a", label: "PASS" },
  fail:    { bg: "#fee2e2", color: "#dc2626", label: "FAIL" },
  unknown: { bg: "#fef9c3", color: "#b45309", label: "UNKNOWN" },
};

export default function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const c = cfg[verdict] ?? { bg: "#f1f5f9", color: "#64748b", label: verdict.toUpperCase() };
  return (
    <span style={{
      display: "inline-block",
      padding: "3px 10px",
      borderRadius: 999,
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: 0.5,
      background: c.bg,
      color: c.color,
    }}>
      {c.label}
    </span>
  );
}
