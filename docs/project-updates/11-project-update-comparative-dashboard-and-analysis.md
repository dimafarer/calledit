# Project Update 11 — Comparative Eval Dashboard, Architecture Analysis & Next Steps

**Date:** March 18-19, 2026
**Context:** Built the comparative eval dashboard (Spec 11), ran first architecture comparison (serial vs single), analyzed failure profiles, identified next prompt changes
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/comparative-eval-dashboard/` — Spec 11: Comparative Eval Dashboard (dashboard tasks COMPLETE, eval runs partially complete)

### Prerequisite Reading
- `docs/project-updates/10-project-update-vb-iteration-and-architecture-vision.md` — Spec 10, pluggable backends, per-agent evaluators
- `docs/project-updates/decision-log.md` — All decisions through Decision 57
- `docs/project-updates/eval-run-log.md` — All 14 eval runs with insights
- `docs/project-updates/architecture-insights.md` — Serial vs single failure profiles and analysis

---

## What Was Built

### Spec 11: Comparative Eval Dashboard
- Data loader extended with `vb_centric_score`, `per_agent_aggregates`, `execution_time_ms`, and DDB-local enrichment (DDB records get backfilled from local data when missing fields)
- New Architecture Comparison page with side-by-side evaluator scores, Verification-Builder-centric score delta, per-category accuracy, execution time
- Trends page enhanced with per-agent judge score traces (Final-Output and Per-Agent & Cross-Pipeline sections), architecture filtering, composite score weights reference table
- Heatmap rewritten with pipeline-ordered columns (Parser → Categorizer → Verification Builder → Review → Cross-Pipeline), color-coded labels (blue = LLM judge, gray = deterministic), evaluator descriptions on hover
- Coherence View updated to recognize all 6 LLM judges with per-judge agreement breakdown and judge-vs-judge correlation
- Prompt Correlation enhanced with Verification-Builder-centric score deltas, per-agent evaluator deltas, and architecture-aware effect grouping
- Sidebar updated with Architecture Comparison page, routing wired in app.py
- Fixed `score_history.py` to write `architecture`, `model_config`, `vb_centric_score`, `verification_quality_aggregates`
- Fixed Streamlit `use_container_width` deprecation warnings

### Supporting Docs Created
- `docs/project-updates/eval-run-log.md` — Append-only run log (runs 1-14)
- `docs/project-updates/architecture-insights.md` — Architecture comparison findings
- `docs/project-updates/common-commands.md` — Frequently used commands
- `docs/project-updates/project-summary.md` — Full project summary for resume agent
- `docs/project-updates/backlog.md` — 8 backlog items
- `docs/research/mcp-verification-pipeline.md` — MCP ecosystem research
- `.kiro/steering/eval-run-capture.md` — Auto-triggers run log updates when eval report is shared

---

## Architecture Comparison Results

### Run 13 (single, prompts 1/2/2/2, all 6 judges) vs Run 14 (serial, same config)

| Metric | Serial | Single |
|---|---|---|
| Pass rate | 25% | 16% |
| Verification-Builder-centric | 0.50 | 0.50 |
| IntentPreservation | 0.78 | 0.80 |
| CriteriaMethodAlignment | 0.75 | 0.77 |
| auto_verifiable | 100% | 71% |
| automatable | 71% | 79% |
| human_only | 94% | 82% |

### Key Finding: Shared Failure Profile

The failure profiles are remarkably similar across architectures. ClarificationRelevance is the biggest failure source on BOTH (25 serial, 23 single). The silo problem (PipelineCoherence) has only 2 failures on each — not the bottleneck we expected.

| Evaluator | Serial | Single | Architecture-Specific? |
|---|---|---|---|
| ClarificationRelevance | 25 | 23 | No — Review prompt |
| CategoryMatch | 5 | 10 | Yes — single worse |
| IntentExtraction | 3 | 7 | Yes — single worse |
| JSONValidity_parser | 3 | 6 | Yes — single worse |
| PipelineCoherence | 2 | 2 | No — identical |

---

## Next Prompt Changes (Decided)

Based on the data, the next iteration should be a combined update before pivoting to verification pipeline implementation:

### 1. Review prompt v3 (both architectures)
- Make clarification questions target the Verification Builder's specific operationalization assumptions
- Biggest failure count (25 serial, 23 single), 10% composite weight
- Architecture-agnostic fix

### 2. Single backend JSON discipline (single only)
- Add explicit "Return ONLY raw JSON, no markdown fences" to each conversation turn
- 6 parser JSON failures cascading downstream
- Architecture-specific fix

### What We're NOT Doing (and why)
- Serial coherence instructions — PipelineCoherence only has 2 failures. The agents are already building on each other 97% of the time. Don't fix what isn't broken.
- Further prompt iteration beyond these two changes — verification pipeline implementation will reshape the eval framework. Further tuning has diminishing returns until verification is implemented.

---

## Backlog (8 items)

1. Migrate all eval data storage to DynamoDB
2. Build swarm backend architecture
3. Review and expand golden dataset (including fast eval subset)
4. Eval runner resume/checkpoint support
5. Deprecated and misplaced file cleanup
6. Code quality review (non-prompt)
7. Verification pipeline via MCP tools (HIGH PRIORITY — see `docs/research/mcp-verification-pipeline.md`)
8. Evaluator pipeline review — replace deterministic with LLM judges where data shows low agreement

---

## What the Next Agent Should Do

### Immediate (this session or next)
1. Draft Review prompt v3 — targeted clarification questions
2. Update single backend prompt with JSON discipline instructions
3. Deploy prompt changes via CloudFormation (`infrastructure/prompt-management/template.yaml`)
4. Run both architectures with new prompts: serial + single, both with `--judge`
5. Update eval-run-log.md and architecture-insights.md with results

### After prompt iteration
6. Begin verification pipeline implementation (backlog item 7)
   - Start with 3 free MCP servers: `server-fetch`, `mcp-brave-search`, `mcp-playwright`
   - Wire into Verification Builder and categorizer via Strands `MCPClient`
   - Build verification execution agent
   - See `docs/research/mcp-verification-pipeline.md` for full plan

### Key Files
- `infrastructure/prompt-management/template.yaml` — Bedrock Prompt Management (add review v3)
- `backend/calledit-backend/handlers/strands_make_call/backends/single.py` — Single backend prompt
- `backend/calledit-backend/handlers/strands_make_call/eval_runner.py` — Eval runner with `--backend` and `--judge`
- `eval/dashboard/` — Dashboard code
- `docs/project-updates/eval-run-log.md` — Append run results here
- `docs/project-updates/architecture-insights.md` — Update with new findings
- `.kiro/steering/eval-run-capture.md` — Steering doc that auto-triggers updates

### Key Context
- The eval framework is the portfolio centerpiece — the verification pipeline will extend it, not replace it
- Composite score weights: IntentPreservation 25%, CriteriaMethodAlignment 25%, PipelineCoherence 15%, IntentExtraction 10%, CategorizationJustification 10%, ClarificationRelevance 10%, CategoryMatch 2.5%, JSONValidity 2.5%
- Do NOT use "VB" as an abbreviation in prose — always write "Verification Builder" in full
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
- TTY errors: stop immediately and ask the user to run the command
