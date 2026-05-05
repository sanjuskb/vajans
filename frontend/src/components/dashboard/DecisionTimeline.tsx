import React from "react";
import { Upload, Cpu, CheckSquare, UserCheck, Award } from "lucide-react";
import type { JobStatus } from "../../services/types";

interface Props { jobStatus: JobStatus; hasReviews: boolean; }

const STEPS = [
  { id: "upload",     label: "Upload",     sub: "Documents ingested",   icon: Upload },
  { id: "extraction", label: "Extraction", sub: "Criteria & fields",    icon: Cpu },
  { id: "evaluation", label: "Evaluation", sub: "Rule engine ran",      icon: CheckSquare },
  { id: "review",     label: "Review",     sub: "Human verification",   icon: UserCheck },
  { id: "decision",   label: "Decision",   sub: "Final verdict issued", icon: Award },
];

function getActiveStep(status: JobStatus, hasReviews: boolean): number {
  if (status === "pending")    return 0;
  if (status === "ingesting")  return 0;
  if (status === "extracting") return 1;
  if (status === "evaluating") return 2;
  if (status === "failed")     return 1;
  // completed
  if (hasReviews) return 4;
  return 3;
}

export default function DecisionTimeline({ jobStatus, hasReviews }: Props) {
  const active = getActiveStep(jobStatus, hasReviews);
  const failed = jobStatus === "failed";

  return (
    <div style={{
      background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14,
      padding: "20px 24px", marginBottom: 24,
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", letterSpacing: 1, marginBottom: 16 }}>
        PIPELINE PROGRESS
      </div>
      <div style={{ display: "flex", alignItems: "center" }}>
        {STEPS.map((step, i) => {
          const done    = i < active;
          const current = i === active;
          const Icon    = step.icon;
          const isFail  = failed && i === 1;

          const nodeColor  = isFail ? "#dc2626" : done || current ? "#1e40af" : "#e2e8f0";
          const textColor  = isFail ? "#dc2626" : done || current ? "#0f172a" : "#94a3b8";
          const lineColor  = i < active ? "#1e40af" : "#e2e8f0";

          return (
            <React.Fragment key={step.id}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 0 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: "50%",
                  background: done ? nodeColor : current ? "#eff6ff" : "#f8fafc",
                  border: `2px solid ${nodeColor}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  position: "relative",
                  boxShadow: current ? `0 0 0 4px rgba(30,64,175,0.15)` : "none",
                  transition: "all 0.3s",
                }}>
                  <Icon size={16} color={done ? "#fff" : nodeColor} />
                  {current && jobStatus !== "completed" && (
                    <span style={{
                      position: "absolute", top: -4, right: -4,
                      width: 10, height: 10, borderRadius: "50%",
                      background: "#2563eb",
                      animation: "pulse 1.5s infinite",
                    }} />
                  )}
                </div>
                <div style={{ marginTop: 8, textAlign: "center", width: 72 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: textColor }}>{step.label}</div>
                  <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 1, lineHeight: 1.3 }}>{step.sub}</div>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{
                  flex: 1, height: 2, background: lineColor,
                  margin: "-20px 4px 0", transition: "background 0.3s",
                }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
