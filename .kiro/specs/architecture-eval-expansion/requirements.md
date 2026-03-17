# Requirements Document: Architecture Backend Abstraction + Per-Agent Evaluators

## Introduction

The CalledIt eval framework currently hardcodes the serial 4-agent graph as the only execution backend. This spec adds a backend abstraction so that serial graph, agent swarm, and single-agent architectures can be tested with the same golden dataset, evaluators, and dashboard. It also adds per-agent evaluators (IntentExtraction for Parser, ClarificationRelevance for ReviewAgent) so that each agent's contribution to the system goals is measured independently — critical for meaningful architecture comparison.

## Glossary

- **Backend**: The execution engine that processes a prediction and returns a structured output dict. Three variants: serial (4-agent graph), swarm (collaborative multi-round), single (one agent, one context).
- **Output_Contract**: The dict shape all backends must return: `{parser: {...}, categorizer: {...}, verification_builder: {...}, review: {...}}` with consistent field names regardless of architecture.
- **IntentExtraction_Evaluator**: LLM-as-judge evaluator scoring whether the Parser correctly extracted the factual claim from the raw prediction, stripping framing language and resolving temporal references.
- **ClarificationRelevance_Evaluator**: LLM-as-judge evaluator scoring whether the ReviewAgent's clarification questions target the VB's specific operationalization assumptions rather than being generic.

## Requirements

### Requirement 1: Backend Abstraction Interface

**User Story:** As an eval developer, I want a backend abstraction that lets me swap execution engines without changing the eval runner, evaluators, or dashboard.

#### Acceptance Criteria

1. THE eval runner SHALL accept a `--backend` CLI argument with values `serial`, `swarm`, or `single`, defaulting to `serial`.
2. EACH backend SHALL accept a prediction text and tool manifest as input and return a dict conforming to the Output_Contract.
3. THE Output_Contract SHALL require keys: `parser`, `categorizer`, `verification_builder`, `review`, each containing the agent's structured output dict.
4. THE eval report SHALL record the `architecture` field matching the `--backend` value.
5. THE eval report SHALL record the `model_config` field mapping agent names to model IDs used by the backend.

### Requirement 2: Single-Agent Backend

**User Story:** As an eval developer, I want a single-agent backend that processes predictions in one model call with one context, so I can compare it against the multi-agent graph.

#### Acceptance Criteria

1. THE single-agent backend SHALL use one model invocation (Opus 4.6) with a comprehensive prompt covering all four pipeline steps.
2. THE single-agent backend SHALL return output conforming to the Output_Contract with all four keys populated from the single response.
3. THE single-agent backend SHALL use the same tools available to the serial graph (web_search, etc. per tool manifest).
4. THE single-agent backend's prompt SHALL include the VB v2 operationalization and specificity matching instructions.

### Requirement 3: Swarm Backend

**User Story:** As an eval developer, I want a swarm backend where agents collaborate iteratively, so I can compare collaborative multi-round processing against serial and single-agent approaches.

#### Acceptance Criteria

1. THE swarm backend SHALL use multiple agents that collaborate on a shared output over multiple rounds.
2. THE swarm backend SHALL return output conforming to the Output_Contract after collaboration completes.
3. THE swarm backend SHALL record the number of collaboration rounds in the output metadata.

### Requirement 4: IntentExtraction Evaluator (Parser)

**User Story:** As an eval developer, I want an evaluator that scores whether the Parser correctly extracted the factual claim from the raw prediction, so I can measure parser quality independently.

#### Acceptance Criteria

1. THE IntentExtraction_Evaluator SHALL accept the raw prediction text, the Parser's extracted prediction statement, and the expected verification criteria from the golden dataset.
2. THE IntentExtraction_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: framing language stripped, temporal references resolved, factual claim preserved.
3. THE IntentExtraction_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "IntentExtraction", judge_reasoning, and judge_model.
4. THE eval runner SHALL invoke IntentExtraction_Evaluator for each base prediction when `--judge` is enabled.

### Requirement 5: ClarificationRelevance Evaluator (ReviewAgent)

**User Story:** As an eval developer, I want an evaluator that scores whether the ReviewAgent's questions target the VB's operationalization assumptions, so I can measure review quality independently.

#### Acceptance Criteria

1. THE ClarificationRelevance_Evaluator SHALL accept the VB's verification criteria (with operationalization assumptions), the ReviewAgent's clarification questions, and the prediction text.
2. THE ClarificationRelevance_Evaluator SHALL use Strands Evals SDK OutputEvaluator with a rubric scoring: questions target specific assumptions, questions would improve verification accuracy if answered, questions are not generic.
3. THE ClarificationRelevance_Evaluator SHALL return a structured result with score (0.0-1.0), evaluator label "ClarificationRelevance", judge_reasoning, and judge_model.
4. THE eval runner SHALL invoke ClarificationRelevance_Evaluator for each base prediction when `--judge` is enabled.

### Requirement 6: Dashboard Architecture Comparison

**User Story:** As an eval developer, I want the dashboard to compare runs across architectures, so I can make data-driven decisions about which architecture to use.

#### Acceptance Criteria

1. THE dashboard sidebar SHALL include an architecture filter populated from available architecture values across loaded runs.
2. THE dashboard Prompt Correlation page SHALL support comparing runs with different architecture values, showing architecture alongside prompt version diffs.
3. THE dashboard Trends page SHALL support filtering by architecture to show trends within a single architecture.
4. WHEN comparing runs across architectures, THE dashboard SHALL display a notice: "Comparing different architectures — score differences may reflect architecture effects, not just prompt changes."
