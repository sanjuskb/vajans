import { useNavigate } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import {
  Clock, GitBranch, AlertOctagon, ArrowRight,
  FileText, Cpu, CheckCircle2, BookOpen, Lock, ShieldCheck,
  FileSearch, Shield,
} from "lucide-react";
import Button from "../components/ui/Button";
import Logo from "../components/ui/Logo";

// ── Reusable reveal wrapper ───────────────────────────────────────────────────

function Reveal({
  children,
  delay = 0,
  y = 20,
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{ duration: 0.45, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {children}
    </motion.div>
  );
}

// ── Data ──────────────────────────────────────────────────────────────────────

const PROBLEMS = [
  {
    icon: Clock,
    title: "5–7 days per tender",
    desc: "Manual review creates an unbearable bottleneck — every day of delay has procurement cost implications and exposes the process to pressure.",
  },
  {
    icon: GitBranch,
    title: "No consistent evaluation",
    desc: "Two officers evaluating identical bids produce different outcomes. Subjectivity is the enemy of fairness and legal defensibility.",
  },
  {
    icon: AlertOctagon,
    title: "Legally exposed decisions",
    desc: "Without a traceable, evidence-linked audit trail, every evaluation is a potential liability in procurement disputes and RTI requests.",
  },
];

const HOW_STEPS = [
  { icon: FileText,     label: "Ingest",         desc: "Upload tender & bidder documents" },
  { icon: BookOpen,     label: "Extract Rules",  desc: "AI reads eligibility criteria" },
  { icon: Cpu,          label: "Extract Values", desc: "RAG extracts bidder data" },
  { icon: CheckCircle2, label: "Evaluate",       desc: "Deterministic rule engine decides" },
  { icon: Lock,         label: "Audit + Review", desc: "Full hash-chain audit trail" },
];

const FEATURES = [
  {
    icon: FileSearch,
    color: "#3B82F6",
    title: "Document Intelligence",
    desc: "AI extracts eligibility criteria from complex tender PDFs. Every criterion traced to source page and paragraph.",
  },
  {
    icon: Shield,
    color: "#059669",
    title: "Deterministic Engine",
    desc: "Same input always produces identical output. No LLM randomness in the decision path — LLMs extract, rules decide.",
  },
  {
    icon: Lock,
    color: "#7C3AED",
    title: "Legal Audit Trail",
    desc: "SHA-256 cryptographic hash chain links every action. Tamper-evident, court-admissible, independently verifiable.",
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={{ background: "#0B0F1A", color: "#F9FAFB", minHeight: "100vh" }}>

      {/* ── Fixed Navbar ── */}
      <motion.nav
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
          height: 64,
          background: "rgba(11,15,26,0.9)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(30,42,59,0.5)",
          display: "flex", alignItems: "center",
          padding: "0 48px",
          justifyContent: "space-between",
        }}
      >
        <Logo size="md" clickable showText />
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button
            onClick={() => navigate("/about")}
            style={{ fontSize: 14, color: "#9CA3AF", background: "none", border: "none", cursor: "pointer", transition: "color 0.15s" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#F9FAFB")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#9CA3AF")}
          >
            About
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

        {/* Grid pattern overlay */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: `
            linear-gradient(rgba(37,99,235,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(37,99,235,0.05) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }} />

        {/* Radial glow behind title */}
        <div style={{
          position: "absolute",
          top: "30%", left: "50%",
          transform: "translate(-50%, -50%)",
          width: 600, height: 400,
          background: "radial-gradient(ellipse, rgba(37,99,235,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        <div style={{
          position: "relative",
          padding: "96px 48px 80px",
          maxWidth: 900, margin: "0 auto", textAlign: "center",
        }}>
          {/* Institution badge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4 }}
            style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "#1E3A5F", border: "1px solid rgba(37,99,235,0.3)",
              borderRadius: 6, padding: "6px 14px", marginBottom: 32,
            }}
          >
            <ShieldCheck size={13} color="#60A5FA" />
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", color: "#60A5FA", textTransform: "uppercase" }}>
              AI for Bharat · Government Procurement · Theme 3 · CRPF
            </span>
          </motion.div>

          {/* VAJANS title with gradient */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <div style={{
              fontSize: 72,
              fontWeight: 900,
              letterSpacing: "-0.02em",
              background: "linear-gradient(135deg, #FFFFFF 0%, #60A5FA 50%, #3B82F6 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              lineHeight: 1.1,
              marginBottom: 8,
            }}>
              VAJANS
            </div>
            <div style={{
              fontSize: 14,
              fontWeight: 500,
              letterSpacing: "0.3em",
              color: "#60A5FA",
              textTransform: "uppercase",
              marginBottom: 28,
            }}>
              Verified AI-driven Judgement and Normalization System
            </div>
          </motion.div>

          {/* Tagline */}
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            style={{
              fontSize: 36, fontWeight: 700, color: "#F9FAFB",
              lineHeight: 1.3, maxWidth: 700, textAlign: "center",
              margin: "0 auto 16px", letterSpacing: "-0.01em",
            }}
          >
            Tender Evaluation That<br />
            <span style={{ color: "#60A5FA" }}>Stands Up in Court</span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.45 }}
            style={{
              fontSize: 18, color: "#9CA3AF",
              maxWidth: 560, textAlign: "center",
              lineHeight: 1.7, margin: "0 auto 40px",
            }}
          >
            Deterministic AI evaluation with complete audit trail.
            Legally defensible procurement decisions in hours, not days.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            style={{ display: "flex", gap: 16, justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}
          >
            <button
              onClick={() => navigate("/login")}
              style={{
                background: "#2563EB", color: "white",
                padding: "14px 32px", borderRadius: 8,
                fontSize: 16, fontWeight: 600, border: "none", cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#1D4ED8")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "#2563EB")}
            >
              Start Evaluation <ArrowRight size={16} />
            </button>
            <button
              onClick={() => navigate("/about")}
              style={{
                background: "transparent", color: "#60A5FA",
                padding: "14px 32px", border: "1px solid #2D3F57",
                borderRadius: 8, fontSize: 16, fontWeight: 500,
                cursor: "pointer", transition: "border-color 0.15s",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#3B82F6"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#2D3F57"; }}
            >
              See how it works
            </button>
          </motion.div>

          {/* Trust badges */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.65, duration: 0.4 }}
            style={{
              display: "flex", gap: 40, alignItems: "center", justifyContent: "center", marginTop: 56,
              background: "rgba(17,24,39,0.7)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(37,99,235,0.2)",
              borderRadius: 16, padding: "24px 48px",
              boxShadow: "0 4px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: "#F9FAFB" }}>5-7 Days</div>
              <div style={{ fontSize: 13, color: "#9CA3AF", marginTop: 2 }}>Reduced to Hours</div>
            </div>
            <div style={{ width: 1, height: 40, background: "#1E2A3B" }} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: "#059669" }}>100%</div>
              <div style={{ fontSize: 13, color: "#9CA3AF", marginTop: 2 }}>Audit Traceable</div>
            </div>
            <div style={{ width: 1, height: 40, background: "#1E2A3B" }} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: "#3B82F6" }}>Deterministic</div>
              <div style={{ fontSize: 13, color: "#9CA3AF", marginTop: 2 }}>Every Run</div>
            </div>
            <div style={{ width: 1, height: 40, background: "#1E2A3B" }} />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: "#F59E0B" }}>SHA-256</div>
              <div style={{ fontSize: 13, color: "#9CA3AF", marginTop: 2 }}>Tamper-Evident Chain</div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Feature Cards ── */}
      <section style={{ padding: "80px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <div style={{ textAlign: "center", marginBottom: 48 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", color: "#60A5FA", textTransform: "uppercase", marginBottom: 12 }}>
                Built for Accountability
              </div>
              <h2 style={{ fontSize: 28, fontWeight: 700, color: "#F9FAFB", margin: 0 }}>
                Everything you need for defensible procurement
              </h2>
            </div>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            {FEATURES.map(({ icon: Icon, color, title, desc }, i) => (
              <Reveal key={title} delay={i * 0.1}>
                <div
                  style={{
                    background: "#111827",
                    border: "1px solid #1E2A3B",
                    borderRadius: 12,
                    padding: 24,
                    height: "100%",
                    transition: "border-color 0.2s, transform 0.2s, box-shadow 0.2s",
                    cursor: "default",
                  }}
                  onMouseEnter={(e) => { const d = e.currentTarget as HTMLDivElement; d.style.borderColor = "#2563EB"; d.style.transform = "translateY(-3px)"; d.style.boxShadow = "0 12px 32px rgba(37,99,235,0.15)"; }}
                  onMouseLeave={(e) => { const d = e.currentTarget as HTMLDivElement; d.style.borderColor = "#1E2A3B"; d.style.transform = "translateY(0)"; d.style.boxShadow = "none"; }}
                >
                  <div style={{
                    width: 44, height: 44, borderRadius: 10,
                    background: `${color}20`, border: `1px solid ${color}40`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginBottom: 16,
                  }}>
                    <Icon size={20} color={color} />
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#F9FAFB", marginBottom: 8 }}>{title}</div>
                  <p style={{ fontSize: 14, color: "#9CA3AF", lineHeight: 1.65, margin: 0 }}>{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Problem Statement ── */}
      <section style={{
        background: "#111827",
        borderTop: "1px solid #1E2A3B",
        borderBottom: "1px solid #1E2A3B",
        padding: "80px 48px",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", color: "#60A5FA", textTransform: "uppercase", marginBottom: 12 }}>
              The Problem
            </div>
            <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 40, color: "#F9FAFB" }}>
              Manual procurement evaluation is broken
            </h2>
          </Reveal>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            {PROBLEMS.map(({ icon: Icon, title, desc }, i) => (
              <Reveal key={title} delay={i * 0.1}>
                <div style={{
                  background: "#1C2333", border: "1px solid #1E2A3B",
                  borderRadius: 12, padding: 24,
                  borderTop: "2px solid #DC2626",
                  height: "100%",
                  transition: "transform 0.2s, box-shadow 0.2s",
                }}
                  onMouseEnter={(e) => { const d = e.currentTarget as HTMLDivElement; d.style.transform = "translateY(-2px)"; d.style.boxShadow = "0 8px 24px rgba(220,38,38,0.12)"; }}
                  onMouseLeave={(e) => { const d = e.currentTarget as HTMLDivElement; d.style.transform = "translateY(0)"; d.style.boxShadow = "none"; }}
                >
                  <Icon size={24} color="#DC2626" style={{ marginBottom: 16 }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8, color: "#F9FAFB" }}>{title}</h3>
                  <p style={{ fontSize: 14, color: "#9CA3AF", lineHeight: 1.65, margin: 0 }}>{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section id="how" style={{ padding: "80px 48px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Reveal>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.15em", color: "#60A5FA", textTransform: "uppercase", marginBottom: 12 }}>
              How It Works
            </div>
            <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 48, color: "#F9FAFB" }}>
              Five-stage deterministic pipeline
            </h2>
          </Reveal>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 0, justifyContent: "space-between" }}>
            {HOW_STEPS.map(({ icon: Icon, label, desc }, i) => (
              <Reveal key={label} delay={i * 0.1} y={12}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 0 }}>
                  <div style={{ textAlign: "center", flex: 1, padding: "0 8px" }}>
                    <motion.div
                      whileHover={{ scale: 1.06 }}
                      transition={{ type: "spring", stiffness: 400, damping: 25 }}
                      style={{
                        width: 52, height: 52, borderRadius: "50%",
                        background: "#1E3A5F", border: "1.5px solid #2563EB",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        margin: "0 auto", marginBottom: 12,
                      }}
                    >
                      <Icon size={20} color="#60A5FA" />
                    </motion.div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#F9FAFB", marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 11, color: "#6B7280", lineHeight: 1.5 }}>{desc}</div>
                  </div>
                  {i < HOW_STEPS.length - 1 && (
                    <div style={{ flexShrink: 0, paddingTop: 26, color: "#374151" }}>
                      <ArrowRight size={16} />
                    </div>
                  )}
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <Reveal>
        <section style={{
          background: "linear-gradient(135deg, #0F2748 0%, #1E3A5F 50%, #0F2748 100%)",
          borderTop: "1px solid rgba(37,99,235,0.3)",
          borderBottom: "1px solid rgba(37,99,235,0.3)",
          padding: "80px 48px",
          textAlign: "center",
        }}>
          <div style={{ maxWidth: 600, margin: "0 auto" }}>
            <h2 style={{ fontSize: 26, fontWeight: 700, color: "#F9FAFB", marginBottom: 12 }}>
              Ready to modernize procurement?
            </h2>
            <p style={{ fontSize: 15, color: "#9CA3AF", marginBottom: 32, lineHeight: 1.7 }}>
              Sign in with your officer credentials. Evaluation results are available within minutes.
            </p>
            <button
              onClick={() => navigate("/login")}
              style={{
                background: "#2563EB", color: "white",
                padding: "14px 32px", borderRadius: 8,
                fontSize: 16, fontWeight: 600, border: "none", cursor: "pointer",
                display: "inline-flex", alignItems: "center", gap: 8,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#1D4ED8")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "#2563EB")}
            >
              Sign In to VAJANS <ArrowRight size={16} />
            </button>
          </div>
        </section>
      </Reveal>

      {/* ── Footer ── */}
      <footer style={{
        padding: "24px 48px",
        borderTop: "1px solid #1E2A3B",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        flexWrap: "wrap", gap: 12,
      }}>
        <Logo size="sm" showText />
        <div style={{ fontSize: 12, color: "#6B7280" }}>
          Theme 3 · CRPF · AI for Bharat · Government of India
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {["About", "Privacy", "Terms"].map((label) => (
            <button
              key={label}
              onClick={() => label === "About" ? navigate("/about") : undefined}
              style={{ background: "none", border: "none", color: "#6B7280", cursor: "pointer", fontSize: 12, transition: "color 0.15s" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#9CA3AF")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#6B7280")}
            >
              {label}
            </button>
          ))}
        </div>
      </footer>
    </div>
  );
}
