---
inclusion: auto
---

# Project Documentation Standards

## MANDATORY Documentation Workflow

**CRITICAL**: After every spec completion, planning session, or significant milestone, you MUST follow this exact sequence. Do NOT skip steps. Do NOT update the decision log without a project update. The numbered update is the source of truth — everything else derives from it.

### Step-by-Step Sequence (follow in order)

1. **Create a numbered project update** (`docs/project-updates/NN-project-update-*.md`)
   - Check the latest numbered file to determine the next number
   - This is the detailed narrative — decisions, rationale, results, next steps
   - Must include all sections listed in "Format Requirements" below
   - Must reference Kiro spec paths and git commit (or "pending" if not yet committed)

2. **Update `docs/project-updates/decision-log.md`**
   - Append new decisions made during the session
   - Continue the global numbering sequence (check the last entry for the current highest number)
   - Each decision must reference its source (the numbered update you just created)

3. **Update `docs/project-updates/project-summary.md`**
   - Add a condensed entry under "Project Evolution" (2-3 sentences max per update)
   - Update the "Current State" section with new metrics, counts, and next steps
   - Do NOT over-update — keep entries concise

4. **Update `docs/project-updates/backlog.md`**
   - Add any new backlog items identified during the session
   - Update status of existing items that were addressed
   - Remove items that are fully resolved

5. **Update `docs/project-updates/architecture-insights.md`** (if applicable)
   - Only if the session produced new eval data or changed the architecture comparison

6. **Update `docs/project-updates/eval-run-log.md`** (if applicable)
   - Only if eval runs were performed (see `eval-run-capture.md` steering for format)

### When This Workflow Triggers

You MUST run this workflow when:
- A spec is completed (all required tasks done)
- A spec planning session produces new specs or splits existing ones
- A major deployment is completed
- Significant architectural decisions are made
- A session ends with meaningful progress

You do NOT need this workflow for:
- Minor bug fixes or typo corrections
- Routine test runs without significant findings
- Code refactoring that doesn't change behavior
- Mid-task work that hasn't reached a milestone

## Format Requirements for Project Updates

Every project update (`docs/project-updates/NN-project-update-*.md`) must include:

```markdown
# Project Update NN — Descriptive Title

**Date:** YYYY-MM-DD
**Context:** One-line summary of what happened
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** SHA or "Pending"

### Referenced Kiro Specs
- List all spec paths referenced in this update with status

### Prerequisite Reading
- Previous update(s) needed for context

---

## What Happened This Session
[Detailed narrative]

## Decisions Made
[List with decision numbers]

## Files Created/Modified
[Organized by Created/Modified]

## What the Next Agent Should Do
[Prioritized action items with key files and important notes]
```

## Decision Numbering

Decisions are numbered globally across all project updates. ALWAYS check the last entry in `decision-log.md` for the current highest number before adding new ones. Never reuse or skip numbers.

## Spec References

When working on a spec, always check `docs/project-updates/` for context. The updates contain decisions and rationale that may not be in the spec files themselves.
