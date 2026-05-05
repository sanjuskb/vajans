import { useNavigate } from "react-router-dom";
import { C, SP } from "../styles/tokens";
import Button from "../components/ui/Button";
import { LayoutDashboard, ArrowLeft } from "lucide-react";

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", minHeight: "100vh",
      textAlign: "center", padding: SP.xl2,
      background: C.bgPrimary,
    }}>
      <div style={{
        fontSize: 96, fontWeight: 900,
        color: C.bgTertiary, lineHeight: 1,
        marginBottom: SP.lg,
        fontFamily: "JetBrains Mono, monospace",
        letterSpacing: "-0.04em",
        userSelect: "none",
      }}>
        404
      </div>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: C.textSecondary, marginBottom: SP.sm }}>
        Page not found
      </h1>
      <p style={{ fontSize: 14, color: C.textTertiary, marginBottom: SP.xl, maxWidth: 320, lineHeight: 1.6 }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div style={{ display: "flex", gap: SP.sm }}>
        <Button variant="secondary" icon={<ArrowLeft size={14} />} onClick={() => navigate(-1)}>
          Go back
        </Button>
        <Button variant="primary" icon={<LayoutDashboard size={14} />} onClick={() => navigate("/dashboard")}>
          Dashboard
        </Button>
      </div>
    </div>
  );
}
