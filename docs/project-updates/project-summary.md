# CalledIt Project Summary

A condensed narrative of the CalledIt project — from inception through v3 (Lambda-based pipeline) to v4 (AgentCore clean rebuild). Use this alongside `decision-log.md` for full context.

---

## What CalledIt Is

CalledIt is a prediction verification platform built on Amazon Bedrock AgentCore. Users make predictions ("Lakers win tonight", "it'll rain tomorrow", "S&P 500 closes above 5000 by Friday") through a mobile-first React PWA. Two specialized AI agents — a creation agent and a verification agent — collaborate through a shared DynamoDB prediction bundle to understand the user's intent, build a machine-actionable verification plan, score verifiability on a continuous 0.0–1.0 scale, and autonomously verify predictions when their verification date arrives.

The system demonstrates production-grade AI agent deployment: AgentCore Runtime for serverless agent hosting with session isolation, Cognito JWT authentication for browser-to-agent WebSocket streaming, CloudFront + S3 for the frontend, and a three-layer eval architecture (Strands Evals SDK → AgentCore Evaluations → Bedrock Evaluations) for continuous quality monitoring.

## Architecture (v4)

Two AgentCore Runtime deployments with shared infrastructure:

- **Creation Agent** — user-facing, streaming. Receives predictions via WebSocket, runs a 3-turn prompt flow (parse → plan → review), scores verifiability, supports multi-round clarification, saves structured prediction bundles to DynamoDB.
- **Verification Agent** — batch, autonomous. Triggered by EventBridge every 15 minutes via a scanner Lambda. Loads prediction bundles from DynamoDB, gathers real evidence using AgentCore Browser + Code Interpreter, produces structured verdicts (confirmed/refuted/inconclusive).

Both agents use Claude Sonnet 4 via Bedrock, AgentCore built-in tools (Browser + Code Interpreter), and Bedrock Prompt Management for versioned prompts. The prediction bundle in DynamoDB is the contract between them.

## Tech Stack

- **Frontend:** React PWA (TypeScript, Vite) served via CloudFront + private S3 (OAC)
- **Agent Runtime:** Amazon Bedrock AgentCore Runtime (two separate deployments)
- **Model:** Claude Sonnet 4 via Amazon Bedrock
- **Tools:** AgentCore Browser (Chromium in Firecracker microVM) + Code Interpreter (Python sandbox)
- **Auth:** Cognito User Pool with JWT authorization on both API Gateway HTTP API and AgentCore WebSocket
- **Storage:** DynamoDB (`calledit-v4` table with GSIs for user listing and scanner queries)
- **Prompts:** Bedrock Prompt Management with immutable versions (no hardcoded fallbacks)
- **Scheduling:** EventBridge → Scanner Lambda → Verification Agent
- **Infrastructure:** CloudFormation/SAM templates under `infrastructure/`
- **Eval:** Strands Evals SDK (local), AgentCore Evaluations (deployed), Bedrock Evaluations (production)

## Key Design Decisions

- **Two agents, not one** — different prompts, memory needs, scaling profiles, and observability. Creation scales with users, verification scales with EventBridge batch size.
- **Verifiability strength score** — continuous 0.0–1.0 score replaces the v3 3-category system. Users see a green/yellow/red indicator and can choose to clarify to improve the score.
- **Single agent, multi-turn prompts** — the creation agent runs 3 sequential prompt turns in one Strands Agent. Validated by 16 eval runs showing equivalent quality to a 4-agent serial graph, with simpler code and no silo problem.
- **Hybrid memory model** — DynamoDB for structured prediction bundles (exact fields, precise lookup), AgentCore Memory for conversational context (semantic search, user preferences). Each used for its strengths.
- **Built-in tools first, Gateway later** — AgentCore Browser + Code Interpreter cover web search, URL fetching, JS rendering, and calculations with zero external API keys. Gateway with domain-specific APIs (Brave, Alpha Vantage) is Phase 2.
- **JWT auth for browser WebSocket** — browser connects directly to AgentCore Runtime via WebSocket using Cognito JWT in the `Sec-WebSocket-Protocol` header. No SigV4 presigned URLs, no streaming proxy Lambda.
- **Spec-driven development** — 20+ specs with requirements → design → tasks, property-based testing with Hypothesis, 121 documented architectural decisions.

## Project Evolution (10 Updates)

### Update 01 (March 6): v2 Architecture Planning
Replaced the v1 two-path architecture (separate graph + standalone ReviewAgent + hardcoded HITL loop) with a unified 4-agent Strands Graph. Split into two specs: cleanup/foundation first, then the unified graph. Key decisions: clean break on WebSocket protocol, model upgrade to Sonnet 4, prompt-first approach to JSON parsing (fix prompts, not regex).

### Update 02 (March 9): Frontend v2 Alignment
Fixed frontend to work with v2 backend. Investigated streaming text issue (turned out to be stale SAM build cache, not a code bug). Wired clarification UI using existing ImprovementModal component. Confirmed LogCallButton compatibility with v2 data shape.

### Update 03 (March 9-13): Lambda SnapStart
Enabled SnapStart across all 8 Lambda functions. Cold start went from 2,441ms to 444ms (82% improvement). Fixed alias DependsOn race condition in CloudFormation. Created Strands Graph guide documentation.

### Update 04 (March 13): Category Simplification
Simplified from 5 verifiability categories to 3: `auto_verifiable`, `automatable`, `human_only`. Built tool registry in DynamoDB. Implemented web search as first registered tool. Upgraded verification agent to Sonnet 4.

### Update 05 (March 13): Eval Strategy
Evaluated 6 AWS services for prompt evaluation. Chose Bedrock Prompt Management (versioned prompts), CloudWatch GenAI Observability (per-agent metrics), and AgentCore Evaluations (span-level analysis). Skipped Bedrock Evaluations, Guardrails, and SageMaker Clarify. Designed two-tier evaluator strategy: deterministic for structural regression, LLM-as-judge for reasoning quality.

### Update 06 (March 14): Eval Framework Execution
Built the eval framework: standalone test graph, OTEL instrumentation, Bedrock Prompt Management migration (4 prompts with immutable versions), golden dataset (15 base + 5 fuzzy), 5 evaluators (4 deterministic + 1 Opus 4.6 judge), eval runner CLI, score tracking with regression detection. Baseline results showed ReviewAgent as primary improvement target (judge scores 0.3-0.55).

### Update 07 (March 14): Golden Dataset v2
Designed production-quality golden dataset with ground truth metadata per prediction (verifiability reasoning, date derivation, verification sources, objectivity assessment, verification criteria, verification steps). 45 base + 23 fuzzy predictions across 18 personas. DynamoDB eval reasoning store for full model traces. Clean break from v1 dataset.

### Update 08 (March 15): Eval Insights & Architecture Flexibility
Critical reframe: categorization is a routing hint, verification criteria quality is the real metric. Identified the silo problem (agents re-interpreting from scratch instead of building on predecessors). Proposed architecture comparison (serial vs swarm vs single agent). Integrated Strands Evals SDK. Three eval runs established baselines showing categorizer v2 tradeoffs.

### Update 09 (March 16): Dashboard v1 & Eval Reframe
Launched 6-page Streamlit eval dashboard (Trends, Heatmap, Prompt Correlation, Reasoning Explorer, Coherence View, Fuzzy Convergence). Dashboard data revealed verification criteria is the primary eval target. Defined two new evaluators: IntentPreservation and CriteriaMethodAlignment. Established the "operationalize vs acknowledge" framework for vague predictions.

### Update 10 (March 17): Verification Builder Iteration & Architecture Vision
Verification Builder v2 prompt pushed IntentPreservation to 0.82 (past 0.80 target). CriteriaMethodAlignment improved to 0.74. Completed per-agent LLM judge coverage (6 judges total). Built pluggable backend system (serial + single backends). Ran 12 eval iterations with isolated single-variable testing methodology. Created consolidated decision log (57 decisions).

### Update 11 (March 18-19): Comparative Eval Dashboard & Architecture Analysis
Built 7-page comparative eval dashboard with architecture comparison, pipeline-ordered heatmap, and coherence view. Ran first full architecture comparison (serial vs single, all 6 judges). Key finding: shared failure profile — ClarificationRelevance is the biggest failure source on both architectures. Review v3 produced the biggest single-prompt gain in the project (+13% serial, +21% single). Architectures essentially tied on composite score.

### Update 12 (March 20): Production Prompt Management Wiring
Discovered production was running stale v1 hardcoded prompts — Lambda lacked `bedrock-agent:GetPrompt` IAM permission and `PROMPT_VERSION_*` env vars. Added both to SAM template, pinned to eval-validated versions (parser 1, categorizer 2, VB 2, review 3). Updated all 4 fallback constants to match latest Prompt Management text. Deployed and confirmed new prompts are live. Categorizer now produces v2 reasoning but conservatively labels predictions without registered tools — verification pipeline is the fix.

### Update 13 (March 20): Verification Pipeline Planning & Spec Split
Planned the MCP verification pipeline build. Split the combined 17-task spec into Spec A1 (teardown + Docker Lambda) and Spec A2 (MCP Manager + tool-aware agents). Key tradeoff: Docker Lambda loses SnapStart (cold starts ~2-5s slower), accepted because MCP subprocess startup would invalidate SnapStart anyway and AgentCore migration is planned. Version bump to v3 planned after Spec A2. Eight new decisions (61-68) covering production prompts, composite weight grounding, spec split, Docker Lambda, SnapStart loss, v3 versioning, and AgentCore migration path.

### Update 14 (March 20-21): Verification Teardown & Docker Lambda (Spec A1)
Tore down old verification system (EventBridge, S3 logs, standalone agent). Switched MakeCallStreamFunction to Docker Lambda with Python 3.12 + Node.js LTS. Hit `tar: command not found` on AL2023 base — fixed with `dnf install`. Orphaned S3 bucket (non-empty, harmless). Pipeline confirmed working with Docker Lambda.

### Update 15 (March 21): MCP Tool Integration (Spec A2)
Built MCP Manager module, wired into prediction graph, made all 4 agents tool-aware. Debugged MCP server package names (npm vs Python), JSON double-brace issue (`.format()` → `.replace()`). Beach day test confirmed end-to-end: categorizer routes to `auto_verifiable`, VB references `brave_web_search` by name, review asks tool-aware questions. Cold start ~30s validates AgentCore migration priority.

### Update 16 (March 21): Spec B Planning & A2 Cleanup
Completed A2 cleanup (Prompt Management VB v3 + Review v4 deployed, SAM env vars bumped, v3.0.0 in CHANGELOG). Planned Spec B (verification execution agent) — user caught that most predictions can't be verified immediately (verification_date matters), and that eval should fold into existing framework. Split Spec B into B1 (executor agent, 5 reqs), B2 (triggers/storage, 3 reqs), B3 (eval integration, 4 reqs).

### Update 17 (March 21): Spec B1 — Verification Executor Agent
Built and tested the Verification Executor Agent. Single Strands agent that invokes MCP tools (brave_web_search, fetch) to verify predictions. Lazy singleton pattern avoids MCP connections at import time. `run_verification()` entry point never raises — returns inconclusive on any error. Established no-mocks policy: all tests hit real Bedrock + MCP servers. 24 pure + 7 integration tests, all passing. Agent correctly confirmed/refuted Christmas 2025 day-of-week predictions using brave_web_search.

### Update 18 (March 21): Spec B2 — Verification Triggers & Storage
Built DynamoDB storage utility and EventBridge verification scanner. Production verification fully decoupled from prediction creation (Decision 81). Scanner runs every 15 minutes, finds eligible predictions, verifies them. Float→Decimal conversion needed for DynamoDB (Decision 82). 13 tests passing against real DynamoDB.

### Update 19 (March 22): Spec B3 — Verification Eval Integration
Extended the eval framework with `--verify` mode and 4 new verification alignment evaluators (ToolAlignment, SourceAccuracy, CriteriaQuality, StepFidelity). Golden dataset extended with `verification_readiness` field (10 immediate, 35 future). Delta classification categorizes plan-execution mismatches as `plan_error`, `new_information`, or `tool_drift`. New Verification Alignment dashboard page. End-to-end verified: base-002 confirmed as Friday with confidence 0.9.

### Update 20 (March 22): v4 AgentCore Architecture Planning
Planned the v4 clean rebuild on Amazon Bedrock AgentCore. Three architectural insights: (1) two separate agents (creation + verification) with shared infrastructure, (2) verifiability strength score replacing 3-category system, (3) three-layer eval architecture (Strands Evals → AgentCore Evaluations → Bedrock Evaluations). Designed hybrid memory model — DynamoDB for structured prediction bundles, AgentCore Memory for conversational context and user preferences. Fixed Prompt Management versions (VB v3 + Review v4 were missing). Created AgentCore steering doc with pushback protocol. Chose single agent with multi-turn prompts based on 16 eval runs of experimental data (Decision 94). Built-in tools first — Browser + Code Interpreter, Gateway later (Decision 93). 11-spec plan with dependency graph, all ≥88% confidence. V4-1 spec (AgentCore Foundation) created with requirements, design, and tasks. Ten new decisions (86-95).

## The Eval Framework (Portfolio Centerpiece)

The eval framework demonstrates production-grade AI quality assurance across three layers:

**Layer 1 — Strands Evals SDK (Inner Loop):** Local eval runner invoking deployed AgentCore agents via HTTPS + JWT auth. Tiered evaluator strategy: 6 fast deterministic checks (every run, instant) + 2 targeted LLM judges (intent preservation, plan quality — on-demand). Smoke test subset (12 cases) for fast iteration, full suite (45 cases) for milestones. Structured run metadata enables multi-dimensional comparison: model, prompt versions, git commit, feature flags (LTM/STM/tools).

**Layer 2 — AgentCore Evaluations (Bridge):** Deployed agent evaluation with span-level trace analysis. Online eval (every Nth request) + on-demand eval (triggered runs). Production-like traffic patterns on real AgentCore Runtime. (Planned — V4-7a-4)

**Layer 3 — Bedrock Evaluations (Outer Loop):** Production quality monitoring at scale. LLM-as-judge on production samples, human evaluation for edge cases, trend monitoring over days/weeks. (Planned — future)

The dashboard enables multi-dimensional comparison: filter and overlay runs by model, prompt versions, git commit, and feature flags. Designed to support future experiments (LTM integration, STM between clarification rounds, model swaps).

For the full technical deep dive — evaluator rubrics, dataset design, calibration logic, historical baselines, and cost breakdown — see [docs/eval-framework-deep-dive.md](docs/eval-framework-deep-dive.md).

Key artifacts (v4):
- Golden dataset v4.0 (45 base + 23 fuzzy predictions, schema 4.0, 12 smoke test cases)
- 6 Tier 1 deterministic evaluators (schema validity, field completeness, score range, date resolution, dimension count, tier consistency)
- 2 Tier 2 LLM judges (intent preservation — priority #1, plan quality — priority #2)
- Structured run metadata: model_id, prompt_versions, git_commit, agent_runtime_arn, features dict
- First baseline: 12/12 smoke cases, 100% Tier 1 pass rate (March 25, 2026)
- CLI eval runner with tiered execution: smoke / smoke+judges / full
- Separate eval experiments per agent (creation + verification) with shared dashboard

### Update 22 (March 22): V4-1 AgentCore Foundation Complete
First v4 spec executed. Installed AgentCore toolkit, scaffolded `calleditv4/` project, wrote entrypoint with Claude Sonnet 4 and error handling, validated via `agentcore dev` + `agentcore invoke --dev`. Tightened no-mocks policy — mocks now require proven value + explicit user approval (Decision 96).

### Update 23 (March 22): V4-2 Built-in Tools Complete
Wired AgentCore Browser and Code Interpreter into the v4 agent entrypoint (~10 lines of code). Browser validated with Seattle weather search (22 tool calls, 321s). Code Interpreter validated with compound interest calculation (correct, fast). Discovered playwright + nest-asyncio are required deps of strands_tools.browser (Decision 97).

### Update 24 (March 23): V4-3a Creation Agent Core Complete
First v4 spec with real business logic. Implemented the 3-turn creation flow: prediction text → parse (extract claim, resolve dates with timezone awareness) → plan (build verification plan with tool references) → review (score verifiability 0.0-1.0 + identify assumptions for clarification). Used Strands `structured_output_model` with Pydantic models for type-safe extraction at each turn. Ported v3 `prompt_client` with Decision 98 fallback behavior. Deployed 3 new CloudFormation prompts. DynamoDB save with float→Decimal conversion. 133 automated tests, all 5 integration tests passed. Three new decisions: 98 (dev fails clearly, prod falls back), 99 (3 turns not 4), 100 (LLM-native date resolution).

## Current State (March 23, 2026)

- v3.0.0 released — MCP-powered verification pipeline with Docker Lambda
- v4 architecture planned — clean rebuild on Amazon Bedrock AgentCore (zero technical debt)
- Production prompts: parser v1, categorizer v2, VB v3 (tool-aware), review v4 (tool-aware) — all versions now confirmed in Prompt Management
- v4 design: two separate AgentCore agents (creation + verification), verifiability strength score (replaces categories), hybrid memory model (DDB + AgentCore Memory), three-layer eval (Strands + AgentCore + Bedrock)
- Eval framework: 15 evaluators, 8-page dashboard, `--verify` mode, 17 eval runs
- Golden dataset: 45 base + 23 fuzzy predictions, 10 marked `immediate` for verification
- 17 specs complete (A1 + A2 + B1 + B2 + B3), v4 specs pending
- AgentCore steering doc created with pushback protocol and documented deviations
- v4 spec plan: 11 specs, 36 requirements, ~80-92 tasks, all ≥88% confidence (Decision 92)
- V4-1 spec (AgentCore Foundation) COMPLETE: `calleditv4/` scaffolded, entrypoint working, dev server validated, 6 tests passing
- V4-2 spec (Built-in Tools) COMPLETE: Browser + Code Interpreter wired, both validated via agentcore invoke --dev, 15 tests passing
- V4-3a spec (Creation Agent Core) COMPLETE: 3-turn creation flow working end-to-end, 133 v4 tests passing, all 5 integration tests passed
- No-mocks policy tightened: mocks require proven value + explicit user approval (Decision 96)
- 100 architectural decisions documented
- Next: V4-3b (Clarification & Streaming) — fully specced (requirements + design + tasks), ready to execute

### Update 25 (March 23): V4-3b Clarification & Streaming Complete
Evolved the V4-3a synchronous entrypoint into an async streaming generator with multi-round clarification support. Handler now yields turn-by-turn stream events (`flow_started`, `turn_complete` ×3, `flow_complete`) instead of returning a single JSON string. Added clarification routing: user answers reviewer questions → agent re-runs 3-turn flow with enriched context → DDB `update_item` (not new item). Clarification cap of 5 rounds (configurable via env var). User timezone from frontend payload (Decision 101) takes priority over server timezone. Three new pure functions in `bundle.py` (`load_bundle_from_ddb`, `build_clarification_context`, `format_ddb_update`). Split `ConditionalCheckFailedException` handling per Req 7.4/7.5. V4-2 test regression fixed for async handler. 136 automated tests passing. No new decisions — all implementation followed existing decisions (94, 96, 98-101).

### Update 26 (March 23): V4-4 Verifiability Scorer Complete
Extended PlanReview structured output with score tier metadata, per-dimension assessments, and LLM-generated guidance text. First design was over-engineered (separate scorer.py module with regex parsing) — simplified to let the LLM produce everything via structured output. New `DimensionAssessment` Pydantic model, 4 new PlanReview fields (`score_tier`, `score_label`, `score_guidance`, `dimension_assessments`), deterministic `score_to_tier()` function for color/icon mapping. No legacy category — clean break from v3 (Decision 103). Updated plan-reviewer prompt in CloudFormation. Strands structured_output_model populated new fields correctly even before prompt deploy. 148 tests passing.

### Update 30 (March 25): V4-7a Eval Framework Redesign + Execution
Research session redesigned the eval framework from first principles for v4. Audited v3 (17 evaluators, 12 LLM judges, 60+ min per run) and Strands Evals SDK best practices. Established tiered evaluator strategy: 6 deterministic + 2 LLM judges (down from 17). Golden dataset reshaped to v4-native (schema 4.0, removed 3-category system, added verifiability score ranges, 12 smoke test cases). Built creation agent eval runner with AgentCore HTTPS + JWT auth backend. First baseline: 12/12 smoke cases pass all Tier 1 evaluators (100% structural correctness). Structured run metadata captures model_id, prompt_versions, git_commit, features dict for future experiment comparison. Seven new decisions (122-127).

### Update 30 (continued — V4-7a-3 verification agent eval, March 25-26, 2026)
Built and ran the verification agent eval framework (V4-7a-3). Key design discoveries: prediction verification has four timing modes (`immediate`, `at_date`, `before_date`, `recurring`) — evaluators scoped to `immediate` only for V4-7a-3, other modes additive (Decision 130, backlog item 0). Two-source architecture: `--source golden` writes to `calledit-v4-eval` table with `table_name` payload override, `--source ddb` queries live predictions. Verification agent uses SigV4 (not JWT) — it's a batch agent. Handler returns summary only; full verdict (evidence + reasoning) read back from DDB. First smoke baseline: 100% Tier 1 pass rate on 2 cases. base-002 (Christmas Friday) confirmed with confidence 1.0. base-011 (Python 3.13) returned inconclusive — real agent quality signal. Decision 130 added.

### Update 31 (March 26): V4-7a Eval Completion + Dashboard + Production Deploy
Completed V4-7a-3 with smoke+judges and full tier runs. Full baseline (7 cases): verdict_accuracy=0.43, evidence_quality=0.46, all Tier 1=1.00. Key finding: 4/7 failures caused by Browser tool inability. Built V4-7a-4: DDB report store (resolves backlog item 1), calibration runner (first baseline: calibration_accuracy=0.50), React dashboard in frontend-v4. Deployed to production with API Gateway + Cognito JWT auth. SnapStart on all 5 v4 Lambdas using AutoPublishAlias (Decision 135). Vite dev proxy for local DDB access (Decision 136). Six new decisions (131-136). Backlog item 16 added (tool action tracking).

## Current State (March 26, 2026)

### Update 32 (March 27): Dark Theme Unification + Dashboard UX Fixes
UX polish session without a formal spec. Fixed eval dashboard table column alignment (nested `<tbody>` bug + inconsistent score key ordering). Unified the entire frontend on a dark slate theme (`#0f172a` background). Replaced gradient navigation buttons with clean underline tabs. Added collapsible metadata accordion to dashboard. Deployed to production. Two new decisions (137-138).

### Update 33 (March 27): Verification Modes + TTY Fix + Prompt Pinning
Three wins in one session. (1) Resolved the long-standing TTY/command execution issue — Amazon Q CLI shell integration conflicted with Kiro's PROMPT_COMMAND output capture; fixed with TERM_PROGRAM guards in ~/.bashrc. (2) Pinned all prompt versions to numbered defaults (never DRAFT) for eval traceability. (3) Implemented all four verification modes (immediate, at_date, before_date, recurring) — resolving backlog item 0. Verification planner classifies mode, plan reviewer confirms. Scanner has mode-aware scheduling with recurring interval checks. Golden dataset expanded 45→54 cases. Three new evaluators + per-mode aggregate breakdowns in both eval runners. Two new decisions (139-140).

## Current State (March 27, 2026)

- v4 production COMPLETE — full MVP + eval dashboard + verification modes deployed
- Eval dashboard live at `https://d2fngmclz6psil.cloudfront.net/eval`
- Four verification modes supported: immediate, at_date, before_date, recurring
- Three eval frameworks: creation (IP=0.88, PQ=0.57), verification (VA=0.43, EQ=0.46), calibration (CA=0.50)
- Golden dataset: 54 base + 23 fuzzy predictions (schema 4.0, 12 smoke test cases)
- DDB report store: `calledit-v4-eval-reports` table, reports include per-mode breakdowns
- All prompts pinned to numbered versions (parser:2, planner:2, reviewer:3, executor:2)
- Frontend: unified dark theme, underline tab navigation
- TTY/command execution issue resolved — Amazon Q CLI guard in ~/.bashrc
- 142 architectural decisions documented across 33 project updates
- Next: full eval baselines with mode data, prompt iteration on mode classification, verification planner self-report (backlog 15)

### Update 34 (March 30): DDB Cleanup + Eval Isolation + Brave Search
Major infrastructure and tooling session. (1) Investigated "only 5 predictions visible" — traced to v3 vs v4 PK format difference and 64 eval artifacts in the production table. (2) Added `table_name` payload override to creation agent for eval isolation (Decision 143). (3) Cleaned 64 junk items from `calledit-v4` and 18 items from `calledit-db`. (4) Added base-055 (beach day) to golden dataset from v3 data. (5) Created full infrastructure diagram (`docs/architecture-v4-infrastructure.md`). (6) Investigated Browser tool failure — works via direct API but fails in deployed runtime. Added Browser IAM permissions (Decision 144) but issue persists. (7) Added Brave Search `@tool` to verification agent (Decision 145) — verdict accuracy jumped from 0.43 to 0.86 (corrected). (8) Ran full baselines across all three eval frameworks. Three new decisions (143-145).

### Update 35 (March 30): Dynamic Golden Dataset Spec
Discovered fundamental flaw in golden dataset: time-dependent ground truth goes stale (base-010 false failure). 47 of 55 predictions have null expected outcomes, zero `refuted` cases. Built complete spec for dynamic golden dataset generator: 10 requirements, design with 16 correctness properties, 9 implementation tasks. Generator produces 12 time-anchored predictions (3 per mode) with computed ground truth via deterministic calculations + Brave Search. Eval runners merge static + dynamic datasets via `--dynamic-dataset` flag. Added backlog item 17 (Browser debugging).

## Current State (March 31, 2026)

- v4 production COMPLETE — full MVP + eval dashboard + verification modes + Brave Search deployed
- Eval dashboard live at `https://d2fngmclz6psil.cloudfront.net/eval`
- Unified eval pipeline built — single `eval/unified_eval.py` replaces 3 separate runners (Decision 147)
- Dynamic golden dataset generator — 16 templates (9 deterministic + 7 Brave) across all 4 modes
- Merged dataset: 70 predictions (54 static + 16 dynamic), 23 qualifying (non-null verdicts)
- First unified baseline (23 cases, March 31):
  - Creation: T1=1.00, IP=0.89, PQ=0.88
  - Verification: T1=1.00, VA=0.89, EQ=0.59
  - Calibration: CA=~0.91 (after logic fix, Decision 148)
- Calibration logic fixed: high score = easy to verify (confirm OR refute), not just confirm
- Eval table `calledit-v4-eval` imported into CloudFormation (proper IaC)
- Both AgentCore execution roles have eval table DDB permissions
- Browser tool debugging spec complete (`.kiro/specs/browser-tool-fix/`) — 9 requirements, 12 tasks
  - Root cause identified via Kiro powers research: Browser uses a two-layer architecture (boto3 API + WebSocket/Playwright CDP) that Code Interpreter doesn't have
  - PoC agent planned to test each layer independently in deployed runtime
  - Tool configurability planned: `VERIFICATION_TOOLS` env var drives both agents' tool lists
  - Creation agent tool synchronization: planner/reviewer must know what tools verification agent has
- Browser tool FIXED in deployed runtime (Decision 149 — IAM resource ARN mismatch with AWS-owned system browser)
- Tool configurability: `VERIFICATION_TOOLS` env var drives both agents (Decision 150)
- Browser baseline (22 cases): VA=0.94 (+0.05), EQ=0.73 (+0.14), CA=0.95 (+0.04)
- Creation PQ regression: 0.81 (was 0.88) — tool manifest change, needs investigation
- base-013 excluded from qualifying set (Wikipedia reference count is time-varying)
- 151 architectural decisions documented across 37 project updates
- Scanner Lambda FIXED — SnapStart published version had stale env vars, predictions weren't being verified for 2+ weeks (Decision 151)
- Verification agent now deployed with VERIFICATION_TOOLS=both (Browser + Brave Search)
- Knicks prediction verified correctly via Brave: "Thunder 111, Knicks 100" — refuted
- Yankees prediction verified incorrectly: agent searched for World Series instead of April 13 game — verification executor prompt needs date anchoring fix
- Golden dataset gap identified: 55 predictions but only 7 qualifying, none in sports/weather/finance domains where Brave adds most value (backlog item 21)
- Next: Strands Evals SDK migration (`.kiro/specs/strands-evals-migration/`) → dataset expansion (backlog 21) → dashboard adaptation (Spec B). Then dual-model reflection (backlog 20).

### Update 39 (April 19-20): Strands Evals SDK Migration
Migrated the entire custom eval framework (~1,200 lines) to the Strands Evals SDK. Clean break — all custom eval orchestration, evaluator interfaces, LLM judge wrappers, and legacy runners deleted. 18 SDK evaluator subclasses (8 creation + 10 verification), new CLI runner, case loader, task function, calibration module. 98 tests (10 property-based). Full baseline: 70 cases, Creation T1=1.00, Qualifying VA=1.00 (19/19). Old Streamlit dashboard deleted. Decision 152 added.

### Update 40 (April 21-23): Continuous Verification Eval — Full Implementation
Designed and implemented the continuous verification eval system — extending the batched eval pipeline to mirror production's continuous verification behavior. 12 requirements, 7 correctness properties, 12 tasks (55 sub-tasks). All code tasks complete: ContinuousState module, ContinuousMetrics module, ContinuousEvalRunner class with full loop orchestration (SIGINT, token refresh, resume), CLI flags (--continuous, --interval, --max-passes, --once, --reverify-resolved), report schema with continuous-specific fields, and 5 new dashboard components (ContinuousTab, ResolutionRateChart, ResolutionSpeedChart, case color coding, TypeScript types). 31 new tests (7 property-based P1-P7, 24 unit), 129/129 total passing. Manual integration tests remaining.

### Update 41 (April 24): Continuous Eval Dashboard Fixes Spec
Specced three bugfixes discovered during Update 40 integration testing. Bug 1: ResolutionRateChart lines invisible at Y-axis boundaries (1.0 and 0.0) — fix via padded domain `[-0.05, 1.05]` + larger dots (Decision 153). Bug 2: Inconclusive cases missing from CalibrationScatter because `_run_verification_pass()` only constructs vresult for `status == "resolved"`, excluding `status == "inconclusive"` — fix by widening condition to include inconclusive (Decision 154). Bug 3: Pass numbering always "Pass 1" because `pass_num` starts at 0 on every CLI invocation instead of resuming from saved state — fix by initializing from `self.state.pass_number` on `--resume` (Decision 155). Bugfix requirements complete (5 defect + 5 fix + 6 regression prevention clauses). Design and tasks pending.

## Current State (April 24, 2026)

- v4 production COMPLETE — full MVP + eval dashboard + verification modes + Brave Search deployed
- Eval dashboard live at `https://d2fngmclz6psil.cloudfront.net/eval`
- Strands Evals SDK migration COMPLETE — replaced ~1,200 lines custom code with SDK primitives (Decision 152)
- Continuous verification eval COMPLETE — all tasks done, integration tested, dashboard working
  - `eval/continuous_state.py` — state management with verdict history
  - `eval/continuous_metrics.py` — resolution rate, stale inconclusive, resolution speed by tier
  - `ContinuousEvalRunner` class in `eval/run_eval.py` — full loop orchestration
  - CLI: `--continuous`, `--interval`, `--max-passes`, `--once`, `--reverify-resolved`
  - Dashboard: Continuous Eval tab with ResolutionRateChart, ResolutionSpeedChart, score grids, scatter plot
  - Integration tested: base-002 created, verified (confirmed), V-Score=0.92, report in DDB
  - 31 new tests (7 property-based, 24 unit), 129/129 total passing
- Continuous eval dashboard fixes SPECCED — 3 bugs (chart visibility, scatter plot, pass numbering), requirements complete, design + tasks pending
- Eval framework: 18 SDK evaluators (8 creation + 10 verification), 129 eval tests
- Golden dataset: 70 predictions (54 static + 16 dynamic), 22 qualifying
- 158 architectural decisions documented across 41 project updates
- Next: Execute AgentCore CDK migration spec → Run continuous eval Pass 3 → dataset expansion (backlog 21)
