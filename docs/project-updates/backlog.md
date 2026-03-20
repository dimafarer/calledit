# CalledIt Backlog

Items identified during development that aren't urgent but should be addressed.

---

## 1. Migrate All Eval Data Storage to DynamoDB

**Source:** Spec 11 design review (March 17, 2026)

**Problem:** Eval data is split across local files and DDB with inconsistent coverage:
- `eval/score_history.json` (local, git-tracked) — run summaries
- `eval/reports/eval-*.json` (local, gitignored) — full reports with per-test-case scores, per-agent judge aggregates, evaluator groups, Verification-Builder-centric scores
- DDB `report_summary#SUMMARY` — run summaries (but missing LLM judge aggregates)
- DDB `test_result#`, `agent_output#`, `judge_reasoning#`, `token_counts#` — per-test-case data

The full eval report (including per-agent judge averages, evaluator groups, and Verification-Builder-centric composite score) only lives in local JSON. DDB's `report_summary` doesn't include these fields. Running the dashboard from a different machine without the local files loses this data.

**What to do:**
- Write the complete report summary to DDB (add LLM judge aggregates, `vb_centric_score`, `evaluator_groups`, `skipped_evaluators` to `write_run_metadata`)
- Store the full eval report blob in DDB or S3 (the per-test-case detail is large — may warrant S3 with a DDB pointer)
- Keep local files as cache/fallback but make DDB the source of truth
- Update the data loader to prefer DDB data over local when both exist (it already does this for run summaries, extend to full reports)

**References:**
- Decision 29: Local eval results (not DynamoDB — yet)
- Decision 34: DynamoDB for eval reasoning capture
- Decision 38: Storage — git now, S3 later

---

## 2. Review and Expand Golden Dataset

**Source:** Ongoing eval iteration (March 14-17, 2026)

**Problem:** The golden dataset (v3.1) has ~25 test cases. As the eval framework matures with 6 LLM judges and architecture comparison, the dataset needs review:
- Are there enough predictions per category to draw meaningful conclusions?
- Are the ground truth metadata fields (`verifiability_reasoning`, `date_derivation`, `verification_sources`, etc.) still accurate after the Verification Builder v2 operationalization changes?
- Do we have enough fuzziness level 0 (control) cases where the ReviewAgent should find nothing to clarify?
- Are the 5 "coherence anchor" predictions (complete expected outputs for all 4 agents) still representative?

**What to do:**
- Audit existing predictions against the current prompt versions (parser v1, categorizer v2, Verification Builder v2, review v2)
- Add predictions targeting known weak spots (CriteriaMethodAlignment at 0.73 — what types of predictions score lowest?)
- Add more fuzziness level 0 controls
- Expand to ~50 predictions (Decision 38 threshold before moving to S3)
- Re-derive expected categories from ground truth metadata if the 4-category system (Decision 33) is adopted
- Create a curated "fast eval" subset (~15-20 predictions) that covers all 3 categories, multiple fuzziness levels, and the coherence anchors — enough to catch regressions without running the full 68-prediction suite with 6 LLM judges (~470 model calls). The eval runner already supports `--name` filtering; a named subset list or `--subset fast` flag would make this a one-liner

**References:**
- Decision 31: Ground truth metadata per prediction
- Decision 32: Clean break from v1 dataset
- Decision 33: Future 4-category system
- Decision 35: Lightweight expected outputs
- Decision 36: Fuzziness level 0 (control cases)
- Decision 37: Cross-agent coherence as first-class concern
- Decision 38: Storage — git now, S3 later


---


## 3. Build Swarm Backend Architecture

**Source:** Spec 10 design (March 17, 2026) — Task 10 marked optional

**Problem:** The pluggable backend system has serial and single backends implemented, but the swarm backend (collaborative multi-round agents) was deferred as optional in Spec 10. The backend interface and output contract are ready — adding a swarm backend is just dropping a new module in `backends/`.

**What to do:**
- Create `backends/swarm.py` implementing `run()` and `metadata()`
- Use Strands Swarm pattern with multiple collaborating agents
- Record `collaboration_rounds` in output metadata
- Test against golden dataset and compare with serial/single using the eval framework
- The PipelineCoherence evaluator will be especially interesting here — swarm agents share context differently than serial or single

**References:**
- Spec 10 Requirement 5: Swarm Backend
- Decision 49: Architecture backend abstraction
- Decision 55: Pluggable backend with flexible output contract


---

## 4. Eval Runner Resume/Checkpoint Support

**Source:** Spec 11 comparative eval runs (March 18, 2026)

**Problem:** The eval runner writes the report and score_history entry only after all test cases complete. A full judge run with 68 test cases and 6 LLM judges takes 60+ minutes. If the run gets interrupted (system shutdown, network issue, throttling), all progress is lost and the entire run must be restarted from scratch.

**What to do:**
- Add per-test-case checkpointing — write each test case result to a checkpoint file as it completes
- Add a `--resume` flag that reads the checkpoint file and skips already-completed test cases
- On successful completion, write the full report as normal and clean up the checkpoint file
- Checkpoint file should include the run config (backend, prompt versions, dataset version) so resume validates it's continuing the same run
- Consider also writing partial results to DDB as each test case completes (the reasoning store already does this, but the report summary only writes at the end)

**References:**
- Decision 50: Isolated single-variable testing (long runs are the norm now)
- Backlog item 1: Migrate all eval data storage to DDB (partial writes would help here too)

---

## 5. Deprecated and Misplaced File Cleanup

**Source:** Ongoing observation (March 18, 2026)

**Problem:** The project has accumulated files from earlier iterations that are no longer used or are in the wrong location. Examples likely include old handler files that were superseded (e.g., `make_call_stream_simple.py` vs the current Strands streaming handler), archived datasets still in the main tree, one-off scripts in handler directories, and build artifacts that shouldn't be tracked. This creates confusion for both humans and agents trying to understand the project structure.

**What to do:**
- Audit every file in the project tree against what's actually imported/used
- Move deprecated files to `docs/historical/` or delete them
- Verify SAM template handler references match actual file locations
- Check for orphaned test files, one-off scripts, and experiment notebooks that belong in `experiments/` or `historical/`
- Clean up `.gitignore` to ensure build artifacts and generated files aren't tracked
- Verify `__init__.py` files are present where needed and absent where not

---

## 6. Code Quality Review (Non-Prompt)

**Source:** Ongoing observation (March 18, 2026)

**Problem:** As the codebase evolved through 10+ specs, code quality debt has accumulated separately from prompt quality (which the eval framework handles). This includes dead code paths, unused imports, inconsistent error handling patterns, duplicated utility functions, and naming inconsistencies (e.g., legacy "prediction" terminology mixed with current "call" terminology in backend code).

**What to do:**
- Run a linter/type checker across the Python backend (mypy, ruff, or flake8) and fix issues
- Identify dead code paths — functions that are defined but never called
- Look for duplicated utility logic across handlers (e.g., JSON parsing helpers, DDB access patterns)
- Audit error handling consistency — some handlers use structured error responses, others raise raw exceptions
- Check for naming consistency — the frontend moved from "prediction" to "call" terminology but backend code may still mix both
- Review import hygiene — unused imports, circular import risks, sys.path hacks that could be cleaned up
- This is separate from prompt review (handled by the eval framework) — this is pure code quality

---

## 7. Verification Pipeline via MCP Tools

**Source:** Architecture insight + MCP ecosystem research (March 18, 2026)
**Priority:** High — this is the key enabler for the entire verification use case
**Research:** See `docs/research/mcp-verification-pipeline.md` for full ecosystem analysis

**Problem:** The Verification Builder currently writes verification plans (criteria, sources, steps) that describe how to verify a prediction, but there's no pipeline that actually executes those plans. The Verification Builder is guessing what tools might exist. Meanwhile, Decision 57 already flagged that tools should be architecture-agnostic.

**Key Insight:** If verification tools are implemented as MCP servers, both the Verification Builder and the verification execution pipeline see the exact same tool registry via Strands' native `MCPClient.list_tools_sync()`. This means:
- The Verification Builder references real, available tools when writing verification plans
- The verification pipeline directly executes the plan using the same tools
- Adding a new MCP server immediately makes it available to both planning and execution
- The categorizer's routing becomes more accurate because it can check the tool registry
- This naturally implements the tool graduation pattern from Decision 18

**Recommended Starting Stack (all free, open-source):**
1. `@modelcontextprotocol/server-fetch` — fetch any URL, no API key needed. Covers URL-based verification
2. `@nicobailon/mcp-brave-search` — web search, free tier 2,000 queries/month (free API key from brave.com)
3. `@nicobailon/mcp-playwright` — full browser automation, no API key. Covers dynamic web content

**Future Expansion:**
- Jentic (single MCP server aggregating thousands of APIs) — evaluate as a scaling path
- Weather API MCP server (OpenWeatherMap free tier, 1,000 calls/day)
- Sports scores API MCP server
- Financial data API MCP server (Alpha Vantage free tier)

**What to do:**
- Start with the 3 free MCP servers above, connected via Strands `MCPClient`
- Wire the tool registry into the Verification Builder's context
- Wire the same registry into the categorizer for routing decisions
- Build the verification execution pipeline as a Strands agent that receives a plan and executes it
- Evaluate Jentic as a single-server replacement that scales to more APIs

**References:**
- Decision 18: Simplify to 3 verifiability categories (tool graduation pattern)
- Decision 19: Tool registry in DynamoDB
- Decision 20: Web search as first registered tool
- Decision 57: Tools should be architecture-agnostic (future)
- `docs/research/mcp-verification-pipeline.md` — full research doc

---

## 8. Evaluator Pipeline Review — Replace Deterministic with LLM Judges Where It Makes Sense

**Source:** Architecture comparison analysis (March 18, 2026)
**Priority:** High — consistency of measurement matters more than cost savings

**Problem:** The evaluator pipeline has a mix of deterministic evaluators and LLM judges. The deterministic evaluators (CategoryMatch, JSONValidity, ClarificationQuality, Convergence) are cheap and fast but shallow — they check surface-level properties (label match, JSON parse, keyword presence, category match) without understanding whether the output is actually good. This creates inconsistent measurement: some dimensions are evaluated by reasoning, others by string matching.

The data from Runs 13-14 shows that deterministic evaluators often pass test cases that LLM judges fail. The gap between deterministic and judge scores is where the real quality issues hide. Running fewer, more expensive runs with consistent LLM judge coverage across the board would produce more trustworthy data than many cheap runs with mixed measurement quality.

**Current evaluators and proposed changes:**

| Evaluator | Current Type | Proposed | Rationale |
|---|---|---|---|
| CategoryMatch | Deterministic | Keep as cheap regression check, add LLM judge version | CategorizationJustification already covers this better — CategoryMatch stays as a fast sanity check |
| JSONValidity | Deterministic | Keep deterministic | This is genuinely a structural check — either it parses or it doesn't. LLM judge adds no value here. |
| ClarificationQuality | Deterministic (keyword) | Replace with LLM judge | Keyword matching is too brittle. ClarificationRelevance (LLM judge) already exists and is better — retire ClarificationQuality entirely |
| Convergence | Deterministic (category match) | Replace with LLM judge or embedding similarity | Current check is too shallow (category label match). Should measure whether round 2's verification plan actually converged toward the base prediction's intent. Embedding similarity for continuous score, LLM judge for rich assessment |
| ReasoningQuality | LLM judge (generic) | Retire or refocus | Superseded by the targeted per-agent judges (IntentExtraction, CategorizationJustification, ClarificationRelevance). The generic "is the reasoning good?" question is less useful than "did this specific agent do its specific job?" |

**What to do:**
- Keep all deterministic evaluators running alongside LLM judges for now — don't retire anything yet
- Use the Coherence View dashboard page to measure per-evaluator agreement rates between deterministic and LLM judges across multiple runs
- When the data shows a deterministic evaluator agrees with its LLM judge counterpart 90%+ of the time, that deterministic evaluator is a trustworthy cheap proxy — use it for quick iteration runs, save the judge for milestone runs
- When agreement is low (e.g., ClarificationQuality vs ClarificationRelevance), the deterministic evaluator is misleading and should be retired or replaced
- Build a Convergence LLM judge that assesses whether clarification moved the verification plan toward the correct one (embedding similarity as fast score, LLM judge for rich assessment)
- Keep JSONValidity as deterministic (it's genuinely structural)
- The goal: a tiered run strategy based on data
  - Quick runs: fast subset (~15 predictions) + deterministic only (5 min, near-free)
  - Standard runs: full dataset + deterministic + only judges without a high-agreement proxy (30 min)
  - Full runs: full dataset + all judges (60+ min, milestone comparisons only)
- This connects to backlog item 3 (golden dataset fast eval subset) — both reduce run cost

**References:**
- Decision 30: Two-tier evaluator strategy validated
- Decision 44: Verification criteria is the primary eval target
- Decision 48: Per-agent evaluators
- `docs/project-updates/architecture-insights.md` — shared failure profile showing deterministic/judge disagreements

---

## 9. Per-Architecture Prompt Management and Prompt Change Visualization

**Source:** Architecture comparison analysis (March 19, 2026)
**Priority:** Medium — needed as architectures diverge

**Problem:** Currently all architectures share the same 4 prompts from Bedrock Prompt Management. As architectures diverge (serial may need coherence instructions, single may need stronger JSON discipline), they'll need separate prompt variants. Additionally, the dashboard shows prompt version numbers (e.g., "review v2 → v3") but not what actually changed in the prompt text. The eval run reports identify runs by timestamp, not by a semantic description of what was tested.

**What to do:**
- Support per-architecture prompt variants in Prompt Management (e.g., `calledit-review-serial`, `calledit-review-single`) when architectures need different instructions
- Add prompt diff visualization to the dashboard — when comparing two runs with different prompt versions, show the actual text diff (or at least a summary of what changed)
- Add a "run description" field to eval reports so runs can be labeled with semantic meaning (e.g., "review v3 — targeted clarification questions") instead of just timestamps
- Track prompt augmentations — if any code adds instructions beyond what's in Prompt Management, that's an untracked change and should be flagged or moved into Prompt Management
- The principle: Prompt Management is the single source of truth for all prompt text. No untracked augmentations in backend code.

**References:**
- Decision 28: CloudFormation for Prompt Management
- Decision 50: Isolated single-variable testing
- Decision 59: Combined prompt update before verification pipeline pivot
