/**
 * VAJANS — Focused Evidence Viewer
 * =================================
 * Enterprise-grade evidence inspection modal. Instead of dropping the user
 * into a "raw PDF" they have to search through, this viewer behaves like a
 * legal/audit review tool:
 *
 *   • Auto-loads the bidder PDF inline (authenticated blob fetch)
 *   • Auto-jumps to the resolved page
 *   • Auto-scrolls the matched snippet into view
 *   • Renders a horizontal "evidence band" — content above + below the
 *     matched snippet is dimmed/blurred so the eye lands on the hit
 *   • Pulses the highlight with a yellow + blue enterprise glow
 *   • Side panel with criterion, verdict, score, page, and AI reasoning
 *   • Smart fallback: if exact text coords cannot be located, opens the
 *     correct page and shows an "Approximate evidence location" banner
 *
 * Backward compatible — when no `evidence` prop is provided the side panel
 * is hidden and the viewer behaves like a standard inline PDF reader.
 */

import {
  useEffect, useMemo, useRef, useState, useCallback, useLayoutEffect,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
// Vite-friendly worker URL — bundles the worker as a module asset.
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2,
  Loader2, AlertTriangle, Download, FileText, Sparkles, Focus,
  CheckCircle2, XCircle, AlertCircle, Hash, Quote, Brain,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { C, SP } from "../../styles/tokens";
import { filesApi } from "../../services/api";

// One-time worker config (idempotent — multiple imports won't reset it).
pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

// ── One-time CSS injection (mark glow + pulse keyframes) ─────────────────────

const FOCUS_STYLE_TAG_ID = "vajans-pdf-evidence-styles";
const FOCUS_STYLES = `
@keyframes vajans-evidence-pulse {
  0%, 100% {
    box-shadow:
      0 0 0 2px rgba(255,214,10,0.55),
      0 0 14px 3px rgba(255,214,10,0.55),
      0 0 28px 8px rgba(59,130,246,0.30);
  }
  50% {
    box-shadow:
      0 0 0 3px rgba(255,214,10,0.85),
      0 0 22px 7px rgba(255,214,10,0.80),
      0 0 44px 14px rgba(59,130,246,0.45);
  }
}
@keyframes vajans-evidence-rise {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* True highlighter: yellow background over the canvas glyphs.
   Text inside <mark> stays transparent (matching the rest of the
   text-layer) so the canvas glyph underneath remains crisp — no
   ghost / double-rendered text. */
mark[data-vajans-hit="1"] {
  background: rgba(255,214,10,0.62) !important;
  color: transparent !important;
  border-radius: 2px;
  padding: 0 !important;
  margin: 0;
  position: relative;
  z-index: 5;
  animation: vajans-evidence-pulse 2.4s ease-in-out infinite;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}
mark[data-vajans-hit="1"].first-hit {
  outline: 2px solid rgba(234,179,8,0.95);
  outline-offset: 1px;
  background: rgba(255,214,10,0.78) !important;
}
.vajans-pdf-page-wrap { position: relative; isolation: isolate; }
.vajans-pdf-page-wrap .react-pdf__Page { position: relative; }
.vajans-evidence-band {
  position: absolute; left: 0; right: 0;
  pointer-events: none;
  background: rgba(8, 12, 22, 0.78);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 4;
  transition: top 0.32s ease, height 0.32s ease, opacity 0.25s ease;
}
.vajans-evidence-band.top    { top: 0; }
.vajans-evidence-band.bottom { bottom: 0; }
.vajans-evidence-spotlight {
  position: absolute;
  left: 0; right: 0;
  border-top: 1px solid rgba(255,214,10,0.35);
  border-bottom: 1px solid rgba(255,214,10,0.35);
  pointer-events: none;
  z-index: 3;
  animation: vajans-evidence-rise 0.45s ease-out both;
}
`;

function ensureStylesInjected() {
  if (typeof document === "undefined") return;
  if (document.getElementById(FOCUS_STYLE_TAG_ID)) return;
  const tag = document.createElement("style");
  tag.id = FOCUS_STYLE_TAG_ID;
  tag.textContent = FOCUS_STYLES;
  document.head.appendChild(tag);
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Normalize text for substring matching: collapse whitespace, lowercase.
 */
function normalize(s: string): string {
  return s.replace(/\s+/g, " ").trim().toLowerCase();
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ── Snippet match engine ─────────────────────────────────────────────────────
// PDF text items are short fragments split across many spans, and the
// underlying text often contains Unicode artefacts (smart quotes, em-dashes,
// non-breaking spaces) that silently break exact matching. We:
//
//   1. Build a flat string from every rendered text-layer item in order,
//      with a parallel per-character map back to (item index, char offset).
//   2. Apply 1:1 character normalisation to BOTH the haystack and snippet
//      so position offsets stay aligned (no length-changing replacements).
//   3. Run a 3-tier search (exact → longest phrase → distinctive token).
//   4. Rewrite each affected item's innerHTML to wrap matched chars in <mark>.
//   5. Auto-scroll the first mark into view via native scrollIntoView —
//      reliable across browsers and immune to async layout shifts.

const PDF_DEBUG =
  typeof window !== "undefined" &&
  Boolean((window as unknown as { __VAJANS_DEBUG_PDF?: boolean }).__VAJANS_DEBUG_PDF);

function dbg(...args: unknown[]) {
  if (PDF_DEBUG) console.log("[VAJANS PDF]", ...args);
}

/** Position-preserving (1 char in → 1 char out) Unicode normalisation. Maps
 *  smart quotes, dashes, NBSP and zero-width characters to ASCII equivalents
 *  so a snippet like  Annual\u00A0Turnover\u2014Rs.\u00A09.23\u00A0Crore
 *  matches a haystack like  Annual Turnover - Rs. 9.23 Crore. */
const CHAR_NORM_TABLE: Record<string, string> = {
  "\u2018": "'", "\u2019": "'", "\u201A": "'", "\u201B": "'",
  "\u201C": '"', "\u201D": '"', "\u201E": '"', "\u201F": '"',
  "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2010": "-",
  "\u2011": "-", "\u2212": "-",
  "\u00A0": " ", "\u2007": " ", "\u202F": " ", "\u2009": " ", "\u200A": " ",
  "\u200B": " ", "\u200C": " ", "\u200D": " ", "\uFEFF": " ",
};
function normalizeChars(s: string): string {
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    out += CHAR_NORM_TABLE[c] ?? c;
  }
  return out;
}

/** Whitespace + light-punctuation + case flexible regex builder.
 *  Allows the gap between tokens to absorb dashes, colons, commas etc. so
 *  "ISO 9001:2015 Certificate" still matches a haystack that reads
 *  "ISO 9001:2015 — Certificate" or "ISO 9001:2015, Certificate". */
function makeFlexRe(phrase: string): RegExp | null {
  const escaped = phrase
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\s+/g, "[\\s\\-\u2013\u2014:;,]+");
  if (!escaped) return null;
  try { return new RegExp(escaped, "i"); }
  catch { return null; }
}

export type MatchTier = "exact" | "phrase" | "token";
export type MatchRange = { start: number; end: number; tier: MatchTier };

/**
 * Three-tier snippet locator.
 *
 *   exact  — the entire snippet matches as a flexible-whitespace phrase.
 *   phrase — some contiguous ≥3-token window from the snippet matches.
 *            This recovers when the LLM lightly paraphrased the snippet,
 *            when extraction stitched together a paragraph, or when the
 *            snippet is wrapped/dashed differently in the PDF.
 *   token  — a single distinctive number or 6+ char word from the snippet
 *            appears somewhere in the haystack. Last-resort glue for
 *            synthetic backend snippets like "Qualifying projects: 5"
 *            where no full phrase exists in the source PDF; at least the
 *            distinguishing value is highlighted.
 */
function findBestMatch(snippet: string, haystack: string): MatchRange | null {
  const trimmed = snippet.trim();
  if (!trimmed || !haystack) return null;

  // Tier 1 — full snippet, whitespace + case flexible.
  const exactRe = makeFlexRe(trimmed);
  if (exactRe) {
    const m = exactRe.exec(haystack);
    if (m) {
      dbg("exact match", { idx: m.index, len: m[0].length });
      return { start: m.index, end: m.index + m[0].length, tier: "exact" };
    }
  }

  // Tier 2 — longest contiguous N-token sub-phrase.
  const tokens = trimmed.split(/\s+/).filter(Boolean);
  const maxLen = Math.min(tokens.length, 30);
  for (let len = maxLen; len >= 3; len--) {
    let best: { start: number; end: number } | null = null;
    for (let start = 0; start + len <= tokens.length; start++) {
      const phrase = tokens.slice(start, start + len).join(" ");
      const re = makeFlexRe(phrase);
      if (!re) continue;
      const m = re.exec(haystack);
      if (m && (!best || m[0].length > (best.end - best.start))) {
        best = { start: m.index, end: m.index + m[0].length };
      }
    }
    if (best) {
      dbg("phrase match", { tokens: len, idx: best.start, len: best.end - best.start });
      return { start: best.start, end: best.end, tier: "phrase" };
    }
  }

  // Tier 3 — longest distinctive single token (number or 6+ char word).
  //          Matches at least "something" so the user always lands on a
  //          highlighted region rather than an empty page.
  const distinctive = tokens
    .map((t) => t.replace(/[^A-Za-z0-9.\-]/g, ""))
    .filter((t) => /^\d+(?:\.\d+)?$/.test(t) || /^[A-Za-z][A-Za-z\-]{5,}$/.test(t))
    .sort((a, b) => b.length - a.length);

  for (const tok of distinctive) {
    const re = new RegExp(`\\b${tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    const m = re.exec(haystack);
    if (m) {
      dbg("token match", { token: tok, idx: m.index });
      return { start: m.index, end: m.index + m[0].length, tier: "token" };
    }
  }

  dbg("no match", { snippet: trimmed.slice(0, 80), haystackLen: haystack.length });
  return null;
}

/** Collect the rendered text items inside a text layer.
 *
 *  pdfjs v4 (used by react-pdf v9) tags each text item with
 *  role="presentation". Older versions just used leaf <span>s.
 *  We try the modern selector first and fall back. */
function collectTextItems(textLayer: HTMLElement): HTMLElement[] {
  const roleItems = Array.from(
    textLayer.querySelectorAll<HTMLElement>('[role="presentation"]')
  ).filter((el) => (el.textContent?.length ?? 0) > 0);
  if (roleItems.length) return roleItems;

  return Array.from(
    textLayer.querySelectorAll<HTMLElement>("span")
  ).filter(
    (el) => !el.querySelector("span") && (el.textContent?.length ?? 0) > 0
  );
}

/** Apply <mark> wrapping to a text layer for the located snippet. Returns
 *  the match tier or null when no match was found. */
function applyTextLayerHighlight(
  textLayer: HTMLElement,
  snippet: string,
): MatchTier | null {
  // 1. Strip any prior marks. textContent reset removes child elements while
  //    keeping the original visible text — idempotent across re-applications.
  const marked = textLayer.querySelectorAll<HTMLElement>(
    '[data-vajans-marked="1"]'
  );
  for (const el of marked) {
    el.textContent = el.textContent ?? "";
    el.removeAttribute("data-vajans-marked");
  }

  const items = collectTextItems(textLayer);
  dbg("text items found", items.length);
  if (!items.length) return null;

  // 2. Build flat raw + normalised strings with parallel item/offset maps.
  //    Normalisation is strictly 1:1 so positions in flatNorm map directly
  //    onto positions in flatRaw and therefore onto charToItem/charToOffset.
  const flatRawChars: string[] = [];
  const flatNormChars: string[] = [];
  const charToItem: number[] = [];
  const charToOffset: number[] = [];
  for (let i = 0; i < items.length; i++) {
    const text = items[i].textContent ?? "";
    for (let j = 0; j < text.length; j++) {
      const c = text[j];
      flatRawChars.push(c);
      flatNormChars.push(CHAR_NORM_TABLE[c] ?? c);
      charToItem.push(i);
      charToOffset.push(j);
    }
    // Synthetic separator so cross-item phrases match cleanly.
    if (text.length && !/\s$/.test(text)) {
      flatRawChars.push(" ");
      flatNormChars.push(" ");
      charToItem.push(-1);
      charToOffset.push(-1);
    }
  }
  const flatNorm = flatNormChars.join("");
  const snipNorm = normalizeChars(snippet);

  // 3. Locate.
  const range = findBestMatch(snipNorm, flatNorm);
  if (!range) return null;

  // 4. Group matched character positions back into per-item ranges.
  type ItemRange = { itemIdx: number; from: number; to: number };
  const ranges: ItemRange[] = [];
  let cur: ItemRange | null = null;
  for (let p = range.start; p < range.end; p++) {
    const it = charToItem[p];
    const off = charToOffset[p];
    if (it < 0) continue;
    if (cur && cur.itemIdx === it) {
      cur.to = off + 1;
    } else {
      if (cur) ranges.push(cur);
      cur = { itemIdx: it, from: off, to: off + 1 };
    }
  }
  if (cur) ranges.push(cur);
  if (!ranges.length) return null;

  dbg("applying ranges", ranges.length, "tier=" + range.tier);

  // 5. Rewrite each item's innerHTML to inject <mark>. Item styles
  //    (transform, position, font) live on the element attribute, so
  //    they survive innerHTML reassignment.
  for (let i = 0; i < ranges.length; i++) {
    const r = ranges[i];
    const item = items[r.itemIdx];
    const text = item.textContent ?? "";
    if (r.from >= text.length) continue;
    const before = text.slice(0, r.from);
    const inside = text.slice(r.from, Math.min(r.to, text.length));
    const after  = text.slice(Math.min(r.to, text.length));
    const cls    = i === 0 ? " class=\"first-hit\"" : "";
    item.innerHTML =
      escapeHtml(before) +
      `<mark data-vajans-hit="1"${cls}>${escapeHtml(inside)}</mark>` +
      escapeHtml(after);
    item.setAttribute("data-vajans-marked", "1");
  }

  return range.tier;
}

// Verdict palette
const VERDICT_COLOR: Record<string, string> = {
  pass: "#10B981", fail: "#EF4444", review: "#F59E0B", unknown: "#94A3B8",
};
function verdictColor(v?: string) {
  return VERDICT_COLOR[(v ?? "unknown").toLowerCase()] ?? VERDICT_COLOR.unknown;
}
function verdictIcon(v?: string) {
  const k = (v ?? "unknown").toLowerCase();
  if (k === "pass")   return <CheckCircle2 size={13} />;
  if (k === "fail")   return <XCircle size={13} />;
  return <AlertCircle size={13} />;
}
function verdictLabel(v?: string) {
  const k = (v ?? "unknown").toLowerCase();
  if (k === "pass")   return "PASS";
  if (k === "fail")   return "FAIL";
  if (k === "review") return "REVIEW";
  return "UNKNOWN";
}

// ── Public types ─────────────────────────────────────────────────────────────

export type EvidenceContext = {
  criterionLabel?: string;
  verdict?: string;            // "pass" | "fail" | "review" | "unknown"
  score?: number;              // 0-100
  explanation?: string;
  mandatory?: boolean;
  threshold?: string;
};

export interface PdfViewerModalProps {
  open: boolean;
  fileId: string | null;
  fileName?: string;
  page?: number;             // 1-indexed; defaults to 1
  snippet?: string;          // text to highlight in the PDF text layer
  evidence?: EvidenceContext;
  onClose: () => void;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function PdfViewerModal({
  open, fileId, fileName, page = 1, snippet, evidence, onClose,
}: PdfViewerModalProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(page);
  // Higher initial zoom when we have a snippet to focus on — the goal is for
  // matched text to be immediately readable, not a tiny letterbox of a page.
  const [scale, setScale] = useState(snippet ? 1.6 : 1.2);
  const [pageInputValue, setPageInputValue] = useState(String(page));
  const [highlightFound, setHighlightFound] = useState<boolean | null>(null);
  const [focusMode, setFocusMode] = useState(true);
  const [focusBand, setFocusBand] = useState<{
    top: number; bottom: number; pageHeight: number;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const pageWrapRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Inject keyframe + mark styles once
  useEffect(() => { ensureStylesInjected(); }, []);

  // ── Fetch PDF bytes when modal opens ──────────────────────────────────────
  useEffect(() => {
    if (!open || !fileId) return;
    let revoked = false;
    let createdUrl: string | null = null;

    setBlobUrl(null);
    setLoadError(null);
    setNumPages(0);
    setHighlightFound(null);
    setFocusBand(null);
    setCurrentPage(page);
    setPageInputValue(String(page));
    setScale(snippet ? 1.6 : 1.2);
    setFocusMode(true);

    (async () => {
      try {
        const blob = await filesApi.getInline(fileId);
        if (revoked) return;
        createdUrl = URL.createObjectURL(blob);
        setBlobUrl(createdUrl);
      } catch (err: unknown) {
        const msg = (err as { message?: string })?.message ?? "Failed to load document";
        setLoadError(msg);
      }
    })();

    return () => {
      revoked = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [open, fileId, page, snippet]);

  useEffect(() => { setPageInputValue(String(currentPage)); }, [currentPage]);

  // ── Compute focus band + auto-scroll after page renders ───────────────────
  // Run multiple times because react-pdf's text layer is built asynchronously
  // and we need the marks to exist before measuring.
  const recomputeFocusBand = useCallback(() => {
    const wrap = pageWrapRef.current;
    if (!wrap) return;
    const pageEl = wrap.querySelector(".react-pdf__Page") as HTMLElement | null;
    if (!pageEl) return;
    const marks = Array.from(
      pageEl.querySelectorAll('mark[data-vajans-hit="1"]')
    ) as HTMLElement[];
    if (!marks.length) { setFocusBand(null); return; }

    const pageRect = pageEl.getBoundingClientRect();
    let top = Infinity, bottom = -Infinity;
    for (const m of marks) {
      const r = m.getBoundingClientRect();
      if (r.top < top)    top = r.top;
      if (r.bottom > bottom) bottom = r.bottom;
    }
    if (!isFinite(top) || !isFinite(bottom)) { setFocusBand(null); return; }
    setFocusBand({
      top:    top    - pageRect.top,
      bottom: bottom - pageRect.top,
      pageHeight: pageRect.height,
    });
    // Note: scroll is intentionally NOT performed here. The highlight effect
    // owns auto-scroll via mark.scrollIntoView() so it runs exactly once per
    // (snippet, page) instead of fighting band recomputations on every retry.
  }, []);

  useLayoutEffect(() => {
    if (!blobUrl) return;
    // Multiple staggered passes — text layer renders asynchronously.
    const timers = [80, 220, 500, 900].map((d) =>
      window.setTimeout(recomputeFocusBand, d)
    );
    return () => { timers.forEach(window.clearTimeout); };
  }, [currentPage, blobUrl, scale, snippet, recomputeFocusBand]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") setCurrentPage((p) => clamp(p + 1, 1, numPages || 1));
      if (e.key === "ArrowLeft"  || e.key === "PageUp")   setCurrentPage((p) => clamp(p - 1, 1, numPages || 1));
      if (e.key === "+" || e.key === "=")                 setScale((s) => clamp(s + 0.15, 0.5, 3));
      if (e.key === "-")                                  setScale((s) => clamp(s - 0.15, 0.5, 3));
      if (e.key === "f" || e.key === "F")                 setFocusMode((m) => !m);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, numPages, onClose]);

  // ── Snippet highlighting ─────────────────────────────────────────────────
  // (post-render DOM walk — see applyTextLayerHighlight at module scope)
  const normalizedSnippet = useMemo(() => normalize(snippet ?? ""), [snippet]);
  const [textLayerVersion, setTextLayerVersion] = useState(0);

  // Reset state when the page or snippet changes.
  useEffect(() => {
    setHighlightFound(null);
    setFocusBand(null);
  }, [currentPage, snippet]);

  // Bumped from onRenderTextLayerSuccess; drives the highlight effect.
  const onTextLayerRendered = useCallback(() => {
    setTextLayerVersion((v) => v + 1);
  }, []);

  // Post-render text-layer search + mark injection.
  // Runs every time react-pdf finishes building/rebuilding the text layer
  // (page change, scale change, fresh open). We re-apply marks because
  // react-pdf wipes the text layer DOM on each rebuild.
  const [matchTier, setMatchTier] = useState<MatchTier | null>(null);
  const hasScrolledRef = useRef(false);
  useEffect(() => { hasScrolledRef.current = false; }, [snippet, currentPage]);

  useEffect(() => {
    if (!snippet || textLayerVersion === 0) return;
    const wrap = pageWrapRef.current;
    if (!wrap) return;

    const run = () => {
      const tl = wrap.querySelector(
        ".react-pdf__Page__textContent, .textLayer"
      ) as HTMLElement | null;
      if (!tl) {
        dbg("text layer not found yet");
        return false;
      }
      const tier = applyTextLayerHighlight(tl, snippet);
      setMatchTier(tier);
      setHighlightFound(tier !== null);
      if (tier !== null && !hasScrolledRef.current) {
        // Center the first mark in the viewport using native scroll.
        const firstMark = tl.querySelector<HTMLElement>(
          'mark[data-vajans-hit="1"]'
        );
        if (firstMark) {
          firstMark.scrollIntoView({ behavior: "smooth", block: "center" });
          hasScrolledRef.current = true;
        }
      }
      // Recompute the dim-band overlay positions now that marks exist.
      recomputeFocusBand();
      return tier !== null;
    };

    // Run immediately + staggered retries to absorb async font / layout
    // settling that can shift bounding boxes after the text layer paints.
    const ok = run();
    const t1 = window.setTimeout(run, 120);
    const t2 = window.setTimeout(run, 360);
    const t3 = ok ? -1 : window.setTimeout(run, 800);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      if (t3 > 0) window.clearTimeout(t3);
    };
  }, [snippet, textLayerVersion, recomputeFocusBand]);

  if (!open) return null;

  // ── Layout flags ──────────────────────────────────────────────────────────
  const showSidePanel = !!evidence;
  const PAD = 18; // padding around the focus band

  return (
    <AnimatePresence>
      <motion.div
        key="pdf-modal-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(2,6,18,0.78)",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: SP.lg,
          backdropFilter: "blur(4px)",
          WebkitBackdropFilter: "blur(4px)",
        }}
      >
        <motion.div
          ref={containerRef}
          role="dialog"
          aria-modal="true"
          aria-label={fileName ? `Evidence viewer — ${fileName}` : "Evidence viewer"}
          initial={{ opacity: 0, scale: 0.97, y: 14 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.97, y: 14 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          style={{
            background: C.bgPrimary,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 14,
            width: showSidePanel ? "min(1340px, 100%)" : "min(1100px, 100%)",
            maxWidth: "100%",
            height: "min(900px, 100%)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "0 30px 80px rgba(0,0,0,0.55), 0 0 0 1px rgba(59,130,246,0.08)",
          }}
        >
          {/* ── Header / toolbar ── */}
          <div style={{
            display: "flex", alignItems: "center", gap: SP.sm,
            padding: `${SP.sm}px ${SP.md}px`,
            background: C.bgSecondary,
            borderBottom: `1px solid ${C.borderSubtle}`,
            flexShrink: 0,
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: 7,
              background: "linear-gradient(135deg, #2563EB, #1D4ED8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 6px rgba(37,99,235,0.45)",
              flexShrink: 0,
            }}>
              <Sparkles size={14} color="#fff" />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 13, fontWeight: 700, color: C.textPrimary,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                letterSpacing: "0.01em",
              }}>
                {fileName ?? "Document"}
              </div>
              <div style={{
                fontSize: 10.5, color: C.textTertiary, marginTop: 2,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontWeight: 500, letterSpacing: "0.04em",
                textTransform: "uppercase",
              }}>
                <Brain size={10} style={{ verticalAlign: "-1px", marginRight: 5 }} />
                AI-located evidence · Page {currentPage}{numPages ? ` of ${numPages}` : ""}
              </div>
            </div>

            {/* Focus toggle */}
            {snippet && (
              <ToolButton
                title={focusMode ? "Disable focus mode (F)" : "Enable focus mode (F)"}
                onClick={() => setFocusMode((m) => !m)}
                active={focusMode}
              >
                <Focus size={14} />
              </ToolButton>
            )}

            {/* Page nav */}
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <ToolButton
                title="Previous page"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => clamp(p - 1, 1, numPages || 1))}
              ><ChevronLeft size={15} /></ToolButton>
              <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: C.textSecondary }}>
                <input
                  value={pageInputValue}
                  onChange={(e) => setPageInputValue(e.target.value.replace(/[^0-9]/g, ""))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const n = parseInt(pageInputValue, 10);
                      if (!Number.isNaN(n)) setCurrentPage(clamp(n, 1, numPages || 1));
                    }
                  }}
                  onBlur={() => {
                    const n = parseInt(pageInputValue, 10);
                    if (!Number.isNaN(n)) setCurrentPage(clamp(n, 1, numPages || 1));
                    else setPageInputValue(String(currentPage));
                  }}
                  aria-label="Jump to page"
                  style={{
                    width: 38, padding: "3px 4px",
                    background: C.bgPrimary,
                    border: `1px solid ${C.borderSubtle}`,
                    borderRadius: 4,
                    color: C.textPrimary, fontSize: 12, textAlign: "center",
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                />
                <span style={{ color: C.textTertiary }}>/ {numPages || "—"}</span>
              </div>
              <ToolButton
                title="Next page"
                disabled={!numPages || currentPage >= numPages}
                onClick={() => setCurrentPage((p) => clamp(p + 1, 1, numPages || 1))}
              ><ChevronRight size={15} /></ToolButton>
            </div>

            {/* Zoom */}
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 6 }}>
              <ToolButton title="Zoom out (-)" onClick={() => setScale((s) => clamp(s - 0.15, 0.5, 3))}>
                <ZoomOut size={15} />
              </ToolButton>
              <span style={{
                fontSize: 11, fontFamily: "JetBrains Mono, monospace",
                color: C.textSecondary, minWidth: 38, textAlign: "center",
              }}>
                {Math.round(scale * 100)}%
              </span>
              <ToolButton title="Zoom in (+)" onClick={() => setScale((s) => clamp(s + 0.15, 0.5, 3))}>
                <ZoomIn size={15} />
              </ToolButton>
              <ToolButton title="Reset to 100%" onClick={() => setScale(1)}>
                <Maximize2 size={14} />
              </ToolButton>
            </div>

            <ToolButton
              title="Download original"
              onClick={() => fileId && filesApi.download(fileId, fileName ?? "document.pdf")}
            >
              <Download size={14} />
            </ToolButton>
            <ToolButton title="Close (Esc)" onClick={onClose}>
              <X size={16} />
            </ToolButton>
          </div>

          {/* ── Body: side panel + viewer ── */}
          <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
            {/* Evidence side panel */}
            {showSidePanel && (
              <EvidencePanel
                evidence={evidence!}
                snippet={snippet ?? ""}
                pageNumber={currentPage}
                approximate={!!normalizedSnippet && highlightFound === false}
              />
            )}

            {/* PDF viewport */}
            <div style={{
              flex: 1, display: "flex", flexDirection: "column",
              minWidth: 0, minHeight: 0,
            }}>
              {/* Banner row */}
              {snippet && highlightFound === false && (
                <div style={{
                  display: "flex", alignItems: "center", gap: SP.sm,
                  padding: `${SP.xs}px ${SP.md}px`,
                  background: `${C.uncertainSolid}1F`,
                  borderBottom: `1px solid ${C.uncertainSolid}50`,
                  color: C.uncertainText,
                  fontSize: 12, fontWeight: 500,
                  flexShrink: 0,
                }}>
                  <AlertTriangle size={13} />
                  Approximate evidence location — opened to page {currentPage} as best match.
                  Use Find / scroll to inspect surrounding context.
                </div>
              )}
              {snippet && highlightFound === true && (
                <div style={{
                  display: "flex", alignItems: "center", gap: SP.sm,
                  padding: `${SP.xs}px ${SP.md}px`,
                  background: matchTier === "token"
                    ? `${C.uncertainSolid}1F`
                    : "rgba(255,214,10,0.14)",
                  borderBottom: matchTier === "token"
                    ? `1px solid ${C.uncertainSolid}50`
                    : `1px solid rgba(255,214,10,0.40)`,
                  color: matchTier === "token" ? C.uncertainText : C.textPrimary,
                  fontSize: 12, fontWeight: 600, letterSpacing: "0.02em",
                  flexShrink: 0,
                }}>
                  <Sparkles
                    size={13}
                    color={matchTier === "token" ? C.uncertainText : "#EAB308"}
                  />
                  {matchTier === "exact" && (
                    <>Exact evidence located on page {currentPage} · highlighted text below ↓</>
                  )}
                  {matchTier === "phrase" && (
                    <>Closest phrase highlighted on page {currentPage} — the source PDF wording differs slightly ↓</>
                  )}
                  {matchTier === "token" && (
                    <>Approximate keyword highlighted on page {currentPage} — the exact phrase isn't present in the source PDF ↓</>
                  )}
                </div>
              )}

              {/* PDF area */}
              <div
                ref={scrollAreaRef}
                style={{
                  flex: 1, overflow: "auto",
                  background: "#0B0F1A",
                  display: "flex",
                  justifyContent: "center",
                  padding: SP.lg,
                  minHeight: 0,
                }}
              >
                {loadError ? (
                  <ErrorState message={loadError} onClose={onClose} />
                ) : !blobUrl ? (
                  <LoadingState />
                ) : (
                  <div
                    ref={pageWrapRef}
                    className="vajans-pdf-page-wrap"
                    style={{ alignSelf: "flex-start", display: "inline-block" }}
                  >
                    <Document
                      file={blobUrl}
                      onLoadSuccess={({ numPages: n }) => {
                        setNumPages(n);
                        setCurrentPage((p) => clamp(p, 1, n));
                      }}
                      onLoadError={(err) => setLoadError(err.message || "Could not parse PDF")}
                      loading={<LoadingState />}
                      error={<ErrorState message="Could not parse PDF" onClose={onClose} />}
                    >
                      <Page
                        pageNumber={currentPage}
                        scale={scale}
                        onRenderTextLayerSuccess={onTextLayerRendered}
                        renderAnnotationLayer={false}
                      />
                    </Document>

                    {/* Focus band overlays — fade everything except the
                        matched snippet's row. Only render when we have
                        located the snippet AND focus mode is on. */}
                    {focusMode && focusBand && (
                      <>
                        {/* Top dim band */}
                        <div
                          className="vajans-evidence-band top"
                          style={{
                            height: Math.max(0, focusBand.top - PAD),
                            opacity: focusMode ? 1 : 0,
                          }}
                        />
                        {/* Bottom dim band */}
                        <div
                          className="vajans-evidence-band bottom"
                          style={{
                            top: focusBand.bottom + PAD,
                            height: Math.max(
                              0,
                              focusBand.pageHeight - (focusBand.bottom + PAD),
                            ),
                            opacity: focusMode ? 1 : 0,
                          }}
                        />
                        {/* Spotlight border */}
                        <div
                          className="vajans-evidence-spotlight"
                          style={{
                            top:    Math.max(0, focusBand.top - PAD),
                            height: (focusBand.bottom - focusBand.top) + PAD * 2,
                          }}
                        />
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// ── Subcomponents ────────────────────────────────────────────────────────────

function EvidencePanel({
  evidence, snippet, pageNumber, approximate,
}: {
  evidence: EvidenceContext;
  snippet: string;
  pageNumber: number;
  approximate: boolean;
}) {
  const vColor = verdictColor(evidence.verdict);
  return (
    <aside
      style={{
        width: 340, flexShrink: 0,
        background: C.bgSecondary,
        borderRight: `1px solid ${C.borderSubtle}`,
        padding: SP.md,
        overflowY: "auto",
        display: "flex", flexDirection: "column", gap: SP.md,
      }}
    >
      {/* Title */}
      <div>
        <div style={{
          fontSize: 10, fontWeight: 700, color: C.textTertiary,
          textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 6,
        }}>
          Evidence Detail
        </div>
        <div style={{
          fontSize: 15, fontWeight: 700, color: C.textPrimary,
          lineHeight: 1.4,
        }}>
          {evidence.criterionLabel ?? "Source evidence"}
        </div>
        {evidence.mandatory !== undefined && evidence.mandatory && (
          <span style={{
            display: "inline-block", marginTop: 8,
            fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
            color: "#DC2626", background: "rgba(220,38,38,0.12)",
            border: "1px solid rgba(220,38,38,0.3)",
            padding: "2px 8px", borderRadius: 4,
          }}>
            MANDATORY
          </span>
        )}
      </div>

      {/* Verdict + Score row */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8,
      }}>
        <div style={{
          padding: 10, borderRadius: 8,
          background: `${vColor}14`, border: `1px solid ${vColor}55`,
        }}>
          <div style={{
            fontSize: 9, fontWeight: 700, color: C.textTertiary,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4,
          }}>
            Verdict
          </div>
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            color: vColor, fontWeight: 700, fontSize: 13, letterSpacing: "0.03em",
          }}>
            {verdictIcon(evidence.verdict)}
            {verdictLabel(evidence.verdict)}
          </div>
        </div>
        <div style={{
          padding: 10, borderRadius: 8,
          background: C.cardBg, border: `1px solid ${C.borderSubtle}`,
        }}>
          <div style={{
            fontSize: 9, fontWeight: 700, color: C.textTertiary,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4,
          }}>
            Score
          </div>
          <div style={{
            display: "flex", alignItems: "baseline", gap: 4,
            fontFamily: "JetBrains Mono, monospace",
          }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary }}>
              {evidence.score ?? "—"}
            </span>
            <span style={{ fontSize: 11, color: C.textTertiary }}>/100</span>
          </div>
        </div>
      </div>

      {/* Page indicator */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "8px 10px", borderRadius: 8,
        background: "rgba(37,99,235,0.10)",
        border: `1px solid rgba(37,99,235,0.28)`,
        color: C.accentText, fontSize: 12, fontWeight: 600,
      }}>
        <Hash size={12} />
        Located on page {pageNumber}
        {approximate && (
          <span style={{
            marginLeft: "auto",
            fontSize: 10, fontWeight: 600, letterSpacing: "0.05em",
            color: C.uncertainText, textTransform: "uppercase",
          }}>
            Approx.
          </span>
        )}
      </div>

      {/* Threshold row */}
      {evidence.threshold && evidence.threshold !== "—" && (
        <div style={{
          fontSize: 11, color: C.textSecondary,
          padding: "6px 0",
          borderTop: `1px solid ${C.borderSubtle}`,
        }}>
          <span style={{
            fontSize: 10, fontWeight: 700, color: C.textTertiary,
            textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 6,
          }}>Threshold</span>
          <span style={{ fontFamily: "JetBrains Mono, monospace" }}>{evidence.threshold}</span>
        </div>
      )}

      {/* Snippet preview */}
      {snippet && (
        <div>
          <div style={{
            display: "flex", alignItems: "center", gap: 5,
            fontSize: 10, fontWeight: 700, color: C.textTertiary,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
          }}>
            <Quote size={10} />
            Matched Snippet
          </div>
          <blockquote style={{
            margin: 0, padding: "10px 12px",
            background: "rgba(255,214,10,0.10)",
            borderLeft: `3px solid #EAB308`,
            borderRadius: "0 6px 6px 0",
            fontSize: 12, lineHeight: 1.55,
            color: C.textPrimary,
            fontFamily: "Georgia, serif",
            fontStyle: "italic",
            maxHeight: 180, overflow: "auto",
          }}>
            “{snippet}”
          </blockquote>
        </div>
      )}

      {/* AI Reasoning */}
      {evidence.explanation && (
        <div>
          <div style={{
            display: "flex", alignItems: "center", gap: 5,
            fontSize: 10, fontWeight: 700, color: C.textTertiary,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
          }}>
            <Brain size={10} />
            AI Reasoning
          </div>
          <div style={{
            padding: "10px 12px",
            background: C.cardBg,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 6,
            fontSize: 12, lineHeight: 1.55,
            color: C.textSecondary,
            maxHeight: 200, overflow: "auto",
          }}>
            {evidence.explanation}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{
        marginTop: "auto",
        paddingTop: SP.sm,
        borderTop: `1px solid ${C.borderSubtle}`,
        fontSize: 10, color: C.textTertiary, fontWeight: 500,
        letterSpacing: "0.04em",
      }}>
        <FileText size={10} style={{ verticalAlign: "-1px", marginRight: 5 }} />
        Use ← → to flip pages · F to toggle focus · +/− to zoom
      </div>
    </aside>
  );
}

function ToolButton({
  children, title, onClick, disabled, active,
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={title}
      aria-pressed={active}
      disabled={disabled}
      style={{
        background: active ? `${C.accent}28` : "none",
        border: active ? `1px solid ${C.accent}55` : "1px solid transparent",
        color: disabled ? C.textTertiary : (active ? C.accentText : C.textSecondary),
        opacity: disabled ? 0.45 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        padding: 6,
        borderRadius: 5,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "background 0.12s, border-color 0.12s",
      }}
      onMouseEnter={(e) => {
        if (disabled) return;
        e.currentTarget.style.background = active ? `${C.accent}38` : C.bgHover;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = active ? `${C.accent}28` : "none";
      }}
    >
      {children}
    </button>
  );
}

function LoadingState() {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: SP.sm, padding: SP.xl, color: C.textTertiary, fontSize: 13,
    }}>
      <Loader2 size={28} className="animate-spin" />
      Loading document…
    </div>
  );
}

function ErrorState({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: SP.sm, padding: SP.xl2, color: C.failText, textAlign: "center", maxWidth: 420,
    }}>
      <AlertTriangle size={32} />
      <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary }}>
        Could not load document
      </div>
      <div style={{ fontSize: 12, color: C.textSecondary }}>{message}</div>
      <button
        onClick={onClose}
        style={{
          marginTop: SP.sm,
          background: C.accent, color: "#fff", border: "none",
          borderRadius: 6, padding: "6px 14px",
          fontSize: 13, fontWeight: 600, cursor: "pointer",
        }}
      >
        Close
      </button>
    </div>
  );
}
