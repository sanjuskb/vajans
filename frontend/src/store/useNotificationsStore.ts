/**
 * VAJANS — Notification Store
 * ============================
 * Zustand store with localStorage persistence for in-app notifications.
 *
 * Notifications are produced by two sources:
 *   1. `add(notification)` — explicit producer (e.g. evaluation done, upload failed)
 *   2. `syncFromJobs(jobs)` — derives notifications from the live jobs list
 *      (status transitions, review pending, etc.) and de-duplicates by id.
 *
 * Read state (`read: true/false`) is preserved across sessions in localStorage.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Job } from "../services/types";

export type NotificationType =
  | "evaluation_completed"
  | "review_required"
  | "bidder_disqualified"
  | "upload_failed"
  | "processing_completed"
  | "processing_started"
  | "info";

export interface AppNotification {
  id: string;             // stable, deterministic — used for de-dup
  type: NotificationType;
  title: string;
  description: string;
  createdAt: string;      // ISO timestamp
  read: boolean;
  jobId?: string;
  bidderId?: string;
  /** Where to navigate when the user clicks the item. */
  href?: string;
}

interface NotificationsState {
  notifications: AppNotification[];
  /** Add a single notification. Idempotent on `id` (replaces silently on dup). */
  add: (n: Omit<AppNotification, "read"> & { read?: boolean }) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  remove: (id: string) => void;
  clearAll: () => void;
  /** Derive notifications from the current jobs list and merge in. */
  syncFromJobs: (jobs: Job[]) => void;
}

const MAX_NOTIFS = 50;

function jobNotifId(jobId: string, kind: string) {
  return `job:${jobId}:${kind}`;
}

export const useNotificationsStore = create<NotificationsState>()(
  persist(
    (set, get) => ({
      notifications: [],

      add: (n) => {
        const incoming: AppNotification = {
          read: false,
          ...n,
        };
        set((s) => {
          const existingIdx = s.notifications.findIndex((x) => x.id === incoming.id);
          let next: AppNotification[];
          if (existingIdx >= 0) {
            // Preserve the prior `read` state on dup so we don't re-mark unread.
            const merged = { ...incoming, read: s.notifications[existingIdx].read };
            next = [...s.notifications];
            next[existingIdx] = merged;
          } else {
            next = [incoming, ...s.notifications];
          }
          return { notifications: next.slice(0, MAX_NOTIFS) };
        });
      },

      markRead: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),

      markAllRead: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, read: true })),
        })),

      remove: (id) =>
        set((s) => ({
          notifications: s.notifications.filter((n) => n.id !== id),
        })),

      clearAll: () => set({ notifications: [] }),

      syncFromJobs: (jobs) => {
        const additions: AppNotification[] = [];

        for (const job of jobs) {
          const jobLabel = job.title || `Job ${job.id.slice(0, 8)}`;
          const href = `/jobs/${job.id}`;

          if (job.status === "completed") {
            additions.push({
              id: jobNotifId(job.id, "completed"),
              type: "evaluation_completed",
              title: "Evaluation completed",
              description: `${jobLabel} finished evaluation.`,
              createdAt: job.updated_at ?? job.created_at,
              read: false,
              jobId: job.id,
              href,
            });
          } else if (job.status === "failed") {
            additions.push({
              id: jobNotifId(job.id, "failed"),
              type: "upload_failed",
              title: "Pipeline failed",
              description: `${jobLabel} failed to process.`,
              createdAt: job.updated_at ?? job.created_at,
              read: false,
              jobId: job.id,
              href,
            });
          } else if (
            job.status === "ingesting" ||
            job.status === "extracting" ||
            job.status === "evaluating"
          ) {
            additions.push({
              id: jobNotifId(job.id, "processing"),
              type: "processing_started",
              title: "Processing in progress",
              description: `${jobLabel} — current step: ${job.status}.`,
              createdAt: job.updated_at ?? job.created_at,
              read: false,
              jobId: job.id,
              href,
            });
          }
        }

        if (!additions.length) return;

        // Merge: preserve read state and existing entries by id
        const existing = get().notifications;
        const byId = new Map(existing.map((n) => [n.id, n]));
        for (const a of additions) {
          const prior = byId.get(a.id);
          if (prior) {
            byId.set(a.id, { ...a, read: prior.read });
          } else {
            byId.set(a.id, a);
          }
        }
        const merged = Array.from(byId.values()).sort((a, b) =>
          a.createdAt < b.createdAt ? 1 : -1
        );
        set({ notifications: merged.slice(0, MAX_NOTIFS) });
      },
    }),
    {
      name: "vajans-notifications",
      version: 1,
    }
  )
);

// ── Selectors ────────────────────────────────────────────────────────────────

export const selectUnreadCount = (s: NotificationsState) =>
  s.notifications.filter((n) => !n.read).length;
