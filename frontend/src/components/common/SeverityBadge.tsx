import React from "react";
import type { Severity } from "../../services/types";

const cfg: Record<Severity, { bg: string; border: string; color: string; dot: string }> = {
  critical: { bg: "#fff1f2", border: "#fecdd3", color: "#be123c", dot: "#e11d48" },
  warning:  { bg: "#fffbeb", border: "#fde68a", color: "#92400e", dot: "#d97706" },
  info:     { bg: "#eff6ff", border: "#bfdbfe", color: "#1e40af", dot: "#3b82f6" },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const c = cfg[severity] ?? cfg.info;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "2px 9px", borderRadius: 999,
      fontSize: 11, fontWeight: 700,
      background: c.bg, border: `1px solid ${c.border}`, color: c.color,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: c.dot, display: "inline-block" }} />
      {severity.toUpperCase()}
    </span>
  );
}
