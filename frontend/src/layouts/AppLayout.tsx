import React, { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard, Briefcase, ClipboardCheck, ScrollText,
  Settings, HelpCircle, LogOut, ChevronLeft, ChevronRight,
  Plus, Sun, Moon,
} from "lucide-react";
import { C, SP } from "../styles/tokens";
import { jobsApi, analyzeApi } from "../services/api";
import { useStore } from "../store/useStore";
import Logo from "../components/ui/Logo";
import NotificationDropdown from "../components/notifications/NotificationDropdown";
import type { Job } from "../services/types";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/jobs":      "Evaluations",
  "/review":    "Review Queue",
  "/audit":     "Audit Logs",
  "/settings":  "Settings",
  "/help":      "Help",
};

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate  = useNavigate();
  const location  = useLocation();
  const W = collapsed ? 64 : 240;

  const { theme, setTheme, user, clearUser } = useStore();

  // Redirect to login if no token
  useEffect(() => {
    if (!user) {
      navigate("/login", { replace: true });
    }
  }, [user, navigate]);

  const handleLogout = () => {
    clearUser();
    navigate("/login");
  };

  const title = Object.entries(PAGE_TITLES).find(([path]) =>
    location.pathname === path || location.pathname.startsWith(path + "/")
  )?.[1] ?? "VAJANS";

  const segments = location.pathname.split("/").filter(Boolean);
  const breadcrumbs = segments.map((seg, i) => ({
    label: seg.length === 36 ? seg.slice(0,8) + "…" : seg.replace(/-/g, " "),
    path: "/" + segments.slice(0, i + 1).join("/"),
  }));

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn:  () => jobsApi.list(0, 100),
    staleTime: 60_000,
  });
  const completedJobs = (jobs as Job[]).filter((j) => j.status === "completed");

  const { data: pendingCount = 0 } = useQuery({
    queryKey: ["pending-review-count", completedJobs.map((j) => j.id).join(",")],
    queryFn: async () => {
      let count = 0;
      for (const job of completedJobs.slice(0, 5)) {
        try {
          const dash = await analyzeApi.getDashboard(job.id);
          count += dash.summary.unknown;
        } catch { /* skip */ }
      }
      return count;
    },
    enabled: completedJobs.length > 0,
    staleTime: 120_000,
  });

  const NAV_PRIMARY = [
    { to: "/dashboard", label: "Dashboard",   Icon: LayoutDashboard, count: 0 },
    { to: "/jobs",      label: "Jobs",         Icon: Briefcase,       count: 0 },
    { to: "/review",    label: "Review Queue", Icon: ClipboardCheck,  count: pendingCount },
    { to: "/audit",     label: "Audit Logs",   Icon: ScrollText,      count: 0 },
  ];
  const NAV_SYSTEM = [
    { to: "/settings", label: "Settings", Icon: Settings },
    { to: "/help",     label: "Help",     Icon: HelpCircle },
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.bgPrimary }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: W, flexShrink: 0,
        background: "var(--sidebar-bg)",
        borderRight: "1px solid var(--nav-divider)",
        display: "flex", flexDirection: "column",
        transition: "width 0.2s ease",
        position: "fixed", left: 0, top: 0, bottom: 0,
        zIndex: 50, overflow: "hidden",
      }}>
        {/* Brand header */}
        <div style={{
          height: 64, display: "flex", alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
          padding: collapsed ? 0 : `0 ${SP.lg}px 0 ${SP.md}px`,
          borderBottom: "1px solid var(--nav-divider)",
          flexShrink: 0,
        }}>
          <Logo size="md" collapsed={collapsed} clickable showText={!collapsed} />
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              style={{
                background: "none", border: "none",
                color: "var(--nav-icon)", cursor: "pointer",
                padding: SP.xs, borderRadius: 4,
                display: "flex", alignItems: "center",
              }}
            >
              <ChevronLeft size={15} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: `${SP.sm}px ${collapsed ? 6 : SP.sm}px`, overflow: "auto" }}>
          {!collapsed && (
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--nav-section-label)", letterSpacing: "0.1em", padding: `${SP.sm}px ${SP.sm}px ${SP.xs}px`, textTransform: "uppercase" }}>
              Navigation
            </div>
          )}
          {NAV_PRIMARY.map(({ to, label, Icon, count }) => (
            <NavItem key={to} to={to} label={label} icon={<Icon size={16} />} collapsed={collapsed} badge={count} />
          ))}

          <div style={{ height: 1, background: "var(--nav-divider)", margin: `${SP.sm}px 0` }} />

          {!collapsed && (
            <div style={{ fontSize: 10, fontWeight: 700, color: "var(--nav-section-label)", letterSpacing: "0.1em", padding: `${SP.sm}px ${SP.sm}px ${SP.xs}px`, textTransform: "uppercase" }}>
              System
            </div>
          )}
          {NAV_SYSTEM.map(({ to, label, Icon }) => (
            <NavItem key={to} to={to} label={label} icon={<Icon size={16} />} collapsed={collapsed} badge={0} />
          ))}
        </nav>

        {/* User section */}
        <div style={{
          borderTop: "1px solid var(--nav-divider)",
          padding: collapsed ? `${SP.sm}px 6px` : `${SP.sm}px ${SP.sm}px`,
          display: "flex", alignItems: "center", gap: SP.sm,
          flexShrink: 0, minWidth: 0,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
            background: C.accentMuted, display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 11, fontWeight: 700, color: "var(--nav-icon-active)",
            border: `1px solid ${C.accent}30`,
          }}>
            {user?.username ? user.username.slice(0, 2).toUpperCase() : "PO"}
          </div>
          {!collapsed && (
            <>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--user-name-color)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user?.username ?? "Officer"}
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "var(--user-role-color)", letterSpacing: "0.05em" }}>
                  {(user?.role ?? "officer").toUpperCase()}
                </div>
              </div>
              <button
                onClick={handleLogout}
                style={{ background: "none", border: "none", color: "var(--nav-icon)", cursor: "pointer", padding: 4, flexShrink: 0 }}
                title="Sign out"
              >
                <LogOut size={14} />
              </button>
            </>
          )}
        </div>

        {/* Expand button when collapsed */}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            style={{
              background: "none", border: "1px solid var(--nav-divider)",
              borderRadius: 6, color: "var(--nav-icon)", cursor: "pointer",
              padding: 5, margin: `${SP.sm}px auto`, display: "flex",
            }}
          >
            <ChevronRight size={14} />
          </button>
        )}
      </aside>

      {/* ── Main content area ── */}
      <div style={{
        marginLeft: W, flex: 1, display: "flex", flexDirection: "column",
        transition: "margin-left 0.2s ease", minWidth: 0,
      }}>

        {/* Topbar */}
        <header style={{
          height: 56, background: C.bgSecondary,
          borderBottom: `1px solid ${C.borderSubtle}`,
          display: "flex", alignItems: "center",
          padding: `0 ${SP.xl}px`, gap: SP.lg,
          flexShrink: 0, position: "sticky", top: 0, zIndex: 40,
        }}>
          {/* Title + breadcrumb */}
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: C.textPrimary, lineHeight: 1.2 }}>{title}</div>
            {breadcrumbs.length > 1 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 1 }}>
                {breadcrumbs.map((b, i) => (
                  <React.Fragment key={b.path}>
                    <span style={{ fontSize: 11, color: i === breadcrumbs.length - 1 ? C.textSecondary : C.textTertiary, textTransform: "capitalize" }}>
                      {b.label}
                    </span>
                    {i < breadcrumbs.length - 1 && (
                      <span style={{ fontSize: 10, color: C.textTertiary }}>›</span>
                    )}
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: SP.xs, flexShrink: 0 }}>
            {/* Theme toggle */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              style={{ background: "none", border: "none", color: C.textSecondary, cursor: "pointer", padding: 7, borderRadius: 6, display: "flex" }}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            <NotificationDropdown />
            <button
              onClick={() => navigate("/jobs?new=true")}
              style={{
                display: "flex", alignItems: "center", gap: SP.xs,
                background: C.accent, color: "#fff", border: "none",
                borderRadius: 6, padding: "6px 14px",
                fontSize: 13, fontWeight: 600, cursor: "pointer",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = C.accentHover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = C.accent)}
            >
              <Plus size={14} /> New Evaluation
            </button>
          </div>
        </header>

        <main style={{ flex: 1, overflow: "auto", padding: SP.xl }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              style={{ height: "100%" }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function NavItem({
  to, label, icon, collapsed, badge,
}: {
  to: string; label: string; icon: React.ReactNode;
  collapsed: boolean; badge: number;
}) {
  return (
    <NavLink
      to={to}
      title={collapsed ? label : undefined}
      style={({ isActive }) => ({
        display: "flex", alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between",
        gap: SP.sm,
        padding: collapsed ? "9px 0" : `8px ${SP.sm}px`,
        borderRadius: 6, marginBottom: 2,
        textDecoration: "none", fontSize: 13,
        fontWeight: isActive ? 600 : 400,
        color: isActive ? "var(--nav-item-color-active)" : "var(--nav-item-color)",
        background: isActive ? "var(--nav-item-bg-active)" : "transparent",
        transition: "all 0.12s",
      })}
    >
      {({ isActive }) => (
        <>
          <span style={{ display: "flex", alignItems: "center", gap: SP.sm }}>
            <span style={{ color: isActive ? "var(--nav-icon-active)" : "var(--nav-icon)" }}>{icon}</span>
            {!collapsed && label}
          </span>
          {!collapsed && badge > 0 && (
            <span style={{
              background: C.failSolid, color: "#fff",
              borderRadius: 9999, fontSize: 10, fontWeight: 700,
              padding: "1px 6px", lineHeight: 1.5, minWidth: 18, textAlign: "center",
            }}>
              {badge > 99 ? "99+" : badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}
