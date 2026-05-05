import React from "react";
import { CheckCircle, XCircle, Edit3, Clock } from "lucide-react";
import type { ReviewActionRead } from "../../services/types";

interface Props { reviews: ReviewActionRead[]; }

const actionCfg = {
  approve: { color: "#16a34a", bg: "#dcfce7", icon: <CheckCircle size={14} />, label: "Approved" },
  edit:    { color: "#1e40af", bg: "#dbeafe", icon: <Edit3 size={14} />,       label: "Edited" },
  reject:  { color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} />,     label: "Rejected" },
};

export default function ReviewHistory({ reviews }: Props) {
  if (reviews.length === 0) {
    return (
      <div style={{ textAlign: "center", color: "#94a3b8", padding: "32px 0", fontSize: 14 }}>
        No review actions yet
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {[...reviews].reverse().map((r) => {
        const cfg = actionCfg[r.reviewer_action] ?? actionCfg.approve;
        return (
          <div key={r.id} style={{
            background: "#fff", border: "1px solid #e2e8f0",
            borderRadius: 10, padding: "14px 18px",
            display: "flex", gap: 14, alignItems: "flex-start",
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%",
              background: cfg.bg, color: cfg.color,
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
            }}>
              {cfg.icon}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <span style={{
                  fontSize: 13, fontWeight: 700, color: cfg.color,
                  background: cfg.bg, padding: "2px 10px", borderRadius: 999,
                }}>
                  {cfg.label}
                </span>
                <span style={{ fontSize: 11, color: "#94a3b8", display: "flex", alignItems: "center", gap: 4 }}>
                  <Clock size={11} />
                  {new Date(r.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                </span>
              </div>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#374151", lineHeight: 1.5 }}>
                {r.reason}
              </p>
              {r.updated_value && (
                <p style={{ margin: "4px 0 0", fontSize: 12, color: "#64748b" }}>
                  Updated value: <strong>{r.updated_value}</strong>
                </p>
              )}
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94a3b8" }}>
                Criterion: <code>{r.criterion_id.slice(0, 8)}…</code>
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
