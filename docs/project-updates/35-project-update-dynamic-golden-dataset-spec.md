# Project Update 35 — Dynamic Golden Dataset Spec

**Date:** March 30, 2026
**Context:** Continuation of Update 34 session. After establishing the Brave Search baseline and analyzing verification failures, discovered a fundamental design flaw in the golden dataset: time-dependent ground truth goes stale. Built a complete spec for a dynamic golden dataset generator.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/dynamic-golden-dataset/` — Dynamic Golden Dataset spec (requirements + design + tasks, READY TO EXECUTE)

### Prerequisite Reading
- `docs/project-updates/34-project-update-ddb-cleanup-and-eval-isolation.md` — Earlier in this session: DDB cleanup, eval isolation, Brave Search, full baselines
- `.kiro/specs/dynamic-golden-dataset/requirements.md` — 10 requirements
- `.kiro/specs/dynamic-golden-dataset/design.md` — Generator architecture, 16 correctness properties

---

## What Happened

### The Problem: Stale Ground Truth

The full eval baselines from Update 34 revealed that base-010 ("The next full moon will occur before April 1, 2026") was scored as a verification failure — but the agent was actually correct. The golden dataset expected `confirmed` because when it was written, the next full moon was March 3 (before April 1). But by March 30, the March 3 full moon had passed and the next one was April 2 (after April 1). The agent correctly returned `refuted`.

This isn't just one prediction. Any time-dependent prediction will eventually have stale ground truth. And the deeper analysis revealed a bigger problem: 47 of 55 predictions have null expected outcomes, only 8 have actual verdicts (all `confirmed`, zero `refuted`), and only 10 immediate-mode cases are testable in the verification eval. The other 45 cases (at_date, before_date, recurring) have future verification dates and can't be verified.

### The Solution: Dynamic Golden Dataset Generator

The user proposed a generator script that produces a fresh golden dataset with time-anchored predictions each time it runs. We built a complete spec with 10 requirements, a detailed design with 16 correctness properties, and 9 implementation tasks.

Key design decisions:
- **Two-file strategy**: Static dataset stays for timeless cases; dynamic dataset is regenerated before each eval run
- **3 predictions per mode** (12 total dynamic): Enough to catch "this mode is broken" without diminishing returns
- **Ground truth at generation time**: Deterministic calculations (calendar, math, astronomy) + Brave Search API lookups
- **Backward-compatible merging**: `--dynamic-dataset` CLI arg is optional, existing workflows unchanged
- **Brave template pragmatism**: If a query doesn't parse well, swap it for one that does. Goal is reliable templates per mode, not every possible domain.

### Static Dataset Quality Assessment

Analyzed the existing 55-prediction static dataset:
- Difficulty spread: solid (11 easy, 30 medium, 14 hard)
- Domain diversity: excellent (12 domains)
- Mode distribution: imbalanced (31 at_date, 10 immediate, 11 before_date, 3 recurring)
- Expected outcomes: 47 null, 8 confirmed, 0 refuted — massive confirmation bias
- Subjective predictions: only 6 of 55

The static dataset is fine for creation eval (parsing, planning, scoring) but almost useless for verification eval without the dynamic supplement.

### Backlog Update

Added backlog item 17: Debug AgentCore Browser Tool in Deployed Runtime. The Browser tool works via direct API calls but fails silently inside the deployed AgentCore Runtime. Root cause unknown. Brave Search covers the primary use case but Browser is needed for interactive page fetching.

## Files Created/Modified

### Created
- `.kiro/specs/dynamic-golden-dataset/requirements.md` — 10 requirements
- `.kiro/specs/dynamic-golden-dataset/design.md` — Generator architecture, templates, merger, 16 properties
- `.kiro/specs/dynamic-golden-dataset/tasks.md` — 9 tasks with sub-tasks
- `.kiro/specs/dynamic-golden-dataset/.config.kiro` — Spec config
- `docs/project-updates/35-project-update-dynamic-golden-dataset-spec.md` — this update

### Modified
- `docs/project-updates/backlog.md` — Added item 17 (Browser debugging) at top

## What the Next Agent Should Do

### Priority 1: Execute Dynamic Golden Dataset Spec
The spec at `.kiro/specs/dynamic-golden-dataset/tasks.md` has 9 tasks ready to execute. Start with task 1 (static dataset migration + merger), then task 3 (generator core + deterministic templates). The Brave templates (task 4) should be approached experimentally — try queries, keep what parses cleanly, swap what doesn't.

### Priority 2: Fix base-010 Golden Dataset Entry
Part of task 1.1 — add `time_sensitive: true` to base-010. The dynamic generator will produce a replacement with current ground truth.

### Priority 3: Debug AgentCore Browser Tool (Backlog Item 17)
The Browser tool works via direct API calls but fails in the deployed runtime. Investigate the Strands `AgentCoreBrowser` wrapper behavior in the container environment.

### Priority 4: Verification Planner Self-Report Plans (Backlog Item 15)
Plan quality is 0.56-0.58. Personal/subjective cases average ~0.26. Self-report plans are the highest-impact prompt change for creation quality.
