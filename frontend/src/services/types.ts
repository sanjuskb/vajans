// ── Core enums ───────────────────────────────────────────────────────────────

export type JobStatus =
  | "pending" | "ingesting" | "extracting" | "evaluating" | "completed" | "failed";

export type FileType   = "tender" | "bidder";
export type FileStatus = "uploaded" | "processing" | "processed" | "failed";
export type Verdict    = "pass" | "fail" | "unknown";
export type Importance = "high" | "medium" | "low";
export type Severity   = "critical" | "warning" | "info";
export type ReviewerAction = "approve" | "edit" | "reject";

// ── Phase 3 — Criteria detail (from /criteria endpoint) ──────────────────────

export interface CriterionDetail {
  id: string;
  job_id: string;
  label: string;
  criterion_key: string;
  criterion_type: string;
  description: string;
  mandatory: boolean;
  threshold_value: number | null;
  threshold_unit: string | null;
  operator: string | null;
  ambiguous: boolean;
  source_snippet: string | null;
  created_at: string;
}

export interface CriteriaListResponse {
  total: number;
  data: CriterionDetail[];
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  title: string;
  status: JobStatus;
  created_by: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface JobCreate {
  title: string;
  created_by: string;
  metadata?: Record<string, unknown>;
}

// ── Files ─────────────────────────────────────────────────────────────────────

export interface FileRecord {
  id: string;
  job_id: string;
  original_name: string;
  file_type: FileType;
  status: FileStatus;
  storage_path: string;
  size_bytes: number;
  mime_type: string;
  checksum_sha256: string;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

// ── Phase 4 — Evaluation ──────────────────────────────────────────────────────

export interface EvalResultRow {
  id: string;
  job_id: string;
  criterion_id: string;
  bidder_file_id: string | null;
  verdict: Verdict;
  score: number;
  weight: number;
  weighted_score: number;
  explanation: string;
  created_at: string;
}

export interface EvalSummary {
  total: number;
  pass: number;
  fail: number;
  unknown: number;
}

export interface BidderEvalSummary {
  bidder_file_id: string;
  bidder_name: string;
  final_status: string;
  final_score: number;
  summary: EvalSummary;
  results: EvalResultRow[];
}

export interface EvaluationResponse {
  job_id: string;
  final_status: string;
  final_score: number;
  summary: EvalSummary;
  results: EvalResultRow[];
  bidders: BidderEvalSummary[];
}

// ── Phase 5 — Review ──────────────────────────────────────────────────────────

export interface ReviewActionCreate {
  criterion_id: string;
  evaluation_result_id: string;
  reviewer_action: ReviewerAction;
  original_value?: string;
  updated_value?: string;
  reason: string;
}

export interface ReviewActionRead {
  id: string;
  job_id: string;
  criterion_id: string;
  evaluation_result_id: string | null;
  reviewer_action: ReviewerAction;
  original_value: string | null;
  updated_value: string | null;
  reason: string;
  created_at: string;
}

export interface ReviewListResponse {
  total: number;
  data: ReviewActionRead[];
}

// ── Phase 6 — Insights ────────────────────────────────────────────────────────

export interface InsightSummary {
  total_criteria: number;
  pass: number;
  fail: number;
  unknown: number;
  final_score: number;
  final_status: string;
  review_required: boolean;
}

export interface CriterionInsight {
  criterion_id: string;
  label: string;
  verdict: Verdict;
  explanation: string;
  weight: number;
  importance_level: Importance;
  bidder_file_id?: string | null;
  bidder_name?: string;
}

export interface InsightFlag {
  code: string;
  message: string;
  severity: Severity;
  affected_criteria?: string[];
}

export interface InsightResponse {
  summary: InsightSummary;
  criteria: CriterionInsight[];
  flags: InsightFlag[];
}

// ── Phase 6 — Comparison ─────────────────────────────────────────────────────

export interface BidderEntry {
  bidder_id: string | null;
  bidder_name: string;
  total_score: number;
  pass: number;
  fail: number;
  unknown: number;
  total_criteria: number;
}

export interface BidderRanking {
  rank: number;
  bidder_id: string | null;
  bidder_name: string;
  total_score: number;
}

export interface ComparisonResponse {
  bidders: BidderEntry[];
  rankings: BidderRanking[];
}

// ── Phase 6 — Dashboard ───────────────────────────────────────────────────────

export interface DashboardResponse {
  summary: InsightSummary;
  criteria: CriterionInsight[];
  comparison: ComparisonResponse;
  flags: InsightFlag[];
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export interface AuditChainEntry {
  id: string;
  job_id: string;
  action_type: string;
  payload: Record<string, unknown>;
  previous_hash: string;
  current_hash: string;
  created_at: string;
}

export interface AuditTrailResponse {
  job_id: string;
  total_entries: number;
  chain_valid: boolean;
  entries: AuditChainEntry[];
}

export interface AuditLog {
  id: string;
  job_id: string;
  file_id: string | null;
  action: string;
  actor: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface ApiError {
  status: number;
  message: string;
  requestId?: string;
}
