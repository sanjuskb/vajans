import type React from "react";

// VAJANS Design System Tokens
// Surface / text / border colors use CSS variables to support dark/light themes.
// Verdict and accent colors are identical in both themes (hardcoded).

export const C = {
  // Surfaces — theme-aware via CSS variables
  bgPrimary:   "var(--bg-primary)",
  bgSecondary: "var(--bg-secondary)",
  bgTertiary:  "var(--bg-tertiary)",
  bgHover:     "var(--bg-hover)",
  borderSubtle:"var(--border-subtle)",
  borderActive:"var(--border-active)",

  // Brand — hardcoded hex so they work in template literals e.g. `${C.accent}30`
  accent:      "#2563EB",
  accentHover: "#1D4ED8",
  accentMuted: "#1E3A5F",
  accentText:  "var(--accent-text)",   // CSS var so light mode shows darker blue

  // Card / topbar / sidebar surfaces
  cardBg:      "var(--card-bg)",
  topbarBg:    "var(--topbar-bg)",
  sidebarBg:   "var(--sidebar-bg)",

  // Chart
  chartGrid:   "var(--chart-grid)",
  chartAxis:   "var(--chart-axis)",

  // Tooltip
  tooltipBg:     "var(--tooltip-bg)",
  tooltipBorder: "var(--tooltip-border)",

  // Table
  tableHeader:   "var(--table-header)",
  tableRow:      "var(--table-row)",
  tableRowHover: "var(--table-row-hover)",

  // Verdicts — same in both themes (always dark-style badges)
  passSolid:   "#059669",
  passText:    "#D1FAE5",
  passBg:      "#064E3B",
  failSolid:   "#DC2626",
  failText:    "#FCA5A5",
  failBg:      "#450A0A",
  uncertainSolid: "#D97706",
  uncertainText:  "#FCD34D",
  uncertainBg:    "#451A03",
  reviewSolid: "#7C3AED",
  reviewText:  "#C4B5FD",
  reviewBg:    "#2E1065",

  // Text — theme-aware via CSS variables
  textPrimary:   "var(--text-primary)",
  textSecondary: "var(--text-secondary)",
  textTertiary:  "var(--text-tertiary)",

  // Functional — same in both themes
  info:    "#0EA5E9",
  warning: "#F59E0B",
  danger:  "#EF4444",
  success: "#10B981",
  neutral: "#6B7280",
} as const;

export const SP = {
  xs:  4,
  sm:  8,
  md:  12,
  lg:  16,
  xl:  24,
  xl2: 32,
  xl3: 48,
  xl4: 64,
} as const;

export const R = {
  card:  8,
  inner: 6,
  badge: 4,
} as const;

// Compound style helpers
export const cardBase: React.CSSProperties = {
  background:   C.cardBg,
  border:       `1px solid ${C.borderSubtle}`,
  borderRadius: 12,
  padding:      SP.xl,
};

export const cardHover: React.CSSProperties = {
  outline: `1px solid ${C.borderActive}`,
};
