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

## Current State (March 19, 2026)

- Serial backend: 38% pass rate, IP 0.81, CMA 0.74, Verification-Builder-centric 0.53 (Run 15, review v3)
- Single backend: 37% pass rate, IP 0.79, CMA 0.77, Verification-Builder-centric 0.52 (Run 16, review v3)
- Architectures essentially tied on pass rate and composite score after review v3
- Serial routes better (100% vs 71% auto_verifiable), single reasons better (CMA 0.77 vs 0.74)
- Review v3 was the biggest single-prompt improvement: +13% serial, +21% single
- 16 eval runs completed, architecture comparison dashboard fully operational
- Next: pivot to MCP verification pipeline implementation
- 8 backlog items: DDB migration, swarm backend, golden dataset review, eval runner resume, file cleanup, code review, MCP verification pipeline, evaluator pipeline review
- 60 architectural decisions documented in decision log
