# Project Update 32 — Dark Theme Unification + Dashboard UX Fixes

**Date:** March 27, 2026
**Context:** Fixed eval dashboard column alignment bug, unified the entire frontend on a dark slate theme, cleaned up navigation layout, and added collapsible metadata panel. No spec — this was a collaborative UX polish session.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- None — this was a direct UX iteration session without a formal spec

### Prerequisite Reading
- `docs/project-updates/31-project-update-v4-7a-eval-completion-and-dashboard-spec.md` — dashboard was built and deployed here

---

## What Happened This Session

This was a UX polish session. The user wanted to fix visual issues in the eval dashboard and main app before doing a deeper dashboard review and eval iteration. No spec was created — the changes were small, targeted, and conversational. The user drove priorities by sharing screenshots and describing what looked wrong.

### The Column Alignment Bug

The first issue was immediately visible in the eval dashboard: the case results table had data values that didn't line up with their column headers. The screenshot showed 8 numeric values per row but only 6-7 column headers, with everything shifted.

Two bugs caused this:

**Bug 1: Nested `<tbody>` inside `<tbody>`.** The `CaseTable` component wrapped each case's rows (data row + optional expanded detail row) in a `<tbody key={c.id}>` inside the parent `<tbody>`. This is invalid HTML — browsers try to fix it by creating implicit table sections, which breaks column alignment. The fix was replacing the inner `<tbody>` with React `<Fragment>`.

**Bug 2: Score keys derived from only the first case.** The old code used `Object.keys(cases[0].scores)` to determine column headers. JavaScript object key order depends on insertion order, which can vary between cases or between what DDB returns vs what the JSON file had. The fix collects all unique score keys across every case and sorts them alphabetically. This guarantees headers match data regardless of which case is first or if cases have different score sets.

Also fixed: `colSpan={99}` on the expanded detail row replaced with a computed `colCount` based on actual column count.

### The Contrast Problem

After fixing alignment, the user noticed the table text was nearly invisible — light slate text (`#e2e8f0`) on a white background. The dashboard components had all been built with dark-background colors (slate-900 backgrounds, light text), but the page container had no background set. It inherited the default white from `index.css`'s light-mode media query.

The fix was simple: give the dashboard container a proper dark background (`#0f172a` — Tailwind's slate-900). All the existing text colors immediately became readable.

### The Dark Theme Unification

The user liked the dashboard's dark look and asked to extend it to the homepage and predictions list. This meant updating:

- `index.css` — global background to `#0f172a`, text to `#e2e8f0`, button defaults to dark
- `App.css` — complete rewrite. Removed all light-mode colors, removed the `prefers-color-scheme` media queries (the app is now always dark), updated every component class
- `PredictionInput.tsx` — inline styles for streaming response, score badges, dimension assessments, clarification section all updated from light-mode colors to dark-mode equivalents
- `ListPredictions.tsx` — score color function updated for dark backgrounds (brighter greens/yellows/reds)

The color palette is now consistent everywhere: `#0f172a` (page background), `#1e293b` (cards/containers), `#334155` (borders), `#e2e8f0` (primary text), `#cbd5e1` (secondary text), `#94a3b8` (muted text), `#60a5fa` (accent blue), `#64748b` (labels).

### The Button Cleanup

The old gradient buttons (purple-to-pink, blue-to-cyan) clashed badly with the clean dark theme. The user called them ugly — they were right. The navigation was also awkward: Make Prediction, My Predictions, Eval Dashboard, and Logout all in a row of gradient pills.

The fix restructured the header layout:
- Title centered, Logout pinned to top-right corner as a subtle ghost button (border only, no fill)
- Navigation moved to underline tabs below the title (matching the dashboard's tab pattern)
- Active tab gets a blue underline, inactive tabs are muted gray
- Login button is a simple solid blue pill
- Send/submit button is flat blue (`#3b82f6`), no gradients
- All gradient CSS removed entirely

### The Metadata Accordion

The user noticed the dashboard metadata panel was fine for verification and calibration (few fields, one line), but creation agent reports have a lot of metadata (prompt versions, features, git commit, model ID, agent runtime ARN, etc.) that cluttered the top of the page.

The fix: show 5 key fields always visible (agent, run_tier, case_count, duration_seconds, dataset_version) and collapse everything else behind a native `<details>` accordion showing `+ N more fields`. Zero dependencies, stays fully data-driven. For tabs with few metadata fields, the accordion doesn't even appear.

## Decisions Made

### Decision 137: Always-Dark Theme (No Light Mode Toggle)

**Source:** This update — UX polish session
**Date:** March 27, 2026

The frontend is now always dark (`#0f172a` background). The `prefers-color-scheme` media queries were removed entirely. The app was already rendering with dark-themed dashboard components on a light page background, creating an inconsistent experience. Rather than maintaining two themes for a single-user project, we committed to dark. If light mode is ever needed, it would be a proper theme system, not scattered media queries.

### Decision 138: Underline Tab Navigation (Not Gradient Buttons)

**Source:** This update — UX polish session
**Date:** March 27, 2026

The main app navigation uses underline tabs (matching the dashboard tab pattern) instead of gradient pill buttons. Logout is a ghost button pinned to the top-right corner. This creates visual consistency between the main app and the eval dashboard, and removes the gradient button system that clashed with the dark theme. The `navigation-button`, `navigation-button.secondary`, and `navigation-button.legacy` CSS classes were removed entirely.

## Files Created/Modified

### Created
- `docs/project-updates/32-project-update-dark-theme-and-dashboard-ux.md` — this update

### Modified
- `frontend-v4/src/pages/EvalDashboard/components/CaseTable.tsx` — fixed nested `<tbody>` → `<Fragment>`, score keys from all cases sorted alphabetically, computed `colSpan`
- `frontend-v4/src/pages/EvalDashboard/index.tsx` — added dark background and explicit text colors to dashboard container
- `frontend-v4/src/pages/EvalDashboard/components/AgentTab.tsx` — MetadataPanel now shows 5 summary fields inline + collapsible accordion for the rest
- `frontend-v4/src/index.css` — global dark theme (removed light mode, removed `color-scheme: light dark`)
- `frontend-v4/src/App.css` — complete rewrite for dark theme, new header/nav layout, removed all gradient button styles
- `frontend-v4/src/App.tsx` — restructured header (title centered, logout top-right, nav tabs below)
- `frontend-v4/src/components/LoginButton.tsx` — simplified to use `btn-login`/`btn-logout` classes
- `frontend-v4/src/components/PredictionInput.tsx` — all inline styles updated for dark theme (score badges, streaming response, clarification section, dimension assessments)
- `frontend-v4/src/components/ListPredictions.tsx` — score color function updated for dark backgrounds

## What the Next Agent Should Do

### Priority 1: Dashboard Review and Eval Iteration
The user wants to review the full dashboard and understand what the data tells them. Walk through each tab (Creation, Verification, Calibration), explain the metrics, and discuss what the baselines reveal about where to improve next.

### Priority 2: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality baseline is 0.57. The 5 personal/subjective cases average ~0.26. Teaching the planner to build self-report plans is the highest-impact prompt change. Target: PQ ≥ 0.75.

### Priority 3: Tool Action Tracking (Backlog Item 16)
4/7 verification failures are Browser tool inability. Structured tracking would identify which tool to add or prompt to fix next.

### Priority 4: base-010 Full Moon Investigation
The agent returned `refuted` with 0.9 confidence when expected `confirmed`. Either a lunar calculation bug or golden dataset issue.

### TTY / Command Execution Fix (Resolved This Session)
The long-standing `TTY=not a tty` and `Exit Code: -1` issues that plagued every agent session were caused by Amazon Q CLI shell integration (`q init bash pre/post`) conflicting with Kiro's `PROMPT_COMMAND`-based output capture. Fixed by wrapping both Amazon Q blocks in `~/.bashrc` with `if [[ "$TERM_PROGRAM" != "kiro" ]]` guards, plus `unset TTY` as a safety net. Amazon Q still works in regular terminals. Agent commands now return full output with `Exit Code: 0`.

### Key Files
- `https://d2fngmclz6psil.cloudfront.net` — production frontend (just deployed with dark theme)
- `https://d2fngmclz6psil.cloudfront.net/eval` — production eval dashboard
- `frontend-v4/src/App.css` — the new unified dark theme styles
- `frontend-v4/src/pages/EvalDashboard/components/CaseTable.tsx` — fixed table alignment
- `frontend-v4/src/pages/EvalDashboard/components/AgentTab.tsx` — collapsible metadata panel
- `~/.bashrc` — Amazon Q guard + TTY unset fix
