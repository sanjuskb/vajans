import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { C, SP } from "../styles/tokens";
import Button from "../components/ui/Button";
import Logo from "../components/ui/Logo";
import { authApi } from "../services/api";
import { useStore } from "../store/useStore";

const FEATURES = [
  "Legally defensible decisions with source evidence",
  "Complete cryptographic audit trail",
  "AI-extracted values, deterministic verdicts",
  "Human review escalation for uncertain cases",
];

export default function LoginPage() {
  const navigate = useNavigate();
  const setUser  = useStore((s) => s.setUser);

  const [show,    setShow]    = useState(false);
  const [loading, setLoading] = useState(false);
  const [id,      setId]      = useState("");
  const [pw,      setPw]      = useState("");
  const [error,   setError]   = useState("");

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!id.trim() || !pw.trim()) {
      setError("Officer ID and password are required.");
      return;
    }
    setLoading(true);
    try {
      const data = await authApi.login(id.trim(), pw);
      setUser({ username: data.username, role: data.role, token: data.access_token });
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.message ?? "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.bgPrimary }}>

      {/* ── Left panel — brand ── */}
      <div style={{
        width: "42%", flexShrink: 0,
        background: C.bgSecondary,
        borderRight: `1px solid ${C.borderSubtle}`,
        display: "flex", flexDirection: "column",
        justifyContent: "space-between",
        padding: `${SP.xl4}px ${SP.xl3}px`,
        position: "relative", overflow: "hidden",
      }}>
        {/* Background watermark — faint render of the new brand mark */}
        <div style={{
          position: "absolute", top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          opacity: 0.06, pointerEvents: "none",
          userSelect: "none",
          filter: "blur(0.5px)",
        }}>
          <img
            src="/brand/vajans-logo-512.png"
            width={420}
            height={420}
            alt=""
            aria-hidden="true"
            draggable={false}
            decoding="async"
            loading="lazy"
            style={{ display: "block", borderRadius: 32 }}
          />
        </div>

        <div>
          <div style={{ marginBottom: SP.xl2 }}>
            <Logo size="lg" clickable showText />
          </div>
          <p style={{ fontSize: 15, color: C.textSecondary, lineHeight: 1.75, maxWidth: 300, marginBottom: SP.xl2 }}>
            Automated, evidence-backed procurement evaluation for government officers.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: SP.md }}>
            {FEATURES.map((f) => (
              <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: SP.sm }}>
                <CheckCircle2 size={15} color={C.passSolid} style={{ flexShrink: 0, marginTop: 2 }} />
                <span style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.5 }}>{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Compliance note */}
        <div style={{ fontSize: 11, color: C.textTertiary, lineHeight: 1.6 }}>
          VAJANS · Theme 3 · AI for Bharat<br />
          Central Reserve Police Force
        </div>
      </div>

      {/* ── Right panel — form ── */}
      <div style={{
        flex: 1, display: "flex", alignItems: "center",
        justifyContent: "center", padding: SP.xl3,
      }}>
        <div style={{ width: "100%", maxWidth: 400 }}>

          {/* Header */}
          <div style={{ marginBottom: SP.xl2 }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: C.textPrimary, marginBottom: SP.xs }}>
              Sign in to VAJANS
            </h2>
            <p style={{ fontSize: 14, color: C.textTertiary }}>
              Authorized procurement officers only
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div style={{
              background: C.failBg, border: `1px solid ${C.failSolid}40`,
              borderRadius: 6, padding: `${SP.sm}px ${SP.md}px`,
              fontSize: 13, color: C.failText, marginBottom: SP.lg,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSignIn}>
            <div style={{ marginBottom: SP.lg }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: C.textSecondary, marginBottom: SP.sm }}>
                Officer ID / Username
              </label>
              <input
                type="text" value={id}
                onChange={(e) => setId(e.target.value)}
                style={{ width: "100%" }}
                placeholder="officer"
                autoComplete="username"
                autoFocus
              />
            </div>

            <div style={{ marginBottom: SP.xl }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: C.textSecondary, marginBottom: SP.sm }}>
                Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={show ? "text" : "password"} value={pw}
                  onChange={(e) => setPw(e.target.value)}
                  style={{ width: "100%", paddingRight: 44 }}
                  placeholder="Enter password"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShow(!show)}
                  style={{
                    position: "absolute", right: 10, top: "50%",
                    transform: "translateY(-50%)",
                    background: "none", border: "none",
                    color: C.textTertiary, cursor: "pointer", padding: 4,
                    display: "flex",
                  }}
                >
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: SP.xl }}>
              <label style={{ display: "flex", alignItems: "center", gap: SP.sm, fontSize: 13, color: C.textSecondary, cursor: "pointer" }}>
                <input type="checkbox" style={{ width: 14, height: 14, accentColor: C.accent }} />
                Remember this device
              </label>
              <span style={{ fontSize: 12, color: C.textTertiary }}>Forgot credentials? Contact admin</span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              style={{ width: "100%" }}
            >
              Sign In
            </Button>
          </form>

          {/* Security notice */}
          <div style={{
            marginTop: SP.xl2, padding: SP.md,
            background: C.bgTertiary, borderRadius: 6,
            border: `1px solid ${C.borderSubtle}`,
            display: "flex", gap: SP.sm, alignItems: "flex-start",
          }}>
            <Lock size={13} color={C.textTertiary} style={{ marginTop: 2, flexShrink: 0 }} />
            <p style={{ fontSize: 12, color: C.textTertiary, lineHeight: 1.55 }}>
              Access is restricted to authorized personnel. Unauthorized access attempts are logged and reported to the security team.
            </p>
          </div>

          {/* Integrity badge */}
          <div style={{ display: "flex", alignItems: "center", gap: SP.xs, marginTop: SP.lg, justifyContent: "center" }}>
            <ShieldCheck size={12} color={C.passSolid} />
            <span style={{ fontSize: 11, color: C.textTertiary }}>Secured · Audited · Compliant</span>
          </div>
        </div>
      </div>
    </div>
  );
}
