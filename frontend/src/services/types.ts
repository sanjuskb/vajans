// ── Core enums ───────────────────────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "ingesting"
  | "extracting"
  | "evaluating"
  | "completed"
  | "failed";

export type FileType = "tender" | "bidder";
export type FileStatus = "uploaded" | "processing" | "processed" | "failed";
export type Verdict = "pass" | "fail" | "unknown";
export type Importance = "high" | "medium" | "low";
export type Severity = "critical" | "warning" | "info";
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

// One extraction row = one (criterion, bidder file) pair's extracted field.
// `file_id` is the BIDDER file the value was pulled from (not the tender).
export interface ExtractionRow {
  id: string;
  job_id: string;
  file_id: string;
  criterion_id: string;
  field_name: string;
  raw_value: string | null;
  parsed_value: string | null;
  unit: string | null;
  source_snippet: string | null;
  extraction_confidence: number;
  not_found: boolean;
  raw_llm_output: string;
  page_number: number | null;
  created_at: string;
}

export interface ExtractionsResponse {
  total: number;
  data: ExtractionRow[];
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
  // Post-ingestion enrichment from the backend `/files/job` and `/files/{id}`
  // endpoints. Both are optional because they're populated only after the
  // INGESTION_DONE audit-log entry is written. NEVER substitute a placeholder
  // when null — render the cell as "—" so the operator knows the document
  // hasn't finished processing yet (or hasn't been ingested in this build).
  ocr_quality?: number | null;
  document_kind?: "digital" | "scanned" | "image" | null;
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

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface TimelinePoint {
  date: string;   // ISO date "YYYY-MM-DD"
  count: number;
}

export interface TimelineResponse {
  days: number;
  points: TimelinePoint[];
}

export interface VerdictBucket {
  verdict: string;
  label: string;
  count: number;
  color: string;   // hex from backend — single source of truth
}

export interface VerdictDistributionResponse {
  total: number;
  buckets: VerdictBucket[];
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
  // Real per-row confidence signals (backend `insight_engine`).
  // All optional for backward compatibility with older API responses.
  score?: number; // evaluator score, 0–1
  extraction_confidence?: number | null; // extraction signal, 0–1, null = no extraction row
  ocr_quality?: number; // 0–1; 1.0 ≈ digital PDF
  review_confidence?: number; // composite, 0–1 — what the Review Queue should display
  source_snippet?: string | null;
  page_number?: number | null;
  extracted_value?: string | null;
  not_found?: boolean;
  ambiguous?: boolean;
  has_threshold?: boolean;
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
