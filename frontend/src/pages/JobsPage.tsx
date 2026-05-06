import React, { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Plus, Search, ChevronRight, Briefcase, X, Upload, ChevronDown, Archive, Calendar, FileText, CheckCircle2, AlertCircle, Trash2 } from "lucide-react";
import { C, SP } from "../styles/tokens";
import { jobsApi, filesApi } from "../services/api";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import { CardSkeleton } from "../components/ui/Card";
import toast from "react-hot-toast";
import type { Job } from "../services/types";

const PAGE_SIZE = 25;

function statusVariant(s: string): any {
  const m: Record<string, string> = {
    completed: "completed", failed: "failed",
    ingesting: "processing", extracting: "processing", evaluating: "processing",
    pending: "pending",
  };
  return m[s] ?? "draft";
}

export default function JobsPage() {
  const navigate    = useNavigate();
  const [searchParams] = useSearchParams();
  const [search,  setSearch]  = useState("");
  const [filter,  setFilter]  = useState("all");
  const [sortDir, setSortDir] = useState<"desc"|"asc">("desc");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo,   setDateTo]   = useState("");
  const [page,    setPage]    = useState(1);
  const [modal,   setModal]   = useState(false);

  // Auto-open modal when navigated with ?new=true (from topbar CTA)
useEffect(() => {
  if (searchParams.get("new") === "true") {
    setModal(true);

    // ✅ REMOVE query param after opening
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("new");

    navigate({
      pathname: "/jobs",
      search: newParams.toString(),
    }, { replace: true });
  }
}, [searchParams, navigate]);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list(0, 200),
    refetchInterval: 10_000,
  });

  const all = jobs as Job[];

  const filtered = all.filter((j) => {
    const ms = !search || j.title.toLowerCase().includes(search.toLowerCase()) || j.id.includes(search);
    const mf = filter === "all" || j.status === filter ||
      (filter === "processing" && ["ingesting","extracting","evaluating"].includes(j.status));
    const mdfrom = !dateFrom || new Date(j.created_at) >= new Date(dateFrom);
    const mdto   = !dateTo   || new Date(j.created_at) <= new Date(dateTo + "T23:59:59");
    return ms && mf && mdfrom && mdto;
  }).sort((a, b) => {
    const diff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    return sortDir === "desc" ? diff : -diff;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset to page 1 when filters change
  const handleSearch = (v: string) => { setSearch(v); setPage(1); };
  const handleFilter = (v: string) => { setFilter(v); setPage(1); };

  const FILTERS = [
    { id: "all",        label: "All" },
    { id: "processing", label: "Processing" },
    { id: "completed",  label: "Completed" },
    { id: "failed",     label: "Failed" },
    { id: "pending",    label: "Pending" },
  ];

  return (
    <div className="fade-in">
      {/* Filter bar */}
      <div style={{ display: "flex", gap: SP.md, alignItems: "center", marginBottom: SP.lg, flexWrap: "wrap" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 220px", maxWidth: 300 }}>
          <Search size={15} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: C.textTertiary, pointerEvents: "none" }} />
          <input
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search by title or ID..."
            style={{ width: "100%", paddingLeft: 34 }}
          />
        </div>

        {/* Status filters */}
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {FILTERS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => handleFilter(id)}
              style={{
                padding: "5px 12px", borderRadius: 6, cursor: "pointer",
                fontSize: 12, fontWeight: 500, border: "none",
                background: filter === id ? C.accent : C.bgTertiary,
                color: filter === id ? "#fff" : C.textSecondary,
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Date range */}
        <div style={{ display: "flex", alignItems: "center", gap: SP.xs }}>
          <Calendar size={14} color={C.textTertiary} />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
            style={{ padding: "5px 8px", fontSize: 12, width: 130 }}
            title="From date"
          />
          <span style={{ fontSize: 11, color: C.textTertiary }}>–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
            style={{ padding: "5px 8px", fontSize: 12, width: 130 }}
            title="To date"
          />
        </div>

        {/* Sort */}
        <button
          onClick={() => setSortDir(d => d === "desc" ? "asc" : "desc")}
          style={{
            display: "flex", alignItems: "center", gap: 4,
            padding: "5px 10px", borderRadius: 6, border: `1px solid ${C.borderActive}`,
            background: "none", color: C.textSecondary, cursor: "pointer", fontSize: 12,
          }}
        >
          {sortDir === "desc" ? "Newest first" : "Oldest first"}
          <ChevronDown size={12} style={{ transform: sortDir === "asc" ? "rotate(180deg)" : "none", transition: "transform 0.15s" }} />
        </button>

        <div style={{ marginLeft: "auto" }}>
          <Button variant="primary" icon={<Plus size={14} />} onClick={() => setModal(true)}>
            New Evaluation
          </Button>
        </div>
      </div>

      {/* Count */}
      {!isLoading && (
        <div style={{ fontSize: 12, color: C.textTertiary, marginBottom: SP.sm }}>
          {filtered.length} job{filtered.length !== 1 ? "s" : ""} found
          {totalPages > 1 && ` · Page ${page} of ${totalPages}`}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <CardSkeleton lines={8} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Briefcase size={48} />}
          title="No evaluations found"
          description={search ? "Try a different search term." : "Create your first evaluation job to begin."}
          action={!search ? { label: "New Evaluation", onClick: () => setModal(true) } : undefined}
        />
      ) : (
        <>
          <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8, overflow: "hidden" }}>
            <table>
              <thead>
                <tr style={{ background: C.bgPrimary }}>
                  {["#","Job Title","Status","Tender Ref","Started","Completed","Actions"].map((h) => (
                    <th key={h} style={{ padding: `${SP.md}px ${SP.lg}px`, textAlign: "left", fontSize: 11, fontWeight: 600, color: C.textTertiary, textTransform: "uppercase", letterSpacing: "0.05em", whiteSpace: "nowrap" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginated.map((job, idx) => (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/jobs/${job.id}`)}
                    style={{ borderBottom: `1px solid ${C.borderSubtle}`, cursor: "pointer" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = C.bgHover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                  >
                    <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      {(page - 1) * PAGE_SIZE + idx + 1}
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>{job.title}</div>
                      <div style={{ fontSize: 11, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace", marginTop: 2 }}>{job.id.slice(0,8)}…</div>
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                      <Badge variant={statusVariant(job.status)} dot />
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      {(job as any).metadata?.tender_ref ?? "—"}
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      {new Date(job.created_at).toLocaleDateString("en-IN")}
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px`, fontSize: 12, color: C.textTertiary, fontFamily: "JetBrains Mono, monospace" }}>
                      {job.status === "completed" ? new Date(job.updated_at).toLocaleDateString("en-IN") : "—"}
                    </td>
                    <td style={{ padding: `${SP.md}px ${SP.lg}px` }}>
                      <div style={{ display: "flex", alignItems: "center", gap: SP.xs }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/jobs/${job.id}`); }}
                          style={{ background: "none", border: "none", color: C.accentText, cursor: "pointer", fontSize: 12, display: "flex", alignItems: "center", gap: 3 }}
                        >
                          View <ChevronRight size={12} />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); toast.success("Job archived"); }}
                          style={{ background: "none", border: "none", color: C.textTertiary, cursor: "pointer", padding: 4, display: "flex", alignItems: "center" }}
                          title="Archive"
                        >
                          <Archive size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: SP.sm, marginTop: SP.xl, flexWrap: "wrap" }}>
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                style={{
                  padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.borderActive}`,
                  background: "none", color: page === 1 ? C.textTertiary : C.textSecondary,
                  cursor: page === 1 ? "not-allowed" : "pointer", fontSize: 12,
                }}
              >
                ← Prev
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).filter(p =>
                p === 1 || p === totalPages || Math.abs(p - page) <= 2
              ).reduce<(number | "…")[]>((acc, p, i, arr) => {
                if (i > 0 && (p as number) - (arr[i - 1] as number) > 1) acc.push("…");
                acc.push(p);
                return acc;
              }, []).map((p, i) =>
                p === "…" ? (
                  <span key={`ellipsis-${i}`} style={{ fontSize: 12, color: C.textTertiary, padding: "5px 4px" }}>…</span>
                ) : (
                  <button
                    key={p}
                    onClick={() => setPage(p as number)}
                    style={{
                      padding: "5px 10px", borderRadius: 6, border: `1px solid ${p === page ? C.accent : C.borderActive}`,
                      background: p === page ? C.accent : "none",
                      color: p === page ? "#fff" : C.textSecondary,
                      cursor: "pointer", fontSize: 12, fontWeight: p === page ? 600 : 400,
                    }}
                  >
                    {p}
                  </button>
                )
              )}
              <button
                disabled={page === totalPages}
                onClick={() => setPage(p => p + 1)}
                style={{
                  padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.borderActive}`,
                  background: "none", color: page === totalPages ? C.textTertiary : C.textSecondary,
                  cursor: page === totalPages ? "not-allowed" : "pointer", fontSize: 12,
                }}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {modal && (
        <CreateJobModal
          onClose={() => setModal(false)}
          onCreated={(id) => { setModal(false); navigate(`/jobs/${id}`); }}
        />
      )}
    </div>
  );
}

// ── Create modal (full-screen overlay) ───────────────────────────────────────

function CreateJobModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const qc        = useQueryClient();
  const [step,    setStep]    = useState(1);
  const [title,   setTitle]   = useState("");
  const [ref,     setRef]     = useState("");
  const [desc,    setDesc]    = useState("");
  const [jobId,   setJobId]   = useState<string | null>(null);
  const tenderRef = useRef<HTMLInputElement>(null);
  const bidderRef = useRef<HTMLInputElement>(null);
  const [tender,  setTender]  = useState<File | null>(null);
  const [bidders, setBidders] = useState<File[]>([]);

  const createMut = useMutation({
    mutationFn: () => jobsApi.create({ title: title.trim(), created_by: "procurement.officer", metadata: { tender_ref: ref, description: desc } }),
    onSuccess: (job) => { setJobId(job.id); qc.invalidateQueries({ queryKey: ["jobs"] }); setStep(2); },
    onError:   () => toast.error("Failed to create job. Check backend."),
  });

  const uploadMut = useMutation({
    mutationFn: async (jid: string) => {
      if (tender) await filesApi.upload(jid, "tender", tender);
      for (const f of bidders) await filesApi.upload(jid, "bidder", f);
    },
    onSuccess: () => setStep(3),
    onError:   () => toast.error("Upload failed. Please retry."),
  });

  const STEPS = ["Job Details", "Upload Documents", "Confirm"];

  return createPortal(
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: C.bgPrimary,
        display: "flex", flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* ── Fixed Header ── */}
      <div style={{
        flexShrink: 0,
        background: C.bgSecondary,
        borderBottom: `1px solid ${C.borderSubtle}`,
        padding: `${SP.xl}px ${SP.xl2}px ${SP.lg}px`,
      }}>
        {/* Title row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: SP.xl }}>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary, letterSpacing: "-0.02em" }}>
              New Evaluation Job
            </div>
            <div style={{ fontSize: 13, color: C.textTertiary, marginTop: 4 }}>
              Step {step} of {STEPS.length} — {STEPS[step - 1]}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: C.bgTertiary, border: `1px solid ${C.borderSubtle}`,
              color: C.textSecondary, cursor: "pointer",
              padding: "7px 14px", borderRadius: 8,
              display: "flex", alignItems: "center", gap: SP.xs,
              fontSize: 13, fontWeight: 500,
            }}
          >
            <X size={15} /> Close
          </button>
        </div>

        {/* Horizontal Stepper */}
        <div style={{ display: "flex", gap: SP.xs, alignItems: "center" }}>
          {STEPS.map((s, i) => (
            <React.Fragment key={s}>
              <div style={{ display: "flex", alignItems: "center", gap: SP.sm }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: i + 1 < step ? C.passSolid : i + 1 === step ? C.accent : C.bgTertiary,
                  border: `2px solid ${i + 1 < step ? C.passSolid : i + 1 === step ? C.accent : C.borderActive}`,
                  fontSize: 11, fontWeight: 800,
                  color: i + 1 <= step ? "#fff" : C.textTertiary,
                  flexShrink: 0, transition: "all 0.25s",
                }}>
                  {i + 1 < step ? "✓" : i + 1}
                </div>
                <span style={{
                  fontSize: 13,
                  fontWeight: i + 1 === step ? 700 : 400,
                  color: i + 1 === step ? C.textPrimary : i + 1 < step ? C.passText : C.textTertiary,
                  whiteSpace: "nowrap",
                }}>
                  {s}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{
                  flex: 1, height: 2, borderRadius: 2,
                  background: i + 1 < step ? C.passSolid + "80" : C.borderSubtle,
                  transition: "background 0.25s",
                }} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Progress bar */}
        <div style={{ height: 3, background: C.bgTertiary, marginTop: SP.lg, borderRadius: 2 }}>
          <div style={{
            height: "100%", borderRadius: 2,
            width: `${(step / STEPS.length) * 100}%`,
            background: `linear-gradient(90deg, ${C.accent}, #3B82F6)`,
            transition: "width 0.35s ease",
          }} />
        </div>
      </div>

      {/* ── Scrollable Content Area ── */}
      <div style={{ flex: "1 1 0", minHeight: 0, overflowY: "auto", padding: `${SP.xl2}px` }}>
        <div>

          {/* ── Step 1: Job Details ── */}
          {step === 1 && (
            <div style={{
              background: C.bgSecondary,
              border: `1px solid ${C.borderSubtle}`,
              borderRadius: 12,
              padding: SP.xl2,
            }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary, marginBottom: SP.xl }}>
                Job Information
              </div>
              <div style={{ marginBottom: SP.xl }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: SP.sm }}>
                  Job Title <span style={{ color: C.failSolid }}>*</span>
                </label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  style={{ width: "100%", fontSize: 14, padding: "10px 14px" }}
                  placeholder="e.g. KSRDC Bridge Construction Tender 2024"
                  autoFocus
                />
              </div>
              <div style={{ marginBottom: SP.xl }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: SP.sm }}>
                  Tender Reference Number
                </label>
                <input
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                  style={{ width: "100%", fontFamily: "JetBrains Mono, monospace", fontSize: 13, padding: "10px 14px" }}
                  placeholder="e.g. TENDER/2024/087"
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: SP.sm }}>
                  Description <span style={{ fontSize: 11, fontWeight: 400, color: C.textTertiary }}>(optional)</span>
                </label>
                <textarea
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  rows={4}
                  style={{ width: "100%", resize: "vertical", fontFamily: "inherit", fontSize: 13, padding: "10px 14px" }}
                  placeholder="Brief description of the procurement..."
                />
              </div>
            </div>
          )}

          {/* ── Step 2: Upload Documents ── */}
          {step === 2 && jobId && (
            <div>
              {/* Tender document card */}
              <div style={{
                background: C.bgSecondary,
                border: `1px solid ${C.borderSubtle}`,
                borderRadius: 12,
                padding: SP.xl2,
                marginBottom: SP.xl,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.md }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.failSolid, flexShrink: 0 }} />
                  <span style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary }}>Tender Document</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: C.failText, background: C.failBg, padding: "2px 8px", borderRadius: 4, letterSpacing: "0.05em" }}>REQUIRED</span>
                </div>
                <p style={{ fontSize: 13, color: C.textTertiary, marginBottom: SP.lg, lineHeight: 1.6 }}>
                  The main tender document containing eligibility criteria, financial requirements, and technical specifications.
                </p>
                <DropZone
                  file={tender}
                  onFile={(f) => setTender(f)}
                  onClear={() => setTender(null)}
                  inputRef={tenderRef}
                  accept=".pdf,.docx"
                  hint="PDF or DOCX · Max 50MB"
                />
                <input ref={tenderRef} type="file" accept=".pdf,.docx" style={{ display: "none" }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) setTender(f);
                    e.target.value = "";
                  }} />
              </div>

              {/* Bidder documents card */}
              <div style={{
                background: C.bgSecondary,
                border: `1px solid ${C.borderSubtle}`,
                borderRadius: 12,
                padding: SP.xl2,
                marginBottom: SP.xl,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.md }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: C.accentText, flexShrink: 0 }} />
                  <span style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary }}>Bidder Documents</span>
                  <span style={{ fontSize: 11, fontWeight: 400, color: C.textTertiary }}>one file per bidder</span>
                  {bidders.length > 0 && (
                    <span style={{
                      fontSize: 11, fontWeight: 700,
                      color: C.passText, background: C.passBg,
                      padding: "2px 10px", borderRadius: 9999,
                      marginLeft: "auto",
                    }}>
                      {bidders.length} file{bidders.length !== 1 ? "s" : ""} selected
                    </span>
                  )}
                </div>
                <p style={{ fontSize: 13, color: C.textTertiary, marginBottom: SP.lg, lineHeight: 1.6 }}>
                  Upload each bidder's submission as a separate file. Each file is evaluated independently against the tender criteria.
                </p>
                <DropZone
                  file={null}
                  onFile={(f) => setBidders((p) => [...p, f])}
                  onClear={() => {}}
                  inputRef={bidderRef}
                  accept=".pdf,.docx,.jpg,.png"
                  hint="PDF, DOCX, JPG or PNG · Click or drag to add files"
                  multi
                  multiCount={bidders.length}
                />
                <input ref={bidderRef} type="file" accept=".pdf,.docx,.jpg,.png" multiple style={{ display: "none" }}
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    setBidders((p) => [...p, ...files]);
                    e.target.value = "";
                  }} />

                {/* Bidder file list */}
                {bidders.length > 0 && (
                  <div style={{
                    marginTop: SP.lg,
                    border: `1px solid ${C.passSolid}40`,
                    borderRadius: 8,
                    overflow: "hidden",
                    background: "rgba(5, 150, 105, 0.12)",
                  }}>
                    <div style={{
                      padding: `${SP.sm}px ${SP.md}px`,
                      borderBottom: `1px solid ${C.passSolid}25`,
                      display: "flex", alignItems: "center", gap: SP.sm,
                      background: "rgba(5, 150, 105, 0.25)",
                    }}>
                      <CheckCircle2 size={13} color={C.passSolid} />
                      <span style={{ fontSize: 12, fontWeight: 600, color: C.passText }}>
                        {bidders.length} bidder document{bidders.length !== 1 ? "s" : ""} ready for upload
                      </span>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      {bidders.map((f, i) => (
                        <div
                          key={i}
                          style={{
                            display: "flex", alignItems: "center", gap: SP.sm,
                            padding: `${SP.sm}px ${SP.md}px`,
                            borderBottom: i < bidders.length - 1 ? `1px solid ${C.borderSubtle}` : "none",
                          }}
                        >
                          <FileText size={13} color={C.passSolid} style={{ flexShrink: 0 }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 500, color: C.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {f.name}
                            </div>
                            <div style={{ fontSize: 11, color: C.textTertiary, marginTop: 1 }}>
                              {(f.size / 1024).toFixed(1)} KB
                            </div>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); setBidders((p) => p.filter((_, j) => j !== i)); }}
                            style={{
                              background: "none", border: `1px solid ${C.borderSubtle}`,
                              borderRadius: 4, color: C.textTertiary,
                              cursor: "pointer", padding: "3px 6px",
                              fontSize: 11, display: "flex", alignItems: "center", gap: 3,
                              flexShrink: 0,
                            }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = C.failText; (e.currentTarget as HTMLButtonElement).style.borderColor = C.failSolid; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = C.textTertiary; (e.currentTarget as HTMLButtonElement).style.borderColor = C.borderSubtle; }}
                          >
                            <X size={11} /> Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Info box */}
              <div style={{ background: C.accentMuted, border: `1px solid ${C.accent}25`, borderRadius: 8, padding: SP.lg, display: "flex", gap: SP.sm, alignItems: "flex-start" }}>
                <AlertCircle size={15} color={C.accentText} style={{ marginTop: 1, flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: C.accentText, lineHeight: 1.6 }}>
                  Processing takes 2–5 minutes per document. You can navigate away and check progress on the Job Detail page.
                </span>
              </div>
            </div>
          )}

          {/* ── Step 3: Confirmation ── */}
          {step === 3 && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: SP.xl2 }}>
              <div style={{
                width: 80, height: 80, borderRadius: "50%",
                background: C.passBg, border: `2px solid ${C.passSolid}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                marginBottom: SP.xl,
              }}>
                <CheckCircle2 size={40} color={C.passSolid} />
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, color: C.passText, marginBottom: SP.sm, textAlign: "center" }}>
                Documents Uploaded
              </h3>
              <p style={{ fontSize: 15, color: C.textSecondary, marginBottom: SP.sm, lineHeight: 1.6, textAlign: "center" }}>
                {tender ? `1 tender document` : "No tender"}{bidders.length > 0 ? ` + ${bidders.length} bidder submission${bidders.length !== 1 ? "s" : ""}` : ""} ready for evaluation.
              </p>
              <p style={{ fontSize: 13, color: C.textTertiary, marginBottom: SP.xl2, lineHeight: 1.6, textAlign: "center" }}>
                Open the job page to run the AI pipeline and monitor progress in real-time.
              </p>

              {/* Summary card */}
              <div style={{
                background: C.bgSecondary,
                border: `1px solid ${C.borderSubtle}`,
                borderRadius: 12,
                padding: SP.xl2,
                width: "100%",
              }}>
                {[
                  { label: "Job Title",  value: title },
                  { label: "Tender Ref", value: ref || "—" },
                  { label: "Documents",  value: `${tender ? 1 : 0} tender + ${bidders.length} bidder` },
                ].map(({ label, value }) => (
                  <div key={label} style={{ display: "flex", gap: SP.lg, marginBottom: SP.md, fontSize: 14, alignItems: "flex-start" }}>
                    <span style={{ color: C.textTertiary, minWidth: 110, flexShrink: 0 }}>{label}</span>
                    <span style={{ color: C.textPrimary, fontFamily: label === "Tender Ref" ? "JetBrains Mono, monospace" : "inherit", fontWeight: 500 }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* ── Sticky Bottom Action Bar ── */}
      <div style={{
        flexShrink: 0,
        background: C.bgSecondary,
        borderTop: `1px solid ${C.borderSubtle}`,
        padding: `${SP.lg}px ${SP.xl2}px`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        {/* Left: Back button */}
        <div>
          {step === 2 && (
            <Button variant="secondary" onClick={() => setStep(1)}>← Back</Button>
          )}
        </div>

        {/* Right: Cancel + primary action */}
        <div style={{ display: "flex", gap: SP.sm, alignItems: "center" }}>
          {step < 3 && (
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
          )}
          {step === 1 && (
            <Button variant="primary" disabled={!title.trim()} loading={createMut.isPending} onClick={() => createMut.mutate()}>
              Continue →
            </Button>
          )}
          {step === 2 && (
            <Button
              variant="primary"
              disabled={!tender}
              loading={uploadMut.isPending}
              onClick={() => uploadMut.mutate(jobId!)}
              icon={<Upload size={14} />}
            >
              {uploadMut.isPending ? "Uploading…" : "Upload & Continue →"}
            </Button>
          )}
          {step === 3 && (
            <Button variant="primary" size="lg" onClick={() => jobId && onCreated(jobId)}>
              Open Job → Run Pipeline
            </Button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

// ── Drop zone with drag support ───────────────────────────────────────────────

function DropZone({ file, onFile, onClear, inputRef, accept, hint, multi = false, multiCount = 0 }: {
  file: File | null;
  onFile: (f: File) => void;
  onClear: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  accept: string;
  hint?: string;
  multi?: boolean;
  multiCount?: number;
}) {
  const [dragging, setDragging] = useState(false);
  const [rejectMsg, setRejectMsg] = useState<string | null>(null);

  // Validate a dropped file against the accept string (.pdf,.docx etc.)
  const isAccepted = useCallback((f: File) => {
    if (!accept) return true;
    const exts = accept.split(",").map((s) => s.trim().toLowerCase());
    const fname = f.name.toLowerCase();
    return exts.some((ext) => fname.endsWith(ext));
  }, [accept]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    setRejectMsg(null);
    const dropped = Array.from(e.dataTransfer.files);
    const valid   = dropped.filter(isAccepted);
    const invalid = dropped.filter((f) => !isAccepted(f));
    if (invalid.length) {
      setRejectMsg(`${invalid.length} unsupported file${invalid.length > 1 ? "s" : ""} ignored. Accepted: ${accept}`);
      setTimeout(() => setRejectMsg(null), 4000);
    }
    if (valid.length > 0) {
      if (multi) valid.forEach(onFile);
      else onFile(valid[0]);
    }
  }, [onFile, multi, isAccepted, accept]);

  const isDone      = !multi && file !== null;
  const hasMulti    = multi && multiCount > 0;
  const borderColor = isDone || hasMulti ? C.passSolid : dragging ? C.accent : C.borderActive;
  const bgColor     = isDone || hasMulti ? "rgba(5, 150, 105, 0.18)" : dragging ? "rgba(37, 99, 235, 0.12)" : C.bgTertiary;

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      style={{
        border: `1.5px dashed ${borderColor}`,
        borderRadius: 8,
        padding: "24px",
        minHeight: 200,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        cursor: "pointer",
        background: bgColor,
        transition: "all 0.15s ease",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      {isDone && file ? (
        /* Single-file success state */
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: SP.md }}>
          <div style={{
            width: 48, height: 48, borderRadius: "50%",
            background: C.passBg, border: `1.5px solid ${C.passSolid}40`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <CheckCircle2 size={22} color={C.passSolid} />
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: C.passText, marginBottom: 3 }}>{file.name}</div>
            <div style={{ fontSize: 11, color: C.textTertiary }}>{(file.size / 1024).toFixed(1)} KB</div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onClear(); }}
            style={{
              background: "none", border: `1px solid ${C.borderSubtle}`,
              borderRadius: 5, color: C.textTertiary,
              cursor: "pointer", padding: "3px 10px",
              fontSize: 11, display: "flex", alignItems: "center", gap: 4,
            }}
          >
            <Trash2 size={11} /> Replace
          </button>
        </div>
      ) : hasMulti ? (
        /* Multi-file: files already added — show add-more prompt */
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: SP.sm }}>
          <div style={{
            width: 44, height: 44, borderRadius: "50%",
            background: C.passBg, border: `1.5px solid ${C.passSolid}40`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <CheckCircle2 size={20} color={C.passSolid} />
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.passText }}>
            {multiCount} file{multiCount !== 1 ? "s" : ""} added
          </div>
          <div style={{ fontSize: 11, color: C.textSecondary }}>
            {dragging ? "Drop to add more" : "Click or drag to add more files"}
          </div>
        </div>
      ) : (
        /* Empty state */
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: SP.sm }}>
          <div style={{
            width: 48, height: 48, borderRadius: "50%",
            background: dragging ? C.accentMuted : C.bgSecondary,
            border: `1.5px solid ${dragging ? C.accent : C.borderActive}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.15s",
          }}>
            <Upload size={20} color={dragging ? C.accentText : C.textTertiary} />
          </div>
          <div style={{ fontSize: 13, fontWeight: 500, color: dragging ? C.textPrimary : C.textSecondary }}>
            {dragging ? "Drop file here" : "Click to browse or drag and drop"}
          </div>
          {hint && <div style={{ fontSize: 11, color: C.textTertiary }}>{hint}</div>}
        </div>
      )}
      {rejectMsg && (
        <div style={{ marginTop: 8, fontSize: 11, color: C.failText, background: C.failBg, borderRadius: 4, padding: "4px 8px" }}>
          ⚠ {rejectMsg}
        </div>
      )}
    </div>
  );
}
