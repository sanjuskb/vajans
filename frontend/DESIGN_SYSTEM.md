# VAJANS Frontend Design System
## Complete UI Architecture for Production Deployment

---

# PART 1 — DESIGN SYSTEM FOUNDATION

Before designing pages, establish the visual language. Every component derives from this.

## Color Palette

**Primary Surface Colors**
The application runs on a dark navy base — not consumer-dark, but the controlled, high-contrast dark used in financial terminals and defense dashboards. This communicates seriousness and data density.

```
Background Primary:    #0B0F1A  (deepest surface — page background)
Background Secondary:  #111827  (cards, panels)
Background Tertiary:   #1C2333  (nested cards, table rows)
Background Hover:      #1F2937  (interactive hover state)
Border Subtle:         #1E2A3B  (dividers, card borders)
Border Active:         #2D3F57  (focused elements)
```

**Brand Accent — Institutional Blue**
Not electric blue. A measured, authoritative blue that reads as trustworthy.
```
Accent Primary:        #2563EB  (primary actions, active states)
Accent Hover:          #1D4ED8  (button hover)
Accent Muted:          #1E3A5F  (accent backgrounds, subtle highlight)
Accent Text:           #60A5FA  (links, active labels)
```

**Verdict Colors — The Most Important Color Decisions**
These colors carry the weight of every decision in the system. They must be immediately readable, unambiguous, and accessible.
```
PASS Green:            #059669  (solid) / #D1FAE5 (text on dark) / #064E3B (background)
FAIL Red:              #DC2626  (solid) / #FCA5A5 (text on dark) / #450A0A (background)
UNCERTAIN Amber:       #D97706  (solid) / #FCD34D (text on dark) / #451A03 (background)
REVIEW Purple:         #7C3AED  (solid) / #C4B5FD (text on dark) / #2E1065 (background)
```

**Text Hierarchy**
```
Text Primary:          #F9FAFB  (headings, critical data)
Text Secondary:        #9CA3AF  (labels, metadata)
Text Tertiary:         #6B7280  (disabled, placeholder)
Text Inverse:          #111827  (text on light backgrounds)
```

**Status and Functional Colors**
```
Info:                  #0EA5E9
Warning:               #F59E0B
Danger:                #EF4444
Success:               #10B981
Neutral:               #6B7280
```

---

## Typography System

**Font Choice:** Inter for UI (system fallback: -apple-system, BlinkMacSystemFont). Monospace: JetBrains Mono for all numerical data, IDs, hashes, and code.

```
Scale (rem-based, base 16px):

Display:    2.25rem / 36px — Bold 700 — Page titles, hero metrics
H1:         1.875rem / 30px — Bold 700 — Section headers
H2:         1.5rem / 24px   — SemiBold 600 — Card titles
H3:         1.25rem / 20px  — SemiBold 600 — Subsection headers
H4:         1.125rem / 18px — Medium 500 — Table headers, labels
Body:       0.9375rem / 15px — Regular 400 — Main content
Body SM:    0.875rem / 14px  — Regular 400 — Supporting text
Caption:    0.8125rem / 13px — Regular 400 — Metadata, timestamps
Mono:       0.875rem / 14px  — JetBrains Mono — IDs, hashes, values
```

**Line heights:** 1.2 for headings, 1.6 for body text, 1.4 for compact data.

---

## Spacing System

8-point grid. Every margin, padding, and gap is a multiple of 8.

```
4px   — xs  — Inline tight gaps
8px   — sm  — Component internal padding
12px  — md  — Dense table cell padding
16px  — lg  — Card padding, list item spacing
24px  — xl  — Section gaps
32px  — 2xl — Major section separation
48px  — 3xl — Page section breaks
64px  — 4xl — Page-level vertical rhythm
```

---

## Component Design Tokens

**Cards**
```
Border radius:    8px (cards), 6px (inner components), 4px (badges)
Border:           1px solid #1E2A3B
Shadow:           none by default (flat design, borders carry structure)
Hover shadow:     0 0 0 1px #2D3F57
Padding:          24px
```

**Badges — Verdict and Status**
Badges are the most-read element in the system. They appear in every table row.
```
Height:           22px
Padding:          0 8px
Border radius:    4px
Font:             0.75rem / 12px, SemiBold 600, uppercase, letter-spacing 0.04em
Style:            Filled background from verdict color palette
```

Badge examples:
- PASS → green background #064E3B, text #D1FAE5
- FAIL → red background #450A0A, text #FCA5A5
- UNCERTAIN → amber background #451A03, text #FCD34D
- NEEDS REVIEW → purple background #2E1065, text #C4B5FD
- MANDATORY → blue background #1E3A5F, text #60A5FA
- PREFERRED → neutral background #1C2333, text #9CA3AF

**Buttons**
```
Primary:    bg #2563EB, text white, hover #1D4ED8, height 36px, padding 0 16px
Secondary:  bg transparent, border 1px #2D3F57, text #9CA3AF, hover bg #1C2333
Danger:     bg #DC2626, text white, hover #B91C1C
Ghost:      no background, no border, text #60A5FA, hover text #93C5FD
Icon:       32x32px, ghost style, used in table actions
```

**Tables**
```
Header:        bg #0B0F1A, text #6B7280, uppercase 12px SemiBold, padding 12px 16px
Row:           bg #111827, border-bottom 1px #1E2A3B, padding 14px 16px
Row hover:     bg #1C2333
Zebra stripe:  off (border + hover is sufficient)
Sticky header: yes
```

---

# PART 2 — NAVIGATION ARCHITECTURE

## Global Navigation Structure

VAJANS uses a **persistent left sidebar** as the primary navigation rail. This is non-negotiable for a multi-page enterprise application — it keeps orientation constant as users move through complex evaluation workflows.

**Sidebar width:** 240px (expanded) / 64px (collapsed icon rail)

**Sidebar sections:**

```
VAJANS Logo + wordmark (top, 64px height header)

PRIMARY NAVIGATION
  ● Dashboard          /dashboard
  ● Jobs               /jobs
  ● Review Queue       /review          [badge: pending count]
  ● Audit Logs         /audit

SYSTEM
  ● Settings           /settings
  ● Help               /help

USER SECTION (bottom)
  Profile avatar
  Officer name
  Role badge
  Logout
```

**Top bar (persistent, 56px):**
Contains: Page title (dynamic), breadcrumb, global search, notifications bell, and a prominent "New Evaluation" CTA button.

The combination of sidebar + topbar creates a professional shell that wraps every authenticated page.

---

# PART 3 — COMPLETE PAGE DESIGNS

---

## PAGE 1 — LANDING PAGE

**Purpose:** Communicate what VAJANS is to a first-time visitor (government officer, administrator, evaluator). This is not a marketing page. It is an institutional entry point — it should communicate credibility, not excitement.

**Layout:** Full-width, single-column, no sidebar. Light mode or maintained dark mode (dark preferred for consistency).

**Sections:**

**Section 1 — Navigation Bar (fixed)**
Left: VAJANS logo + wordmark.
Right: "Sign In" button (primary), "About" link.
Height: 64px. Background: #0B0F1A with bottom border.

**Section 2 — Hero**
Full-width, centered content. No background imagery — a subtle grid pattern or nothing.
```
Tag line (small, uppercase):   AI FOR BHARAT · GOVERNMENT PROCUREMENT
Headline (Display):            Tender Evaluation That Stands Up in Court
Sub-headline (Body):           VAJANS converts unstructured procurement documents 
                               into evidence-backed, legally defensible evaluation 
                               records — automatically.
CTA Button (large, primary):   Start Evaluation →
Secondary link:                See how it works ↓
```

**Section 3 — Problem Statement (3-column cards)**
Three cards, each presenting one failure of the current system:
```
Card 1: "5–7 days per tender" — icon: clock — desc: manual review bottleneck
Card 2: "No consistent evaluation" — icon: split — desc: two officers, two outcomes
Card 3: "Legally exposed decisions" — icon: shield-off — desc: no traceable audit
```

**Section 4 — How VAJANS Works (pipeline visualization)**
Horizontal 5-step flow with connecting arrows:
```
[Ingest] → [Extract Rules] → [Extract Values] → [Evaluate] → [Audit + Review]
```
Each step: icon, name, one-line description.

**Section 5 — Key Properties (2x3 grid)**
Six properties in a clean grid. No icons needed — just label + one sentence.
Deterministic · Explainable · Auditable · Fail-Safe · Evidence-Linked · Legally Defensible

**Section 6 — Footer**
VAJANS name, theme attribution (Theme 3 · CRPF · AI for Bharat), links to privacy/terms placeholders.

---

## PAGE 2 — AUTHENTICATION (LOGIN)

**Purpose:** Secure entry for authorized procurement officers. This is not a public-facing sign-up flow. It is an institutional login — it should feel controlled and deliberate.

**Layout:** Split-screen. Left panel (40%): brand + context. Right panel (60%): form.

**Left panel:**
```
VAJANS logo (large)
"Government Tender Evaluation System"
Three feature lines with checkmarks:
  ✓ Legally defensible decisions
  ✓ Complete audit trail
  ✓ Evidence-linked evaluation
```
Background: #111827 with subtle VAJANS watermark pattern.

**Right panel:**
```
Header:    "Sign in to VAJANS"
Sub:       "Authorized government procurement officers only"

Form fields:
  Officer ID / Email (label above, not placeholder)
  Password (with show/hide toggle)
  
Options:
  "Remember this device" checkbox
  "Forgot credentials? Contact administrator" link (no self-service reset)
  
Primary action: "Sign In" button (full width, 44px height)

Footer note: "Access is restricted to authorized personnel. 
              Unauthorized access attempts are logged."
```

No social login. No OAuth. No "Create account" link. Officers are provisioned by administrators — this is intentional and communicates institutional seriousness.

---

## PAGE 3 — DASHBOARD (OVERVIEW)

**Purpose:** Command center. An officer lands here after login. They should immediately understand: what is active, what needs attention, and what was recently completed.

**Layout:** Sidebar + topbar shell. Content area is a responsive grid.

**Row 1 — Metric Cards (4 cards, equal width)**
```
Card 1: Active Jobs          [number]    Jobs currently processing
Card 2: Pending Reviews      [number]    Cases awaiting human review  [highlighted if > 0]
Card 3: Completed Today      [number]    Evaluations finished today
Card 4: Avg. Processing Time [X hrs]     Rolling average
```
Each card: large number (Display size), label below, subtle trend indicator (up/down arrow + % vs last week).

**Row 2 — Left 60% / Right 40% split**

Left: Recent Jobs (table, last 5)
```
Columns: Job Title | Status | Bidders | Started | Action
Status badges: PROCESSING / COMPLETED / FAILED
Action: "View →" link
"View all jobs →" at bottom
```

Right: Review Queue Preview
```
Header: "Pending Reviews" + count badge
List of top 5 escalated cases:
  - Bidder name
  - Criterion that needs review
  - Escalation reason (in amber text)
  - "Review →" button
"Go to Review Queue →" at bottom
```

**Row 3 — Full width: Verdict Distribution (last 30 days)**
A horizontal stacked bar showing aggregate verdict distribution across all completed jobs. Pass (green) / Fail (red) / Uncertain (amber) segments. X-axis: dates. Shows system-wide trends.

---

## PAGE 4 — JOBS LIST PAGE

**Purpose:** Complete listing of all evaluation jobs with filtering, search, and creation capability.

**Layout:** Sidebar + topbar. Content is full-width.

**Top bar content:** "Evaluations" title + breadcrumb + "New Evaluation" button (primary, top right).

**Filter bar (below top bar, sticky):**
```
Search input:     "Search by job title or ID..."
Status filter:    All | Processing | Completed | Failed | Draft
Date range:       Date picker (from/to)
Sort:             Newest first ▾
```

**Jobs Table:**
```
Columns:
  # (row number)
  Job Title
  Status (badge)
  Tender Reference
  Bidders (count)
  Started
  Completed
  TrustScore Avg (for completed jobs)
  Actions (View | Archive)

Row expansion (optional): clicking a row navigates to Job Detail
Empty state: illustrated empty state with "Create your first evaluation" CTA
Pagination: 25 per page, numbered pagination at bottom
```

**New Evaluation Modal (triggered by button):**
Rather than a separate page, a focused modal keeps the flow tight.
```
Step 1: Job details
  - Job title (text field)
  - Tender reference number
  - Description (optional)
  
Step 2: Upload documents
  - Drag-and-drop zone (large, clear)
  - "Tender Document" upload (required, labeled)
  - "Bidder Documents" upload (multiple, labeled with bidder name input per file)
  - Supported formats listed below zone
  - File size indicator per upload
  
Step 3: Confirm + Submit
  - Summary of what will be processed
  - "Start Evaluation" button
  - Estimated processing time note
```

---

## PAGE 5 — JOB DETAIL PAGE (CORE OF THE SYSTEM)

This is the most important page. Every design decision here affects whether the system is trusted by officers.

**Layout:** Sidebar + topbar. Content area divided into a **main column (68%)** and **right panel (32%)**.

---

### TOP SECTION — Job Header Bar

Full-width bar directly below topbar. Contains:
```
Left:
  Job title (H1)
  Tender ref · Started date · Duration
  Status badge (large)

Right:
  "Export Report" button
  "Re-run Evaluation" button (if completed)
  Status indicator (animated dot if processing)
```

---

### SECTION 1 — FINAL DECISION PANEL

The first thing officers need to see. Full-width card, visually weighted.

```
Layout: Three columns inside card

Column 1 — Overall Verdict (largest visual element)
  Large verdict badge (PASS / FAIL / UNCERTAIN / NEEDS REVIEW)
  Verdict label: "Overall Eligibility Verdict"
  Sub-line: "X of Y mandatory criteria passed"
  
Column 2 — Score Breakdown
  Overall weighted score: [number]/100 (large, mono font)
  Progress bar (segmented: pass/fail/uncertain)
  Financial criteria: score
  Technical criteria: score
  Compliance criteria: score

Column 3 — Quick Statistics
  Total criteria evaluated: X
  Auto-decided: X
  Escalated to review: X
  Rejected (low confidence): X
  Bidders in evaluation: X
```

---

### SECTION 2 — TABS NAVIGATION

Below the decision panel, a tab bar switches between views:

```
[ Criteria Evaluation ]  [ Bidder Comparison ]  [ Documents ]  [ Audit Trail ]
```

---

### TAB 1 — CRITERIA EVALUATION (Default Active)

This is the heart of the evaluation view.

**Criteria Filter Bar:**
```
Filter by: All Criteria | Mandatory Only | Failed Only | Needs Review | Uncertain
```

**Criteria Table (expandable rows):**

Each row is a criterion. The table is the primary interface.

```
Columns:
  Criterion Name          (with mandatory badge if applicable)
  Type                    (Financial / Technical / Compliance / Certification)
  Verdict                 (PASS / FAIL / UNCERTAIN badge)
  TrustScore              (numeric + thin color bar)
  Extracted Value         (actual value found, mono font)
  Threshold               (required threshold, mono font)
  Review Status           (Auto / Pending Review / Reviewed)
  Actions                 (Review button if escalated, expand row icon)
```

**Expandable Row (when officer clicks a criterion):**
The row expands inline — no modal. This keeps context.

```
Expanded view has 3 panels side by side:

Panel 1 — Evidence
  "Source Document": filename
  "Page": number (clickable link to document view)
  "Source Snippet": quoted text block (styled differently — border-left accent, 
                    monospace, slight background)
  Confidence indicator

Panel 2 — Justification
  "Rule Applied": criterion description
  "Value Found": extracted canonical value
  "Threshold": required threshold
  "Comparison": "6.2 Cr ≥ 5 Cr minimum ✓" (human readable)
  "Verdict Reasoning": one sentence
  
Panel 3 — Review Actions (only shown if TrustScore < 0.85 or verdict = UNCERTAIN)
  Three action buttons:
    [✓ Approve]   — green, confirms automated extraction is correct
    [✎ Edit]      — opens inline edit form with corrected value input + justification
    [✗ Reject]    — marks for re-submission, adds reason
  
  If already reviewed:
    Shows reviewer name, timestamp, action taken, and note
    "Reviewed" badge replaces action buttons
```

---

### TAB 2 — BIDDER COMPARISON

For jobs with multiple bidders, this tab provides the comparative view.

**Bidder Summary Cards (horizontal scroll if many bidders):**
One card per bidder at top:
```
Bidder name
Overall score: [number]
Verdict badge
Criteria passed: X/Y
```

**Comparison Matrix Table:**
```
Rows: Each criterion
Columns: Each bidder

Cell content: PASS (green dot) / FAIL (red dot) / UNCERTAIN (amber dot) / REVIEW (purple dot)

Bottom row: Weighted Score per bidder
Rightmost column: Threshold / Requirement
```

This gives the officer an immediate visual read of who passes what.

**Ranking Panel (right side):**
Eligible bidders ranked by weighted score. Non-eligible bidders shown separately below with the first criterion they failed.

---

### TAB 3 — DOCUMENTS

List of all uploaded documents for this job.

```
Columns: File Name | Type (Tender/Bidder) | Pages | OCR Quality | Status | Processed At

OCR Quality shown as: bar (green if >0.85, amber if 0.60-0.85, red if <0.60) + number

Actions:
  View (opens document preview panel on right)
  Download
```

Document Preview Panel (right side, 40%):
Simple PDF viewer embedded. When officer clicks evidence snippets in Tab 1, this panel opens to the relevant page automatically. This is the most important UX connection — evidence-to-document linkage.

---

### TAB 4 — AUDIT TRAIL

Full audit log for this specific job.

```
Timeline view (vertical, newest first):

Each entry:
  Timestamp (mono, precise to second)
  Actor (System / Officer Name)
  Action (color-coded by action type)
  Details (expandable)
  Hash (mono, truncated — hover for full)

Action type colors:
  System actions: blue
  Reviewer approvals: green
  Reviewer rejections: red
  Reviewer edits: amber

At bottom:
  "Verify chain integrity" button → triggers hash verification, shows result
  "Export full audit log" button → downloads signed JSON
```

---

### RIGHT PANEL (Persistent, 32% width)

This panel sits to the right of the main content across all tabs. It shows job-level context that doesn't change with tab switching.

```
Section 1 — Job Information
  ID (mono), Status, Created by, Started, Duration

Section 2 — Processing Status
  Step tracker:
    ✓ Ingestion complete
    ✓ Criteria extracted (X criteria)
    ✓ Data extracted
    ✓ Evaluation complete
    ⏳ Review pending (X items)
  
Section 3 — TrustScore Distribution (small chart)
  Donut or small bar showing distribution of 
  high/medium/low confidence extractions

Section 4 — Quick Actions
  Export Report (PDF)
  Export Audit Log
  Share job link
  Archive job
```

---

## PAGE 6 — REVIEW QUEUE PAGE

**Purpose:** Centralized view of all cases across all jobs that require human review. This is where officers spend time making judgment calls.

**Layout:** Sidebar + topbar. Full-width content.

**Header:** "Review Queue" + count of pending items + "Items assigned to me" toggle.

**Filter Bar:**
```
Status: All | Pending | In Review | Resolved
Priority: All | High | Normal | Low
Job: All jobs ▾
Escalation reason: All | Low OCR | Data Conflict | Ambiguous Criterion | Missing Evidence
```

**Queue Table:**
```
Columns:
  Priority (High/Normal/Low badge)
  Bidder Name
  Criterion
  Escalation Reason (the specific reason — not just a code)
  TrustScore (number + colored bar)
  Job Title (linked)
  Escalated (time ago)
  Assigned To
  Actions: [Review →]

Row click: navigates to Job Detail Page, Criteria tab, auto-scrolls to and expands the relevant criterion row.
```

**Empty State:** When queue is empty — "All cases reviewed. No pending items." with a checkmark illustration.

---

## PAGE 7 — AUDIT LOGS PAGE

**Purpose:** System-wide audit trail. For administrators and compliance officers who need to see all actions across all jobs.

**Layout:** Sidebar + topbar. Full-width content.

**Filter Bar:**
```
Date range picker
Actor filter (System / Specific officer)
Action type filter (multi-select)
Job filter
Search (keyword in details)
```

**Log Table:**
```
Columns:
  Timestamp (mono, precise)
  Job
  Actor
  Action (color-coded badge)
  Details (truncated, expandable)
  Hash (mono, truncated)

Row expansion: shows full details JSON, full hash, previous hash reference
```

**Integrity Check Section (top of page, collapsible):**
```
"Chain Integrity Status"
Last verified: [timestamp]
Status: INTACT ✓ (green) or COMPROMISED ✗ (red)
"Run Verification" button → triggers full hash chain check → shows result with timestamp
```

**Export:**
```
"Export Logs" button → date range selector → downloads CSV or signed JSON
```

---

# PART 4 — INTERACTION FLOW

## Full User Journey

**Entry flow:**
Officer lands on landing page → reads what the system does → clicks "Sign In" → enters credentials → lands on Dashboard.

**Starting an evaluation:**
Dashboard → "New Evaluation" button → Modal opens → Enter job title + tender reference → Upload tender document (required first) → Upload bidder documents one by one (assign name to each) → Review uploads → Click "Start Evaluation" → Modal closes → Jobs list updates with new job showing "Processing" badge → Officer can leave and come back → Job detail page shows real-time progress via status tracker in right panel.

**Reviewing results:**
Officer navigates to Jobs → finds completed job → clicks "View →" → Job Detail page loads → Final Decision Panel is first thing seen → Officer reads overall verdict → Scrolls to Criteria table → Sees all criteria with verdicts → Clicks a row with "UNCERTAIN" verdict → Row expands → Reads evidence snippet → Reads justification → Clicks "Approve" or "Edit" → Action is logged → Row updates to "Reviewed" state → After all reviews complete, overall verdict updates if applicable.

**Review queue workflow:**
Notification in sidebar shows "5" badge on Review Queue → Officer clicks Review Queue → Sees all pending cases sorted by priority → Clicks "Review →" on highest priority item → Taken to Job Detail page, criterion row already expanded → Reviews and acts → Returns to queue → Next item.

**Audit verification:**
Admin navigates to Audit Logs → sets date range → filters by job → views all actions → clicks "Run Verification" → system confirms chain is intact → exports signed log for compliance file.

---

# PART 5 — RESPONSIVE AND STATE DESIGN

## Loading States
- Skeleton screens (not spinners) for tables and cards — maintains layout while data loads
- Processing jobs show animated step tracker with current step highlighted
- No blocking full-page loaders

## Empty States
Every list and table has a designed empty state: icon + title + description + CTA if applicable. Never show a blank table.

## Error States
API errors surface as inline banners below affected sections — not full-page errors. Critical failures show a contained error card with retry option.

## Success States
Actions (approve, submit, export) show brief inline confirmation — not toast popups that interrupt flow. The row/button updates to confirmed state directly.

---

# PART 6 — IMPLEMENTATION NOTES FOR DEVELOPERS

When this design goes to code:

**Component library approach:** Build a small internal component library starting with: Badge, Button, Card, Table, Tab, ExpandableRow, StatusTracker, MetricCard, TrustScoreBar. All other components compose from these.

**Navigation:** React Router v6, layout component wraps all authenticated pages with sidebar + topbar. Landing and auth pages use a separate minimal layout.

**State management:** React Query for all server state (jobs, results, audit logs). No Redux needed — server state is the source of truth.

**Charts:** Recharts (already in stack). Verdict distribution: horizontal stacked bar. TrustScore distribution: simple bar chart. Bidder comparison: matrix built from table, not a chart library.

**Document viewer:** react-pdf for the document preview panel in the Documents tab.

**Accessibility:** All color decisions maintain WCAG AA contrast ratios. Verdict badges include text, not just color. Tables have proper ARIA labels. Focus management on expandable rows.

---

This design system is complete and ready for implementation. Every page, component, interaction, and visual decision is specified. Begin with the Design System tokens and shared components, then implement pages in this order: Shell (sidebar + topbar) → Dashboard → Jobs List → Job Detail → Review Queue → Audit Logs → Landing → Auth.