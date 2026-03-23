# CalledIt Project Summary

A condensed narrative of the CalledIt project from inception through 10 project updates. Use this alongside `decision-log.md` for full context.

---

## What CalledIt Is

CalledIt is a prediction verification platform. Users make predictions ("Lakers win tonight", "it'll rain tomorrow", "Miriam will be home by 3pm") through a mobile-first web app. The system analyzes each prediction, builds a structured verification plan (what to check, where to check it, when to check), and categorizes it by verifiability. The goal: understand the user's intent and repackage it into a machine-actionable verification plan.

## Tech Stack

- React frontend (mobile-first PWA) with WebSocket streaming
- AWS Lambda backend (Python, SAM/CloudFormation)
- Strands Agents SDK for multi-agent AI pipeline
- Amazon Bedrock (Claude Sonnet 4) for model inference
- DynamoDB for prediction storage and eval data
- Cognito for auth (with auto-refresh for mobile UX)
- SnapStart on all 8 Lambda functions (82% cold start improvement)

## The Agent Pipeline

Four specialized agents in a Strands Graph:
1. Parser — extracts the factual claim, strips framing ("I bet"), resolves temporal references
2. Categorizer — routes to `auto_verifiable`, `automatable`, or `human_only` based on available tools
3. Verification Builder — creates the verification plan (criteria, method, sources, steps)
4. ReviewAgent — identifies gaps and asks clarification questions

The pipeline supports multi-round refinement: user makes prediction → sees structured output → optionally clarifies → agents refine.

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

The eval framework is the transferable artifact:
- Golden dataset with ground truth metadata (45 base + 23 fuzzy predictions)
- 12 evaluators: 6 LLM judges (IntentPreservation, CriteriaMethodAlignment, IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence) + 6 deterministic
- Pluggable backend system for architecture comparison (serial graph vs single agent)
- Verification-Builder-centric composite score as primary metric
- Streamlit dashboard with 7 pages for visual analysis
- DynamoDB reasoning store for full model traces
- Bedrock Prompt Management with immutable versions
- 13 eval runs with isolated single-variable testing methodology
- Score tracking with regression detection and prompt version correlation

## Key Technical Decisions

- Spec-driven development with Kiro (11 specs, each with requirements → design → tasks)
- Property-based testing with Hypothesis for correctness properties
- Isolated single-variable testing for prompt iteration (change one thing per run)
- Frontend-as-session for refinement state (deliberate architectural choice, not a shortcut)
- Two-tier evaluator strategy (deterministic catches structure, LLM judge catches reasoning)
- Verification Builder output as the primary eval target (not categorization)

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
