import React, { useState } from "react";
import {
  ChevronDown, ChevronUp, MessageSquare,
  FileText, RotateCcw, Info,
} from "lucide-react";
import VerdictBadge from "../common/VerdictBadge";
import ReviewModal from "../review/ReviewModal";
import type {
  CriterionInsight, EvalResultRow, CriterionDetail, ReviewActionRead,
} from "../../services/types";

interface Props {
  jobId: string;
  criteria: CriterionInsight[];
  evalRows: EvalResultRow[];
  criteriaDetails: CriterionDetail[];
  reviews: ReviewActionRead[];
}

const importanceColor: Record<string, string> = {
  high:   "#7c3aed",
  medium: "#1e40af",
  low:    "#64748b",
};

const verdictBorder: Record<string, string> = {
  pass:    "#bbf7d0",
  fail:    "#fecdd3",
  unknown: "#fde68a",
};
const verdictBg: Record<string, string> = {
  pass:    "#f0fdf4",
  fail:    "#fff1f2",
  unknown: "#fffbeb",
};

export default function CriteriaList({
  jobId, criteria, evalRows, criteriaDetails, reviews,
}: Props) {
  const [expanded, setExpanded]  = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<CriterionInsight | null>(null);

  const rowMap    = Object.fromEntries(evalRows.map((r) => [r.criterion_id, r]));
  const detailMap = Object.fromEntries(criteriaDetails.map((c) => [c.id, c]));

  // Latest review per criterion
  const reviewMap: Record<string, ReviewActionRead> = {};
  for (const rv of reviews) {
    const cid = rv.criterion_id;
    if (!reviewMap[cid] || rv.created_at > reviewMap[cid].created_at) {
      reviewMap[cid] = rv;
    }
  }

  if (criteria.length === 0) {
    return (
      <div style={{
        textAlign: "center", padding: "48px 24px", color: "#94a3b8",
        background: "#f8fafc", borderRadius: 12,
      }}>
        <Info size={32} color="#cbd5e1" style={{ marginBottom: 10 }} />
        <p style={{ fontSize: 15, fontWeight: 600 }}>No criteria evaluated yet</p>
        <p style={{ fontSize: 13, marginTop: 4 }}>Run the AI pipeline to extract and evaluate criteria.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {criteria.map((c) => {
        const isOpen  = expanded === c.criterion_id;
        const row     = rowMap[c.criterion_id];
        const detail  = detailMap[c.criterion_id];
        const review  = reviewMap[c.criterion_id];
        const mand    = detail?.mandatory ?? (c.importance_level === "high");
        const isOverridden = review && review.reviewer_action !== "approve";

        return (
          <div
            key={c.criterion_id}
            style={{
              background: isOpen ? verdictBg[c.verdict] ?? "#fff" : "#fff",
              border: `1px solid ${isOpen ? verdictBorder[c.verdict] ?? "#e2e8f0" : "#e2e8f0"}`,
              borderLeft: mand ? `4px solid ${c.verdict === "fail" ? "#dc2626" : c.verdict === "pass" ? "#16a34a" : "#d97706"}` : "1px solid #e2e8f0",
              borderRadius: 12,
              overflow: "hidden",
              transition: "all 0.2s",
              boxShadow: isOpen ? "0 2px 8px rgba(0,0,0,0.06)" : "none",
            }}
          >
            {/* ── Row header ── */}
            <div
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "13px 16px", cursor: "pointer",
              }}
              onClick={() => setExpanded(isOpen ? null : c.criterion_id)}
            >
              <VerdictBadge verdict={c.verdict} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontWeight: 700, fontSize: 14, color: "#0f172a" }}>
                    {c.label}
                  </span>
                  {mand && (
                    <span style={{
                      fontSize: 9, fontWeight: 800, letterSpacing: 0.8,
                      background: "#fee2e2", color: "#dc2626",
                      padding: "2px 7px", borderRadius: 999, border: "1px solid #fecdd3",
                    }}>
                      MANDATORY
                    </span>
                  )}
                  {!mand && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: 0.6,
                      background: "#fef9c3", color: "#b45309",
                      padding: "2px 7px", borderRadius: 999, border: "1px solid #fde68a",
                    }}>
                      OPTIONAL
                    </span>
                  )}
                  {isOverridden && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: 0.6,
                      background: "#ede9fe", color: "#7c3aed",
                      padding: "2px 7px", borderRadius: 999,
                      display: "inline-flex", alignItems: "center", gap: 3,
                      border: "1px solid #ddd6fe",
                    }}>
                      <RotateCcw size={8} /> REVIEWER OVERRIDE
                    </span>
                  )}
                </div>

                {/* Inline explanation preview */}
                {!isOpen && (
                  <div style={{
                    fontSize: 12, color: "#64748b", marginTop: 3,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    maxWidth: 480,
                  }}>
                    {c.explanation}
                  </div>
                )}
              </div>

              {/* Right side */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, color: importanceColor[c.importance_level] ?? "#64748b",
                  textTransform: "uppercase", letterSpacing: 0.5,
                }}>
                  {c.importance_level}
                </span>
                <span style={{ fontSize: 11, color: "#94a3b8" }}>w:{c.weight.toFixed(1)}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setReviewing(c); }}
                  style={{
                    display: "flex", alignItems: "center", gap: 4,
                    padding: "5px 11px", borderRadius: 7,
                    background: "#eff6ff", color: "#1e40af",
                    border: "none", cursor: "pointer", fontSize: 11, fontWeight: 700,
                  }}
                >
                  <MessageSquare size={12} /> Review
                </button>
                {isOpen
                  ? <ChevronUp size={15} color="#94a3b8" />
                  : <ChevronDown size={15} color="#94a3b8" />
                }
              </div>
            </div>

            {/* ── Expanded detail ── */}
            {isOpen && (
              <div style={{ borderTop: "1px solid rgba(0,0,0,0.06)", padding: "14px 16px 16px" }}>

                {/* Verdict explanation */}
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: 0.8, marginBottom: 5 }}>
                    EVALUATION RESULT
                  </div>
                  <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.6, margin: 0 }}>
                    {c.explanation}
                  </p>
                </div>

                {/* Review override detail */}
                {isOverridden && review && (
                  <div style={{
                    background: "#ede9fe", border: "1px solid #ddd6fe",
                    borderRadius: 9, padding: "10px 14px", marginBottom: 12,
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#7c3aed", marginBottom: 6, display: "flex", alignItems: "center", gap: 5 }}>
                      <RotateCcw size={11} /> REVIEWER OVERRIDE
                    </div>
                    <div style={{ fontSize: 12, color: "#4c1d95", lineHeight: 1.5 }}>
                      <strong>Action:</strong> {review.reviewer_action.toUpperCase()}
                      {review.updated_value && <> · <strong>New value:</strong> {review.updated_value}</>}
                      <br />
                      <strong>Reason:</strong> {review.reason}
                    </div>
                  </div>
                )}

                {/* Source evidence */}
                {detail?.source_snippet && (
                  <div style={{
                    background: "#f8fafc", border: "1px solid #e2e8f0",
                    borderRadius: 9, padding: "10px 14px", marginBottom: 12,
                  }}>
                    <div style={{
                      fontSize: 11, fontWeight: 700, color: "#64748b", letterSpacing: 0.8,
                      marginBottom: 6, display: "flex", alignItems: "center", gap: 5,
                    }}>
                      <FileText size={11} /> SOURCE EVIDENCE
                    </div>
                    <blockquote style={{
                      margin: 0, fontSize: 12, color: "#374151",
                      lineHeight: 1.6, fontStyle: "italic",
                      borderLeft: "3px solid #cbd5e1", paddingLeft: 10,
                    }}>
                      "{detail.source_snippet}"
                    </blockquote>
                  </div>
                )}

                {/* Description */}
                {detail?.description && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: 0.8, marginBottom: 4 }}>
                      REQUIREMENT DESCRIPTION
                    </div>
                    <p style={{ fontSize: 12, color: "#64748b", lineHeight: 1.6, margin: 0 }}>
                      {detail.description}
                    </p>
                  </div>
                )}

                {/* Score row */}
                {row && (
                  <div style={{
                    display: "flex", gap: 16, marginTop: 10,
                    padding: "8px 0", borderTop: "1px solid rgba(0,0,0,0.06)",
                    fontSize: 12, color: "#94a3b8",
                  }}>
                    <span>Score: <strong style={{ color: "#0f172a" }}>{(row.score * 100).toFixed(0)}%</strong></span>
                    <span>Weighted: <strong style={{ color: "#0f172a" }}>{row.weighted_score.toFixed(3)}</strong></span>
                    <span>Weight: <strong style={{ color: "#0f172a" }}>{row.weight.toFixed(1)}</strong></span>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {reviewing && (
        <ReviewModal
          jobId={jobId}
          criterion={reviewing}
          evalRow={rowMap[reviewing.criterion_id]}
          onClose={() => setReviewing(null)}
        />
      )}
    </div>
  );
}
