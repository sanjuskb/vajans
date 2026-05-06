import { useNavigate } from "react-router-dom";

interface LogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  showText?: boolean;
  /** If true, clicking navigates to /about */
  clickable?: boolean;
  collapsed?: boolean;
}

// Display dimensions (CSS pixels). The actual image asset is served at higher
// physical resolution via srcSet so the mark stays crisp on retina / 2x DPR
// screens without forcing a heavier asset on standard-DPR clients.
const ICON_SIZES = { sm: 22, md: 28, lg: 40, xl: 96 } as const;
const TEXT_SIZES = { sm: 14, md: 16, lg: 24, xl: 32 } as const;
const SUB_SIZES  = { sm: 0, md: 9, lg: 10, xl: 12 } as const;

// Asset paths (served from /public/brand). Resolution-tier srcSet lets the
// browser pick the smallest sufficient asset for the user's display.
const LOGO_SRC     = "/brand/vajans-logo-128.png";
const LOGO_SRC_SET =
  "/brand/vajans-logo-128.png 1x, " +
  "/brand/vajans-logo-256.png 2x, " +
  "/brand/vajans-logo-512.png 4x";

export default function Logo({
  size = "md",
  className,
  showText = true,
  clickable = false,
  collapsed = false,
}: LogoProps) {
  const navigate = useNavigate();
  const px = ICON_SIZES[size];

  // The brand mark itself. width/height are intrinsic so the browser reserves
  // exact box space before the PNG decodes (zero CLS). Subtle border-radius
  // softens the dark-navy corners against light theme without clipping the
  // hexagon — the hexagon sits inside its own padding within the artwork.
  const mark = (
    <img
      src={LOGO_SRC}
      srcSet={LOGO_SRC_SET}
      width={px}
      height={px}
      alt="VAJANS"
      decoding="async"
      loading="eager"
      draggable={false}
      style={{
        width: px,
        height: px,
        flexShrink: 0,
        objectFit: "contain",
        borderRadius: size === "xl" ? 16 : size === "lg" ? 8 : 6,
        display: "block",
      }}
    />
  );

  return (
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
            fontSize: TEXT_SIZES[size],
            fontWeight: 800,
            color: "var(--text-primary)",
            letterSpacing: "0.12em",
            lineHeight: 1,
          }}>
            VAJANS
          </div>
          {size !== "sm" && (
            <div style={{
              fontSize: SUB_SIZES[size],
              color: "var(--text-tertiary)",
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
}
