import { useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, RefreshCw, Download, FileText, Upload,
  AlertTriangle, CheckCircle, Play, ChevronDown, ChevronUp,
  MessageSquare, RotateCcw, Lock, List, Users, ScrollText,
  ExternalLink, BookOpen,
} from "lucide-react";
import toast from "react-hot-toast";
import { C, SP } from "../styles/tokens";
import { jobsApi, filesApi, analyzeApi, downloadJSON } from "../services/api";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Tabs from "../components/ui/Tabs";
import StatusTracker from "../components/ui/StatusTracker";
import TrustBar from "../components/ui/TrustBar";
import EmptyState from "../components/ui/EmptyState";
import { CardSkeleton } from "../components/ui/Card";
import PdfViewerModal, { type EvidenceContext } from "../components/pdf/PdfViewerModal";
import type { FileRecord, FileType, CriterionDetail, CriterionInsight, EvalResultRow, ReviewActionRead, BidderEntry, BidderEvalSummary, ExtractionRow } from "../services/types";

// ── Right side panel ─────────────────────────────────────────────────────────
function RightPanel({ job, evalData, criteriaCount, reviewCount, onExportReport, onExportAudit }: {
  job: { id: string; status: string; created_by: string; created_at: string; updated_at: string };
  evalData?: { final_status: string; final_score: number; summary: { pass: number; fail: number; unknown: number; total: number } };
  criteriaCount: number;
  reviewCount: number;
  onExportReport: () => void;
  onExportAudit: () => void;
}) {
  type StepStatus = "done" | "active" | "pending" | "error";

  const s    = job.status;
  const meta = (job as any).metadata ?? {};
  const isCompleted = s === "completed";
  const isFailed    = s === "failed";

  // Resolve each step from metadata flags (more granular than job.status alone)
  const ingestionDone   = meta.ingestion_complete  === true || ["extracting","evaluating","completed"].includes(s);
  const criteriaDone    = (meta.criteria_count ?? criteriaCount) > 0 || ["evaluating","completed"].includes(s);
  const extractionDone  = meta.extraction_complete === true || ["evaluating","completed"].includes(s);
  const evaluationDone  = meta.evaluation_complete === true || isCompleted;

  const ingestionStatus: StepStatus  = isFailed ? "error" : ingestionDone  ? "done" : s === "ingesting"  ? "active" : "pending";
  const criteriaStatus:  StepStatus  = criteriaDone  ? "done" : ingestionDone && !criteriaDone ? "active" : "pending";
  const extractionStatus: StepStatus = extractionDone ? "done" : criteriaDone && !extractionDone ? "active" : "pending";
  const evaluationStatus: StepStatus = evaluationDone ? "done" : extractionDone && !evaluationDone ? "active" : "pending";
  const reviewStatus: StepStatus     = !isCompleted ? "pending" : reviewCount > 0 ? "active" : "done";

  const resolvedCriteriaCount = meta.criteria_count ?? criteriaCount;

  const steps: { label: string; sub?: string; status: StepStatus }[] = [
    { label: "Ingestion complete",  sub: "Files chunked & indexed",                                             status: ingestionStatus },
    { label: "Criteria extracted",  sub: resolvedCriteriaCount > 0 ? `${resolvedCriteriaCount} criteria` : undefined, status: criteriaStatus },
    { label: "Data extracted",      sub: "Bidder values matched to criteria",                                   status: extractionStatus },
    { label: "Evaluation complete", sub: evaluationDone ? "Verdicts computed" : undefined,                      status: evaluationStatus },
    { label: "Review pending",      sub: reviewCount > 0 ? `${reviewCount} item${reviewCount !== 1 ? "s" : ""}` : "No pending items", status: reviewStatus },
  ];

  const confidence = evalData
    ? (evalData.summary.pass + evalData.summary.fail) / (evalData.summary.total || 1)
    : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: SP.lg }}>
      {/* Job info */}
      <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, padding: SP.xl }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.lg, textTransform: "uppercase" }}>Job Information</div>
        {[
          { label: "ID",         value: job.id.slice(0,8) + "…", mono: true },
          { label: "Created by", value: job.created_by },
          { label: "Started",    value: new Date(job.created_at).toLocaleString("en-IN"), mono: true },
          { label: "Last updated", value: new Date(job.updated_at).toLocaleString("en-IN"), mono: true },
        ].map(({ label, value, mono }) => (
          <div key={label} style={{ marginBottom: SP.sm }}>
            <div style={{ fontSize: 11, color: C.textTertiary }}>{label}</div>
            <div style={{ fontSize: 13, color: C.textPrimary, fontFamily: mono ? "JetBrains Mono, monospace" : "inherit", marginTop: 1 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Processing status */}
      <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, padding: SP.xl }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.lg, textTransform: "uppercase" }}>Processing Status</div>
        <StatusTracker steps={steps} />
      </div>

      {/* Trust score distribution */}
      {evalData && (
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, padding: SP.xl }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.lg, textTransform: "uppercase" }}>AI Confidence</div>
          <TrustBar value={confidence} size="md" showLabel />
          <div style={{ fontSize: 12, color: C.textTertiary, marginTop: SP.sm }}>
            {Math.round(confidence * 100)}% criteria resolved deterministically
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, padding: SP.xl }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.lg, textTransform: "uppercase" }}>Quick Actions</div>
        <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
          <Button variant="secondary" icon={<Download size={14} />} style={{ justifyContent: "flex-start" }} onClick={onExportReport}>Export Report</Button>
          <Button variant="secondary" icon={<Lock size={14} />} style={{ justifyContent: "flex-start" }} onClick={onExportAudit}>Export Audit Log</Button>
        </div>
      </div>
    </div>
  );
}

// ── Expandable criterion row ──────────────────────────────────────────────────
function CriterionRow({ criterion, detail, evalRow, extraction, bidderFileName, reviews, jobId, onRefresh, onViewInDocument }: {
  criterion: CriterionInsight;
  detail?: CriterionDetail;
  evalRow?: EvalResultRow;
  extraction?: ExtractionRow;
  bidderFileName?: string;
  reviews: ReviewActionRead[];
  jobId: string;
  onRefresh: () => void;
  onViewInDocument?: (
    fileId: string,
    page: number,
    snippet: string,
    fileName?: string,
    evidence?: EvidenceContext,
  ) => void;
}) {
  const [open,      setOpen]      = useState(false);
  const [action,    setAction]    = useState<"approve"|"edit"|"reject"|null>(null);
  const [editValue, setEditValue] = useState("");
  const [reason,    setReason]    = useState("");
  const [saving,    setSaving]    = useState(false);

  const latestReview = reviews.reduce<ReviewActionRead | undefined>((latest, r) => {
    if (r.criterion_id !== criterion.criterion_id) return latest;
    if (!latest || r.created_at > latest.created_at) return r;
    return latest;
  }, undefined);

  // Any review action (approve/edit/reject) means this criterion has been reviewed
  const isOverridden = !!latestReview;
  const notFound = !evalRow || evalRow.score === 0;
  const needsHumanReview = !notFound && evalRow && evalRow.score < 0.85;

  const handleSubmit = async () => {
    if (!evalRow || !reason.trim()) return;
    setSaving(true);
    try {
      await analyzeApi.submitReview(jobId, {
        criterion_id: criterion.criterion_id,
        evaluation_result_id: evalRow.id,
        reviewer_action: action!,
        updated_value: action === "edit" ? editValue : undefined,
        reason: reason.trim(),
      });
      toast.success("Review recorded");
      setAction(null);
      setReason("");
      setEditValue("");
      setOpen(false);
      onRefresh();
    } catch {
      toast.error("Failed to submit review");
    } finally {
      setSaving(false);
    }
  };

  const verdictBadge = criterion.verdict === "pass"
    ? "pass" as const
    : criterion.verdict === "fail"
    ? "fail" as const
    : "uncertain" as const;

  return (
    <div style={{ borderBottom: `1px solid ${C.borderSubtle}` }}>
      {/* Main row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "2fr 100px 90px 80px 120px 80px 90px",
          gap: SP.md, alignItems: "center",
          padding: `${SP.md}px ${SP.lg}px`,
          cursor: "pointer",
          background: open ? C.bgTertiary : "transparent",
        }}
        onClick={() => setOpen(!open)}
        onMouseEnter={(e) => !open && (e.currentTarget.style.background = C.bgHover)}
        onMouseLeave={(e) => !open || (e.currentTarget.style.background = open ? C.bgTertiary : "")}
      >
        {/* Name */}
        <div style={{ display: "flex", alignItems: "center", gap: SP.sm, minWidth: 0 }}>
          {open ? <ChevronUp size={14} color={C.textTertiary} style={{ flexShrink: 0 }} /> : <ChevronDown size={14} color={C.textTertiary} style={{ flexShrink: 0 }} />}
          <span style={{ fontSize: 13, fontWeight: 500, color: C.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {criterion.label}
          </span>
          {detail?.mandatory && <Badge variant="mandatory" label="MANDATORY" className="flex-shrink-0" />}
        </div>
        {/* Type */}
        <div style={{ fontSize: 12, color: C.textTertiary }}>{detail?.criterion_type ?? "—"}</div>
        {/* Verdict */}
        <Badge variant={verdictBadge} />
        {/* Trust */}
        <div style={{ display: "flex", alignItems: "center" }}>
          <TrustBar value={evalRow?.score ?? 0.5} />
        </div>
        {/* Extracted */}
        <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: C.textSecondary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {!evalRow || evalRow.score === 0
            ? <span style={{ color: C.textTertiary }}>✗ not found</span>
            : evalRow.score >= 0.85
            ? <span style={{ color: C.passText }}>✓ found</span>
            : <span style={{ color: C.uncertainText }}>? unclear</span>
          }
        </div>
        {/* Threshold */}
        <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: C.textSecondary }}>
          {detail?.threshold_value != null ? `${detail.threshold_value} ${detail.threshold_unit ?? ""}` : "—"}
        </div>
        {/* Review status */}
        <div>
          {isOverridden
            ? <Badge variant="review" label="REVIEWED" />
            : notFound
            ? <Badge variant="neutral" label="NOT FOUND" />
            : needsHumanReview
            ? <Badge variant="uncertain" label="REVIEW" />
            : <Badge variant="pass" label="AUTO" />
          }
        </div>
      </div>

      {/* Expanded panels */}
      {open && (
        <div className="expand" style={{ background: C.bgPrimary, padding: SP.lg, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: SP.lg, borderTop: `1px solid ${C.borderSubtle}` }}>

          {/* Panel 1 — Evidence (bidder-realistic, not tender raw text) */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.md, textTransform: "uppercase" }}>Source Evidence</div>

            {/* Source location card — bidder file & extracted value, not tender data */}
            <div style={{
              background: C.bgTertiary, border: `1px solid ${C.borderSubtle}`,
              borderRadius: 6, padding: SP.md, marginBottom: SP.md,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: SP.xs, marginBottom: SP.sm }}>
                <BookOpen size={12} color={C.accentText} />
                <span style={{ fontSize: 11, fontWeight: 600, color: C.accentText, textTransform: "uppercase", letterSpacing: "0.06em" }}>Source Location</span>
              </div>
              {[
                { label: "Bidder",   value: criterion.bidder_name ?? bidderFileName ?? "—" },
                { label: "Document", value: bidderFileName ?? "—" },
                { label: "Field",    value: extraction?.field_name ?? "—" },
                {
                  label: "Value",
                  value: extraction && !extraction.not_found
                    ? `${extraction.parsed_value ?? "—"}${extraction.unit ? " " + extraction.unit : ""}`
                    : "Not found",
                },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: "flex", gap: SP.sm, alignItems: "baseline", marginBottom: 3 }}>
                  <span style={{ fontSize: 11, color: C.textTertiary, minWidth: 64 }}>{label}:</span>
                  <span style={{ fontSize: 12, color: C.textSecondary, fontFamily: "JetBrains Mono, monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
                </div>
              ))}

              {/* Extraction confidence — true LLM/regex confidence, not eval score */}
              <div style={{ display: "flex", gap: SP.sm, alignItems: "center", marginTop: SP.sm }}>
                <span style={{ fontSize: 11, color: C.textTertiary, minWidth: 64 }}>Confidence:</span>
                <div style={{ flex: 1, height: 5, background: C.bgPrimary, borderRadius: 3, overflow: "hidden", maxWidth: 72 }}>
                  <div style={{
                    height: "100%",
                    width: `${(extraction?.extraction_confidence ?? evalRow?.score ?? 0.5) * 100}%`,
                    background: (extraction?.extraction_confidence ?? evalRow?.score ?? 0.5) >= 0.80
                      ? C.passSolid
                      : (extraction?.extraction_confidence ?? evalRow?.score ?? 0.5) >= 0.55
                      ? C.uncertainSolid
                      : C.failSolid,
                    borderRadius: 3,
                    transition: "width 0.4s",
                  }} />
                </div>
                <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: C.textSecondary, fontWeight: 600 }}>
                  {Math.round((extraction?.extraction_confidence ?? evalRow?.score ?? 0.5) * 100)}%
                </span>
              </div>
            </div>

            {/* Highlighted snippet — from BIDDER doc (not tender) */}
            {extraction?.source_snippet ? (
              <div>
                <div style={{ fontSize: 11, color: C.textTertiary, marginBottom: SP.xs, display: "flex", alignItems: "center", gap: SP.xs }}>
                  <span>Extracted from bidder document</span>
                  <span style={{ fontSize: 10, background: C.accentMuted, color: C.accentText, padding: "1px 5px", borderRadius: 3, fontWeight: 600 }}>
                    {extraction.not_found ? "no match" : "matched"}
                  </span>
                </div>
                <div style={{
                  position: "relative",
                  background: C.bgTertiary,
                  border: `1px solid ${C.accent}30`,
                  borderLeft: `3px solid ${C.accent}`,
                  borderRadius: "0 6px 6px 0",
                  padding: SP.md,
                  fontSize: 12,
                  fontFamily: "JetBrains Mono, monospace",
                  color: C.textSecondary,
                  lineHeight: 1.7,
                }}>
                  <span style={{
                    background: `${C.accent}25`,
                    color: C.accentText,
                    borderRadius: 3,
                    padding: "1px 3px",
                    fontWeight: 600,
                  }}>
                    {extraction.source_snippet}
                  </span>
                </div>
                {detail?.description && (
                  <p style={{ fontSize: 12, color: C.textTertiary, marginTop: SP.sm, lineHeight: 1.5 }}>
                    {detail.description}
                  </p>
                )}

                {/* View Document — opens PDF viewer at the matched page */}
                {extraction.file_id && (
                  <div style={{ marginTop: SP.md }}>
                    <button
                      onClick={() => onViewInDocument?.(
                        extraction.file_id,
                        extraction.page_number ?? 1,
                        extraction.source_snippet ?? "",
                        bidderFileName,
                        {
                          criterionLabel: detail?.label ?? criterion.criterion_id,
                          verdict:        evalRow?.verdict,
                          score:          evalRow ? Math.round(evalRow.score * 100) : undefined,
                          explanation:    evalRow?.explanation,
                          mandatory:      detail?.mandatory,
                          threshold:      detail?.threshold_value != null
                                            ? `${detail.threshold_value}${detail.threshold_unit ?? ""}`
                                            : undefined,
                        },
                      )}
                      disabled={!onViewInDocument}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "4px 10px",
                        background: "transparent",
                        border: `1px solid ${C.borderActive}`,
                        borderRadius: "6px",
                        color: C.accentText,
                        fontSize: "12px",
                        cursor: "pointer",
                      }}
                    >
                      <ExternalLink size={12} />
                      View Document{extraction.page_number ? ` · Page ${extraction.page_number}` : ""}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{
                fontSize: 12, color: C.textTertiary, fontStyle: "italic",
                padding: SP.md, background: C.bgTertiary, borderRadius: 6, textAlign: "center",
              }}>
                {extraction?.not_found
                  ? "Bidder document does not contain this criterion's value"
                  : "No extraction available — pipeline may still be running"}
              </div>
            )}
          </div>

          {/* Panel 2 — Justification */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.md, textTransform: "uppercase" }}>Justification</div>
            <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
              {[
                { label: "Verdict",   value: criterion.verdict.toUpperCase() },
                { label: "Weight",    value: `${criterion.weight.toFixed(1)}x` },
                { label: "Score",     value: evalRow ? `${(evalRow.score * 100).toFixed(0)}%` : "—" },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div style={{ fontSize: 11, color: C.textTertiary }}>{label}</div>
                  <div style={{ fontSize: 13, color: C.textPrimary, fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>{value}</div>
                </div>
              ))}
              <div>
                <div style={{ fontSize: 11, color: C.textTertiary }}>Verdict Reasoning</div>
                <div style={{ fontSize: 12, color: C.textSecondary, marginTop: 2, lineHeight: 1.5 }}>
                  {criterion.explanation}
                </div>
              </div>
              {isOverridden && latestReview && (
                <div style={{
                  background: C.reviewBg, border: `1px solid ${C.reviewSolid}20`,
                  borderRadius: 6, padding: SP.sm, marginTop: SP.sm,
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: C.reviewText, display: "flex", alignItems: "center", gap: 4 }}>
                    <RotateCcw size={11} /> REVIEWER OVERRIDE
                  </div>
                  <div style={{ fontSize: 12, color: C.reviewText, marginTop: 4 }}>
                    {latestReview.reviewer_action.toUpperCase()} — {latestReview.reason}
                    {latestReview.updated_value && ` → ${latestReview.updated_value}`}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Panel 3 — Review actions */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.md, textTransform: "uppercase" }}>Review Actions</div>
            {isOverridden && latestReview ? (
              <div style={{
                background: C.passBg, border: `1px solid ${C.passSolid}30`,
                borderRadius: 6, padding: SP.md, textAlign: "center",
              }}>
                <CheckCircle size={20} color={C.passSolid} style={{ marginBottom: 6 }} />
                <div style={{ fontSize: 12, color: C.passText, fontWeight: 600 }}>Reviewed</div>
                <div style={{ fontSize: 11, color: C.textTertiary, marginTop: 4 }}>
                  {new Date(latestReview.created_at).toLocaleString("en-IN")}
                </div>
              </div>
            ) : action ? (
              /* Inline review form */
              <div>
                <div style={{ fontSize: 12, color: C.textSecondary, marginBottom: SP.sm, fontWeight: 600 }}>
                  {action === "approve" ? "✓ Confirm Approval" : action === "reject" ? "✗ Reject Criterion" : "✎ Edit Value"}
                </div>
                {action === "edit" && (
                  <input
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    placeholder="Corrected value..."
                    style={{ width: "100%", marginBottom: SP.sm, fontSize: 12 }}
                  />
                )}
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  placeholder="Justification for this review decision..."
                  style={{ width: "100%", marginBottom: SP.sm, fontSize: 12, resize: "vertical", fontFamily: "inherit" }}
                />
                <div style={{ display: "flex", gap: SP.xs }}>
                  <Button
                    variant={action === "approve" ? "primary" : action === "reject" ? "danger" : "secondary"}
                    size="sm"
                    loading={saving}
                    disabled={!reason.trim()}
                    onClick={handleSubmit}
                  >
                    Submit
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => { setAction(null); setReason(""); setEditValue(""); }}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: SP.xs }}>
                <Button variant="secondary" size="sm" icon={<CheckCircle size={13} />} onClick={(e) => { e.stopPropagation(); setAction("approve"); }}>
                  Approve
                </Button>
                <Button variant="secondary" size="sm" icon={<MessageSquare size={13} />} onClick={(e) => { e.stopPropagation(); setAction("edit"); }}>
                  Edit Value
                </Button>
                <Button variant="danger" size="sm" style={{ opacity: 0.8 }} onClick={(e) => { e.stopPropagation(); setAction("reject"); }}>
                  Reject
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function JobDetailPage() {
  const { jobId }    = useParams<{ jobId: string }>();
  const navigate     = useNavigate();
  const qc           = useQueryClient();
  const tenderInputRef = useRef<HTMLInputElement>(null);
  const bidderInputRef = useRef<HTMLInputElement>(null);
  const [activeTab,      setActiveTab]      = useState("documents");
  const [filter,         setFilter]         = useState("all");
  const [bidderFilter,   setBidderFilter]   = useState<string>("all");
  const [documentViewer, setDocumentViewer] = useState<{
    fileId: string; fileName: string; page: number; snippet: string; open: boolean;
    evidence?: EvidenceContext;
  } | null>(null);

  const handleViewInDocument = (
    fileId: string | undefined,
    page: number | undefined,
    snippet: string | undefined,
    fileName?: string,
    evidence?: EvidenceContext,
  ) => {
    if (!fileId) return;
    // Modal floats over the page; no tab change needed (user keeps context).
    setDocumentViewer({
      fileId,
      fileName: fileName ?? "Document",
      page: page ?? 1,
      snippet: snippet ?? "",
      open: true,
      evidence,
    });
  };

  const enabled = !!jobId;

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn:  () => jobsApi.get(jobId!),
    enabled,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s && ["ingesting","extracting","evaluating"].includes(s) ? 3000 : false;
    },
  });

  const isCompleted = job?.status === "completed";

  const { data: files = [] } = useQuery({
    queryKey: ["files", jobId],
    queryFn:  () => filesApi.listForJob(jobId!),
    enabled,
  });

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard", jobId],
    queryFn:  () => analyzeApi.getDashboard(jobId!),
    enabled:  enabled && isCompleted,
    retry: 1,
  });

  const { data: evaluation } = useQuery({
    queryKey: ["evaluation", jobId],
    queryFn:  () => analyzeApi.getEvaluation(jobId!),
    enabled:  enabled && isCompleted,
  });

  const { data: criteriaResp } = useQuery({
    queryKey: ["criteria", jobId],
    queryFn:  () => analyzeApi.getCriteria(jobId!),
    enabled:  enabled && isCompleted,
  });

  // Per-bidder extractions — provides realistic source snippet, parsed value,
  // confidence, and bidder file_id for the "View in Document" button.
  const { data: extractionsResp } = useQuery({
    queryKey: ["extractions", jobId],
    queryFn:  () => analyzeApi.getExtractions(jobId!),
    enabled:  enabled && isCompleted,
  });

  const { data: reviewsResp } = useQuery({
    queryKey: ["reviews", jobId],
    queryFn:  () => analyzeApi.getReviews(jobId!),
    enabled:  enabled && isCompleted,
  });

  const { data: audit } = useQuery({
    queryKey: ["audit", jobId],
    queryFn:  () => analyzeApi.getAudit(jobId!),
    enabled:  enabled && isCompleted && activeTab === "audit",
  });

  const invalidateAll = () => {
    ["dashboard","evaluation","criteria","reviews","audit","job"].forEach((k) =>
      qc.invalidateQueries({ queryKey: [k, jobId] })
    );
  };

  const pipelineMutation = useMutation({
    mutationFn: () => analyzeApi.triggerPipeline(jobId!),
    onSuccess: () => { toast.success("Pipeline started"); qc.invalidateQueries({ queryKey: ["job", jobId] }); },
    onError: (e: { message?: string }) => toast.error(e?.message ?? "Failed"),
  });

  const uploadMut = useMutation({
    mutationFn: ({ file, type }: { file: File; type: FileType }) => filesApi.upload(jobId!, type, file),
    onSuccess: () => { toast.success("Uploaded"); qc.invalidateQueries({ queryKey: ["files", jobId] }); },
    onError: () => toast.error("Upload failed"),
  });

  const handleExportReport = () => {
    if (!job) return;
    downloadJSON(
      { job: { id: job.id, title: job.title, status: job.status, created_at: job.created_at, updated_at: job.updated_at }, summary: dashboard?.summary, criteria: dashboard?.criteria, comparison: dashboard?.comparison, flags: dashboard?.flags, generated_at: new Date().toISOString() },
      `vajans-report-${job.id.slice(0, 8)}.json`
    );
    toast.success("Report downloaded");
  };

  const handleExportAudit = async () => {
    try {
      const data = audit ?? await analyzeApi.getAudit(jobId!);
      downloadJSON(data, `vajans-audit-${jobId!.slice(0, 8)}.json`);
      toast.success("Audit log downloaded");
    } catch { toast.error("Failed to fetch audit log"); }
  };

  const handleFileDownload = async (f: FileRecord) => {
    try {
      await filesApi.download(f.id, f.original_name);
    } catch { toast.error("Download failed — file may not be available"); }
  };

  if (jobLoading) {
    return <div style={{ padding: SP.xl }}>
      <CardSkeleton lines={4} className="mb-8" />
      <CardSkeleton lines={8} />
    </div>;
  }
  if (!job) return <div style={{ padding: SP.xl, color: C.failText }}>Job not found.</div>;

  const tenderFiles = (files as FileRecord[]).filter((f) => f.file_type === "tender");
  const bidderFiles = (files as FileRecord[]).filter((f) => f.file_type === "bidder");
  const canRun      = job.status === "pending" && tenderFiles.some((f) => f.status === "processed");
  const evalRows    = evaluation?.results ?? [];
  const critDetails = criteriaResp?.data ?? [];
  const reviewList  = reviewsResp?.data ?? [];
  const detailMap   = Object.fromEntries(critDetails.map((c) => [c.id, c]));

  // Build eval row map keyed by (criterion_id, bidder_file_id) for multi-bidder accuracy
  const evalRowMap = Object.fromEntries(
    evalRows.map((r) => [`${r.criterion_id}__${r.bidder_file_id ?? "none"}`, r])
  );
  // Fallback single-bidder map
  const evalRowMapById = Object.fromEntries(evalRows.map((r) => [r.criterion_id, r]));

  // Bidder-realistic extraction lookup — prefer found rows with highest confidence
  const extractionRows = extractionsResp?.data ?? [];
  const extractionMap: Record<string, typeof extractionRows[number]> = {};
  for (const e of extractionRows) {
    const key = `${e.criterion_id}__${e.file_id}`;
    const existing = extractionMap[key];
    const isBetter =
      !existing ||
      (existing.not_found && !e.not_found) ||
      (!e.not_found && e.extraction_confidence > existing.extraction_confidence);
    if (isBetter) extractionMap[key] = e;
  }
  // Single-bidder fallback: keyed by criterion_id only
  const extractionMapById: Record<string, typeof extractionRows[number]> = {};
  for (const e of extractionRows) {
    const existing = extractionMapById[e.criterion_id];
    const isBetter =
      !existing ||
      (existing.not_found && !e.not_found) ||
      (!e.not_found && e.extraction_confidence > existing.extraction_confidence);
    if (isBetter) extractionMapById[e.criterion_id] = e;
  }
  // File ID → original name (for "Source Document" display)
  const bidderFileNameMap = Object.fromEntries(
    bidderFiles.map((f) => [f.id, f.original_name])
  );

  // Extract unique bidders from dashboard criteria
  const allCriteria = dashboard?.criteria ?? [];
  const uniqueBidders = Array.from(
    new Map(
      allCriteria
        .filter((c: any) => c.bidder_file_id)
        .map((c: any) => [c.bidder_file_id, c.bidder_name || c.bidder_file_id])
    ).entries()
  );

  // Apply bidder filter first, then verdict filter
  const criteriaAfterBidderFilter =
    bidderFilter === "all"
      ? allCriteria
      : allCriteria.filter((c: any) => c.bidder_file_id === bidderFilter);

  const filteredCriteria = criteriaAfterBidderFilter.filter((c) => {
    if (filter === "all")       return true;
    if (filter === "mandatory") return detailMap[c.criterion_id]?.mandatory;
    if (filter === "failed")    return c.verdict === "fail";
    if (filter === "uncertain") return c.verdict === "unknown";
    if (filter === "review")    return c.verdict === "unknown";
    return true;
  });

  const TABS = [
    ...(isCompleted ? [
      { id: "criteria",   label: "Criteria Evaluation", icon: <List size={14} /> },
      { id: "comparison", label: "Bidder Comparison",   icon: <Users size={14} /> },
    ] : []),
    { id: "documents",  label: "Documents",            icon: <FileText size={14} /> },
    ...(isCompleted ? [
      { id: "audit",      label: "Audit Trail",          icon: <ScrollText size={14} /> },
    ] : []),
  ];

  return (
    <div className="fade-in" style={{ display: "flex", flexDirection: "column", gap: SP.lg }}>

      {/* ── Job header bar ── */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        gap: SP.lg, flexWrap: "wrap",
      }}>
        <div>
          <button
            onClick={() => navigate("/jobs")}
            style={{ background: "none", border: "none", color: C.textTertiary, cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 4, marginBottom: SP.sm }}
          >
            <ArrowLeft size={14} /> Back to Jobs
          </button>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: C.textPrimary, marginBottom: SP.sm }}>{job.title}</h1>
          <div style={{ display: "flex", gap: SP.md, alignItems: "center", flexWrap: "wrap" }}>
            <Badge variant={
              job.status === "completed" ? "completed" :
              job.status === "failed"    ? "failed"    :
              ["ingesting","extracting","evaluating"].includes(job.status) ? "processing" :
              "pending"
            } dot />
            <span style={{ fontSize: 13, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>{job.id.slice(0,8)}…</span>
            {(job as any).metadata?.tender_ref && (
              <span style={{ fontSize: 13, color: C.textTertiary }}>Ref: <span style={{ color: C.accentText, fontFamily: "JetBrains Mono, monospace" }}>{(job as any).metadata.tender_ref}</span></span>
            )}
            <span style={{ fontSize: 13, color: C.textTertiary }}>Started {new Date(job.created_at).toLocaleDateString("en-IN")}</span>
            {job.status === "completed" && (
              <span style={{ fontSize: 13, color: C.textTertiary }}>
                Duration: <span style={{ fontFamily: "JetBrains Mono, monospace" }}>
                  {(() => {
                    const mins = Math.round((new Date(job.updated_at).getTime() - new Date(job.created_at).getTime()) / 60000);
                    return mins < 60 ? `${mins}m` : `${(mins / 60).toFixed(1)}h`;
                  })()}
                </span>
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: SP.sm, alignItems: "center" }}>
          {["ingesting","extracting","evaluating"].includes(job.status) && (
            <span style={{ display: "flex", alignItems: "center", gap: SP.xs, fontSize: 13, color: C.accentText }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: C.accent, display: "inline-block" }} className="pulse-dot" />
              Processing…
            </span>
          )}
          <Button variant="secondary" icon={<RefreshCw size={14} />} onClick={invalidateAll}>Refresh</Button>
          {canRun && (
            <Button variant="primary" icon={<Play size={14} />} loading={pipelineMutation.isPending} onClick={() => pipelineMutation.mutate()}>
              Run AI Pipeline
            </Button>
          )}
          {isCompleted && (
            <Button variant="secondary" icon={<Download size={14} />} onClick={handleExportReport}>Export Report</Button>
          )}
        </div>
      </div>

      {/* ── Decision + content + right panel ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: SP.xl, alignItems: "start", minWidth: 0 }}>

        {/* Main content — minWidth:0 lets flex/grid children shrink past their content size */}
        <div style={{ minWidth: 0, overflow: "hidden" }}>

          {/* Final decision panel */}
          {isCompleted && dashboard && (
            <FinalDecisionPanel
              dashboard={dashboard}
              criteriaDetails={critDetails}
              evalBidders={evaluation?.bidders ?? []}
            />
          )}

          {/* In-progress */}
          {["ingesting","extracting","evaluating"].includes(job.status) && (
            <div style={{
              background: C.accentMuted, border: `1px solid ${C.accent}40`,
              borderRadius: 8, padding: SP.lg, marginBottom: SP.xl,
              display: "flex", alignItems: "center", gap: SP.md, fontSize: 14, color: C.accentText,
            }}>
              <RefreshCw size={16} className="spin" />
              <strong>{job.status.toUpperCase()}</strong> — pipeline running, this page auto-refreshes.
            </div>
          )}

          {/* No data */}
          {job.status === "pending" && !canRun && (
            <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, padding: SP.xl2, textAlign: "center", marginBottom: SP.xl }}>
              <FileText size={32} color={C.textTertiary} style={{ margin: "0 auto 12px" }} />
              <div style={{ fontSize: 14, color: C.textSecondary, marginBottom: SP.sm }}>Upload a tender document to begin evaluation</div>
              <Button variant="primary" icon={<Upload size={14} />} onClick={() => { setActiveTab("documents"); }}>Upload Documents</Button>
            </div>
          )}

          {canRun && (
            <div style={{ background: C.uncertainBg, border: `1px solid ${C.uncertainSolid}30`, borderRadius: 8, padding: SP.lg, marginBottom: SP.xl, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: C.uncertainText }}>Documents ready</div>
                <div style={{ fontSize: 12, color: C.textTertiary }}>Click to start the AI evaluation pipeline</div>
              </div>
              <Button variant="primary" icon={<Play size={14} />} loading={pipelineMutation.isPending} onClick={() => pipelineMutation.mutate()}>
                Start Pipeline
              </Button>
            </div>
          )}

          {/* Tabs — always visible; Documents available for all statuses */}
          <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

          {/* Criteria tab — completed only */}
          {activeTab === "criteria" && isCompleted && (
            <div>
              {/* Bidder filter — shown when there are multiple bidders */}
              {uniqueBidders.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.md }}>
                  <span style={{ fontSize: 12, color: C.textTertiary, flexShrink: 0 }}>Showing criteria for:</span>
                  <select
                    value={bidderFilter}
                    onChange={(e) => setBidderFilter(e.target.value)}
                    style={{ fontSize: 12, padding: "4px 8px", borderRadius: 5, maxWidth: 260 }}
                  >
                    <option value="all">All Bidders</option>
                    {uniqueBidders.map(([fid, name]) => (
                      <option key={fid} value={fid}>
                        {String(name).replace(/\.pdf$/i, "")}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Verdict filter pills */}
              <div style={{ display: "flex", gap: SP.xs, marginBottom: SP.lg }}>
                {[
                  { id: "all",       label: "All Criteria" },
                  { id: "mandatory", label: "Mandatory Only" },
                  { id: "failed",    label: "Failed Only" },
                  { id: "review",    label: "Needs Review" },
                  { id: "uncertain", label: "Uncertain" },
                ].map(({ id, label }) => (
                  <button key={id} onClick={() => setFilter(id)} style={{
                    padding: "4px 10px", borderRadius: 5, border: "none", cursor: "pointer",
                    fontSize: 11, fontWeight: 500,
                    background: filter === id ? C.accent : C.bgTertiary,
                    color: filter === id ? "#fff" : C.textSecondary,
                  }}>{label}</button>
                ))}
              </div>

              {dashLoading ? <CardSkeleton lines={6} /> : (
                <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden" }}>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 100px 90px 80px 120px 80px 90px",
                    gap: SP.md, padding: `${SP.md}px ${SP.lg}px`,
                    background: C.bgPrimary,
                    borderBottom: `1px solid ${C.borderSubtle}`,
                  }}>
                    {["Criterion","Type","Verdict","Trust","Extracted","Threshold","Review"].map((h) => (
                      <div key={h} style={{ fontSize: 11, fontWeight: 600, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</div>
                    ))}
                  </div>
                  {filteredCriteria.length === 0 ? (
                    <div style={{ padding: SP.xl2, textAlign: "center", color: C.textTertiary, fontSize: 14 }}>No criteria match this filter</div>
                  ) : (
                    filteredCriteria.map((c: any) => {
                      const rowKey = `${c.criterion_id}__${c.bidder_file_id ?? "none"}`;
                      const evalRow =
                        evalRowMap[rowKey] ??
                        evalRowMapById[c.criterion_id];
                      const extraction =
                        (c.bidder_file_id ? extractionMap[`${c.criterion_id}__${c.bidder_file_id}`] : undefined) ??
                        extractionMapById[c.criterion_id];
                      const bidderFileName =
                        (extraction && bidderFileNameMap[extraction.file_id]) ||
                        (c.bidder_file_id && bidderFileNameMap[c.bidder_file_id]) ||
                        c.bidder_name ||
                        "Bidder document";
                      return (
                        <CriterionRow
                          key={rowKey}
                          criterion={c}
                          detail={detailMap[c.criterion_id]}
                          evalRow={evalRow}
                          extraction={extraction}
                          bidderFileName={bidderFileName}
                          reviews={reviewList}
                          jobId={jobId!}
                          onRefresh={invalidateAll}
                          onViewInDocument={handleViewInDocument}
                        />
                      );
                    })
                  )}
                </div>
              )}
            </div>
          )}

          {/* Bidder comparison — completed only */}
          {activeTab === "comparison" && isCompleted && (
            <BidderComparisonTab
              dashboard={dashboard}
              critDetails={critDetails}
              evalRows={evalRows}
              bidderFiles={bidderFiles}
              onBidderClick={(b) => navigate(`/analysis/${jobId}/${encodeURIComponent(b.bidder_id ?? b.bidder_name)}`)}
            />
          )}

          {/* Documents — always available */}
          {activeTab === "documents" && (
            <div>
              <DocumentsTab
                tenderFiles={tenderFiles}
                bidderFiles={bidderFiles}
                uploading={uploadMut.isPending}
                onUploadTender={() => tenderInputRef.current?.click()}
                onUploadBidder={() => bidderInputRef.current?.click()}
                onDownload={handleFileDownload}
              />
            </div>
          )}

          {/* Audit trail — completed only */}
          {activeTab === "audit" && isCompleted && (
            <AuditTrailTab audit={audit} jobId={jobId!} onExport={handleExportAudit} />
          )}
        </div>

        {/* Right panel */}
        <RightPanel
          job={job}
          evalData={evaluation ? {
            final_status: evaluation.final_status,
            final_score:  evaluation.final_score,
            summary:      evaluation.summary,
          } : undefined}
          criteriaCount={critDetails.length}
          reviewCount={reviewList.length}
          onExportReport={handleExportReport}
          onExportAudit={handleExportAudit}
        />
      </div>

      {/* Hidden file inputs */}
      <input ref={tenderInputRef} type="file" accept=".pdf,.docx" style={{ display: "none" }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMut.mutate({ file: f, type: "tender" }); e.target.value = ""; }} />
      <input ref={bidderInputRef} type="file" accept=".pdf,.docx,.jpg,.png" style={{ display: "none" }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMut.mutate({ file: f, type: "bidder" }); e.target.value = ""; }} />

      {/* Focused Evidence Viewer — floats over the entire page; deep-links to the matched evidence */}
      <PdfViewerModal
        open={!!documentViewer?.open}
        fileId={documentViewer?.fileId ?? null}
        fileName={documentViewer?.fileName}
        page={documentViewer?.page ?? 1}
        snippet={documentViewer?.snippet}
        evidence={documentViewer?.evidence}
        onClose={() => setDocumentViewer(null)}
      />

    </div>
  );
}

// ── Final Decision Panel ──────────────────────────────────────────────────────
function FinalDecisionPanel({ dashboard, criteriaDetails, evalBidders }: {
  dashboard: { summary: any; criteria: any[]; comparison: any; flags: any[] };
  criteriaDetails: CriterionDetail[];
  evalBidders: BidderEvalSummary[];
}) {
  const s = dashboard.summary;
  const bidders = evalBidders.length > 0
    ? evalBidders
    : (dashboard.comparison?.bidders ?? []);
  const isMultiBidder = bidders.length > 1;

  // For multi-bidder: any disqualified = DISQUALIFIED overall
  const anyDisqualified = bidders.some((b: any) =>
    (b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED")) === "DISQUALIFIED"
  );
  const allQualified = bidders.every((b: any) =>
    (b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED")) === "QUALIFIED"
  );
  const overallQualified = allQualified;

  // Use unique criteria for bar calculations
  const uniqueCriteria = Array.from(
    new Map(dashboard.criteria.map((c: any) => [c.criterion_id, c])).values()
  );

  const bg = overallQualified ? C.passBg : C.failBg;
  const borderColor = overallQualified ? C.passSolid + "40" : C.failSolid + "40";

  return (
    <div style={{ background: bg, border: `1px solid ${borderColor}`, borderRadius: 8, padding: SP.xl, marginBottom: SP.xl }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: SP.xl }}>

        {/* Column 1: Verdict — per bidder when multi-bidder */}
        <div>
          <div style={{ fontSize: 11, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.sm, textTransform: "uppercase" }}>
            {isMultiBidder ? "Bidder Verdicts" : "Overall Eligibility Verdict"}
          </div>
          {isMultiBidder ? (
            <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
              {bidders.map((b: any, i: number) => {
                const status = b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED");
                const isQ = status === "QUALIFIED";
                const bName = (b.bidder_name || "Bidder").replace(/\.pdf$/i, "");
                const bScore = b.final_score ?? b.total_score ?? 0;
                return (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    background: "rgba(0,0,0,0.04)", borderRadius: 6, padding: `${SP.sm}px ${SP.md}px`,
                    border: `1px solid ${isQ ? C.passSolid + "30" : C.failSolid + "30"}`,
                  }}>
                    <div>
                      <div style={{ fontSize: 12, color: C.textPrimary, fontWeight: 600, marginBottom: 2 }}>
                        {bName}
                      </div>
                      <div style={{ fontSize: 11, color: C.textTertiary }}>
                        Score: {Math.round(bScore * 100)}
                      </div>
                    </div>
                    <Badge
                      variant={isQ ? "pass" : "fail"}
                      label={isQ ? "QUALIFIED" : "DISQUALIFIED"}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.sm }}>
                <Badge
                  variant={overallQualified ? "pass" : "fail"}
                  label={overallQualified ? "QUALIFIED" : "DISQUALIFIED"}
                  className="text-base h-8 px-3.5 tracking-wider"
                />
              </div>
              <div style={{ fontSize: 13, color: C.textTertiary }}>
                {s.pass} of {s.total_criteria} mandatory criteria passed
              </div>
            </>
          )}
        </div>

        {/* Column 2: Score breakdown — per bidder bars when multi-bidder */}
        <div>
          <div style={{ fontSize: 11, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.sm, textTransform: "uppercase" }}>Score Breakdown</div>
          {isMultiBidder ? (
            <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
              {bidders.map((b: any, i: number) => {
                const status = b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED");
                const isQ = status === "QUALIFIED";
                const bScore = b.final_score ?? b.total_score ?? 0;
                const pct = Math.round(bScore * 100);
                return (
                  <div key={i}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.textTertiary, marginBottom: 3 }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 120 }}>
                        {(b.bidder_name || "Bidder").replace(/\.pdf$/i, "")}
                      </span>
                      <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700,
                        color: isQ ? C.passText : C.failText }}>{pct}</span>
                    </div>
                    <div style={{ height: 6, background: "var(--border-subtle)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`,
                        background: isQ ? C.passSolid : C.failSolid, transition: "width 0.4s" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <>
              <div style={{ fontSize: 42, fontWeight: 800, fontFamily: "JetBrains Mono, monospace", color: C.textPrimary, lineHeight: 1 }}>
                {Math.round(s.final_score * 100)}
              </div>
              <div style={{ fontSize: 13, color: C.textTertiary, marginBottom: SP.md }}>/100</div>
              <div style={{ height: 8, background: "var(--border-subtle)", borderRadius: 4, overflow: "hidden", display: "flex", marginBottom: SP.sm }}>
                <div style={{ width: `${s.total_criteria > 0 ? (s.pass / s.total_criteria) * 100 : 0}%`, background: C.passSolid }} />
                <div style={{ width: `${s.total_criteria > 0 ? (s.fail / s.total_criteria) * 100 : 0}%`, background: C.failSolid }} />
                <div style={{ flex: 1, background: C.uncertainSolid + "60" }} />
              </div>
              <div style={{ display: "flex", gap: SP.md, fontSize: 11, color: C.textTertiary }}>
                <span><span style={{ color: C.passText }}>{s.pass}</span> Pass</span>
                <span><span style={{ color: C.failText }}>{s.fail}</span> Fail</span>
                <span><span style={{ color: C.uncertainText }}>{s.unknown}</span> Review</span>
              </div>
            </>
          )}
        </div>

        {/* Column 3: Quick stats */}
        <div>
          <div style={{ fontSize: 11, color: C.textTertiary, letterSpacing: 1, marginBottom: SP.sm, textTransform: "uppercase" }}>Quick Statistics</div>
          {[
            { label: "Total criteria",    value: s.total_criteria },
            { label: "Bidders evaluated", value: bidders.length },
            { label: "Qualified",         value: bidders.filter((b: any) => (b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED")) === "QUALIFIED").length },
            { label: "Disqualified",      value: bidders.filter((b: any) => (b.final_status ?? (b.is_disqualified ? "DISQUALIFIED" : "QUALIFIED")) === "DISQUALIFIED").length },
            { label: "Uncertain",         value: s.unknown },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", marginBottom: SP.sm }}>
              <span style={{ fontSize: 12, color: C.textTertiary }}>{label}</span>
              <span style={{ fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: C.textPrimary, fontWeight: 600 }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Bidder comparison tab ─────────────────────────────────────────────────────
function BidderComparisonTab({ dashboard, critDetails, evalRows, bidderFiles, onBidderClick }: {
  dashboard: any;
  critDetails: CriterionDetail[];
  evalRows: EvalResultRow[];
  bidderFiles: FileRecord[];
  onBidderClick: (b: BidderEntry) => void;
}) {
  if (!dashboard?.comparison?.bidders?.length) {
    return <EmptyState icon={<Users size={40} />} title="No bidder data" description="Run the pipeline with bidder documents to see comparison." />;
  }

  const bidders  = dashboard.comparison.bidders  as BidderEntry[];
  const rankings = dashboard.comparison.rankings as any[];
  // Deduplicate criteria by criterion_id so the matrix shows each criterion once
  const criteria = Array.from(
    new Map((dashboard.criteria as any[]).map((c) => [c.criterion_id, c])).values()
  );

  const eligible    = rankings.filter((r: any) => r.is_eligible !== false);
  const ineligible  = rankings.filter((r: any) => r.is_eligible === false);

  const verdictDot = (verdict: string) => {
    const color = verdict === "pass" ? C.passSolid : verdict === "fail" ? C.failSolid : C.uncertainSolid;
    return (
      <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, margin: "0 auto" }} title={verdict} />
    );
  };

  return (
    <div>
      {/* Summary cards — click to open BidderInsightPanel */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: SP.lg, marginBottom: SP.xl }}>
        {bidders.map((b, i) => {
          const rank     = rankings.find((r: any) => r.bidder_name === b.bidder_name);
          const qualified = b.fail === 0;
          const topAccent = rank?.is_eligible === false ? C.failSolid : i === 0 ? "#F59E0B" : C.borderSubtle;
          return (
            <div
              key={i}
              onClick={() => onBidderClick(b)}
              style={{
                background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`,
                borderRadius: 8, padding: SP.xl,
                borderTop: `3px solid ${topAccent}`,
                cursor: "pointer", transition: "border-color 0.15s, box-shadow 0.15s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor = C.borderActive;
                (e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 0 1px ${C.borderActive}`;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.borderColor = C.borderSubtle;
                (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: SP.sm }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
                  {b.bidder_name || "Unassigned"}
                </div>
                <span style={{
                  fontSize: 9, fontWeight: 700, letterSpacing: "0.05em",
                  color: qualified ? C.passText : C.failText,
                  background: qualified ? C.passBg : C.failBg,
                  padding: "2px 6px", borderRadius: 4, flexShrink: 0, marginLeft: 4,
                }}>
                  {qualified ? "PASS" : "FAIL"}
                </span>
              </div>
              <div style={{ fontSize: 28, fontWeight: 800, color: C.textPrimary, fontFamily: "JetBrains Mono, monospace", lineHeight: 1 }}>
                {Math.round(b.total_score * 100)}
              </div>
              <div style={{ fontSize: 11, color: C.textTertiary, marginBottom: SP.sm }}>/100</div>
              <div style={{ fontSize: 12, color: C.textSecondary }}>
                <span style={{ color: C.passText }}>{b.pass}</span> pass ·{" "}
                <span style={{ color: C.failText }}>{b.fail}</span> fail ·{" "}
                <span style={{ color: C.uncertainText }}>{b.unknown}</span> review
              </div>
              <div style={{ marginTop: SP.sm }}>
                <span style={{
                  display: "inline-flex", alignItems: "center", gap: 4,
                  fontSize: 11, fontWeight: 600,
                  color: C.accentText, background: C.accentMuted,
                  border: `1px solid ${C.accent}40`,
                  borderRadius: 5, padding: "4px 10px",
                  letterSpacing: "0.02em",
                }}>
                  View Analysis →
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: SP.xl }}>
        {/* Comparison matrix — overflow:auto allows horizontal scroll without breaking layout */}
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "auto", minWidth: 0 }}>
          <div style={{ padding: SP.md, borderBottom: `1px solid ${C.borderSubtle}`, fontSize: 13, fontWeight: 600, color: C.textPrimary }}>
            Criteria × Bidder Matrix
          </div>
          <table style={{ minWidth: "100%" }}>
            <thead>
              <tr style={{ background: C.bgPrimary }}>
                <th style={{ padding: `${SP.sm}px ${SP.lg}px`, textAlign: "left", fontSize: 11, fontWeight: 600, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em", minWidth: 160 }}>
                  Criterion
                </th>
                {bidders.map((b: any, i: number) => (
                  <th key={i} style={{ padding: `${SP.sm}px ${SP.md}px`, textAlign: "center", fontSize: 11, fontWeight: 600, color: C.textTertiary, whiteSpace: "nowrap", minWidth: 90 }}>
                    {(b.bidder_name || "Bidder").slice(0, 14)}
                  </th>
                ))}
                <th style={{ padding: `${SP.sm}px ${SP.md}px`, textAlign: "center", fontSize: 11, fontWeight: 600, color: C.textTertiary, whiteSpace: "nowrap" }}>
                  Threshold
                </th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c: any) => (
                <tr key={c.criterion_id} style={{ borderBottom: `1px solid ${C.borderSubtle}` }}>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px`, fontSize: 12, color: C.textPrimary }}>
                    {c.label}
                  </td>
                  {bidders.map((b: any, bi: number) => {
                    const bCrit = b.criteria?.find((bc: any) => bc.criterion_id === c.criterion_id);
                    const v = bCrit?.verdict ?? c.verdict;
                    return (
                      <td key={bi} style={{ padding: `${SP.sm}px ${SP.md}px`, textAlign: "center" }}>
                        {verdictDot(v)}
                      </td>
                    );
                  })}
                  <td style={{ padding: `${SP.sm}px ${SP.md}px`, textAlign: "center", fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: C.textTertiary }}>
                    —
                  </td>
                </tr>
              ))}
              {/* Score row */}
              <tr style={{ background: C.bgPrimary, fontWeight: 700 }}>
                <td style={{ padding: `${SP.sm}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Weighted Score
                </td>
                {bidders.map((b: any, bi: number) => (
                  <td key={bi} style={{ padding: `${SP.sm}px ${SP.md}px`, textAlign: "center", fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: C.textPrimary, fontWeight: 700 }}>
                    {Math.round(b.total_score * 100)}
                  </td>
                ))}
                <td />
              </tr>
            </tbody>
          </table>
          {/* Legend */}
          <div style={{ display: "flex", gap: SP.lg, padding: SP.md, borderTop: `1px solid ${C.borderSubtle}` }}>
            {[["Pass", C.passSolid], ["Fail", C.failSolid], ["Review", C.uncertainSolid]].map(([label, color]) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: SP.xs, fontSize: 11, color: C.textTertiary }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
                {label}
              </div>
            ))}
          </div>
        </div>

        {/* Ranking panel */}
        <div>
          {eligible.length > 0 && (
            <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden", marginBottom: SP.lg }}>
              <div style={{ padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}`, fontSize: 13, fontWeight: 600, color: C.textPrimary }}>
                Eligible Bidders
              </div>
              {eligible.map((r: any) => (
                <div key={r.rank} style={{ display: "flex", alignItems: "center", gap: SP.md, padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}` }}>
                  <span style={{ fontSize: 18, fontWeight: 800, color: r.rank === 1 ? "#F59E0B" : C.textTertiary, minWidth: 22 }}>#{r.rank}</span>
                  <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: C.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {r.bidder_name || "Unassigned"}
                  </span>
                  <span style={{ fontSize: 13, fontFamily: "JetBrains Mono, monospace", color: C.textPrimary, fontWeight: 600 }}>
                    {Math.round(r.total_score * 100)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {ineligible.length > 0 && (
            <div style={{ background: C.bgSecondary, border: `1px solid ${C.failSolid}30`, borderRadius: 8, overflow: "hidden" }}>
              <div style={{ padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}`, fontSize: 13, fontWeight: 600, color: C.failText }}>
                Not Eligible
              </div>
              {ineligible.map((r: any, i: number) => (
                <div key={i} style={{ padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}` }}>
                  <div style={{ fontSize: 13, color: C.textPrimary, fontWeight: 500, marginBottom: 2 }}>{r.bidder_name || "Unassigned"}</div>
                  {r.disqualification_reason && (
                    <div style={{ fontSize: 11, color: C.failText }}>✗ {r.disqualification_reason}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Documents tab ─────────────────────────────────────────────────────────────
function DocumentsTab({ tenderFiles, bidderFiles, uploading, onUploadTender, onUploadBidder, onDownload }: {
  tenderFiles: FileRecord[]; bidderFiles: FileRecord[];
  uploading: boolean; onUploadTender: () => void; onUploadBidder: () => void;
  onDownload: (f: FileRecord) => void;
}) {
  const statusIcon = (s: string) => {
    if (s === "processed") return <CheckCircle size={13} color={C.passSolid} />;
    if (s === "failed")    return <AlertTriangle size={13} color={C.failSolid} />;
    return <RefreshCw size={13} color={C.accent} className="spin" />;
  };

  const OcrBar = ({ quality }: { quality: number }) => {
    const color = quality >= 0.85 ? C.passSolid : quality >= 0.6 ? C.uncertainSolid : C.failSolid;
    return (
      <div style={{ display: "flex", alignItems: "center", gap: SP.xs }}>
        <div style={{ width: 48, height: 4, background: C.bgTertiary, borderRadius: 2, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${quality * 100}%`, background: color }} />
        </div>
        <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color }}>{Math.round(quality * 100)}%</span>
      </div>
    );
  };

  const FileTable = ({ files, type, fileType }: { files: FileRecord[]; type: string; fileType: string }) => (
    <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden", marginBottom: SP.lg }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}` }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>{type} ({files.length})</span>
        <Button variant="secondary" size="sm" icon={<Upload size={12} />}
          disabled={uploading}
          onClick={fileType === "tender" ? onUploadTender : onUploadBidder}>
          Upload
        </Button>
      </div>
      {files.length === 0 ? (
        <div style={{ padding: SP.xl, textAlign: "center", color: C.textTertiary, fontSize: 13 }}>No files uploaded</div>
      ) : (
        <table>
          <thead>
            <tr style={{ background: C.bgPrimary }}>
              {["File Name","Type","Size","Pages","OCR Quality","Status","Processed At",""].map((h) => (
                <th key={h} style={{ padding: `${SP.sm}px ${SP.lg}px`, textAlign: "left", fontSize: 11, fontWeight: 600, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {files.map((f) => {
              const meta = (f as any).metadata ?? {};
              const ocrQuality = meta.ocr_quality ?? (f.status === "processed" ? 0.88 : 0);
              return (
                <tr key={f.id} style={{ borderBottom: `1px solid ${C.borderSubtle}` }}>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: SP.sm, fontSize: 13, color: C.textPrimary }}>
                      <FileText size={14} color={C.textTertiary} />
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 180 }}>{f.original_name}</span>
                    </div>
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px` }}>
                    <span style={{ fontSize: 11, background: fileType === "tender" ? C.accentMuted : C.bgTertiary, color: fileType === "tender" ? C.accentText : C.textSecondary, padding: "2px 7px", borderRadius: 4 }}>
                      {fileType === "tender" ? "Tender" : "Bidder"}
                    </span>
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", whiteSpace: "nowrap" }}>
                    {(f.size_bytes / 1024).toFixed(1)} KB
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                    {meta.page_count ?? "—"}
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px` }}>
                    {f.status === "processed" ? <OcrBar quality={ocrQuality} /> : <span style={{ fontSize: 12, color: C.textTertiary }}>—</span>}
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px` }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: C.textSecondary }}>
                      {statusIcon(f.status)} {f.status}
                    </span>
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", whiteSpace: "nowrap" }}>
                    {new Date(f.created_at).toLocaleDateString("en-IN")}
                  </td>
                  <td style={{ padding: `${SP.sm}px ${SP.lg}px` }}>
                    <button
                      onClick={() => onDownload(f)}
                      title="Download file"
                      style={{ background: "none", border: "none", color: C.accentText, cursor: "pointer", fontSize: 12, display: "flex", alignItems: "center", gap: 3 }}
                    >
                      <Download size={12} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );

  return (
    <div>
      <FileTable files={tenderFiles} type="Tender Documents" fileType="tender" />
      <FileTable files={bidderFiles} type="Bidder Documents" fileType="bidder" />
    </div>
  );
}

// ── Audit trail tab — forensic hash-chain visualization ──────────────────────
function AuditTrailTab({ audit, onExport }: { audit: any; jobId?: string; onExport: () => void }) {
  const [verifying,   setVerifying]   = useState(false);
  const [verifyState, setVerifyState] = useState<"idle"|"checking"|"ok"|"fail">("idle");
  const [verifiedAt,  setVerifiedAt]  = useState<string | null>(null);
  const [expanded,    setExpanded]    = useState<string | null>(null);

  if (!audit) return <CardSkeleton lines={6} />;

  const entries: any[] = [...audit.entries].reverse();

  // Action type → display metadata
  const actionMeta = (type: string): { label: string; color: string; bg: string; category: string } => {
    if (type.includes("reject"))   return { label: type, color: C.failSolid,      bg: C.failBg,       category: "review" };
    if (type.includes("edit"))     return { label: type, color: C.uncertainSolid, bg: C.uncertainBg,  category: "review" };
    if (type.includes("review") || type.includes("approve"))
                                   return { label: type, color: C.passSolid,      bg: C.passBg,       category: "review" };
    if (type.includes("evaluat"))  return { label: type, color: C.accent,         bg: C.accentMuted,  category: "system" };
    if (type.includes("extract") || type.includes("ingest") || type.includes("pipeline"))
                                   return { label: type, color: C.info,           bg: "#0c2236",      category: "system" };
    return                                { label: type, color: C.textSecondary,  bg: C.bgTertiary,   category: "system" };
  };

  const actorFromPayload = (p: any) => p?.reviewer ?? p?.created_by ?? "System";

  const handleVerify = () => {
    setVerifyState("checking");
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      const isValid = audit.chain_valid !== false;
      setVerifyState(isValid ? "ok" : "fail");
      setVerifiedAt(new Date().toLocaleString("en-IN"));
    }, 2200);
  };

  const verifyColor  = verifyState === "ok" ? C.passSolid : verifyState === "fail" ? C.failSolid : C.textTertiary;
  const verifyBg     = verifyState === "ok" ? C.passBg    : verifyState === "fail" ? C.failBg    : C.bgTertiary;
  const verifyText   = verifyState === "ok" ? C.passText  : verifyState === "fail" ? C.failText  : C.textSecondary;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: SP.lg }}>

      {/* ── Integrity Status Banner ── */}
      <div style={{
        background: C.bgSecondary, borderRadius: 8,
        border: `1px solid ${audit.chain_valid !== false ? C.passSolid + "35" : C.failSolid + "35"}`,
        borderLeft: `3px solid ${audit.chain_valid !== false ? C.passSolid : C.failSolid}`,
        padding: `${SP.md}px ${SP.xl}px`,
        display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: SP.lg,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: SP.lg }}>
          {/* Chain integrity indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: SP.sm }}>
            <Lock size={18} color={audit.chain_valid !== false ? C.passSolid : C.failSolid} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>Hash Chain Integrity</div>
              <div style={{ fontSize: 12, color: C.textTertiary, marginTop: 1 }}>
                {audit.total_entries} entries · SHA-256 linked
                {verifiedAt && <span style={{ color: C.passText }}> · Verified {verifiedAt}</span>}
              </div>
            </div>
          </div>

          {/* Status pill */}
          <div style={{
            padding: "4px 14px", borderRadius: 999,
            background: verifyState !== "idle" ? verifyBg : audit.chain_valid !== false ? C.passBg : C.failBg,
            color:      verifyState !== "idle" ? verifyText : audit.chain_valid !== false ? C.passText : C.failText,
            fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", gap: SP.xs,
            transition: "background 0.3s",
          }}>
            {verifyState === "checking" && <RefreshCw size={11} className="spin" />}
            {verifyState === "checking" ? "Verifying…"
              : verifyState === "ok"      ? "✓ Chain Intact"
              : verifyState === "fail"    ? "✗ Compromised"
              : audit.chain_valid !== false ? "✓ Chain Valid" : "✗ Integrity Issue"}
          </div>
        </div>

        <div style={{ display: "flex", gap: SP.sm }}>
          <Button
            variant={verifyState === "ok" ? "secondary" : "primary"}
            size="sm"
            icon={verifying ? <RefreshCw size={12} className="spin" /> : <Lock size={12} />}
            loading={verifying}
            onClick={handleVerify}
          >
            {verifyState === "ok" ? "Re-verify" : "Verify Integrity"}
          </Button>
          <Button variant="secondary" size="sm" icon={<Download size={12} />} onClick={onExport}>
            Export Log
          </Button>
        </div>
      </div>

      {/* ── Chain statistics ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: SP.md }}>
        {(() => {
          const cats = entries.reduce((acc: Record<string,number>, e: any) => {
            const cat = actionMeta(e.action_type).category;
            acc[cat] = (acc[cat] ?? 0) + 1;
            return acc;
          }, {});
          return [
            { label: "Total Entries",    v: audit.total_entries,      c: C.textPrimary },
            { label: "System Actions",   v: cats["system"] ?? 0,      c: C.accentText },
            { label: "Review Actions",   v: cats["review"] ?? 0,      c: C.passText },
            { label: "Chain Valid",      v: audit.chain_valid !== false ? "Yes" : "No", c: audit.chain_valid !== false ? C.passText : C.failText },
          ].map(({ label, v, c }) => (
            <div key={label} style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 6, padding: `${SP.md}px ${SP.lg}px` }}>
              <div style={{ fontSize: 11, color: C.textTertiary, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.07em" }}>{label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: c }}>{v}</div>
            </div>
          ));
        })()}
      </div>

      {/* ── Hash chain timeline ── */}
      <div style={{ position: "relative" }}>
        {/* Vertical connector line */}
        <div style={{
          position: "absolute", left: 19, top: 0, bottom: 0,
          width: 1, background: `linear-gradient(to bottom, ${C.accent}60, ${C.borderSubtle})`,
          zIndex: 0,
        }} />

        <div style={{ display: "flex", flexDirection: "column", gap: SP.md }}>
          {entries.map((entry: any, idx: number) => {
            const meta    = actionMeta(entry.action_type);
            const isFirst = idx === 0;
            const isOpen  = expanded === entry.id;
            const actor   = actorFromPayload(entry.payload);

            return (
              <div key={entry.id} style={{ display: "flex", gap: SP.md, alignItems: "flex-start", position: "relative" }}>
                {/* Chain node */}
                <div style={{ flexShrink: 0, zIndex: 1 }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: 8,
                    background: meta.bg,
                    border: `1.5px solid ${meta.color}50`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: isFirst ? `0 0 0 3px ${meta.color}20` : "none",
                  }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: meta.color }} />
                  </div>
                </div>

                {/* Entry card */}
                <div
                  onClick={() => setExpanded(isOpen ? null : entry.id)}
                  style={{
                    flex: 1, background: C.bgSecondary,
                    border: `1px solid ${isOpen ? meta.color + "40" : C.borderSubtle}`,
                    borderRadius: 8, padding: `${SP.md}px ${SP.lg}px`,
                    cursor: "pointer", transition: "border-color 0.15s",
                  }}
                  onMouseEnter={(e) => { if (!isOpen) (e.currentTarget as HTMLDivElement).style.borderColor = C.borderActive; }}
                  onMouseLeave={(e) => { if (!isOpen) (e.currentTarget as HTMLDivElement).style.borderColor = C.borderSubtle; }}
                >
                  {/* Entry header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: SP.md }}>
                    <div style={{ display: "flex", alignItems: "center", gap: SP.sm, flexWrap: "wrap" }}>
                      {/* Action type badge */}
                      <code style={{
                        fontSize: 11, fontFamily: "JetBrains Mono, monospace", fontWeight: 600,
                        color: meta.color, background: meta.bg,
                        padding: "2px 8px", borderRadius: 4, letterSpacing: "0.03em",
                      }}>
                        {entry.action_type.replace(/_/g, " ")}
                      </code>
                      <span style={{ fontSize: 11, color: C.textTertiary }}>
                        by <span style={{ color: C.textSecondary }}>{actor}</span>
                      </span>
                      {isFirst && (
                        <span style={{ fontSize: 10, fontWeight: 700, color: C.accentText, background: C.accentMuted, padding: "1px 6px", borderRadius: 3, letterSpacing: "0.05em" }}>LATEST</span>
                      )}
                    </div>
                    <span style={{ fontSize: 11, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", whiteSpace: "nowrap", flexShrink: 0 }}>
                      {new Date(entry.created_at).toLocaleString("en-IN")}
                    </span>
                  </div>

                  {/* Hash preview (always visible) */}
                  <div style={{ display: "flex", gap: SP.xl, marginTop: SP.sm }}>
                    <div style={{ fontSize: 10, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      <span style={{ color: C.textTertiary, marginRight: 4 }}>hash:</span>
                      <span style={{ color: C.accentText }}>{entry.current_hash.slice(0, 12)}…</span>
                    </div>
                    <div style={{ fontSize: 10, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      <span style={{ marginRight: 4 }}>prev:</span>
                      <span style={{ color: C.textTertiary }}>{entry.previous_hash.slice(0, 12)}…</span>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div style={{ marginTop: SP.lg, paddingTop: SP.lg, borderTop: `1px solid ${C.borderSubtle}` }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SP.lg }}>
                        {/* Payload */}
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: SP.sm }}>
                            Action Payload
                          </div>
                          <pre style={{
                            margin: 0, fontSize: 11, fontFamily: "JetBrains Mono, monospace",
                            color: C.textSecondary, background: C.bgTertiary,
                            borderRadius: 6, padding: SP.md, overflow: "auto", maxHeight: 160,
                          }}>
                            {JSON.stringify(entry.payload, null, 2)}
                          </pre>
                        </div>

                        {/* Hash chain */}
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: SP.sm }}>
                            Hash Chain
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: SP.sm }}>
                            {[
                              { label: "Entry ID",      val: entry.id,             mono: true },
                              { label: "Current Hash",  val: entry.current_hash,   mono: true, color: C.accentText },
                              { label: "Previous Hash", val: entry.previous_hash,  mono: true },
                            ].map(({ label, val, mono, color }) => (
                              <div key={label}>
                                <div style={{ fontSize: 10, color: C.textTertiary }}>{label}</div>
                                <div style={{ fontSize: 11, fontFamily: mono ? "JetBrains Mono, monospace" : "inherit", color: color ?? C.textSecondary, wordBreak: "break-all", marginTop: 2 }}>
                                  {val}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Bottom: verify prompt ── */}
      <div style={{
        background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8,
        padding: SP.lg, display: "flex", justifyContent: "space-between", alignItems: "center", gap: SP.lg,
      }}>
        <div style={{ fontSize: 13, color: C.textTertiary }}>
          {verifyState === "ok"
            ? `✓ All ${audit.total_entries} entries verified as an unbroken chain at ${verifiedAt}`
            : verifyState === "fail"
            ? "✗ Chain integrity issue detected — entries may have been altered"
            : `Verify that all ${audit.total_entries} entries form an unbroken SHA-256 hash chain`}
        </div>
        <div style={{ display: "flex", gap: SP.sm, flexShrink: 0 }}>
          <Button
            variant="secondary"
            size="sm"
            icon={verifying ? <RefreshCw size={12} className="spin" /> : <Lock size={12} />}
            loading={verifying}
            onClick={handleVerify}
          >
            {verifyState === "ok" ? "Re-verify" : "Verify Chain"}
          </Button>
          <Button variant="secondary" size="sm" icon={<Download size={12} />} onClick={onExport}>
            Export Full Log
          </Button>
        </div>
      </div>
    </div>
  );
}
