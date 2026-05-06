import apiClient from "./apiClient";
import type {
  Job, JobCreate, FileRecord, FileType,
  EvaluationResponse, InsightResponse, ComparisonResponse,
  DashboardResponse, ReviewActionCreate, ReviewListResponse,
  AuditTrailResponse, CriteriaListResponse, ExtractionsResponse,
} from "./types";

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    apiClient
      .post<{ access_token: string; token_type: string; username: string; role: string }>(
        "/v1/auth/login",
        { username, password }
      )
      .then((r) => r.data),

  logout: () =>
    apiClient.post("/v1/auth/logout").then((r) => r.data),

  me: () =>
    apiClient.get("/v1/auth/me").then((r) => r.data),
};

// ── Jobs ─────────────────────────────────────────────────────────────────────

export const jobsApi = {
  list: (skip = 0, limit = 50) =>
    apiClient.get<Job[]>("/v1/jobs/", { params: { skip, limit } }).then((r) => r.data),

  get: (jobId: string) =>
    apiClient.get<Job>(`/v1/jobs/${jobId}`).then((r) => r.data),

  create: (payload: JobCreate) =>
    apiClient.post<Job>("/v1/jobs/", payload).then((r) => r.data),

  delete: (jobId: string) =>
    apiClient.delete(`/v1/jobs/${jobId}`),
};

// ── Files ─────────────────────────────────────────────────────────────────────

export const filesApi = {
  listForJob: (jobId: string) =>
    apiClient.get<FileRecord[]>(`/v1/files/job/${jobId}`).then((r) => r.data),

  get: (fileId: string) =>
    apiClient.get<FileRecord>(`/v1/files/${fileId}`).then((r) => r.data),

  upload: (jobId: string, fileType: FileType, file: File) => {
    const form = new FormData();
    form.append("job_id", jobId);
    form.append("file_type", fileType);
    form.append("file", file);
    return apiClient
      .post<FileRecord>("/v1/files/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  download: async (fileId: string, filename: string): Promise<void> => {
    const resp = await apiClient.get(`/v1/files/${fileId}/download`, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  },

  // Fetches the file body for INLINE rendering (e.g. react-pdf in the in-app
  // viewer). The /inline endpoint sets Content-Disposition: inline so browsers
  // do not force a download.
  getInline: async (fileId: string): Promise<Blob> => {
    const resp = await apiClient.get(`/v1/files/${fileId}/inline`, { responseType: "blob" });
    return resp.data as Blob;
  },
};

// ── Client-side download helper ───────────────────────────────────────────────

export function downloadJSON(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () =>
    apiClient.get<{ status: string }>("/health").then((r) => r.data),
};

// ── Phase 4: Evaluation ───────────────────────────────────────────────────────

export const analyzeApi = {
  triggerPipeline: (jobId: string) =>
    apiClient.post(`/v1/analyze/${jobId}`).then((r) => r.data),

  triggerEvaluation: (jobId: string) =>
    apiClient.post(`/v1/analyze/${jobId}/evaluate`).then((r) => r.data),

  getEvaluation: (jobId: string) =>
    apiClient.get<EvaluationResponse>(`/v1/analyze/${jobId}/evaluation`).then((r) => r.data),

  getCriteria: (jobId: string) =>
    apiClient.get<CriteriaListResponse>(`/v1/analyze/${jobId}/criteria`).then((r) => r.data),

  getExtractions: (jobId: string) =>
    apiClient.get<ExtractionsResponse>(`/v1/analyze/${jobId}/extractions`).then((r) => r.data),

  // Phase 5
  getReviews: (jobId: string) =>
    apiClient.get<ReviewListResponse>(`/v1/analyze/${jobId}/review`).then((r) => r.data),

  submitReview: (jobId: string, payload: ReviewActionCreate) =>
    apiClient.post(`/v1/analyze/${jobId}/review`, payload).then((r) => r.data),

  getAudit: (jobId: string) =>
    apiClient.get<AuditTrailResponse>(`/v1/analyze/${jobId}/audit`).then((r) => r.data),

  // Phase 6
  getInsights: (jobId: string) =>
    apiClient.get<InsightResponse>(`/v1/analyze/${jobId}/insights`).then((r) => r.data),

  getComparison: (jobId: string) =>
    apiClient.get<ComparisonResponse>(`/v1/analyze/${jobId}/comparison`).then((r) => r.data),

  getDashboard: (jobId: string) =>
    apiClient.get<DashboardResponse>(`/v1/analyze/${jobId}/dashboard`).then((r) => r.data),
};
