/**
 * VAJANS — Notification Dropdown
 * ===============================
 * Bell button + popover panel.
 *
 * - Click bell → open panel
 * - Click outside / Escape → close
 * - Unread count badge on bell
 * - Mark-all-read action
 * - Click notification → navigate + mark read
 * - Keyboard accessible (focus trap, Esc closes, Enter activates item)
 * - Light/dark themed via existing color tokens
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bell, CheckCheck, Trash2, AlertCircle, CheckCircle2,
  XCircle, Loader2, Inbox, Clock, X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { C, SP } from "../../styles/tokens";
import { jobsApi } from "../../services/api";
import {
  useNotificationsStore,
  selectUnreadCount,
  type AppNotification,
  type NotificationType,
} from "../../store/useNotificationsStore";
import type { Job } from "../../services/types";

// ── Icon + color per type ────────────────────────────────────────────────────

function typeIcon(type: NotificationType) {
  const size = 16;
  switch (type) {
    case "evaluation_completed":
    case "processing_completed":
      return <CheckCircle2 size={size} color={C.passText} />;
    case "review_required":
      return <AlertCircle size={size} color={C.uncertainText} />;
    case "bidder_disqualified":
    case "upload_failed":
      return <XCircle size={size} color={C.failText} />;
    case "processing_started":
      return <Loader2 size={size} color={C.accentText} className="animate-spin" />;
    default:
      return <Bell size={size} color={C.textTertiary} />;
  }
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return "just now";
  const s = Math.floor(ms / 1000);
  if (s < 60)            return `${s}s ago`;
  if (s < 3600)          return `${Math.floor(s / 60)}m ago`;
  if (s < 86_400)        return `${Math.floor(s / 3600)}h ago`;
  if (s < 86_400 * 7)    return `${Math.floor(s / 86_400)}d ago`;
  return new Date(iso).toLocaleDateString();
}

// ── Single notification row ──────────────────────────────────────────────────

function NotificationItem({
  n, onClick, onDismiss,
}: {
  n: AppNotification;
  onClick: () => void;
  onDismiss: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "flex",
        gap: SP.sm,
        padding: `${SP.sm}px ${SP.md}px`,
        borderBottom: `1px solid ${C.borderSubtle}`,
        background: hover
          ? C.bgHover
          : n.read
            ? "transparent"
            : C.accentMuted,
        cursor: "pointer",
        position: "relative",
        outline: "none",
        transition: "background 0.12s",
      }}
    >
      {/* Unread dot */}
      {!n.read && (
        <span
          aria-label="unread"
          style={{
            position: "absolute",
            top: 12,
            left: 6,
            width: 6,
            height: 6,
            background: C.accent,
            borderRadius: "50%",
          }}
        />
      )}

      <div style={{ flexShrink: 0, marginTop: 2, marginLeft: !n.read ? 8 : 0 }}>
        {typeIcon(n.type)}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 13,
          fontWeight: n.read ? 500 : 600,
          color: C.textPrimary,
          marginBottom: 2,
        }}>
          {n.title}
        </div>
        <div style={{
          fontSize: 12,
          color: C.textSecondary,
          lineHeight: 1.4,
          overflow: "hidden",
          textOverflow: "ellipsis",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        }}>
          {n.description}
        </div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          marginTop: 4,
          fontSize: 11,
          color: C.textTertiary,
        }}>
          <Clock size={10} />
          {timeAgo(n.createdAt)}
        </div>
      </div>

      {hover && (
        <button
          onClick={(e) => { e.stopPropagation(); onDismiss(); }}
          aria-label="Dismiss notification"
          style={{
            background: "none",
            border: "none",
            color: C.textTertiary,
            cursor: "pointer",
            padding: 2,
            alignSelf: "start",
            display: "flex",
          }}
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}

// ── Dropdown ─────────────────────────────────────────────────────────────────

export default function NotificationDropdown() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const notifications = useNotificationsStore((s) => s.notifications);
  const unread = useNotificationsStore(selectUnreadCount);
  const markRead = useNotificationsStore((s) => s.markRead);
  const markAllRead = useNotificationsStore((s) => s.markAllRead);
  const remove = useNotificationsStore((s) => s.remove);
  const clearAll = useNotificationsStore((s) => s.clearAll);
  const syncFromJobs = useNotificationsStore((s) => s.syncFromJobs);

  // Auto-derive notifications from jobs list (refreshes every 30s)
  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => jobsApi.list(0, 100),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (jobs.length) syncFromJobs(jobs as Job[]);
  }, [jobs, syncFromJobs]);

  // Close on outside click + Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const handleItemClick = useCallback((n: AppNotification) => {
    markRead(n.id);
    setOpen(false);
    if (n.href) navigate(n.href);
  }, [markRead, navigate]);

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <button
        ref={buttonRef}
        onClick={() => setOpen((o) => !o)}
        title="Notifications"
        aria-label="Notifications"
        aria-haspopup="menu"
        aria-expanded={open}
        style={{
          background: open ? C.bgHover : "none",
          border: "none",
          color: C.textSecondary,
          cursor: "pointer",
          padding: 7,
          borderRadius: 6,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <Bell size={16} />
        {unread > 0 && (
          <span style={{
            position: "absolute",
            top: 1,
            right: 1,
            minWidth: 16,
            height: 16,
            padding: "0 4px",
            borderRadius: 8,
            background: C.failSolid,
            color: "#fff",
            fontSize: 10,
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            lineHeight: 1,
            boxShadow: `0 0 0 2px ${C.bgSecondary}`,
          }}>
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            aria-label="Notifications"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.14, ease: "easeOut" }}
            style={{
              position: "absolute",
              top: "calc(100% + 6px)",
              right: 0,
              width: 380,
              maxHeight: 480,
              background: C.bgSecondary,
              border: `1px solid ${C.borderSubtle}`,
              borderRadius: 10,
              boxShadow: "0 12px 32px rgba(0,0,0,0.32), 0 2px 8px rgba(0,0,0,0.18)",
              zIndex: 100,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Header */}
            <div style={{
              padding: `${SP.sm}px ${SP.md}px`,
              borderBottom: `1px solid ${C.borderSubtle}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexShrink: 0,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: C.textPrimary }}>
                  Notifications
                </span>
                {unread > 0 && (
                  <span style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: C.accentText,
                    background: C.accentMuted,
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}>
                    {unread} new
                  </span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                {notifications.length > 0 && unread > 0 && (
                  <button
                    onClick={markAllRead}
                    title="Mark all as read"
                    style={{
                      display: "flex", alignItems: "center", gap: 4,
                      background: "none", border: "none",
                      color: C.accentText, fontSize: 11, fontWeight: 600,
                      cursor: "pointer", padding: "4px 6px", borderRadius: 4,
                    }}
                  >
                    <CheckCheck size={12} /> Mark all read
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    title="Clear all"
                    style={{
                      background: "none", border: "none",
                      color: C.textTertiary, fontSize: 11,
                      cursor: "pointer", padding: 4, borderRadius: 4,
                      display: "flex",
                    }}
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            </div>

            {/* List */}
            <div style={{ overflow: "auto", flex: 1 }}>
              {notifications.length === 0 ? (
                <div style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: `${SP.xl2}px ${SP.lg}px`,
                  color: C.textTertiary,
                  textAlign: "center",
                  gap: SP.sm,
                }}>
                  <Inbox size={28} color={C.textTertiary} />
                  <div style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}>
                    You're all caught up
                  </div>
                  <div style={{ fontSize: 11 }}>
                    New evaluations and reviews will appear here.
                  </div>
                </div>
              ) : (
                notifications.map((n) => (
                  <NotificationItem
                    key={n.id}
                    n={n}
                    onClick={() => handleItemClick(n)}
                    onDismiss={() => remove(n.id)}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
