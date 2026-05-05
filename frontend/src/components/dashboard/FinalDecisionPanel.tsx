import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";
import type { InsightSummary, CriterionInsight, CriterionDetail } from "../../services/types";

interface Props {
  summary: InsightSummary;
  criteria: CriterionInsight[];
  criteriaDetails: CriterionDetail[];
}

export default function FinalDecisionPanel({ summary, criteria, criteriaDetails }: Props) {
  const qualified   = summary.final_status !== "DISQUALIFIED";
  const detailMap   = Object.fromEntries(criteriaDetails.map((c) => [c.id, c]));
  const failedItems = criteria.filter((c) => c.verdict === "fail");
  const mandatoryFails = failedItems.filter((c) => detailMap[c.criterion_id]?.mandatory);

  const pct = Math.round(summary.final_score * 100);

  return (
    <div
      style={{
        borderRadius: 18,
        padding: "28px 32px",
        marginBottom: 28,
        background: qualified
          ? "linear-gradient(135deg,#052e16 0%,#14532d 100%)"
          : "linear-gradient(135deg,#450a0a 0%,#7f1d1d 100%)",
        color: "#fff",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative ring */}
      <div style={{
        position: "absolute", right: -60, top: -60,
        width: 240, height: 240, borderRadius: "50%",
        background: qualified ? "rgba(74,222,128,0.07)" : "rgba(248,113,113,0.07)",
        pointerEvents: "none",
      }} />

      <div style={{ display: "flex", alignItems: "flex-start", gap: 28, flexWrap: "wrap" }}>

        {/* Status icon + score ring */}
        <div style={{ textAlign: "center", flexShrink: 0 }}>
          <ScoreCircle pct={pct} qualified={qualified} />
        </div>

        {/* Main status */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            {qualified
              ? <CheckCircle2 size={28} color="#4ade80" />
              : <XCircle size={28} color="#f87171" />
            }
            <span style={{
              fontSize: 28, fontWeight: 900, letterSpacing: -0.5,
              color: qualified ? "#4ade80" : "#f87171",
            }}>
              {qualified ? "QUALIFIED" : "DISQUALIFIED"}
            </span>
          </div>

          <div style={{ fontSize: 14, color: "rgba(255,255,255,0.65)", marginBottom: 16 }}>
            Overall score: <strong style={{ color: "#fff", fontSize: 16 }}>{pct}%</strong>
            &nbsp;·&nbsp;{summary.total_criteria} criteria evaluated
            &nbsp;·&nbsp;{summary.pass} passed · {summary.fail} failed · {summary.unknown} pending review
          </div>

          {/* Why panel */}
          {!qualified && failedItems.length > 0 && (
            <div style={{
              background: "rgba(0,0,0,0.35)",
              borderRadius: 12, padding: "14px 18px",
              borderLeft: "3px solid #f87171",
            }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#fca5a5", marginBottom: 10, letterSpacing: 1 }}>
                WHY DISQUALIFIED?
              </div>
              {failedItems.map((c) => {
                const det  = detailMap[c.criterion_id];
                const mand = det?.mandatory ?? true;
                return (
                  <div key={c.criterion_id} style={{
                    display: "flex", alignItems: "flex-start", gap: 8,
                    padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.07)",
                  }}>
                    <XCircle size={14} color="#f87171" style={{ marginTop: 2, flexShrink: 0 }} />
                    <div>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#fff" }}>{c.label}</span>
                      {mand && (
                        <span style={{
                          marginLeft: 8, fontSize: 10, fontWeight: 700,
                          background: "#dc2626", color: "#fff",
                          padding: "1px 7px", borderRadius: 999,
                        }}>MANDATORY</span>
                      )}
                      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>
                        {c.explanation.length > 90 ? c.explanation.slice(0, 90) + "…" : c.explanation}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {qualified && (
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "rgba(0,0,0,0.3)", borderRadius: 10, padding: "10px 16px",
              borderLeft: "3px solid #4ade80",
            }}>
              <ShieldCheck size={16} color="#4ade80" />
              <span style={{ fontSize: 14, color: "rgba(255,255,255,0.8)" }}>
                {mandatoryFails.length === 0
                  ? "No mandatory criteria failed — bidder meets all hard requirements."
                  : `${mandatoryFails.length} mandatory criteria need review.`}
              </span>
            </div>
          )}
        </div>

        {/* Quick counts */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
          {[
            { label: "PASS",    val: summary.pass,    color: "#4ade80" },
            { label: "FAIL",    val: summary.fail,    color: "#f87171" },
            { label: "REVIEW",  val: summary.unknown, color: "#fbbf24" },
          ].map(({ label, val, color }) => (
            <div key={label} style={{ textAlign: "center", minWidth: 64 }}>
              <div style={{ fontSize: 26, fontWeight: 800, color }}>{val}</div>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", fontWeight: 700, letterSpacing: 1 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Review required banner */}
      {summary.review_required && (
        <div style={{
          marginTop: 18, padding: "10px 14px",
          background: "rgba(251,191,36,0.12)",
          border: "1px solid rgba(251,191,36,0.3)",
          borderRadius: 9, display: "flex", alignItems: "center", gap: 8,
        }}>
          <AlertTriangle size={14} color="#fbbf24" />
          <span style={{ fontSize: 13, color: "#fcd34d" }}>
            {summary.unknown} criteria could not be evaluated deterministically — human review recommended before final decision.
          </span>
        </div>
      )}
    </div>
  );
}

function ScoreCircle({ pct, qualified }: { pct: number; qualified: boolean }) {
  const r    = 40;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - pct / 100);
  const color = qualified ? "#4ade80" : "#f87171";
  return (
    <div style={{ position: "relative", width: 100, height: 100 }}>
      <svg width={100} height={100} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={50} cy={50} r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={8} />
        <circle cx={50} cy={50} r={r} fill="none" stroke={color} strokeWidth={8}
          strokeDasharray={circ} strokeDashoffset={fill} strokeLinecap="round" />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontSize: 20, fontWeight: 800, color }}>{pct}%</span>
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.4)", marginTop: 1, letterSpacing: 0.5 }}>SCORE</span>
      </div>
    </div>
  );
}
