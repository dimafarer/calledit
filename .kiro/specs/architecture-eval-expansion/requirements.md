# Requirements Document: Architecture Backend Abstraction + Per-Agent Evaluators

## Introduction

The CalledIt eval framework currently hardcodes the serial 4-agent graph as the only execution backend. This spec adds a pluggable backend abstraction so that any architecture — serial graph, swarm, single agent, 2-agent, 5-agent, or anything else — can be tested with the same golden dataset, evaluators, and dashboard.

More critically, this spec completes the per-agent evaluator coverage so that every agent in the pipeline is evaluated by an LLM judge asking one question: "Is this agent's output contributing to the two system goals?" The two system goals are:

1. **Understand the full intent** of the user's raw prediction
2. **Repackage with 100% intent preservation** in a structure that enables verification at the right time

Per Decision 44, the Verification Builder's output (verification criteria + verification method) is the primary eval target — it's what the verification agent will actually use when checking if a prediction came true. The category label is just a routing hint. Every other agent is evaluated by how well it sets up the Verification Builder to succeed.

### Evaluation Philosophy: Verification-Builder-Centric Lens

The eval framework evolved through three phases:
- **Phase 1** (Spec 5): Focused on categorization accuracy. CategoryMatch was the primary metric.
- **Phase 2** (Spec 8): Reframed around verification criteria quality. Added IntentPreservation and CriteriaMethodAlignment as primary metrics. CategoryMatch downgraded to tertiary.
- **Phase 3** (this spec): Complete per-agent LLM judge coverage. Every agent gets an LLM judge evaluator asking "did this agent do its specific job in service of the Verification Builder producing the best possible verification plan?"

Static/deterministic evaluators (CategoryMatch, JSONValidity, ClarificationQuality) remain as cheap regression catches but are no longer the primary signal. The LLM judges are the real evaluation layer.

### Per-Agent Evaluator Map (After This Spec)

| Agent | Evaluator | Type | Question It Answers |
|---|---|---|---|
| Parser | **IntentExtraction** | LLM Judge | Did it extract the factual claim, strip framing, resolve temporal refs — giving the Verification Builder clean intent to work with? |
| Categorizer | **CategorizationJustification** | LLM Judge | Given the parser output and available tools, does this routing decision set up the Verification Builder to build the most automated, actionable verification plan possible? |
| Verification Builder | IntentPreservation | LLM Judge | Does the Verification Builder's criteria faithfully capture the user's original intent as checkable conditions? (EXISTS) |
| Verification Builder | CriteriaMethodAlignment | LLM Judge | Does the Verification Builder's method provide a realistic plan to determine true/false? (EXISTS) |
| ReviewAgent | **ClarificationRelevance** | LLM Judge | Do the questions target the Verification Builder's specific operationalization assumptions rather than being generic? |
| Cross-Pipeline | **PipelineCoherence** | LLM Judge | Does each agent build on the previous agent's work, or are they re-interpreting from scratch? |

**Bold** = new in this spec. Non-bold = already exist.

## Glossary

- **Backend**: A pluggable execution engine that processes a prediction and returns a structured output. Any architecture (serial graph, swarm, single agent, 2-agent, 5-agent, etc.) can be a backend as long as it implements the `run()` interface and returns a valid Output_Contract.
- **Output_Contract**: The dict shape all backends must return. Required: `final_output` containing the verification criteria and method (the stuff evaluators actually score). Optional: `agent_outputs` dict with whatever agent keys the backend produces (e.g., `parser`, `categorizer`, `verification_builder`, `review` for the serial graph; just `agent` for single-agent). Evaluators adapt to whatever agent keys are present.
- **Backend_Registry**: A directory of backend modules (`backends/`). Each module implements `run(prediction_text, tool_manifest) -> OutputContract` and `metadata() -> dict` (name, description, model_config). Adding a new architecture means adding a new module — no changes to the eval runner.
- **IntentExtraction_Evaluator**: LLM judge scoring whether the Parser correctly extracted the factual claim, stripping framing language and resolving temporal references — giving the Verification Builder clean intent to work with.
- **CategorizationJustification_Evaluator**: LLM judge scoring whether the Categorizer's routing decision (given parser output and tool manifest) sets up the Verification Builder to build the most automated, actionable verification plan possible. Not label matching — routing quality for Verification Builder success.
- **ClarificationRelevance_Evaluator**: LLM judge scoring whether the ReviewAgent's clarification questions target the Verification Builder's specific operationalization assumptions rather than being generic.
- **PipelineCoherence_Evaluator**: LLM judge that sees all agent outputs together and scores whether each agent built on the previous agent's work without losing or distorting the user's intent. Adapts to whatever agents are present in the output.

## Requirements

### Requirement 1: Pluggable Backend Abstraction

**User Story:** As an eval developer, I want a pluggable backend system so I can experiment with any architecture (serial, swarm, single, 2-agent, 5-agent, etc.) without changing the eval runner, evaluators, or dashboard.

#### Acceptance Criteria

1. THE eval runner SHALL accept a `--backend` CLI argument that takes any registered backend name, defaulting to `serial`.
2. BACKENDS SHALL be discovered from a `backends/` directory. Each backend is a Python module implementing: `run(prediction_text: str, tool_manifest: dict) -> OutputContract` and `metadata() -> dict`.
3. THE `metadata()` function SHALL return: `name` (str), `description` (str), `model_config` (dict mapping agent/role names to model IDs).
4. ADDING a new architecture SHALL require only adding a new module to `backends/` — no changes to the eval runner, evaluators, or dashboard.
5. THE eval runner SHALL list available backends with `--list-backends`.
6. THE eval report SHALL record the `architecture` field from the backend's metadata name.
7. THE eval report SHALL record the `model_config` field from the backend's metadata.

### Requirement 2: Flexible Output Contract

**User Story:** As an eval developer, I want the output contract to work with any number of agents so that backends with 1, 2, 4, or 5 agents all produce evaluable output.

#### Acceptance Criteria

1. THE Output_Contract SHALL require a `final_output` dict containing at minimum: `prediction_statement`, `verifiable_category`, `verification_method` (with `criteria`, `source`, `steps`), and `category_reasoning`.
2. THE Output_Contract SHALL include an optional `agent_outputs` dict where keys are agent names and values are each agent's structured output. The serial backend would have keys `parser`, `categorizer`, `verification_builder`, `review`. A single-agent backend might have just `agent`. A 2-agent backend might have `parser_categorizer`, `vb_review`.
3. THE Output_Contract SHALL include a `metadata` dict with: `architecture` (str), `model_config` (dict), `execution_time_ms` (int), and any backend-specific metadata (e.g., `collaboration_rounds` for swarm).
4. EVALUATORS SHALL adapt to the agent keys present in `agent_outputs`. Per-agent evaluators (IntentExtraction, CategorizationJustification, etc.) SHALL only run when their target agent key exists. PipelineCoherence SHALL evaluate whatever agents are present.
5. THE `final_output` SHALL be the canonical source for evaluators that score the pipeline's end result (IntentPreservation, CriteriaMethodAlignment). These evaluators work regardless of how many agents produced the output.

### Requirement 3: Serial Backend (Existing Graph as Plugin)

**User Story:** As an eval developer, I want the existing serial 4-agent graph wrapped as a pluggable backend so it works with the new abstraction.

#### Acceptance Criteria

1. THE serial backend SHALL wrap the existing `run_test_graph()` function.
2. THE serial backend SHALL populate `agent_outputs` with keys: `parser`, `categorizer`, `verification_builder`, `review`.
3. THE serial backend SHALL populate `final_output` from the verification_builder and categorizer outputs.
4. THE serial backend SHALL be the default when `--backend` is not specified.

### Requirement 4: Single-Agent Backend

**User Story:** As an eval developer, I want a single-agent backend that processes predictions in one model call with one context, so I can compare it against the multi-agent graph.

#### Acceptance Criteria

1. THE single-agent backend SHALL use one model invocation (Opus 4.6) with a comprehensive prompt covering all four pipeline steps.
2. THE single-agent backend SHALL populate `final_output` from the single response.
3. THE single-agent backend SHALL populate `agent_outputs` with a single key `agent` containing the full response.
4. THE single-agent backend SHALL use the same tools available to the serial graph (web_search, etc. per tool manifest).
5. THE single-agent backend's prompt SHALL include the Verification Builder v2 operationalization and specificity matching instructions.

### Requirement 5: Swarm Backend

**User Story:** As an eval developer, I want a swarm backend where agents collaborate iteratively, so I can compare collaborative multi-round processing against serial and single-agent approaches.

#### Acceptance Criteria

1. THE swarm backend SHALL use multiple agents that collaborate on a shared output over multiple rounds.
2. THE swarm backend SHALL populate `final_output` from the collaborative result.
3. THE swarm backend SHALL populate `agent_outputs` with keys for each participating agent.
4. THE swarm backend SHALL record `collaboration_rounds` in the output metadata.

### Requirement 6: IntentExtraction Evaluator (Parser)

**User Story:** As an eval developer, I want an LLM judge that scores whether the Parser correctly extracted the factual claim — giving the Verification Builder clean intent to work with.

#### Acceptance Criteria

1. THE IntentExtraction_Evaluator SHALL accept the raw prediction text, the Parser's extracted prediction statement, the Parser's resolved temporal references, and the expected verification criteria from the golden dataset.
2. THE IntentExtraction_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: framing language stripped ("I bet", "I think" removed), temporal references resolved to concrete dates, factual claim preserved without distortion — all in service of giving the Verification Builder clean input.
3. THE IntentExtraction_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "IntentExtraction", judge_reasoning, and judge_model.
4. THE eval runner SHALL invoke IntentExtraction_Evaluator when `--judge` is enabled AND the `agent_outputs` contains a `parser` key.

### Requirement 7: CategorizationJustification Evaluator (Categorizer)

**User Story:** As an eval developer, I want an LLM judge that scores whether the Categorizer's routing decision sets up the Verification Builder for success — not just whether the label matches.

#### Acceptance Criteria

1. THE CategorizationJustification_Evaluator SHALL accept the Parser's extracted claim, the Categorizer's output (category + reasoning), the tool manifest (available tools), and the final_output (to assess downstream impact on Verification Builder).
2. THE CategorizationJustification_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: does the routing decision enable the Verification Builder to build the most automated verification plan possible given available tools? Did the categorizer correctly assess what's automatable vs what requires human judgment? Would a different routing have led to a better Verification Builder output?
3. THE CategorizationJustification_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "CategorizationJustification", judge_reasoning, and judge_model.
4. THE eval runner SHALL invoke CategorizationJustification_Evaluator when `--judge` is enabled AND the `agent_outputs` contains a `categorizer` key.
5. THIS evaluator replaces CategoryMatch as the primary categorizer evaluation. CategoryMatch remains as a cheap deterministic check but is no longer weighted in the primary pass rate.

### Requirement 8: ClarificationRelevance Evaluator (ReviewAgent)

**User Story:** As an eval developer, I want an LLM judge that scores whether the ReviewAgent's questions target the Verification Builder's operationalization assumptions, so I can measure whether the review loop actually improves the verification plan.

#### Acceptance Criteria

1. THE ClarificationRelevance_Evaluator SHALL accept the Verification Builder's verification criteria (with operationalization assumptions), the ReviewAgent's clarification questions, and the prediction text.
2. THE ClarificationRelevance_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: questions target specific Verification Builder assumptions (not generic), questions would improve verification accuracy if answered, questions help the Verification Builder produce a better plan in the next round.
3. THE ClarificationRelevance_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "ClarificationRelevance", judge_reasoning, and judge_model.
4. THE eval runner SHALL invoke ClarificationRelevance_Evaluator when `--judge` is enabled AND the `agent_outputs` contains a `review` key.
5. THIS evaluator replaces ClarificationQuality (keyword-based) as the primary review evaluation. ClarificationQuality remains as a cheap deterministic check.

### Requirement 9: PipelineCoherence Evaluator (Cross-Agent)

**User Story:** As an eval developer, I want an LLM judge that evaluates whether the agents build on each other's work or re-interpret from scratch, so I can detect the silo problem and compare coherence across architectures.

#### Acceptance Criteria

1. THE PipelineCoherence_Evaluator SHALL accept all agent outputs from `agent_outputs` (whatever keys are present) plus the original prediction text and `final_output`.
2. THE PipelineCoherence_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: does each agent's output reference or build on the previous agent's work? Is there a coherent chain of reasoning from first agent to last? Is the user's intent preserved and refined (not lost or distorted) through the chain?
3. THE PipelineCoherence_Evaluator SHALL adapt to any number of agents — for a single-agent backend it scores internal coherence of the response sections; for a 4-agent backend it scores inter-agent coherence.
4. THE PipelineCoherence_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "PipelineCoherence", judge_reasoning, and judge_model.
5. THE eval runner SHALL invoke PipelineCoherence_Evaluator for every backend when `--judge` is enabled.
6. THE PipelineCoherence_Evaluator is especially important for architecture comparison — the serial graph may score low (silo problem) while the single agent scores high (one context), and this evaluator quantifies that difference.

### Requirement 10: Dashboard Architecture Comparison

**User Story:** As an eval developer, I want the dashboard to compare runs across architectures, so I can make data-driven decisions about which architecture to use.

#### Acceptance Criteria

1. THE dashboard sidebar SHALL include an architecture filter populated from available architecture values across loaded runs.
2. THE dashboard Prompt Correlation page SHALL support comparing runs with different architecture values, showing architecture alongside prompt version diffs.
3. THE dashboard Trends page SHALL support filtering by architecture to show trends within a single architecture.
4. WHEN comparing runs across architectures, THE dashboard SHALL display a notice: "Comparing different architectures — score differences may reflect architecture effects, not just prompt changes."

### Requirement 11: Eval Runner Judge Integration

**User Story:** As an eval developer, I want all LLM judge evaluators integrated into the eval runner so they run automatically with `--judge` and adapt to whatever backend produced the output.

#### Acceptance Criteria

1. WHEN `--judge` is enabled, THE eval runner SHALL invoke all applicable LLM judge evaluators based on which agent keys exist in `agent_outputs`: IntentExtraction (if `parser`), CategorizationJustification (if `categorizer`), ClarificationRelevance (if `review`), PipelineCoherence (always). IntentPreservation and CriteriaMethodAlignment (existing) always run against `final_output`.
2. THE eval report SHALL group evaluator results by: final-output evaluators (IntentPreservation, CriteriaMethodAlignment), per-agent evaluators (IntentExtraction, CategorizationJustification, ClarificationRelevance), cross-pipeline evaluators (PipelineCoherence).
3. THE eval report SHALL compute a "Verification-Builder-centric score" — a weighted composite where IntentPreservation and CriteriaMethodAlignment have the highest weight, and other evaluators are weighted by how directly they impact Verification Builder output quality.
4. THE DDB reasoning store SHALL record all judge evaluator results per test case, including judge_reasoning for each.
5. THE eval runner SHALL report which evaluators were skipped (and why) when a backend doesn't produce certain agent keys.
