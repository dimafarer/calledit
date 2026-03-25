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
**Status:** SUPERSEDED by Decision 124 (March 25, 2026) — golden dataset will be reshaped for v4 as part of the eval framework redesign. Remove v3 fields (3-category system, tool_manifest_config), add v4 fields (expected_verifiability_score_range, expected_verification_outcome, smoke_test flag). Smoke test subset of ~12 cases per Decision 125. See Project Update 30.

**References:**
- Decision 124: Golden Dataset Reshape for v4
- Decision 125: Smoke Test Subset Strategy


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
**Status:** Split into 6 specs (March 21, 2026):
- Spec A1 (`verification-teardown-docker`): Old system teardown + Docker Lambda — COMPLETE (March 21)
- Spec A2 (`mcp-tool-integration`): MCP Manager + tool-aware agents — COMPLETE (March 21, deployed)
- Spec B1 (`verification-execution-agent`): Verification Executor agent — next (Decision 75)
- Spec B2 (`verification-triggers`): DynamoDB storage, immediate trigger, EventBridge scanner — after B1
- Spec B3 (`verification-eval-integration`): Eval framework `--verify` mode + 4 new evaluators — after B1
- Spec C: Future expansion (additional MCP servers, tool graduation)

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
**Status:** SUPERSEDED by Decision 122 (March 25, 2026) — the v4 eval framework redesign takes the opposite approach. Instead of replacing deterministic with LLM judges, v4 starts with 6 deterministic evaluators and only 2 targeted LLM judges (intent preservation + plan quality). Expand with intention based on data, not speculation. See Project Update 30.

**References:**
- Decision 122: Tiered Evaluator Strategy for v4
- Decision 126: Creation Agent Priority Metrics

---

## 10. Pre-Graph (v1) Backend Through Eval Framework

**Source:** Agent review session (March 20, 2026)
**Priority:** Medium — validates whether the current graph architecture is actually an improvement

**Problem:** The pre-graph v1 architecture (separate graph + standalone ReviewAgent + hardcoded HITL loop) may have produced better subjective results than the current v2 graph architecture. The pluggable backend system (Decision 55) was built exactly for this comparison — drop a `backends/pregraph.py` module that runs the old v1 logic with the same output contract, and the eval framework scores it identically against serial and single.

**What to do:**
- Create `backends/pregraph.py` implementing `run()` and `metadata()`
- Wire the v1 prediction pipeline logic (pre-graph architecture) into the backend interface
- Run through the eval framework with the same golden dataset and all 6 judges
- Compare against serial (Run 15) and single (Run 16) baselines
- This is a data-driven answer to "was v1 actually better?" rather than relying on subjective feel

**References:**
- Decision 49: Architecture backend abstraction
- Decision 55: Pluggable backend with flexible output contract
- Decision 41: Eval framework as portfolio centerpiece

---

## 11. Composite Score Weight Recalibration from Verification Outcome Data

**Source:** Agent review session (March 20, 2026)
**Priority:** Deferred — depends on verification pipeline implementation

**Problem:** The current Verification-Builder-centric composite score weights (IP 25%, CMA 25%, PipelineCoherence 15%, IntentExtraction 10%, CategorizationJustification 10%, ClarificationRelevance 10%, CategoryMatch 2.5%, JSONValidity 2.5%) were a judgment call, not derived from data. The composite score is directionally useful but not a reliable optimization target.

**What to do:**
- After the verification pipeline is implemented and producing real verification outcomes (success/failure), correlate each evaluator's scores with actual verification success rates
- Derive weights from the correlation data — evaluators that predict verification success get higher weight
- Replace the judgment-based weights with empirically grounded ones
- This turns the composite score from "what we think matters" into "what actually predicts success"

**References:**
- Decision 53: Verification-Builder-centric composite score
- Backlog item 7: Verification pipeline via MCP tools (prerequisite)

---

## 12. Per-Architecture Prompt Management and Prompt Change Visualization

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


---

## 13. Migrate Runtime to Amazon Bedrock AgentCore

**Source:** Spec planning session (March 20, 2026), v4 Architecture Planning (March 22, 2026)
**Priority:** High — next major work after eval analysis
**Status:** V4-1 (AgentCore Foundation) COMPLETE, V4-2 (Built-in Tools) COMPLETE, V4-3a (Creation Agent Core) COMPLETE, V4-3b (Clarification & Streaming) COMPLETE, V4-4 (Verifiability Scorer) COMPLETE, V4-5a (Verification Agent Core) COMPLETE + integration tested, V4-5b (Verification Triggers) COMPLETE. V4-6 (Memory Integration) next.

**Problem:** The current SAM Lambda architecture was chosen for the class being taught (low cost for students to deploy). Now the project aims to demonstrate best-in-class agent architecture. AgentCore is purpose-built for deploying and operating AI agents with built-in observability, scaling, and lifecycle management.

**v4 Architecture Planned (Update 20):**
- Two separate AgentCore Runtimes (creation agent + verification agent) — Decision 86
- Verifiability strength score replaces 3-category system — Decision 87
- Hybrid memory model (DDB + AgentCore Memory) — Decision 88
- Three-layer eval (Strands + AgentCore + Bedrock) — Decision 89
- AgentCore Gateway for all tools — Decision 91
- Full design: `docs/project-updates/v4-agentcore-architecture.md`
- Steering guardrails: `.kiro/steering/agentcore-architecture.md`

**What to do:**
- Complete eval analysis (Update 21) first
- Then begin v4 spec creation following the 8-phase migration sequence in the architecture doc
- Phase 1: AgentCore foundation (agentcore create, dev server, basic invoke)
- Phase 2: Gateway + tools (brave_web_search, fetch as Gateway targets)
- Phase 3: Unified agent (creation + verification modes, DDB bundle contract)
- Phase 4: Verifiability scorer
- Phase 5: Memory integration (STM + LTM)
- Phase 6: Three-layer eval wiring
- Phase 7: Frontend updates (strength indicator UI)
- Phase 8: Production cutover

**References:**
- Decision 23: AgentCore Evaluations — USE
- Decision 65: Docker Lambda for MCP subprocess support (stepping stone)
- Decision 68: AgentCore as post-verification migration target
- Decisions 86-91: v4 architecture decisions


---

## 14. Add DynamoDB GSI to Replace Full Table Scans

**Source:** V4-3b design review (March 23, 2026)
**Priority:** Medium — becomes important as prediction volume grows
**Status:** COMPLETE (V4-5b) — GSI `status-verification_date-index` created on `calledit-db`. Scanner Lambda queries it.

**Problem:** The v3 verification scanner and the `list-predictions` endpoint use DynamoDB `scan` operations to find predictions. Scans read every item in the table and filter client-side, which is O(n) on table size. This works fine at demo scale (~50 predictions) but becomes expensive and slow as the table grows. The V4-3a integration test used a scan with `begins_with(PK, "PRED#pred-")` to verify DDB saves — this pattern should not carry into production queries.

**Common query patterns that need GSIs:**
1. **Predictions by user**: "Show me all predictions for user-123" — needs GSI on `user_id`
2. **Predictions by status**: "Find all pending predictions ready for verification" — needs GSI on `status` + `verification_date`
3. **Predictions by verification date**: "Find predictions due for verification today" — the EventBridge scanner needs this for efficient batch verification (currently scans the entire table)

**What to do:**
- Add a GSI with `user_id` as partition key and `created_at` as sort key — enables efficient per-user prediction listing sorted by date
- Add a GSI with `status` as partition key and `verification_date` as sort key — enables the verification scanner to query only `pending` predictions due before now, instead of scanning everything
- Update the verification scanner (V4-5) to use the status GSI instead of scan
- Update the list-predictions endpoint to use the user_id GSI instead of scan
- Add GSIs to the SAM/CloudFormation template for the `calledit-db` table
- Consider sparse GSIs (only index items with specific attributes) to minimize GSI storage cost

**References:**
- Decision 82: DynamoDB requires Decimal not Float
- V4-3a: DDB save with PK `PRED#{prediction_id}`, SK `BUNDLE`
- V4-5: Verification Agent (will need efficient pending prediction queries)
- Backlog item 13: AgentCore migration (GSIs should be added before V4-8 production cutover)
