# Requirements Document

## Introduction

A prompt evaluation and observability system for the CalledIt prediction verification system, built on three managed AWS services: Bedrock Prompt Management, CloudWatch GenAI Observability, and AgentCore Evaluations. The system replaces hardcoded Python prompt constants with versioned managed prompts, instruments the 4-agent Strands graph (Parser → Categorizer → Verification Builder → ReviewAgent) with OpenTelemetry for per-agent latency and token tracking, and evaluates agent quality using custom evaluators against a golden dataset with span-level scoring. The architecture enables prompt version → score correlation, regression detection, and continuous production monitoring.

## Glossary

- **Prediction_Graph**: The 4-agent Strands graph (Parser → Categorizer → Verification Builder → ReviewAgent) running on Lambda with SnapStart, using Bedrock Claude Sonnet 4
- **Managed_Prompt**: A prompt stored in Bedrock Prompt Management with immutable version numbers, variables support, and API-invokable retrieval
- **Prompt_Version_Manifest**: A record of the specific prompt version numbers (parser:vN, categorizer:vN, vb:vN, review:vN) used during a given evaluation or production invocation
- **OTEL_Instrumentation**: OpenTelemetry SDK integration that emits per-agent spans, token counts, and latency metrics from the Strands graph execution
- **GenAI_Dashboard**: A CloudWatch dashboard displaying per-agent latency, token usage, error rates, and end-to-end trace data from OTEL-instrumented graph executions
- **Custom_Evaluator**: An AgentCore Evaluations evaluator implementing domain-specific scoring logic (CategoryMatch, Convergence, JSONValidity, ClarificationQuality)
- **On_Demand_Evaluation**: A developer-initiated evaluation run that executes the golden dataset against the Prediction_Graph and scores the resulting OTEL traces using Custom_Evaluators
- **Online_Evaluation**: Continuous production evaluation that samples 10% of live sessions and scores them using Custom_Evaluators via AgentCore
- **Golden_Dataset**: A JSON file containing base predictions (Layer 1) and fuzzy predictions (Layer 2) with expected per-agent outputs, difficulty annotations, and tool manifest configurations
- **Base_Prediction**: A fully-specified prediction requiring zero clarification, with known expected outputs for each agent individually (Layer 1)
- **Fuzzy_Prediction**: A degraded version of a base prediction with information removed, requiring clarification to converge to the base prediction's per-agent outputs (Layer 2)
- **Convergence**: The property that a fuzzy prediction, after clarification, produces per-agent outputs equivalent to its corresponding base prediction
- **Verifiability_Category**: One of three classification values: auto_verifiable (verifiable now with current tools), automatable (could be verified with a plausible tool), human_only (requires subjective human judgment)
- **Span_Level_Analysis**: AgentCore's ability to evaluate individual agent nodes within a trace independently, isolating per-agent quality from cascading failures
- **Score_History**: A persistent record of evaluation scores correlated with prompt version manifests, enabling regression detection across prompt iterations
- **Agent_Factory_Function**: The create_*_agent() functions (create_parser_agent, create_categorizer_agent, create_verification_builder_agent, create_review_agent) that construct Strands Agent instances with system prompts and tools

**Important Note — Clarification Is Not Just About Upgrading Verifiability:**
Some predictions remain `human_only` even after clarification (e.g., "Tom will wear that shirt"). The clarification loop still adds value by making the prediction more precise for the human who will eventually verify it. A fuzzy `human_only` prediction should converge to a more detailed `human_only` base prediction — not upgrade to a different category. The golden dataset includes test cases where clarification improves precision without changing the category (Decision 15).

## Requirements

### Requirement 1: OpenTelemetry Instrumentation of the Strands Graph (Phase 1)

**User Story:** As a developer, I want the 4-agent Strands graph instrumented with OpenTelemetry, so that each agent execution emits spans with latency, token counts, and trace context for downstream observability and evaluation.

#### Acceptance Criteria

1. WHEN the Prediction_Graph executes, THE OTEL_Instrumentation SHALL emit one span per agent node (parser, categorizer, verification_builder, review) containing the agent name, start time, end time, and execution status
2. WHEN a Bedrock model invocation occurs within an agent span, THE OTEL_Instrumentation SHALL record input token count, output token count, and model ID as span attributes
3. WHEN the Prediction_Graph executes, THE OTEL_Instrumentation SHALL emit a parent trace span encompassing all agent spans with the end-to-end duration
4. WHEN a Managed_Prompt version is used by an agent, THE OTEL_Instrumentation SHALL record the prompt identifier and version number as span attributes (e.g., `prompt.id=parser`, `prompt.version=3`)
5. WHEN the Lambda function initializes with SnapStart, THE OTEL_Instrumentation SHALL restore the OTEL collector state correctly after snapshot restore without losing trace context
6. IF the OTEL collector fails to export spans, THEN THE OTEL_Instrumentation SHALL log the export failure and continue graph execution without blocking the prediction response

### Requirement 2: CloudWatch GenAI Observability Dashboards and Alarms (Phase 1)

**User Story:** As a developer, I want CloudWatch dashboards showing per-agent latency, token usage, and error rates, so that I can monitor operational health and identify performance bottlenecks in the agent graph.

#### Acceptance Criteria

1. WHEN OTEL spans are exported, THE GenAI_Dashboard SHALL display per-agent latency metrics (p50, p95, p99) for each of the four agents separately
2. WHEN OTEL spans are exported, THE GenAI_Dashboard SHALL display per-agent token usage (input tokens, output tokens) as time-series metrics
3. WHEN OTEL spans are exported, THE GenAI_Dashboard SHALL display end-to-end graph execution latency as a time-series metric
4. WHEN per-agent p95 latency exceeds a configurable threshold, THE GenAI_Dashboard SHALL trigger a CloudWatch alarm
5. WHEN per-agent token usage exceeds a configurable threshold per invocation, THE GenAI_Dashboard SHALL trigger a CloudWatch alarm
6. THE GenAI_Dashboard SHALL provide trace-level drill-down from a latency spike to the individual agent spans within that trace


### Requirement 3: Bedrock Prompt Management Migration (Phase 2)

**User Story:** As a developer, I want the four agent system prompts migrated from hardcoded Python constants to Bedrock Prompt Management, so that prompts are versioned with immutable version numbers and can be iterated independently of code deployments.

#### Acceptance Criteria

1. THE Managed_Prompt service SHALL store four prompts (parser, categorizer, verification_builder, review) each with an initial version (v1) matching the current hardcoded SYSTEM_PROMPT constants
2. WHEN a Managed_Prompt is created or updated, THE Managed_Prompt service SHALL assign an immutable version number that cannot be modified after creation
3. WHEN an Agent_Factory_Function initializes an agent, THE Agent_Factory_Function SHALL fetch the prompt text from Bedrock Prompt Management using the prompt identifier and a configurable version number instead of using a hardcoded Python constant
4. WHEN the Managed_Prompt contains variables (prediction text, datetime, timezone, tool_manifest), THE Agent_Factory_Function SHALL resolve variables at agent creation time using the Bedrock Prompt Management variables API
5. WHEN the Lambda function cold-starts with SnapStart, THE Agent_Factory_Function SHALL cache the fetched prompt text in the SnapStart snapshot so that warm invocations do not make additional Bedrock Prompt Management API calls
6. IF the Bedrock Prompt Management API call fails during agent initialization, THEN THE Agent_Factory_Function SHALL fall back to a bundled copy of the prompt and log the failure at ERROR level

### Requirement 4: Golden Dataset with Enhanced Schema (Phase 3)

**User Story:** As a developer, I want a golden dataset with per-agent expected outputs, difficulty annotations, and tool manifest configurations, so that evaluations can score each agent independently and weight results by difficulty.

#### Acceptance Criteria

1. THE Golden_Dataset SHALL store test cases in a JSON file within the repository with a schema version field to support future format changes
2. WHEN a Base_Prediction test case is defined, THE Golden_Dataset SHALL include: prediction text, difficulty annotation (easy, medium, or hard), tool_manifest_config specifying which tools are registered, and expected_per_agent_outputs containing expected output for each of the four agents individually
3. WHEN a Fuzzy_Prediction test case is defined, THE Golden_Dataset SHALL include: fuzzy prediction text, a reference to the corresponding Base_Prediction, simulated clarification answers, expected clarification question topics, and expected post-clarification per-agent outputs
4. THE Golden_Dataset SHALL contain at least 15 Base_Predictions covering all three Verifiability_Categories (auto_verifiable, automatable, human_only) with at least 3 test cases per category
5. THE Golden_Dataset SHALL include at least 3 Fuzzy_Prediction test cases where clarification improves precision without changing the Verifiability_Category (human_only remains human_only after clarification)
6. WHEN a test case specifies a tool_manifest_config, THE Golden_Dataset SHALL include the tool names and capability descriptions that the Categorizer agent should see during evaluation

### Requirement 5: AgentCore Custom Evaluators (Phase 3)

**User Story:** As a developer, I want four custom evaluators (CategoryMatch, Convergence, JSONValidity, ClarificationQuality) registered in AgentCore Evaluations, so that agent outputs are scored with domain-specific metrics at the span level.

#### Acceptance Criteria

1. WHEN a categorizer span is evaluated, THE CategoryMatchEvaluator SHALL compute a deterministic binary score (1.0 if actual Verifiability_Category equals expected, 0.0 otherwise) by comparing the categorizer span output against the Golden_Dataset expected category
2. WHEN a parser, categorizer, or verification_builder span is evaluated, THE JSONValidityEvaluator SHALL compute a structural score (0.0 to 1.0) based on field presence and type correctness per agent: parser requires prediction_statement, verification_date, and date_reasoning; categorizer requires verifiable_category and category_reasoning; verification_builder requires verification_method with source, criteria, and steps as non-empty lists
3. WHEN a full round-1-plus-round-2 trace from a Fuzzy_Prediction is evaluated, THE ConvergenceEvaluator SHALL compute a score (0.0 to 1.0) by comparing the round 2 per-agent outputs against the corresponding Base_Prediction expected per-agent outputs, with Verifiability_Category match weighted highest
4. WHEN a review span is evaluated, THE ClarificationQualityEvaluator SHALL compute a score (0.0 to 1.0) based on the proportion of expected topic keywords from the Golden_Dataset that appear in the ReviewAgent's generated clarification questions
5. WHEN any Custom_Evaluator scores a span, THE Custom_Evaluator SHALL record the score, the evaluator name, and the evaluated span ID in the evaluation result for traceability
6. IF an agent span contains malformed output that cannot be parsed, THEN THE JSONValidityEvaluator SHALL assign a score of 0.0 and record the parse error message in the evaluation result

### Requirement 6: On-Demand Evaluation for Development (Phase 3)

**User Story:** As a developer, I want to run the golden dataset against the Prediction_Graph and score the results using AgentCore custom evaluators, so that I can measure prompt quality during development before deploying changes.

#### Acceptance Criteria

1. WHEN an On_Demand_Evaluation is initiated, THE On_Demand_Evaluation SHALL load test cases from the Golden_Dataset, execute each through the OTEL-instrumented Prediction_Graph, and collect the resulting traces
2. WHEN a Base_Prediction test case is executed, THE On_Demand_Evaluation SHALL invoke the Prediction_Graph once (round 1) and submit the trace to AgentCore for evaluation with CategoryMatchEvaluator, JSONValidityEvaluator, and ClarificationQualityEvaluator
3. WHEN a Fuzzy_Prediction test case is executed, THE On_Demand_Evaluation SHALL invoke the Prediction_Graph for round 1, construct a round 2 prompt using simulated clarification answers from the Golden_Dataset, invoke the Prediction_Graph again, and submit both traces to AgentCore for evaluation including the ConvergenceEvaluator
4. WHEN an On_Demand_Evaluation completes, THE On_Demand_Evaluation SHALL produce a report containing: per-test-case scores from each Custom_Evaluator, per-agent aggregate scores, per-category accuracy, overall pass rate, and the Prompt_Version_Manifest used
5. WHEN the On_Demand_Evaluation is invoked with a test case filter, THE On_Demand_Evaluation SHALL execute only the test cases matching the filter (by name, category, layer, or difficulty)
6. IF the Prediction_Graph returns an error for a test case, THEN THE On_Demand_Evaluation SHALL record the test case as failed with the error message and assign a score of 0.0 for all evaluators on that test case

### Requirement 7: Online Evaluation for Production (Phase 3)

**User Story:** As a developer, I want continuous production monitoring that samples and scores live prediction sessions, so that I can detect quality regressions in production without manual eval runs.

#### Acceptance Criteria

1. WHEN a production prediction session completes, THE Online_Evaluation SHALL sample the session for evaluation at a configurable rate (default 10% of sessions)
2. WHEN a sampled session trace is evaluated, THE Online_Evaluation SHALL apply the CategoryMatchEvaluator and JSONValidityEvaluator to the relevant agent spans within the trace
3. WHEN Online_Evaluation scores are computed, THE Online_Evaluation SHALL publish the scores as CloudWatch custom metrics with dimensions for agent name, evaluator name, and prompt version
4. WHEN the rolling average of any Custom_Evaluator score drops below a configurable threshold over a configurable time window, THE Online_Evaluation SHALL trigger a CloudWatch alarm indicating quality regression
5. THE Online_Evaluation SHALL record the Prompt_Version_Manifest as a trace attribute on every production trace so that evaluation scores can be correlated to specific prompt versions
6. IF AgentCore Evaluations is unavailable, THEN THE Online_Evaluation SHALL continue serving predictions without evaluation and log the evaluation skip at WARN level

### Requirement 8: Score Tracking and Regression Detection (Phase 4)

**User Story:** As a developer, I want to compare evaluation scores across prompt iterations with prompt version correlation, so that I can verify prompt changes improve quality and detect regressions tied to specific prompt version changes.

#### Acceptance Criteria

1. WHEN an On_Demand_Evaluation completes, THE Score_History SHALL append the per-agent aggregate scores, per-category accuracy, overall pass rate, timestamp, and the Prompt_Version_Manifest to a persistent score history file
2. WHEN a developer requests a comparison, THE Score_History SHALL display the current evaluation scores alongside the previous evaluation scores with delta indicators (improved, regressed, unchanged) for each metric
3. WHEN a comparison shows any per-agent score or per-category accuracy decreased compared to the previous evaluation, THE Score_History SHALL identify which prompt version changed between the two evaluations and flag the correlation
4. WHEN a comparison shows regression, THE Score_History SHALL display which specific agent's prompt version changed and the corresponding score delta for that agent
5. THE Score_History SHALL store evaluation results in a JSON file within the repository, keyed by timestamp and Prompt_Version_Manifest
6. WHEN the On_Demand_Evaluation is invoked with a dry-run flag, THE On_Demand_Evaluation SHALL list the test cases that would be executed and the estimated number of Prediction_Graph invocations without making any API calls

### Requirement 9: LLM-as-Judge Reasoning Quality Evaluator (Phase 3)

**User Story:** As a developer, I want an LLM-as-judge evaluator that scores the quality of agent reasoning (not just output correctness), so that I can detect when agents produce correct answers with poor reasoning, generic boilerplate, or unsound logic.

#### Acceptance Criteria

1. WHEN a categorizer span is evaluated, THE ReasoningQualityEvaluator SHALL invoke a judge model to score whether the category_reasoning is sound, specific to the prediction, and references relevant concepts (not generic boilerplate), returning a score from 0.0 to 1.0
2. WHEN a verification_builder span is evaluated, THE ReasoningQualityEvaluator SHALL invoke a judge model to score whether the verification_method steps are actionable and specific to the prediction (not generic "manual review" boilerplate), returning a score from 0.0 to 1.0
3. WHEN a review span is evaluated, THE ReasoningQualityEvaluator SHALL invoke a judge model to score whether the clarification questions target the actual ambiguity in the prediction (not generic questions that could apply to any prediction), returning a score from 0.0 to 1.0
4. WHEN a Golden_Dataset test case includes an evaluation_rubric field, THE ReasoningQualityEvaluator SHALL include the rubric in the judge prompt so that scoring is grounded in domain-specific expectations
5. THE ReasoningQualityEvaluator SHALL use a different model than the agents being evaluated (to avoid self-evaluation bias), defaulting to a configurable judge model
6. WHEN the ReasoningQualityEvaluator scores a span, THE result SHALL include the judge model's reasoning explanation alongside the numeric score for human review
