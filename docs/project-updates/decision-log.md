# CalledIt Decision Log

A consolidated record of all architectural, technical, and process decisions made across the project. Each decision references the project update where it was originally documented for full context.

---

## Decision 1: Drop Backward Compatibility on the Wire Protocol
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

Clean break on the WebSocket protocol. New message types (`prediction_ready`, `review_ready`) only. Old types (`call_response`, `review_complete`, `improvement_questions`, `improved_response`) removed entirely. The only true backward compatibility constraint is the DynamoDB save format, since existing predictions must remain queryable. This is a demo/educational project with no external API consumers — keeping old types alive creates two code paths and confuses future readers.

---

## Decision 2: Identified and Addressed Additional Architectural Debt
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

Deep code review after initial requirements found 5 issues worth fixing immediately: broken `review_agent.py` import of deleted `error_handling` module, dead `*_node_function()` code in all agent files, 120 lines of regex JSON extraction, response building split across two files, and no separate `improve_call.py` file despite architecture diagrams referencing it. Added as Requirements 11-13 in the original combined spec.

---

## Decision 3: Split Into Two Specs
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

Split the combined 13-requirement spec into Spec 1 (v2 Cleanup & Foundation — 5 requirements, all refactoring) and Spec 2 (v2 Unified Graph with Stateful Refinement — 9 requirements, new behavior). Confidence went from ~65% for one spec to ~90% for two focused specs. If Spec 2 goes sideways, you're debugging against clean code.

---

## Decision 4: Prompt-First Approach to JSON Parsing Cleanup
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

The defensive JSON parsing (120 lines of regex) exists because agents were returning malformed output. Fix the root cause first: (1) harden prompts with explicit "Return ONLY raw JSON" instructions, (2) build a prompt testing harness to validate clean output, (3) only then remove the defensive parsing. Defensive code often exists for a reason — fix the cause, prove the fix, then remove the defense.

---

## Decision 5: Strands Documentation Review via Kiro Power
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

Reviewing Strands Graph docs during spec creation (not during coding) surfaced two critical findings: (1) default edge behavior is "any one" not "all" — ReviewAgent would fire before pipeline completes without conditional edges, (2) Graph doesn't support mid-execution message sending — need `stream_async` with `multiagent_node_stop` events. These would have caused significant debugging time if discovered during implementation.

---

## Decision 6: Model Upgrade from Claude 3.5 Sonnet to Claude Sonnet 4
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

Upgraded all four agents from `anthropic.claude-3-5-sonnet-20241022-v2:0` to `us.anthropic.claude-sonnet-4-20250514-v1:0`. Better instruction following (relevant to JSON output problem), same Sonnet tier (similar latency/cost), current Strands default. Done before prompt hardening so validation runs against the production model.

---

## Decision 7: Simplified Graph Topology — Single Edge, No Conditional Edges
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

The conditional edge approach was overengineered. The pipeline is sequential (Parser → Categorizer → VB), so when VB completes, all three have already completed by definition. ReviewAgent only needs a single edge from `verification_builder`. The "any one dependency" concern only applies to multiple independent branches feeding one node. Graph is now 4 simple edges, no conditions — the idiomatic Strands pattern.

---

## Decision 8: Frontend-as-Session Is a Feature, Not a Compromise
**Source:** [Project Update 01](project-updates/01-project-update-v2-architecture-planning.md)
**Date:** March 6, 2026

The frontend holds session state (round number, accumulated clarifications, latest agent outputs). The Lambda is stateless. DynamoDB stores only the final prediction. This is a deliberate architectural choice: the data is the user's own prediction text being refined (not sensitive), realistically 1-2 rounds max, a few KB of state, backend stays simple and stateless, any Lambda instance can handle any round.

---

## Decision 9: ReviewAgent Sub-Section Names
**Source:** [Project Update 02](project-updates/02-project-update-frontend-v2-alignment.md)
**Date:** March 9, 2026

The ReviewAgent returns dot-notation section names (`verification_method.source`) instead of top-level names (`verification_method`). This is actually better — more specific improvement suggestions. Frontend handles both patterns with `startsWith` matching and question aggregation. If the prompt changes section names, `startsWith` handles it gracefully.

---

## Decision 10: Single-Push vs Two-Push Delivery
**Source:** [Project Update 02](project-updates/02-project-update-frontend-v2-alignment.md)
**Date:** March 9, 2026

The ReviewAgent completes quickly after the pipeline (2-4 seconds). The two-push design (prediction_ready then review_ready) was built to avoid making the user wait. If review time is consistently fast, single-push at graph completion would be simpler. Future consideration — two-push is working and educationally interesting as a Strands streaming pattern.

---

## Decision 11: Skip Connect/Disconnect for SnapStart
**Source:** [Project Update 03](project-updates/03-project-update-snapstart.md)
**Date:** March 9, 2026

Initially skipped SnapStart for ConnectFunction/DisconnectFunction (imports only `json`, risk > benefit). **Reversed in Decision 16.**

---

## Decision 12: Provisioned Concurrency Not Needed
**Source:** [Project Update 03](project-updates/03-project-update-snapstart.md)
**Date:** March 9, 2026

SnapStart restore at 444ms (82% improvement from 2,441ms baseline) is sufficient. $0 additional cost vs ~$39/month for Provisioned Concurrency. Clear winner for a demo project.

---

## Decision 13–15: (Reserved / Implicit in Updates 03-04)

---

## Decision 16: Add SnapStart to WebSocket Lifecycle Functions
**Source:** [Project Update 03](project-updates/03-project-update-snapstart.md)
**Date:** March 13, 2026

Reversed Decision 11. Added SnapStart to ConnectFunction and DisconnectFunction for stack consistency. SAM template only — no handler code changes. All 8 Lambda functions now have SnapStart enabled.

---

## Decision 17: DependsOn Required for All Alias References
**Source:** [Project Update 03](project-updates/03-project-update-snapstart.md)
**Date:** March 13, 2026

First deploy failed because CloudFormation created alias permission before alias existed. Fix: added `DependsOn: {FunctionName}Aliaslive` to all alias-referencing resources, including retroactive fix for MakeCallStreamFunction.

---

## Decision 18: Simplify to 3 Verifiability Categories
**Source:** [Project Update 04](project-updates/04-project-update-category-simplification.md)
**Date:** March 13, 2026

Simplified from 5 categories to 3: `auto_verifiable` (system can verify now with current tools), `automatable` (verifiable in principle, work queue for future tool-finding agent), `human_only` (requires subjective judgment or inaccessible information). Every new tool graduates predictions from `automatable` to `auto_verifiable`.

---

## Decision 19: Tool Registry in DynamoDB
**Source:** [Project Update 04](project-updates/04-project-update-category-simplification.md)
**Date:** March 13, 2026

Tool records stored in DynamoDB (`calledit-db`) with PK `TOOL#{tool_id}`, SK `METADATA`. Fields: name, description, capabilities, input/output schema, status, added_date. Categorizer reads registry at runtime to determine if a prediction is `auto_verifiable` vs `automatable`.

---

## Decision 20: Web Search as First Registered Tool
**Source:** [Project Update 04](project-updates/04-project-update-category-simplification.md)
**Date:** March 13, 2026

Custom `@tool` using Python `requests` + DuckDuckGo Instant Answer API. Serves as the test case for the entire tool registration workflow: create tool → register in DDB → wire into verification agent → re-categorize predictions.

---

## Decision 21: Re-categorization Runs Full Pipeline
**Source:** [Project Update 04](project-updates/04-project-update-category-simplification.md)
**Date:** March 13, 2026

When a tool is added, `automatable` predictions get re-run through the full graph (parser → categorizer → VB → review), not just the categorizer. The verification_method also needs updating when the category changes.

---

## Decision 22: Upgrade Verification Agent to Sonnet 4
**Source:** [Project Update 04](project-updates/04-project-update-category-simplification.md)
**Date:** March 13, 2026

Upgraded verification agent from `claude-3-sonnet-20241022` to `us.anthropic.claude-sonnet-4-20250514-v1:0` for consistency with all prediction pipeline agents and better instruction following.

---

## Decision 23: AgentCore Evaluations — USE
**Source:** [Project Update 05](project-updates/05-project-update-eval-strategy.md)
**Date:** March 13, 2026

Despite preview risk (confidence 5/10), high differentiation value. Purpose-built for evaluating agents with span-level analysis, custom evaluators, online + on-demand evaluation. Being among the first to integrate with a real multi-agent Strands graph is a portfolio differentiator. Fallback: OTEL traces + CloudWatch + custom harness.

---

## Decision 24: Skip Bedrock Evaluations
**Source:** [Project Update 05](project-updates/05-project-update-eval-strategy.md)
**Date:** March 13, 2026

Designed for single model input/output pairs, not multi-agent chains. Redundant with AgentCore Evaluations. BYOI means we still run the graph ourselves.

---

## Decision 25: Skip Bedrock Guardrails / Contextual Grounding
**Source:** [Project Update 05](project-updates/05-project-update-eval-strategy.md)
**Date:** March 13, 2026

Core problem is classification accuracy, not hallucination. Agents return structured JSON, not prose. Contextual grounding expects prose against source documents — wrong problem shape.

---

## Decision 26: Skip SageMaker Clarify / FMEval
**Source:** [Project Update 05](project-updates/05-project-update-eval-strategy.md)
**Date:** March 13, 2026

Heavyweight platform for ML teams, single-model focus, overkill for ~25 test cases. AgentCore Evaluations subsumes FMEval's relevant capabilities.

---

## Decision 27: Opus 4.6 as Judge Model
**Source:** [Project Update 06](project-updates/06-project-update-eval-framework-execution.md)
**Date:** March 14, 2026

Different model generation than agents (Sonnet 4) — avoids self-evaluation bias. Model ID: `us.anthropic.claude-opus-4-6-v1` (without `:0` suffix). Dev-time tool, not production — latency/cost not a constraint.

---

## Decision 28: CloudFormation for Prompt Management
**Source:** [Project Update 06](project-updates/06-project-update-eval-framework-execution.md)
**Date:** March 14, 2026

IaC ensures reproducibility and auditability. Separate stack (`calledit-prompts`) from SAM backend — prompts are shared infrastructure. Template at `infrastructure/prompt-management/template.yaml`. Future: when dev/prod stacks split, both read from the same prompt stack.

---

## Decision 29: Local Eval Results (Not DynamoDB — Yet)
**Source:** [Project Update 06](project-updates/06-project-update-eval-framework-execution.md)
**Date:** March 14, 2026

`score_history.json` tracked in git (portfolio evidence). `eval/reports/` gitignored (large, regenerable). Charts tracked in git (visual portfolio evidence). Will move to DynamoDB/S3 when building the AgentCore eval stack.

---

## Decision 30: Two-Tier Evaluator Strategy Validated
**Source:** [Project Update 06](project-updates/06-project-update-eval-framework-execution.md)
**Date:** March 14, 2026

Tier 1 (deterministic) catches structural regressions fast and cheap. Tier 2 (LLM-as-judge) catches nuanced quality issues. The 80% → 30% pass rate drop when adding the judge proves the judge adds real signal. ReviewAgent prompt is the primary improvement target based on judge data.

---

## Decision 31: Ground Truth Metadata Per Prediction
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Each prediction captures WHY it's that category through structured metadata: verifiability_reasoning, date_derivation, verification_sources, objectivity_assessment, verification_criteria, verification_steps. When categories evolve, expected labels are re-derived from ground truth rather than manually re-tagging 50+ test cases.

---

## Decision 32: Clean Break from V1 Dataset
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

V2 dataset replaces v1 entirely. V2 loader only supports `schema_version: "2.0"`. V1 archived to `eval/golden_dataset_v1_archived.json`. Comparing scores across v1/v2 is apples-to-oranges anyway. Clean break means simpler loader, stronger validation, less maintenance.

---

## Decision 33: Future 4-Category System
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Proposed future categories: `current_agent_verifiable`, `agent_verifiable_with_known_tool`, `assumed_agent_verifiable_with_tool_build`, `human_only`. The model's natural reasoning already aligns more with 4 categories than 3. Ground truth metadata makes this migration a re-derivation exercise, not a re-authoring exercise.

---

## Decision 34: DynamoDB for Eval Reasoning Capture
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

New table `calledit-eval-reasoning` stores full model reasoning traces during eval runs. Fire-and-forget pattern — DDB failures never block eval execution. TTL of 90 days. PAY_PER_REQUEST billing.

---

## Decision 35: Lightweight Expected Outputs
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Only `expected_category` is required per prediction. Parser, VB, and review expected outputs are optional rubric guidance for the LLM-as-judge. Makes maintaining 50+ predictions practical.

---

## Decision 36: Fuzziness Level 0 (Control Cases)
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Added Level 0 — perfectly specified predictions used as controls where the ReviewAgent should find no clarification needed. Levels: 0 (control), 1 (missing one detail), 2 (missing multiple details), 3 (highly ambiguous).

---

## Decision 37: Cross-Agent Coherence as First-Class Concern
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Parser date extraction, categorizer verifiability judgment, and VB methods/sources/criteria/steps should tell a consistent story. At least 5 "coherence anchor" predictions have complete expected outputs for all 4 agents.

---

## Decision 38: Storage — Git Now, S3 Later
**Source:** [Project Update 07](project-updates/07-project-update-golden-dataset-design.md)
**Date:** March 14, 2026

Keep golden dataset in git with explicit `dataset_version` field. Move to private S3 bucket (with versioning, encryption, public access blocked) when dataset exceeds ~100 test cases.

---

## Decision 39: Deploy DDB Table Before Judge Run
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md)
**Date:** March 15, 2026

The judge run produces the most valuable DDB data (full reasoning traces). Running without the table loses that data permanently. Deployed `calledit-eval-reasoning` table via SAM before Run 2.

---

## Decision 40: Architecture Flexibility as Dashboard Requirement
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md)
**Date:** March 15, 2026

Dashboard should include an "architecture" dimension so eval runs can be compared across serial graph, swarm, and single-agent backends. Eval report schema needs `architecture` and `model_config` fields.

---

## Decision 41: Eval Framework as Portfolio Centerpiece
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md)
**Date:** March 15, 2026

The eval suite — golden dataset with ground truth, multi-tier evaluators, DDB reasoning capture, architecture-agnostic scoring, and a visual dashboard — is the transferable skill set. Even if a single Opus 4.6 agent outperforms the multi-agent graph, the eval framework that proved it is the valuable artifact.

---

## Decision 42: Categorizer Prompt Needs Nuance, Not Just Expansion
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md)
**Date:** March 15, 2026

Simply expanding the human_only definition isn't enough. The categorizer needs to distinguish between "private data that no API can access" (human_only) and "personal data that a known API could access with authentication" (automatable). The 4-category system would handle this naturally. For now, the prompt needs more precise language.

---

## Decision 43: Integrate Strands Evals SDK Into Eval Suite
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md)
**Date:** March 15, 2026

Use the SDK over custom code wherever equivalent functionality exists. Replace hand-rolled LLM judge with `OutputEvaluator`, add `TrajectoryEvaluator` for inter-agent coherence, wrap golden dataset entries as `Case` objects. Keep custom code only for DDB persistence, prompt version manifests, architecture comparison, dataset versioning, fuzzy round evaluation, and visual dashboard.

---

## Decision 44: Verification Criteria Is the Primary Eval Target, Not Categorization
**Source:** [Project Update 08](project-updates/08-project-update-eval-insights-and-architecture-flexibility.md) / [Project Update 09](project-updates/09-project-update-dashboard-v1-and-eval-reframe.md)
**Date:** March 15-16, 2026

Category labels downgraded to helpful routing hints. The real success metric: does the verification builder produce verification criteria that a verification agent can use to determine true/false at the right time? Eval priorities reframed: (1) verification criteria quality — PRIMARY, (2) verification method quality — SECONDARY, (3) category accuracy — TERTIARY.

---

## Decision 45: Two-Spec Approach for Eval Reframe
**Source:** [Project Update 09](project-updates/09-project-update-dashboard-v1-and-eval-reframe.md)
**Date:** March 16, 2026

Spec 1 (verification-evaluators): Golden dataset v3 + new evaluators + Strands Evals SDK integration. Must come first — can't improve what you can't measure. Spec 2 (vb-prompt-iteration): Iterate on VB prompt using new evaluators. Depends on Spec 1.

---

## Decision 46: Judge Rubric Recalibration
**Source:** [Project Update 09](project-updates/09-project-update-dashboard-v1-and-eval-reframe.md)
**Date:** March 16, 2026

The question "is the reasoning well-written?" should become "would this verification plan succeed at verifying the prediction?" This is a rubric change mapping naturally to Strands `OutputEvaluator` with a targeted rubric.

---

## Decision 47: Vague Predictions — Operationalize vs Acknowledge
**Source:** [Project Update 09](project-updates/09-project-update-dashboard-v1-and-eval-reframe.md)
**Date:** March 16, 2026

Two types: (1) Operationalizable vague terms ("nice weather") — VB should auto-fill reasonable measurable thresholds, ReviewAgent validates assumptions. (2) Truly subjective ("feel happy") — no external proxy exists, VB keeps human_only, ReviewAgent asks questions that might lead to verifiable reformulation. IntentPreservation evaluator rubric rewards operationalization.

---

## Decision 48: Per-Agent Evaluators
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

Each agent should have at least one evaluator that asks "did this agent do its specific job in service of the two system goals?" Priority: ClarificationRelevance (ReviewAgent), then IntentExtraction (Parser). Both use Strands Evals SDK OutputEvaluator.

---

## Decision 49: Architecture Backend Abstraction
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

Add a `--backend serial|swarm|single` flag to the eval runner. Each backend implements the same output contract. The eval framework scores all architectures identically. Enables data-driven architecture comparison.

---

## Decision 50: Isolated Single-Variable Testing as Standard Practice
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

Every eval iteration should change exactly one variable (prompt, dataset, or architecture) per run. This is now the standard methodology for all future prompt and architecture experiments.


---

## Decision 51: CategorizationJustification Evaluator — VB-Centric Routing Assessment
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

The Categorizer's evaluation shifts from "did it pick the right label?" (CategoryMatch) to "did its routing decision enable the VB to produce the best possible verification plan?" The LLM judge sees parser output, categorizer output, tool manifest, AND VB output — assessing downstream impact. CategoryMatch remains as a cheap deterministic check but is no longer weighted in the primary pass rate.

---

## Decision 52: PipelineCoherence Evaluator — Quantifying the Silo Problem
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

A cross-agent LLM judge that sees all 4 outputs together and scores whether each agent built on the previous agent's work. Directly addresses the silo problem from Update 08. Critical for architecture comparison — quantifies whether the single-agent backend produces more coherent output than the serial graph.

---

## Decision 53: VB-Centric Composite Score
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

The eval report computes a "VB-centric score" — a weighted composite where IntentPreservation and CriteriaMethodAlignment have the highest weight, and other evaluators are weighted by how directly they impact VB output quality. Replaces the old overall pass rate as the primary metric.

---

## Decision 54: Consolidated Decision Log
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

Created `docs/project-updates/decision-log.md` containing all decisions extracted from all project updates. Future agents can read this one file instead of scanning all project updates to understand the decision history.


---

## Decision 55: Pluggable Backend with Flexible Output Contract
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 17, 2026

Backends are extensible — any architecture (2-agent, 5-agent, etc.) can be added by dropping a module in `backends/`. The output contract requires `final_output` (verification criteria + method, what evaluators actually score) and optional `agent_outputs` (whatever agents the backend produces). Per-agent evaluators only run when their target agent key exists in the output. The eval framework never needs to change when experimenting with new architectures.


---

## Decision 56: Single Backend Uses Same Prompts via Prompt Management
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 18, 2026

The single backend creates one agent that receives the same 4 prompts from Bedrock Prompt Management as sequential conversation turns. The agent maintains its own context across turns — no silo problem by design. This is a fairer comparison than a single mega-prompt because the only variable is context propagation (graph-managed vs natural conversation).

---

## Decision 57: Tools Should Be Architecture-Agnostic (Future)
**Source:** [Project Update 10](project-updates/10-project-update-vb-iteration-and-architecture-vision.md)
**Date:** March 18, 2026

Currently tools (web_search, parse_relative_date) are imported from agent-specific modules. They should live as MCP tools or A2A services so any backend architecture can use them without coupling to specific agent code. Future spec when the eval framework proves which architecture works best.


---

## Decision 58: Pipeline-Ordered Heatmap with Color-Coded Evaluator Labels
**Source:** [Project Update 11](project-updates/11-project-update-comparative-dashboard-and-analysis.md)
**Date:** March 18, 2026

Heatmap columns reordered to follow the agent pipeline left to right (Parser → Categorizer → Verification Builder → Review → Cross-Pipeline). LLM judges and deterministic evaluators are mixed within each pipeline group. Labels are color-coded: blue for LLM judges, gray for deterministic. This makes the pipeline story visible — you can see which stage is the bottleneck without reading numbers.

---

## Decision 59: Combined Prompt Update Before Verification Pipeline Pivot
**Source:** [Project Update 11](project-updates/11-project-update-comparative-dashboard-and-analysis.md)
**Date:** March 18, 2026

Breaking isolated single-variable testing (Decision 50) for one iteration. Combining Review prompt v3 (both architectures) + single backend JSON discipline (single only) into one update. Justified because the project is pivoting to verification pipeline implementation — need the best baseline before that shift, not incremental data points. Serial coherence instructions deferred because PipelineCoherence only has 2/68 failures.

---

## Decision 60: Keep Deterministic Evaluators Until Agreement Data Proves Proxies
**Source:** [Project Update 11](project-updates/11-project-update-comparative-dashboard-and-analysis.md)
**Date:** March 18, 2026

Don't retire deterministic evaluators yet. Run both deterministic and LLM judges side by side, use the Coherence View to measure agreement rates. When a deterministic evaluator agrees with its LLM judge counterpart 90%+ of the time, it's a trustworthy cheap proxy for quick iteration runs. When agreement is low, the deterministic evaluator is misleading. This enables a tiered run strategy: quick (deterministic only), standard (deterministic + selective judges), full (all judges).


---

## Decision 61: Production Prompts via Bedrock Prompt Management with Version Pinning
**Source:** Spec 12: Production Prompt Management Wiring
**Date:** March 20, 2026

Production Lambda was silently falling back to hardcoded v1 prompt constants because it lacked `bedrock-agent:GetPrompt` IAM permission and `PROMPT_VERSION_*` environment variables. Fixed by adding both to the SAM template, pinning to eval-validated versions (parser 1, categorizer 2, VB 2, review 3). Hardcoded fallback constants updated to match latest Prompt Management text so even fallback mode uses current prompts. Rollback is a single env var change — no code deployment needed.

---

## Decision 62: Composite Score Weights Need Empirical Grounding
**Source:** Agent review session (March 20, 2026)
**Date:** March 20, 2026

The Verification-Builder-centric composite score weights (IP 25%, CMA 25%, etc.) were a judgment call, not derived from data. The composite is directionally useful but not a reliable optimization target. After the verification pipeline is implemented and producing real verification outcomes, weights should be derived from correlation between evaluator scores and actual verification success rates. Backlog item 11 tracks this.

---

## Decision 63: Pre-Graph (v1) Backend as Eval Comparison Target
**Source:** Agent review session (March 20, 2026)
**Date:** March 20, 2026

The pre-graph v1 architecture may have produced better subjective results than the current v2 graph. The pluggable backend system (Decision 55) enables a data-driven comparison — drop a `backends/pregraph.py` module and run through the eval framework. Backlog item 10 tracks this.



---

## Decision 64: Split MCP Verification Foundation Into Two Specs
**Source:** Spec planning session (March 20, 2026)
**Date:** March 20, 2026

The combined "mcp-verification-foundation" spec had 17 tasks — too large for reliable execution. Split into Spec A1 (verification-teardown-docker: infrastructure teardown + Docker Lambda) and Spec A2 (mcp-tool-integration: MCP Manager + tool-aware agents + Prompt Management). Same reasoning as Decision 3: smaller specs, higher confidence. A1 can be deployed and validated independently before A2 adds application logic.

---

## Decision 65: Docker Lambda for MCP Subprocess Support
**Source:** Spec A1 design (March 20, 2026)
**Date:** March 20, 2026

MCP servers (fetch, brave-search, playwright) are npm packages invoked via `npx`, which requires Node.js. Lambda `python3.12` runtime doesn't include Node.js. Solution: switch MakeCallStreamFunction to `PackageType: Image` with a Dockerfile based on `public.ecr.aws/lambda/python:3.12` + Node.js LTS installed via binary tarball. This is a stepping stone toward AgentCore, which also deploys containerized agents.

---

## Decision 66: Accept SnapStart Loss on MakeCallStreamFunction
**Source:** Spec A1 design (March 20, 2026)
**Date:** March 20, 2026

AWS Lambda SnapStart for Python only supports zip packages, not container images. Switching to Docker means losing SnapStart on MakeCallStreamFunction. Cold starts will be ~2-5s slower (agent creation + graph compilation). Accepted because: (1) the 300s timeout provides ample headroom, (2) MCP server subprocess startup in Spec A2 would invalidate the SnapStart snapshot anyway, (3) provisioned concurrency can mitigate if needed, (4) AgentCore migration is planned shortly after verification pipeline completion. Other functions (Connect, Disconnect) retain SnapStart since they stay as zip packages.

---

## Decision 67: Project Version Bump to v3
**Source:** Spec planning session (March 20, 2026)
**Date:** March 20, 2026

The MCP verification pipeline is a backward-compatibility-breaking change (removes old verification system, changes Lambda packaging model, replaces tool registry pattern). Version bump: v1 = pre-graph architecture, v2 = unified 4-agent Strands Graph, v3 = MCP-powered verification pipeline with Docker Lambda. Version bump happens after Spec A2 completes (both infrastructure and application logic in place).

---

## Decision 68: AgentCore as Post-Verification Migration Target
**Source:** Spec planning session (March 20, 2026)
**Date:** March 20, 2026

After the verification pipeline is implemented (Specs A1 + A2 + B), migrate the runtime to Amazon Bedrock AgentCore. The Docker Lambda infrastructure from Spec A1 is a stepping stone — AgentCore deploys containerized agents, so the container-based architecture transfers directly. The current SAM Lambda architecture was chosen for the class being taught (low cost for students), but the project now aims to demonstrate best-in-class agent architecture.


---

## Decision 69: Dockerfile Requires tar/xz Install on AL2023 Lambda Base
**Source:** Spec A1 deployment (March 20, 2026)
**Date:** March 20, 2026

The AWS Lambda Python 3.12 base image (`public.ecr.aws/lambda/python:3.12`) is Amazon Linux 2023 minimal — it does not include `tar` or `xz` utilities. The Dockerfile must `dnf install -y tar xz` before extracting the Node.js binary tarball. Discovered during first `sam build` attempt when `tar: command not found` failed the Docker build.

---

## Decision 70: Orphaned S3 Bucket Acceptable During Teardown
**Source:** Spec A1 deployment (March 20, 2026)
**Date:** March 20, 2026

CloudFormation cannot delete a non-empty S3 bucket. The VerificationLogsBucket deletion failed during deploy with `DELETE_FAILED` because it contained verification log objects. The bucket is now orphaned (not managed by the stack) but harmless. Manual cleanup can happen later — the deploy succeeded for all other resources including the Docker Lambda switch.

---

## Decision 71: MCP Server Package Names — npm vs Python
**Source:** Spec A2 debugging (March 21, 2026)
**Date:** March 21, 2026

The original MCP research doc listed `@modelcontextprotocol/server-fetch` as an npm package — it doesn't exist. The Anthropic fetch server is Python-only (`uvx mcp-server-fetch`). Corrected to `@tokenizin/mcp-npx-fetch` for npm-based fetch. Brave search is `@modelcontextprotocol/server-brave-search` (not `@nicobailon/mcp-brave-search`). Playwright is `@nicobailon/mcp-playwright` (confirmed working). Local test script (`test_mcp_local.py`) was critical for fast iteration — deploy cycles were too slow for debugging package names.

---

## Decision 72: Use .replace() Not .format() for Tool Manifest Substitution
**Source:** Spec A2 debugging (March 21, 2026)
**Date:** March 21, 2026

Python `.format()` requires `{{` and `}}` to escape literal braces in the template string. The categorizer's bundled prompt had `{{ "verifiable_category": ... }}` as the JSON example — the model saw double braces and mimicked them in output, producing unparseable JSON. Switched all agent factories to `.replace("{tool_manifest}", value)` which doesn't require brace escaping. The JSON examples now use single braces naturally.

---

## Decision 73: 30-Second Cold Start Validates AgentCore Migration Priority
**Source:** Spec A2 deployment testing (March 21, 2026)
**Date:** March 21, 2026

The Docker Lambda with MCP server subprocesses takes ~30 seconds on cold start (npx downloading packages + Node.js subprocess startup + agent creation). Provisioned concurrency could mitigate but fights the natural architecture — tools and agents should be separate execution environments. This validates Decision 68 (AgentCore migration) as the right next step after the verification pipeline is complete. AgentCore manages MCP servers as always-warm network services, eliminating the cold start penalty entirely.

---

## Decision 74: Verification Pipeline Roadmap — Build, Eval, Then Migrate
**Source:** Session planning (March 21, 2026)
**Date:** March 21, 2026

Three-phase plan after Spec A2: (1) Build verification execution agent (Spec B) that actually invokes MCP tools to verify predictions, (2) Run golden dataset against both the prediction builder and verification pipeline to compare quality, (3) Migrate from Lambda to AgentCore where tools and agents run in separate execution environments. The eval comparison is critical — it proves the MCP tools actually improve verification outcomes, not just categorization labels.

---

## Decision 75: Split Spec B Into Three Focused Specs (B1, B2, B3)
**Source:** Spec B planning session (March 21, 2026)
**Date:** March 21, 2026

The original Spec B (verification execution agent) had 9 requirements spanning three distinct concerns: agent construction, infrastructure/triggers, and eval integration. Same reasoning as Decision 3 (Spec 1/2 split) and Decision 64 (A1/A2 split) — smaller specs, higher confidence. Split into:
- **Spec B1** (`verification-execution-agent`): Verification Executor agent, data model, entry point, MCP wiring, factory pattern (5 requirements). Self-contained, testable in isolation.
- **Spec B2** (`verification-triggers`): DynamoDB storage, immediate trigger, EventBridge scanner (3 requirements). Depends on B1. Touches SAM template and production handler.
- **Spec B3** (`verification-eval-integration`): `--verify` mode on eval runner, 4 new evaluators, golden dataset extension, dashboard page (4 requirements). Depends on B1 but NOT B2.

---

## Decision 76: Two-Mode Verification Trigger (Immediate vs Scheduled)
**Source:** Spec B requirements review (March 21, 2026)
**Date:** March 21, 2026

Most `auto_verifiable` predictions can't be verified at prediction time — "it will be nice weather Saturday" is auto_verifiable (brave_web_search can check weather) but verifying on Wednesday only checks the forecast, not the actual weather. The `verification_date` from the parser is the key signal. Two modes: (1) Immediate — verification_date is past or within 5 minutes, verify inline after prediction pipeline. (2) Scheduled — verification_date is future, leave as `pending` for an EventBridge scanner (every 15 minutes) to pick up when the date arrives. Same pattern as the v1 verification system that worked before Spec A1 teardown.

---

## Decision 77: Fold Verification Eval Into Existing Framework, Not a Second One
**Source:** Spec B requirements review (March 21, 2026)
**Date:** March 21, 2026

The VB-Executor comparison eval extends the existing eval framework (`eval_runner.py`, `evaluators/`, `eval/dashboard/`) rather than building a parallel eval system. New `--verify` flag on the existing runner, four new evaluator modules in the existing `evaluators/` directory, scores flow into the existing `evaluator_scores` dict so the Streamlit dashboard picks them up automatically. Golden dataset extended with `verification_readiness` field. One framework, one dashboard, one report format.

---

## Decision 78: No-Mocks Policy — All Tests Must Hit Real Services
**Source:** Spec B1 testing (March 21, 2026)
**Date:** March 21, 2026

User rejected mock-based testing. All tests must exercise real code paths — real Bedrock calls, real MCP server connections, real DynamoDB. Mocks hide real bugs and give false confidence. Integration tests are slower (~75s) and cost money, but test the actual system. Steering doc created at `.kiro/steering/no-mocks-policy.md`. Pure function tests (testing `_validate_outcome`, `_make_inconclusive`, prompt content) don't need mocks because they don't call external services.

---

## Decision 79: Lazy Singleton for Verification Executor Agent
**Source:** Spec B1 implementation (March 21, 2026)
**Date:** March 21, 2026

The module-level singleton pattern (`agent = create_agent()` at module scope) triggers MCP server connections at import time, which breaks test isolation and causes 30s+ delays on every import. Switched to lazy initialization via `_get_executor_agent()` — the agent is created on first use, not at import time. Same warm-Lambda reuse benefit (created once, reused across invocations) without the import-time side effect.

---

## Decision 80: Verification Trigger Is "Log Call", Not Pipeline Completion
**Source:** Spec B1 design review (March 21, 2026)
**Date:** March 21, 2026

The verification executor must NOT be triggered by the prediction pipeline completing or the Verification Builder producing a plan. The prediction pipeline can run multiple HITL rounds (user clarifies → agents refine → user reviews). Only when the user explicitly clicks "Log Call" and the prediction is saved to DynamoDB should verification be considered. This preserves the full HITL workflow — the user has the final say on what gets verified.

---

## Decision 81: Drop Immediate Verification — Scanner-Only in Production
**Source:** Spec B2 requirements review (March 21, 2026)
**Date:** March 21, 2026

The "Log Call" handler (`write_to_db.py`) is a lightweight REST Lambda (python3.12, zip package) — it doesn't have MCP tools, Strands, or Node.js. It can't run `run_verification()` directly. Options considered: Lambda-to-Lambda invocation, DynamoDB Streams trigger, or scanner-only. User chose scanner-only: production verification is completely decoupled from prediction creation. The EventBridge scanner (every 15 minutes) handles all verification. For local evaluation, the eval runner (Spec B3) calls `run_verification()` directly — no production trigger needed. This eliminates the architectural gap and keeps the system simple.

---

## Decision 82: DynamoDB Requires Decimal Not Float — Recursive Converter
**Source:** Spec B2 testing (March 21, 2026)
**Date:** March 21, 2026

DynamoDB's boto3 resource layer rejects Python `float` types with `TypeError: Float types are not supported. Use Decimal types instead`. The `Verification_Outcome` dict contains `confidence: 0.9` as a float from `json.loads()`. Added `_convert_floats_to_decimal()` recursive converter in `verification_store.py` that walks the entire outcome dict and converts all floats to `Decimal(str(value))`. Caught by real integration tests hitting real DynamoDB — would not have been caught by mocks.

---

## Decision 83: Verification Timeout Bumped from 60s to 120s
**Source:** Spec B2 deployment testing (March 21, 2026)
**Date:** March 21, 2026

The first scanner invocation timed out at 60 seconds. MCP cold start takes ~40 seconds (npx downloading packages + Node.js subprocess startup), leaving only ~20 seconds for the agent to invoke tools and reason. Bumped to 120 seconds, giving ~80 seconds after cold start. The scanner Lambda has a 900s total timeout (15 minutes), so 120s per prediction is well within budget. On warm invocations, the agent completes in ~15-20 seconds — the timeout is only relevant for the first prediction on a cold start.

---

## Decision 84: Verification Evaluators NOT Added to EVALUATOR_WEIGHTS
**Source:** Spec B3 requirements review (March 22, 2026)
**Date:** March 22, 2026

The four new verification alignment evaluators (ToolAlignment, SourceAccuracy, CriteriaQuality, StepFidelity) report scores but do NOT contribute to the VB-centric composite score. Per Decision 62, composite weights need empirical grounding from actual verification outcomes before weighting can be calibrated. The evaluators will accumulate data across eval runs, and a future calibration spec will derive weights from correlation between evaluator scores and actual verification success rates.

---

## Decision 85: Golden Dataset Schema Stays at 3.0 for verification_readiness
**Source:** Spec B3 requirements review (March 22, 2026)
**Date:** March 22, 2026

The new `verification_readiness` field on `BasePrediction` is optional with a safe default of `"future"` (conservative — don't attempt verification unless explicitly marked). This is not a breaking change — existing dataset consumers that don't know about the field will continue to work. No schema version bump needed. 10 of 45 base predictions tagged as `immediate` (established facts verifiable now), remaining 35 default to `future`.


---

## Decision 86: Two Separate AgentCore Runtimes (Creation + Verification)
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

Two separate `agentcore launch` deployments instead of one agent with a mode flag. Creation agent is collaborative and user-facing (WebSocket streaming, clarification rounds, AgentCore Memory with STM+LTM). Verification agent is investigative and autonomous (batch execution, no user interaction, DDB-driven with optional Memory enrichment). Different prompts, different scaling profiles, different observability needs. Aligns with AgentCore's recommended multi-agent pattern — the multi-agent CloudFormation template demonstrates exactly this: orchestrator + specialist as separate runtimes.

---

## Decision 87: Verifiability Strength Score Replaces 3-Category System
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

The 3-category system (auto_verifiable / automatable / human_only) is replaced by a continuous 0.0-1.0 verifiability strength score. Mapped to green (0.8-1.0), yellow (0.5-0.79), red (0.0-0.49) for the user. Scored across 5 dimensions: criteria specificity (30%), source availability (25%), temporal clarity (20%), outcome objectivity (15%), tool coverage (10%). The user sees the indicator after round 1 and can choose to do clarification rounds to improve the score. This gives users agency, eliminates false confidence from binary labels, and captures the full spectrum of verifiability.

---

## Decision 88: Hybrid Memory Model — DynamoDB + AgentCore Memory
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

Prediction data lives in two stores, each used for its strength. DynamoDB stores the structured prediction bundle (exact JSON fields: parsed_claim, verification_plan, verifiability_score) — the precise contract between creation and verification agents, loaded by exact prediction_id lookup. AgentCore Memory stores conversational context via three LTM strategies: semantic (prediction facts for cross-prediction learning), user preferences (timezone, sports teams, weather thresholds), and session summaries (clarification round context). The verification agent loads the bundle from DDB for precision and optionally enriches with Memory context for nuance. Neither store alone is sufficient — DDB can't do fuzzy recall or cross-session learning, Memory can't guarantee exact field precision for structured contracts.

---

## Decision 89: Three-Layer Eval Architecture
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

Layer 1: Strands Evals SDK for dev-time evaluation (inner loop, local experiments, prompt iteration, minutes per iteration). Layer 2: AgentCore Evaluations for deployed agent evaluation (bridge, span-level trace analysis, online eval every Nth request, on-demand eval after deploys). Layer 3: Bedrock Evaluations for production monitoring (outer loop, LLM-as-judge at scale, human evaluation for edge cases, trend monitoring over days/weeks). The eval dashboard hero page shows the full lifecycle for any prompt version or configuration change: experiment → deployment → production confidence.

---

## Decision 90: No Hardcoded Prompt Fallbacks in v4
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

v3 had hardcoded fallback constants (Decision 61) — if Prompt Management was unavailable, the agent silently used stale text. v4 removes these. If Prompt Management is down, the agent fails with a clear error. Silent fallback to stale prompts is worse than a visible failure. This was validated by the Prompt Management bug discovered in this session — VB and Review had been running on fallback for weeks without anyone noticing.

---

## Decision 91: AgentCore Built-in Tools Replace Local MCP Subprocesses
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

AgentCore Browser (Chromium in Firecracker microVM) and Code Interpreter (secure Python/JS sandbox) replace the v3 Docker Lambda + npx MCP subprocess architecture. No local MCP subprocesses, no npm packages, no Node.js in the container. Eliminates the 30-second cold start (Decision 73). Browser covers web search, URL fetching, and JavaScript rendering. Code Interpreter covers numerical verification and data analysis. Gateway with domain-specific APIs is Phase 2 (see Decision 93).


---

## Decision 92: Split v4 Into 11 Focused Specs for 90%+ Confidence
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

The v4 AgentCore rebuild is split into 11 specs, each independently deployable and testable. Same reasoning as Decision 3 (Spec 1/2 split), Decision 64 (A1/A2 split), and Decision 75 (B1/B2/B3 split) — smaller specs, higher confidence. The two highest-risk areas were split further: V4-3 (Creation Agent) into core + clarification/streaming, and V4-7 (Three-Layer Eval) into one spec per eval layer. All 11 specs are at ≥88% confidence. Total: 37 requirements, ~84-96 tasks. Critical path: V4-1 → V4-2 → V4-3a → parallel (V4-3b, V4-4, V4-5, V4-7a) → V4-6 → V4-8 → V4-7b → V4-7c.


---

## Decision 93: Built-in Tools First, Gateway Later
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

Start v4 with AgentCore's built-in tools (Browser + Code Interpreter) instead of building Gateway infrastructure with external API dependencies. Browser covers web search (navigate to search engine), URL fetching (navigate to any URL), and JavaScript-heavy sites (full Chromium). Code Interpreter covers numerical verification (calculate percentages, dates, statistics). Zero API keys, zero external dependencies, zero Gateway setup. This simplifies V4-2 from "Gateway + OAuth + Lambda targets" to "wire two built-in tools." Gateway with domain-specific APIs (Brave Search, Alpha Vantage, OpenWeatherMap, sports scores) is Phase 2 — add only when built-in tools become a bottleneck for specific prediction domains. Each Gateway addition graduates a class of predictions from "browser search" to "direct API call." Build smarter, not harder.


---

## Decision 94: Single Agent, Multi-Turn Prompts — Data-Driven Architecture Choice
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026
**Confidence:** 92%

The v4 creation agent uses a single Strands Agent with 4 sequential prompt turns (parse → build plan → score verifiability → review), each managed as a separate versioned prompt in Bedrock Prompt Management. The verification agent uses a single agent with a single prompt. This is a middle ground between the v3 serial graph (4 separate agents) and a single mega-prompt.

**The experimental evidence (16 eval runs, 68 test cases each):**

| Metric | Serial (4 agents) | Single (multi-turn) | Difference |
|---|---|---|---|
| Pass rate | 35% (Run 17) | 34% (Run 18) | Within noise |
| Composite score | 0.52 | 0.49 | Within noise |
| IntentPreservation | 0.81 | 0.80 | Within noise |
| CriteriaMethodAlignment | 0.75 | 0.74 | Within noise |
| PipelineCoherence failures | 2/68 | 2/68 | Identical |
| auto_verifiable accuracy | 100% | 71% | Serial better at routing |
| Parser JSON validity | 96% | 87% | Serial better at formatting |

The reasoning quality metrics (IP, CMA, PipelineCoherence) are identical across architectures. The serial graph's advantages are purely structural (JSON formatting, category routing) — and the categorizer is being replaced by the verifiability scorer anyway.

**Why multi-turn, not 4 separate agents:**
- No silo problem — the agent sees all its own previous reasoning through conversation history
- Simpler code — 1 agent, 1 AgentCore Runtime, no graph wiring
- Faster execution — no inter-agent data serialization overhead
- The eval data proves multi-turn doesn't sacrifice reasoning quality

**Why multi-turn, not 1 mega-prompt:**
- Each prompt is focused and detailed (not a diluted 200-line mega-prompt)
- Each turn is a distinct span in AgentCore Observability — per-step latency, token counts, quality tracing
- Each prompt lives in Prompt Management as a separate versioned resource — iterate on the scorer without touching the parser
- Easier to debug — when quality drops, you can identify which step degraded

**Why 92% confidence, not 100%:**
- The v3 single backend used the same 4 prompts but the v4 creation agent has a new step (verifiability scorer) and different prompt content. The pattern is proven but the specific prompts are new.
- Parser JSON validity was lower on single (87% vs 96%) — the multi-turn approach may need explicit JSON discipline instructions per step.
- If quality is insufficient during V4-3a testing, the fallback is splitting into 2 agents (parse+plan and review+score) — still fewer than v3's 4.

**The 4 creation agent turns:**
1. Parse — extract claim, resolve dates, structure the prediction
2. Build Plan — create verification plan (sources, criteria, steps) using tools
3. Score Verifiability — evaluate the plan's likelihood of successful verification (0.0-1.0)
4. Review — identify assumptions in the plan, generate targeted clarification questions

Each turn receives the full conversation history from previous turns. The agent builds on its own work. If the user clarifies, the whole sequence re-runs with clarification as additional context.

**Portfolio significance:** This is an architectural decision driven by experimental data, not opinion. 16 eval runs with 68 test cases each, 15 evaluators including 6 LLM judges, across 2 architectures. The eval framework that produced this data is the transferable artifact.


---

## Decision 95: Parallel Run Then Phased Teardown — v3 Stays Live Until v4 Validated
**Source:** [Project Update 20](20-project-update-v4-agentcore-architecture-planning.md)
**Date:** March 22, 2026

v3 Lambda backend stays live and untouched through V4-1 to V4-7a. v4 code lives in a separate `calleditv4/` directory. No modifications to v3 during the rebuild. V4-8 (Production Cutover) handles teardown in three phases: (1) Parallel run — deploy v4 to AgentCore, run same predictions through both, compare via eval framework. (2) Traffic cutover — switch frontend to v4 endpoints, keep v3 deployed as rollback target for 1-2 weeks. (3) v3 teardown — delete SAM stack (Lambdas, API Gateway, EventBridge), keep shared resources (DynamoDB tables, Cognito, Prompt Management). v3 predictions in DDB that lack v4 fields (verifiability_score, verifiability_reasoning) are handled gracefully by the verification agent — missing fields treated as v3-era predictions. v3 code archived via git tag.


---

## Decision 96: Zero Mocks by Default in v4 — Proven Value + User Approval Required
**Source:** [Project Update 22](22-project-update-v4-1-agentcore-foundation.md)
**Date:** March 22, 2026

Tightened the no-mocks policy for v4. Decision 78 allowed mocks for unit/property tests — this is now superseded. Default: NO mocks anywhere. Mocks are only allowed if two conditions are met: (1) the agent demonstrates concrete, specific value that cannot be achieved through pure function tests or real integration tests, and (2) the user gives explicit approval before any mock code is written. Never implement a mock silently. Updated `.kiro/steering/no-mocks-policy.md`. The V4-1 property tests (prompt passthrough, response type, exception handling, missing key) were dropped because they only had value with mocks — the real validation is `agentcore invoke --dev` with real Bedrock calls.


---

## Decision 97: playwright and nest-asyncio Are Required Dependencies of AgentCoreBrowser
**Source:** [Project Update 23](23-project-update-v4-2-builtin-tools.md)
**Date:** March 22, 2026

Initially thought `playwright` and `nest-asyncio` were optional (only needed for the alternative direct-Playwright integration path). Wrong — `strands_tools.browser.browser` imports both at module level (`import nest_asyncio` on line 17, `from playwright.async_api import Browser as PlaywrightBrowser` on line 18). The `AgentCoreBrowser` Strands tool wrapper uses Playwright internally to communicate with the AWS-hosted Chromium session via CDP (Chrome DevTools Protocol). Added both to `calleditv4/pyproject.toml`. The imports worked in the project-level venv (which had them from other dependencies) but `agentcore dev` uses the project's `.venv/` which was missing them.


---

## Decision 98: No Fallbacks in Dev, Graceful Fallback in Production
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md) — V4-3a spec planning session
**Date:** March 23, 2026

The v4 prompt client (`calleditv4/src/prompt_client.py`) has environment-dependent fallback behavior controlled by `CALLEDIT_ENV`. When `CALLEDIT_ENV` is not `"production"` (including unset), Prompt Management failures raise exceptions with clear error messages — fail fast, fail visibly. When `CALLEDIT_ENV=production`, failures fall back to hardcoded default prompts, log a warning, and record `"fallback"` in the version manifest. This is a refinement of Decision 90 (no hardcoded fallbacks in v4) — production needs graceful degradation, but dev should never silently use stale prompts.


---

## Decision 99: 3 Turns Not 4 — Merged Score and Review
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md) — V4-3a spec requirements review
**Date:** March 23, 2026

The original 4-turn creation flow from Decision 94 (parse → plan → score → review) is collapsed to 3 turns (parse → plan → review). The score and review turns are merged into a single `calledit-plan-reviewer` turn because scoring verifiability and identifying assumptions are two perspectives on the same analysis of the verification plan. The merged `PlanReview` Pydantic model produces `verifiability_score`, `verifiability_reasoning`, and `reviewable_sections` in one LLM call. This reduces latency by ~1 Bedrock call per prediction and simplifies the flow without losing output quality.


---

## Decision 100: LLM-Native Date Resolution with Timezone Awareness
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md) — V4-3a spec design review
**Date:** March 23, 2026

v4 replaces v3's custom `parse_relative_date` tool (which used the `dateparser` library + `pytz` for deterministic date parsing) with LLM-native date reasoning. The creation agent gets the `current_time` tool from `strands_tools` (returns current date/time with server timezone), Code Interpreter for complex date math, and timezone-aware prompt instructions. The parser prompt instructs the agent to: (1) call `current_time` first for server timezone as default reference, (2) infer timezone from location context in the prediction (e.g., "Lakers" → Pacific), (3) always store `verification_date` in UTC, (4) record timezone assumptions in `date_reasoning`. The reviewer then flags timezone assumptions as high-priority clarification questions. This eliminates `dateparser` and `pytz` dependencies, makes timezone reasoning transparent (visible in `date_reasoning`), and leverages the model's strong date arithmetic capabilities. The tradeoff: occasional model errors on complex date math, mitigated by Code Interpreter availability and reviewer catch.


---

## Decision 98: No Fallbacks in Dev, Graceful Fallback in Production
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md)
**Date:** March 23, 2026

The v4 prompt client's fallback behavior is controlled by the `CALLEDIT_ENV` environment variable. When `CALLEDIT_ENV` is not `production` (including unset), any Prompt Management API failure raises an exception with a clear error message — fail fast, fail visibly. When `CALLEDIT_ENV=production`, the client falls back to hardcoded default prompts, logs a warning, and records `"fallback"` in the version manifest. This is a middle ground between v3's always-fallback approach (Decision 61, which silently used stale prompts for weeks) and the original v4 plan of no fallbacks at all (Decision 90). In dev, you want to know immediately when Prompt Management is broken. In production, you want the agent to keep running even if Prompt Management has a transient failure.

---

## Decision 99: 3 Turns Not 4 — Merged Score and Review
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md)
**Date:** March 23, 2026

The original architecture doc (Decision 94) described 4 turns: Parse → Plan → Score → Review. After analysis during spec requirements review, scoring and reviewing were merged into a single `calledit-plan-reviewer` turn. The reasoning: scoring verifiability and identifying assumptions are two perspectives on the same analysis of the verification plan. The reviewer already needs to deeply understand the plan to generate targeted questions — scoring requires the same deep analysis. Two separate LLM calls doing overlapping analysis wastes tokens and latency. The merged `PlanReview` Pydantic model produces `verifiability_score`, `verifiability_reasoning`, and `reviewable_sections` in one call. This reduces latency by ~1 Bedrock call per prediction and simplifies the flow without losing output quality. The 3 turns are: Parse (`calledit-prediction-parser`), Plan (`calledit-verification-planner`), Review (`calledit-plan-reviewer`).

---

## Decision 100: LLM-Native Date Resolution with Timezone Awareness
**Source:** [Project Update 24](24-project-update-v4-3a-creation-agent-core.md)
**Date:** March 23, 2026

Replaced v3's custom `parse_relative_date` tool (which used the `dateparser` library + `pytz` for deterministic date parsing) with LLM-native date reasoning. The creation agent gets `current_time` from `strands_tools` (returns current date/time with server timezone), Code Interpreter for complex date math, and timezone-aware prompt instructions. The parser prompt instructs the agent to: (1) call `current_time` first for server timezone as default reference, (2) infer timezone from location context when available (e.g., "Lakers" → Pacific), (3) always store `verification_date` in UTC, (4) record timezone assumptions in `date_reasoning`. The reviewer then flags timezone assumptions as high-priority clarification questions. Timezone priority chain: explicit location in prediction > `current_time` tool's timezone > UTC as last resort. This eliminates `dateparser` and `pytz` dependencies, makes timezone reasoning transparent, and leverages Sonnet 4's strong date arithmetic capabilities. The tradeoff: occasional model errors on complex date math, mitigated by Code Interpreter availability and reviewer catch.
