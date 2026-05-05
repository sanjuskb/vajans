import { useNavigate } from "react-router-dom";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
  /** If true, clicking navigates to /about */
  clickable?: boolean;
  collapsed?: boolean;
}

export default function Logo({
  size = "md",
  className,
  showText = true,
  clickable = false,
  collapsed = false,
}: LogoProps) {
  const navigate = useNavigate();

  const iconSizes = { sm: 22, md: 28, lg: 40 };
  const textSizes = { sm: "14px", md: "16px", lg: "24px" };
  const px = iconSizes[size];

  const mark = (
    <svg
      width={px}
      height={px}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      {/* Hexagonal outer frame — structural trust */}
      <path
        d="M16 2L27.856 8.5V21.5L16 28L4.144 21.5V8.5L16 2Z"
        stroke="#2563EB"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Inner shield accent — institutional authority */}
      <path
        d="M16 7L22 10.5V17.5L16 21L10 17.5V10.5L16 7Z"
        fill="#1E3A5F"
        stroke="#2563EB"
        strokeWidth="0.75"
      />
      {/* Scale of justice centerpiece — evaluation core */}
      <line x1="16" y1="10" x2="16" y2="18" stroke="#60A5FA" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="12.5" y1="12.5" x2="19.5" y2="12.5" stroke="#60A5FA" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="12.5" cy="14.5" r="1.5" fill="#60A5FA" />
      <circle cx="19.5" cy="14.5" r="1.5" fill="#60A5FA" />
      {/* Verdict tick — deterministic decision */}
      <path
        d="M14 17.5L15.5 19L18.5 16"
        stroke="#10B981"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  const content = (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: collapsed ? 0 : 10,
        cursor: clickable ? "pointer" : "default",
        userSelect: "none",
      }}
      className={className}
      onClick={clickable ? () => navigate("/about") : undefined}
      title={clickable ? "About VAJANS" : undefined}
    >
      {mark}
      {showText && !collapsed && (
        <div>
          <div style={{
            fontSize: textSizes[size],
            fontWeight: 800,
            color: "#F9FAFB",
            letterSpacing: "0.12em",
            lineHeight: 1,
          }}>
            VAJANS
          </div>
          {size !== "sm" && (
            <div style={{
              fontSize: "9px",
              color: "#6B7280",
              letterSpacing: "0.08em",
              marginTop: 2,
              textTransform: "uppercase",
            }}>
              Tender Evaluation
            </div>
          )}
        </div>
      )}
    </div>
  );

  return content;
}
