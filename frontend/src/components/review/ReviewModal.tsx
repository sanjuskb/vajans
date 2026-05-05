import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { X } from "lucide-react";
import { analyzeApi } from "../../services/api";
import type { CriterionInsight, EvalResultRow, ReviewerAction } from "../../services/types";

interface Props {
  jobId: string;
  criterion: CriterionInsight;
  evalRow: EvalResultRow | undefined;
  onClose: () => void;
}

const actionCfg: Record<ReviewerAction, { label: string; color: string; bg: string }> = {
  approve: { label: "Approve",  color: "#16a34a", bg: "#dcfce7" },
  edit:    { label: "Edit",     color: "#1e40af", bg: "#dbeafe" },
  reject:  { label: "Reject",   color: "#dc2626", bg: "#fee2e2" },
};

export default function ReviewModal({ jobId, criterion, evalRow, onClose }: Props) {
  const qc = useQueryClient();
  const [action, setAction] = useState<ReviewerAction>("approve");
  const [updatedValue, setUpdatedValue] = useState("");
  const [reason, setReason] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      analyzeApi.submitReview(jobId, {
        criterion_id: criterion.criterion_id,
        evaluation_result_id: evalRow?.id ?? "",
        reviewer_action: action,
        updated_value: action === "edit" ? updatedValue : undefined,
        reason: reason.trim(),
      }),
    onSuccess: () => {
      toast.success(`Review submitted: ${action.toUpperCase()}`);
      qc.invalidateQueries({ queryKey: ["dashboard", jobId] });
      qc.invalidateQueries({ queryKey: ["evaluation", jobId] });
      qc.invalidateQueries({ queryKey: ["reviews", jobId] });
      onClose();
    },
    onError: (e: { message?: string }) => {
      toast.error(e?.message ?? "Review submission failed");
    },
  });

  const canSubmit = reason.trim().length > 0 && (action !== "edit" || updatedValue.trim().length > 0);

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff", borderRadius: 16, padding: 32, width: 500,
          boxShadow: "0 25px 60px rgba(0,0,0,0.25)", maxHeight: "90vh", overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: "#0f172a", margin: 0 }}>Submit Review</h2>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>{criterion.label}</p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}>
            <X size={20} />
          </button>
        </div>

        {/* Current verdict */}
        <div style={{ background: "#f8fafc", borderRadius: 10, padding: "12px 16px", marginBottom: 20, fontSize: 13 }}>
          <span style={{ color: "#64748b" }}>Current verdict: </span>
          <strong style={{ color: criterion.verdict === "pass" ? "#16a34a" : criterion.verdict === "fail" ? "#dc2626" : "#d97706" }}>
            {criterion.verdict.toUpperCase()}
          </strong>
          {evalRow?.explanation && (
            <p style={{ color: "#64748b", marginTop: 6, fontSize: 12, lineHeight: 1.5 }}>{evalRow.explanation}</p>
          )}
        </div>

        {/* Action selector */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 8 }}>
            Review Action
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            {(["approve", "edit", "reject"] as ReviewerAction[]).map((a) => {
              const c = actionCfg[a];
              const active = action === a;
              return (
                <button
                  key={a}
                  onClick={() => setAction(a)}
                  style={{
                    flex: 1, padding: "9px 0", borderRadius: 8, fontSize: 13, fontWeight: 600,
                    cursor: "pointer", transition: "all 0.15s",
                    background: active ? c.bg : "#f8fafc",
                    color: active ? c.color : "#94a3b8",
                    border: active ? `2px solid ${c.color}` : "2px solid transparent",
                  }}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Edit value field */}
        {action === "edit" && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
              Updated Value
            </label>
            <input
              value={updatedValue}
              onChange={(e) => setUpdatedValue(e.target.value)}
              placeholder="Enter corrected value…"
              style={{
                width: "100%", padding: "10px 12px", border: "1px solid #d1d5db",
                borderRadius: 8, fontSize: 14, boxSizing: "border-box",
              }}
            />
          </div>
        )}

        {/* Reason */}
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
            Reason <span style={{ color: "#dc2626" }}>*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Explain your review decision…"
            style={{
              width: "100%", padding: "10px 12px", border: "1px solid #d1d5db",
              borderRadius: 8, fontSize: 14, boxSizing: "border-box", resize: "vertical",
              fontFamily: "inherit",
            }}
          />
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              padding: "10px 20px", border: "1px solid #d1d5db", borderRadius: 8,
              background: "#fff", cursor: "pointer", fontSize: 14, color: "#374151",
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit || mutation.isPending}
            style={{
              padding: "10px 24px",
              background: canSubmit ? actionCfg[action].color : "#94a3b8",
              color: "#fff", border: "none", borderRadius: 8,
              cursor: canSubmit ? "pointer" : "not-allowed",
              fontWeight: 600, fontSize: 14,
            }}
          >
            {mutation.isPending ? "Submitting…" : `Submit ${actionCfg[action].label}`}
          </button>
        </div>
      </div>
    </div>
  );
}
