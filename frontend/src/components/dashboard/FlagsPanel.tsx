import React from "react";
import { AlertTriangle, Info, AlertCircle } from "lucide-react";
import SeverityBadge from "../common/SeverityBadge";
import type { InsightFlag } from "../../services/types";

interface Props { flags: InsightFlag[]; }

const iconMap = {
  critical: <AlertCircle size={16} color="#be123c" />,
  warning:  <AlertTriangle size={16} color="#d97706" />,
  info:     <Info size={16} color="#3b82f6" />,
};

export default function FlagsPanel({ flags }: Props) {
  if (flags.length === 0) {
    return (
      <div style={{
        background: "#f0fdf4", border: "1px solid #bbf7d0",
        borderRadius: 10, padding: "14px 18px",
        fontSize: 13, color: "#16a34a", fontWeight: 600,
      }}>
        ✓ No issues detected
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {flags.map((flag, i) => (
        <div key={i} style={{
          background: "#fff", border: "1px solid #e2e8f0",
          borderRadius: 10, padding: "14px 16px",
          display: "flex", gap: 12, alignItems: "flex-start",
        }}>
          <div style={{ marginTop: 1, flexShrink: 0 }}>
            {iconMap[flag.severity] ?? iconMap.info}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <SeverityBadge severity={flag.severity} />
              <code style={{ fontSize: 11, color: "#64748b" }}>{flag.code}</code>
            </div>
            <p style={{ fontSize: 13, color: "#374151", margin: 0, lineHeight: 1.5 }}>
              {flag.message}
            </p>
            {flag.affected_criteria && flag.affected_criteria.length > 0 && (
              <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 6, margin: "6px 0 0" }}>
                Affected: {flag.affected_criteria.length} criteria
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
