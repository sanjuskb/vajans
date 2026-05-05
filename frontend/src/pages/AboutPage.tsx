import { useNavigate } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import {
  ArrowLeft, CheckCircle2, Lock, Scale, ShieldCheck,
  Users, Database, Hash, Eye, ArrowRight, Shield,
} from "lucide-react";
import Button from "../components/ui/Button";
import Logo from "../components/ui/Logo";

// ── Reusable reveal wrapper ───────────────────────────────────────────────────

function Reveal({
  children,
  delay = 0,
  y = 18,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-50px" });
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {children}
    </motion.div>
  );
}

// ── Data ──────────────────────────────────────────────────────────────────────

const TECH_STACK = [
  { label: "LLM Engine",      value: "Anthropic Claude" },
  { label: "Extraction",      value: "RAG pipeline (embeddings + retrieval)" },
  { label: "Rule Engine",     value: "Deterministic Python evaluator" },
  { label: "Backend",         value: "FastAPI + PostgreSQL" },
  { label: "Audit Chain",     value: "SHA-256 cryptographic hash chain" },
  { label: "OCR",             value: "Tesseract + pdfminer" },
  { label: "Frontend",        value: "React 18 + TypeScript + Tailwind CSS" },
  { label: "State",           value: "React Query + Zustand" },
];

const PRINCIPLES = [
  {
    icon: Scale,
    title: "Deterministic Evaluation",
    desc: "The rule engine produces identical verdicts for identical inputs. No LLM randomness enters the decision path — LLMs extract, rules decide.",
  },
  {
    icon: Eye,
    title: "Full Explainability",
    desc: "Every verdict cites the exact source document, page number, extracted text snippet, and the rule applied. Nothing is a black box.",
  },
  {
    icon: Hash,
    title: "Cryptographic Audit Trail",
    desc: "Every action is written to a SHA-256 hash chain. Each entry references the previous hash — tamper-evident, independently verifiable.",
  },
  {
    icon: Users,
    title: "Human Review Integration",
    desc: "Low-confidence extractions are automatically escalated. The system never silently decides on uncertain data — humans remain in control.",
  },
  {
    icon: Lock,
    title: "Legally Defensible",
    desc: "Designed for procurement disputes. Every evaluation produces a signed, exportable audit record reconstructable from raw document to final verdict.",
  },
  {
    icon: Database,
    title: "Fail-Safe Architecture",
    desc: "System failures produce escalations, not silent verdicts. If evidence cannot be found with sufficient confidence, it goes to review.",
  },
];

const PIPELINE_STEPS = [
  {
    num: "01",
    label: "Document Ingestion",
    desc: "Tender and bidder documents are uploaded, SHA-256 checksummed, and processed through OCR. Page structure, tables, and numerical data are extracted and indexed.",
    note: "Every upload is hash-verified. Source documents are immutable once ingested.",
  },
  {
    num: "02",
    label: "Criteria Extraction",
    desc: "Claude reads the tender document and extracts all eligibility criteria — financial turnover requirements, technical specifications, certification mandates, experience thresholds.",
    note: "Criteria are stored with source snippets so every rule is traceable to its origin.",
  },
  {
    num: "03",
    label: "Value Extraction (RAG)",
    desc: "For each criterion, a retrieval-augmented pipeline locates the relevant section in each bidder's document and extracts the declared value with a confidence score.",
    note: "Extraction confidence is computed and stored. Low-confidence extractions are flagged.",
  },
  {
    num: "04",
    label: "Deterministic Evaluation",
    desc: "A rule-based evaluator compares extracted values against thresholds. ₹6.2Cr vs ₹5Cr minimum is a Python comparison — deterministic, testable, repeatable. No LLM decides.",
    note: "Cases below confidence threshold are automatically escalated to human review.",
  },
  {
    num: "05",
    label: "Audit & Review",
    desc: "Every action is appended to an immutable hash chain. Reviewers can approve, edit, or reject AI decisions with justification — all actions are logged and signed.",
    note: "The full audit record can be exported and independently verified against the chain.",
  },
];

const COMPLIANCE = [
  "GFR 2017 — General Financial Rules compliance evaluation",
  "CVC guidelines — Transparency and accountability requirements",
  "RTI Act 2005 — Right to Information audit readiness",
  "Manual of Office Procedure — Process adherence documentation",
  "CRPF procurement framework — Theme 3 implementation",
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function AboutPage() {
  const navigate = useNavigate();

  return (
    <div style={{ background: "#0B0F1A", color: "#F9FAFB", minHeight: "100vh" }}>

      {/* ── Navbar ── */}
      <motion.nav
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
          height: 64,
          background: "rgba(11,15,26,0.9)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(30,42,59,0.5)",
          display: "flex", alignItems: "center",
          padding: "0 48px", justifyContent: "space-between",
        }}
      >
        <button
          onClick={() => navigate("/")}
          style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
        >
          <Logo size="md" showText />
        </button>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              background: "none", border: "none",
              color: "#9CA3AF", cursor: "pointer",
              display: "flex", alignItems: "center", gap: 4, fontSize: 14,
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#F9FAFB")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9CA3AF")}
          >
            <ArrowLeft size={15} /> Back
          </button>
          <Button variant="primary" size="md" onClick={() => navigate("/login")}>Sign In</Button>
        </div>
      </motion.nav>

      {/* ── Hero ── */}
      <section style={{ paddingTop: 64, position: "relative", overflow: "hidden" }}>
        {/* Background gradient */}
        <div style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(135deg, #0B0F1A 0%, #0D1B2A 40%, #0B1120 100%)",
        }} />
        {/* Grid pattern */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: `
            linear-gradient(rgba(37,99,235,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,99,235,0.04) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute",
          top: "40%", left: "50%",
          transform: "translate(-50%, -50%)",
          width: 500, height: 300,
          background: "radial-gradient(ellipse, rgba(37,99,235,0.12) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div style={{ position: "relative", paddingTop: 80, paddingBottom: 80 }}>
          <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 48px" }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.5 }}
            >
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "#1E3A5F", border: "1px solid rgba(37,99,235,0.3)",
                borderRadius: 6, padding: "6px 14px", marginBottom: 24,
              }}>
                <Shield size={13} color="#60A5FA" />
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", color: "#60A5FA", textTransform: "uppercase" }}>
                  AI for Bharat · Theme 3 · CRPF
                </span>
              </div>

              {/* VAJANS gradient title */}
              <div style={{
                fontSize: 56,
                fontWeight: 900,
                letterSpacing: "-0.02em",
                background: "linear-gradient(135deg, #FFFFFF 0%, #60A5FA 50%, #3B82F6 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                lineHeight: 1.1,
                marginBottom: 8,
              }}>
                About VAJANS
              </div>

              <p style={{ fontSize: 17, color: "#9CA3AF", lineHeight: 1.75, maxWidth: 720, marginBottom: 12 }}>
                <strong style={{ color: "#F9FAFB" }}>VAJANS</strong> — Vigilant AI for Justice and Accountability in Nomenclature Systems — is a government-grade procurement evaluation platform built for the Central Reserve Police Force under the AI for Bharat initiative.
              </p>
              <p style={{ fontSize: 15, color: "#9CA3AF", lineHeight: 1.75, maxWidth: 720 }}>
                It automates the evaluation of tender documents and bidder submissions against eligibility criteria, producing evidence-backed, legally defensible verdicts with a complete cryptographic audit trail.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Mission ── */}
      <Reveal>
        <section style={{ background: "#111827", borderTop: "1px solid #1E2A3B", borderBottom: "1px solid #1E2A3B" }}>
          <div style={{ maxWidth: 900, margin: "0 auto", padding: "64px 48px" }}>
            <div style={{
              fontSize: 11, fontWeight: 700, letterSpacing: "0.15em",
              color: "#60A5FA", textTransform: "uppercase", marginBottom: 16,
            }}>
              Mission
            </div>
            <blockquote style={{
              margin: 0,
              borderLeft: "3px solid #2563EB",
              paddingLeft: 24,
              fontSize: 20, fontWeight: 600, color: "#F9FAFB",
              lineHeight: 1.6, fontStyle: "italic",
            }}>
              "Eliminate subjectivity from government procurement. Every tender evaluated by the same rules, to the same standard, with full transparency — every time."
            </blockquote>
          </div>
        </section>
      </Reveal>

      {/* ── The Problem ── */}
      <section style={{ padding: "64px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 8,
              borderLeft: "3px solid #2563EB", paddingLeft: 16,
            }}>
              The Problem We Solve
            </h2>
            <p style={{ fontSize: 15, color: "#9CA3AF", lineHeight: 1.75, marginBottom: 32 }}>
              Manual tender evaluation in Indian government procurement suffers from three systemic failures:
            </p>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            {[
              { num: "01", title: "Inconsistency", desc: "Two officers evaluating identical bids produce different outcomes. There is no objective, repeatable standard." },
              { num: "02", title: "Opacity",       desc: "Evaluation reasoning is not documented. Rejected bidders cannot understand why, and courts cannot review the basis." },
              { num: "03", title: "Delay",         desc: "Manual review of complex technical and financial criteria takes 5–7 days per tender, creating procurement bottlenecks." },
            ].map(({ num, title, desc }, i) => (
              <Reveal key={num} delay={i * 0.1}>
                <div style={{
                  background: "#111827", border: "1px solid #1E2A3B",
                  borderRadius: 12, padding: 24, height: "100%",
                }}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: "#2D3F57", fontFamily: "JetBrains Mono, monospace", marginBottom: 8 }}>
                    {num}
                  </div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: "#F9FAFB", marginBottom: 8 }}>{title}</h3>
                  <p style={{ fontSize: 14, color: "#9CA3AF", lineHeight: 1.6, margin: 0 }}>{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Design Principles ── */}
      <section style={{ background: "#111827", borderTop: "1px solid #1E2A3B", borderBottom: "1px solid #1E2A3B", padding: "64px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 8,
              borderLeft: "3px solid #2563EB", paddingLeft: 16,
            }}>
              Design Principles
            </h2>
            <p style={{ fontSize: 15, color: "#9CA3AF", lineHeight: 1.75, marginBottom: 32 }}>
              Every architectural decision flows from six non-negotiable principles:
            </p>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 20 }}>
            {PRINCIPLES.map(({ icon: Icon, title, desc }, i) => (
              <Reveal key={title} delay={i * 0.08}>
                <motion.div
                  whileHover={{ y: -2, boxShadow: "0 8px 24px rgba(37,99,235,0.15)" }}
                  style={{
                    display: "flex", gap: 16, padding: 24,
                    background: "#1C2333", borderRadius: 12,
                    border: "1px solid #1E2A3B", height: "100%",
                    transition: "border-color 0.2s",
                    cursor: "default",
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "#2563EB")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "#1E2A3B")}
                >
                  <div style={{
                    flexShrink: 0, width: 40, height: 40, borderRadius: 10,
                    background: "#1E3A5F",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Icon size={20} color="#60A5FA" />
                  </div>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: "#F9FAFB", marginBottom: 6 }}>{title}</h3>
                    <p style={{ fontSize: 13, color: "#9CA3AF", lineHeight: 1.65, margin: 0 }}>{desc}</p>
                  </div>
                </motion.div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section style={{ padding: "64px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 8,
              borderLeft: "3px solid #2563EB", paddingLeft: 16,
            }}>
              How It Works
            </h2>
            <p style={{ fontSize: 15, color: "#9CA3AF", lineHeight: 1.75, marginBottom: 32 }}>
              VAJANS runs a deterministic, multi-stage pipeline on every evaluation job:
            </p>
          </Reveal>
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {PIPELINE_STEPS.map(({ num, label, desc, note }, i) => (
              <Reveal key={num} delay={i * 0.08}>
                <div style={{
                  display: "flex", gap: 24, alignItems: "flex-start",
                  paddingBottom: 32, marginBottom: 32,
                  borderBottom: i < PIPELINE_STEPS.length - 1 ? "1px solid #1E2A3B" : "none",
                }}>
                  {/* Step number */}
                  <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{
                      width: 48, height: 48, borderRadius: 10,
                      background: "#1E3A5F", border: "1px solid rgba(37,99,235,0.4)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: "JetBrains Mono, monospace", fontSize: 14,
                      fontWeight: 700, color: "#60A5FA",
                    }}>
                      {num}
                    </div>
                    {i < PIPELINE_STEPS.length - 1 && (
                      <div style={{ width: 1, flex: 1, background: "#1E2A3B", marginTop: 8, minHeight: 16 }} />
                    )}
                  </div>
                  <div style={{ flex: 1, paddingTop: 4 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: "#F9FAFB", marginBottom: 8 }}>{label}</h3>
                    <p style={{ fontSize: 14, color: "#9CA3AF", lineHeight: 1.7, marginBottom: 8 }}>{desc}</p>
                    <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                      <ShieldCheck size={13} color="#059669" style={{ flexShrink: 0, marginTop: 2 }} />
                      <span style={{ fontSize: 12, color: "#D1FAE5", fontStyle: "italic" }}>{note}</span>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <Reveal>
        <section style={{ background: "#111827", borderTop: "1px solid #1E2A3B", borderBottom: "1px solid #1E2A3B", padding: "64px 48px" }}>
          <div style={{ maxWidth: 900, margin: "0 auto" }}>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 32,
              borderLeft: "3px solid #2563EB", paddingLeft: 16,
            }}>
              Technology Stack
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
              {TECH_STACK.map(({ label, value }, i) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.35 }}
                  style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "12px 16px",
                    background: "#1C2333", borderRadius: 8,
                    border: "1px solid #1E2A3B",
                  }}
                >
                  <span style={{ fontSize: 13, color: "#6B7280" }}>{label}</span>
                  <span style={{ fontSize: 13, color: "#F9FAFB", fontFamily: "JetBrains Mono, monospace", textAlign: "right", marginLeft: 12 }}>{value}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      </Reveal>

      {/* ── Compliance ── */}
      <section style={{ padding: "64px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 8,
              borderLeft: "3px solid #2563EB", paddingLeft: 16,
            }}>
              Regulatory Alignment
            </h2>
            <p style={{ fontSize: 15, color: "#9CA3AF", lineHeight: 1.75, marginBottom: 24 }}>
              Designed to align with the regulatory framework governing Central Government procurement:
            </p>
          </Reveal>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {COMPLIANCE.map((item, i) => (
              <Reveal key={item} delay={i * 0.07}>
                <div style={{
                  display: "flex", gap: 12, alignItems: "flex-start",
                  padding: "12px 16px",
                  background: "#111827", border: "1px solid #1E2A3B",
                  borderLeft: "3px solid #059669", borderRadius: 8,
                  transition: "background 0.15s",
                }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#071D11")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "#111827")}
                >
                  <CheckCircle2 size={15} color="#059669" style={{ flexShrink: 0, marginTop: 1 }} />
                  <span style={{ fontSize: 14, color: "#9CA3AF" }}>{item}</span>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <Reveal>
        <section style={{
          background: "#111827", borderTop: "1px solid #1E2A3B",
          padding: "64px 48px", textAlign: "center",
        }}>
          <h2 style={{ fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 12 }}>Ready to evaluate?</h2>
          <p style={{ fontSize: 15, color: "#9CA3AF", marginBottom: 32 }}>
            Sign in with your officer credentials to begin.
          </p>
          <Button variant="primary" size="lg" icon={<ArrowRight size={16} />} onClick={() => navigate("/login")}>
            Sign In to VAJANS
          </Button>
        </section>
      </Reveal>

      {/* ── Footer ── */}
      <footer style={{ padding: "24px 48px", borderTop: "1px solid #1E2A3B", textAlign: "center" }}>
        <div style={{ fontSize: 13, color: "#6B7280" }}>
          VAJANS · AI for Bharat · Theme 3 · CRPF · Government of India
        </div>
      </footer>
    </div>
  );
}
