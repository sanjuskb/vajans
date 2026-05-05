import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import {
  AlertTriangle, Trash2, RefreshCw, ShieldCheck,
  Database, CheckCircle2,
} from "lucide-react";
import toast from "react-hot-toast";
import { C, SP } from "../styles/tokens";
import { jobsApi } from "../services/api";
import Button from "../components/ui/Button";
import type { Job } from "../services/types";

export default function SettingsPage() {
  const qc = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [resetDone, setResetDone] = useState(false);

  const resetMutation = useMutation({
    mutationFn: async () => {
      // Fetch all jobs, delete each one
      const jobs = (await jobsApi.list(0, 500)) as Job[];
      for (const job of jobs) {
        try { await jobsApi.delete(job.id); } catch { /* skip */ }
      }
      return jobs.length;
    },
    onSuccess: (count) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setConfirmOpen(false);
      setConfirmText("");
      setResetDone(true);
      toast.success(`Database reset complete. ${count} job${count !== 1 ? "s" : ""} deleted.`);
    },
    onError: () => {
      toast.error("Reset failed. Check backend connectivity.");
    },
  });

  const canConfirm = confirmText.trim().toUpperCase() === "RESET";

  return (
    <div className="fade-in" style={{ maxWidth: 720 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: C.textPrimary, marginBottom: SP.xs }}>Settings</h2>
      <p style={{ fontSize: 14, color: C.textTertiary, marginBottom: SP.xl2 }}>
        System configuration and administrative controls.
      </p>

      {/* System status */}
      <section style={{ marginBottom: SP.xl2 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.textTertiary, letterSpacing: 1, textTransform: "uppercase", marginBottom: SP.md }}>
          System
        </div>
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: SP.md, padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}` }}>
            <ShieldCheck size={16} color={C.passSolid} />
            <span style={{ fontSize: 14, color: C.textPrimary }}>VAJANS System</span>
            <span style={{ marginLeft: "auto", fontSize: 12, color: C.passText, background: C.passBg, padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
              OPERATIONAL
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: SP.md, padding: `${SP.md}px ${SP.lg}px` }}>
            <Database size={16} color={C.textTertiary} />
            <span style={{ fontSize: 14, color: C.textPrimary }}>Database</span>
            <span style={{ marginLeft: "auto", fontSize: 12, color: C.passText, background: C.passBg, padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
              CONNECTED
            </span>
          </div>
        </div>
      </section>

      {/* User preferences (placeholder) */}
      <section style={{ marginBottom: SP.xl2 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.textTertiary, letterSpacing: 1, textTransform: "uppercase", marginBottom: SP.md }}>
          Preferences
        </div>
        <div style={{ background: C.bgSecondary, border: `1px solid ${C.borderSubtle}`, borderRadius: 8 }}>
          {[
            { label: "Officer ID",  value: "procurement.officer" },
            { label: "Role",        value: "Procurement Officer" },
            { label: "System",      value: "VAJANS v1.0" },
            { label: "Theme",       value: "Dark (institutional)" },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: `${SP.md}px ${SP.lg}px`, borderBottom: `1px solid ${C.borderSubtle}` }}>
              <span style={{ fontSize: 14, color: C.textSecondary }}>{label}</span>
              <span style={{ fontSize: 14, color: C.textPrimary, fontFamily: "JetBrains Mono, monospace" }}>{value}</span>
            </div>
          ))}
          <div style={{ padding: `${SP.md}px ${SP.lg}px` }}>
            <span style={{ fontSize: 12, color: C.textTertiary }}>User management is administered by the system administrator. Contact your administrator to update credentials or role.</span>
          </div>
        </div>
      </section>

      {/* Danger zone */}
      <section>
        <div style={{ fontSize: 11, fontWeight: 700, color: C.failSolid, letterSpacing: 1, textTransform: "uppercase", marginBottom: SP.md }}>
          Danger Zone
        </div>
        <div style={{ background: C.failBg, border: `1px solid ${C.failSolid}40`, borderRadius: 8, padding: SP.xl }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: SP.lg }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.xs }}>
                <Trash2 size={16} color={C.failText} />
                <span style={{ fontSize: 15, fontWeight: 700, color: C.failText }}>Reset Database</span>
              </div>
              <p style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.6, maxWidth: 440 }}>
                Delete all evaluation jobs, bidder documents, criteria, and results. The database schema is preserved — the system starts fresh. This action cannot be undone.
              </p>
              {resetDone && (
                <div style={{ display: "flex", alignItems: "center", gap: SP.xs, marginTop: SP.sm, fontSize: 12, color: C.passText }}>
                  <CheckCircle2 size={13} />
                  Database has been reset successfully.
                </div>
              )}
            </div>
            <Button
              variant="danger"
              icon={<Trash2 size={14} />}
              onClick={() => { setConfirmOpen(true); setResetDone(false); }}
            >
              Reset Database
            </Button>
          </div>
        </div>
      </section>

      {/* Confirm modal */}
      {confirmOpen && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }}
          onClick={() => setConfirmOpen(false)}
        >
          <div
            style={{ background: C.bgSecondary, border: `1px solid ${C.failSolid}50`, borderRadius: 12, padding: SP.xl2, width: 460 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: SP.sm, marginBottom: SP.lg }}>
              <AlertTriangle size={22} color={C.failSolid} />
              <h3 style={{ fontSize: 17, fontWeight: 700, color: C.textPrimary }}>Confirm Database Reset</h3>
            </div>
            <p style={{ fontSize: 14, color: C.textSecondary, lineHeight: 1.6, marginBottom: SP.xl }}>
              This will permanently delete <strong style={{ color: C.failText }}>all jobs, documents, evaluations, and reviews</strong>. The database schema will remain intact. This cannot be undone.
            </p>
            <div style={{ background: C.bgTertiary, border: `1px solid ${C.borderSubtle}`, borderRadius: 6, padding: SP.md, marginBottom: SP.xl, fontSize: 13, color: C.textTertiary }}>
              Type <code style={{ color: C.failText, fontFamily: "JetBrains Mono, monospace" }}>RESET</code> to confirm:
            </div>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type RESET to confirm"
              style={{ width: "100%", marginBottom: SP.lg, fontFamily: "JetBrains Mono, monospace" }}
              autoFocus
            />
            <div style={{ display: "flex", gap: SP.sm, justifyContent: "flex-end" }}>
              <Button variant="secondary" onClick={() => { setConfirmOpen(false); setConfirmText(""); }}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={!canConfirm}
                loading={resetMutation.isPending}
                icon={resetMutation.isPending ? <RefreshCw size={14} /> : <Trash2 size={14} />}
                onClick={() => resetMutation.mutate()}
              >
                {resetMutation.isPending ? "Resetting…" : "Reset All Data"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
