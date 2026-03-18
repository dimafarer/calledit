# Requirements Document: Comparative Eval Dashboard

## Introduction

Spec 10 (architecture-eval-expansion) built the pluggable backend system, per-agent LLM judge evaluators, and basic dashboard architecture filtering. The infrastructure is in place — backends exist, evaluators exist, the eval runner supports `--backend` and `--judge` flags. What's missing is the actual comparative eval runs and the dashboard visualizations needed to analyze the results.

This spec has two halves:

1. **Run the comparative evals** — Execute the recommended run configurations from Project Update 10 on both serial and single-agent backends, producing the data needed for architecture comparison.
2. **Build the dashboard visualizations** — Create new pages and enhance existing pages so the architecture comparison data can be analyzed visually: side-by-side evaluator scores, per-agent judge breakdowns, heatmap groupings, coherence analysis across all 6 LLM judges, and a dedicated architecture comparison page.

The two system goals remain the north star:
1. Understand the full intent of the user's raw prediction
2. Repackage with 100% intent preservation in a structure that enables verification at the right time

### Key Decisions Referenced
- Decision 44: Verification criteria is the primary eval target
- Decision 49: Architecture backend abstraction
- Decision 50: Isolated single-variable testing
- Decision 52: PipelineCoherence evaluator for silo problem
- Decision 53: Verification-Builder-centric composite score
- Decision 55: Pluggable backend with flexible output contract
- Decision 56: Single backend uses same prompts via Prompt Management

## Glossary

- **Dashboard**: The Streamlit application in `eval/dashboard/` that visualizes eval run data across pages (Trends, Heatmap, Prompt Correlation, Reasoning Explorer, Coherence View, Fuzzy Convergence, and the new Architecture Comparison page).
- **Architecture_Comparison_Page**: A new dedicated dashboard page that shows side-by-side comparison of two runs from different architectures, including per-evaluator scores, Verification-Builder-centric composite scores, per-category breakdowns, and execution time.
- **Evaluator_Group**: A classification of evaluators by type: final-output (IntentPreservation, CriteriaMethodAlignment), per-agent (IntentExtraction, CategorizationJustification, ClarificationRelevance), cross-pipeline (PipelineCoherence), deterministic (CategoryMatch, JSONValidity, ClarificationQuality, Convergence).
- **Per_Agent_Aggregates**: A dict in run summaries keyed by evaluator name, containing average scores from per-agent LLM judges (IntentExtraction, CategorizationJustification, ClarificationRelevance). Populated when `--judge` is used.
- **Verification_Builder_Centric_Score**: The Verification-Builder-centric composite score — a weighted composite where IntentPreservation and CriteriaMethodAlignment have the highest weight. The primary metric for comparing architectures.
- **Comparative_Eval_Run**: An eval run executed specifically to compare two architectures using the same prompt versions, dataset, and judge configuration, differing only in the `--backend` flag.
- **Silo_Problem**: The tendency of agents in a serial graph to re-interpret from scratch rather than building on the previous agent's work. Quantified by the PipelineCoherence evaluator.

## Requirements

### Requirement 1: Dashboard Data Loader — Per-Agent Aggregate and Verification-Builder-Centric Score Support

**User Story:** As an eval developer, I want the data loader to surface per-agent aggregate scores and Verification-Builder-centric composite scores from run summaries, so that dashboard pages can display per-agent judge data and the primary comparison metric.

#### Acceptance Criteria

1. THE Data_Loader SHALL read the `per_agent_aggregates` field from run summaries and include evaluator-level averages (IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence, IntentPreservation, CriteriaMethodAlignment) in the normalized run summary.
2. THE Data_Loader SHALL read the `vb_centric_score` field from run summaries and include the value in the normalized run summary.
3. THE Data_Loader SHALL read the `execution_time_ms` field from run detail test cases and include the value in normalized test results.
4. WHEN a run summary lacks `per_agent_aggregates` or `vb_centric_score`, THE Data_Loader SHALL default to empty dict and None respectively, preserving backward compatibility with older runs.

### Requirement 2: Architecture Comparison Page

**User Story:** As an eval developer, I want a dedicated Architecture Comparison page that shows side-by-side metrics for two runs from different architectures, so that I can make data-driven decisions about which architecture produces better verification plans.

#### Acceptance Criteria

1. THE Architecture_Comparison_Page SHALL accept two runs selected from the sidebar (the existing run selector and comparison run selector).
2. THE Architecture_Comparison_Page SHALL display a per-evaluator score comparison chart (bar chart or radar chart) showing each evaluator's average score for both runs, grouped by Evaluator_Group.
3. THE Architecture_Comparison_Page SHALL display the Verification_Builder_Centric_Score for both runs with a delta indicator (arrow up/down and percentage change).
4. THE Architecture_Comparison_Page SHALL display per-agent evaluator scores, showing only evaluators that ran for each architecture (e.g., IntentExtraction only appears for the serial run if the single-agent run lacks a `parser` key).
5. THE Architecture_Comparison_Page SHALL display PipelineCoherence scores for both runs with a callout explaining that PipelineCoherence quantifies the Silo_Problem.
6. THE Architecture_Comparison_Page SHALL display a per-category accuracy breakdown for both runs in a grouped bar chart.
7. THE Architecture_Comparison_Page SHALL display execution time comparison (total and per-test-case average) for both runs.
8. WHEN both selected runs have the same architecture, THE Architecture_Comparison_Page SHALL display a notice: "Both runs use the same architecture — use Prompt Correlation for prompt-level comparison."

### Requirement 3: Trends Page — Per-Agent Judge Score Traces

**User Story:** As an eval developer, I want the Trends page to show all 6 LLM judge evaluator scores over time, so that I can track how per-agent quality evolves across runs.

#### Acceptance Criteria

1. THE Trends page SHALL display a "Per-Agent Judge Scores" chart showing IntentExtraction, CategorizationJustification, ClarificationRelevance, and PipelineCoherence average scores over time, in addition to the existing IntentPreservation and CriteriaMethodAlignment traces.
2. WHEN a run lacks data for a per-agent evaluator, THE Trends page SHALL skip that data point (using `connectgaps=True`) rather than plotting zero.
3. THE Trends page SHALL group the judge score traces into two visual sections: "Final-Output Evaluators" (IntentPreservation, CriteriaMethodAlignment) and "Per-Agent & Cross-Pipeline Evaluators" (IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence).

### Requirement 4: Heatmap Enhancements — Architecture and Evaluator Grouping

**User Story:** As an eval developer, I want the heatmap to show architecture context and group evaluators by type, so that I can quickly identify which evaluator group is driving score differences between architectures.

#### Acceptance Criteria

1. THE Heatmap page SHALL group evaluator columns by Evaluator_Group with visual separators: final-output (IntentPreservation, CriteriaMethodAlignment), per-agent (IntentExtraction, CategorizationJustification, ClarificationRelevance), cross-pipeline (PipelineCoherence), deterministic (CategoryMatch, JSONValidity, ClarificationQuality, Convergence).
2. THE Heatmap page SHALL display the run's architecture label in the page header.
3. WHEN a comparison run is selected and the two runs have different architectures, THE Heatmap page SHALL render two side-by-side heatmaps, one per architecture, with matching test case row order for visual comparison.
4. THE Heatmap page SHALL display Evaluator_Group labels above each column group.

### Requirement 5: Coherence View — Multi-Judge Agreement Analysis

**User Story:** As an eval developer, I want the Coherence View to recognize all 6 LLM judges and provide richer agreement analysis, so that I can understand where deterministic and judge evaluators disagree and which judges are most/least aligned.

#### Acceptance Criteria

1. THE Coherence View SHALL classify evaluators into deterministic and judge groups using all 6 LLM judge names (IntentPreservation, CriteriaMethodAlignment, IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence) instead of only recognizing "ReasoningQuality".
2. THE Coherence View SHALL display a per-judge agreement breakdown showing each LLM judge's agreement rate with the deterministic evaluators.
3. THE Coherence View SHALL display a judge-vs-judge correlation summary showing which pairs of LLM judges tend to agree or disagree on the same test cases.
4. WHEN the run has per-agent evaluator data, THE Coherence View SHALL include per-agent judges in the chain-of-reasoning inspection alongside the existing agent output fields.

### Requirement 6: Sidebar and Routing Updates

**User Story:** As an eval developer, I want the sidebar to include the Architecture Comparison page and apply architecture filtering to all pages, so that I can navigate to the new page and filter data by architecture across the dashboard.

#### Acceptance Criteria

1. THE sidebar page navigation SHALL include "Architecture Comparison" as a page option.
2. THE app.py routing SHALL route the "Architecture Comparison" page to the Architecture_Comparison_Page render function, passing both the selected run detail and comparison run detail.
3. WHEN the architecture filter is set to a specific architecture, THE Trends page SHALL filter runs to only that architecture before rendering.
4. WHEN the architecture filter is set to a specific architecture, THE Heatmap page SHALL display only test cases from runs matching that architecture.

### Requirement 7: Comparative Eval Run — Run 9 Config (Current Best Prompts)

**User Story:** As an eval developer, I want to run the current best prompt configuration (prompts 1/2/2/2 with judge) on both serial and single backends against the full dataset, so that I have an apples-to-apples architecture comparison with the strongest prompts.

#### Acceptance Criteria

1. THE eval runner SHALL execute Run 9 config (PROMPT_VERSION_PARSER=1, PROMPT_VERSION_CATEGORIZER=2, PROMPT_VERSION_VB=2, PROMPT_VERSION_REVIEW=2) with `--backend serial --judge` against the full golden dataset.
2. THE eval runner SHALL execute Run 9 config with `--backend single --judge` against the full golden dataset.
3. THE eval report for each run SHALL include architecture, model_config, vb_centric_score, per_agent_aggregates, and all 6 LLM judge evaluator results per test case.
4. THE score_history.json SHALL contain both runs with distinct timestamps and architecture labels ("serial" and "single").

### Requirement 8: Comparative Eval Run — Run 7 Config (Pre-Verification-Builder Iteration Baseline)

**User Story:** As an eval developer, I want to run the pre-Verification-Builder-iteration prompt configuration (prompts 1/2/1/1 with judge) on both serial and single backends, so that I can see whether the single agent benefits more or less from prompt improvements than the serial graph.

#### Acceptance Criteria

1. THE eval runner SHALL execute Run 7 config (PROMPT_VERSION_PARSER=1, PROMPT_VERSION_CATEGORIZER=2, PROMPT_VERSION_VB=1, PROMPT_VERSION_REVIEW=1) with `--backend serial --judge` against the full golden dataset.
2. THE eval runner SHALL execute Run 7 config with `--backend single --judge` against the full golden dataset.
3. THE eval report for each run SHALL include architecture, model_config, vb_centric_score, per_agent_aggregates, and all 6 LLM judge evaluator results per test case.
4. THE score_history.json SHALL contain both runs with distinct timestamps and architecture labels.

### Requirement 9: Comparative Eval Run — Run 3 Config (Single Backend Only)

**User Story:** As an eval developer, I want to run the categorizer v2 configuration (prompts DRAFT/2/DRAFT/DRAFT with judge) on the single backend only, so that I can test whether the single agent handles the expanded human_only definition better than the serial graph did in Run 3.

#### Acceptance Criteria

1. THE eval runner SHALL execute Run 3 config (PROMPT_VERSION_CATEGORIZER=2, other prompts at DRAFT) with `--backend single --judge` against the full golden dataset.
2. THE eval report SHALL include architecture "single", model_config, vb_centric_score, per_agent_aggregates, and all 6 LLM judge evaluator results per test case.
3. THE score_history.json SHALL contain the run with a distinct timestamp and architecture label "single".

### Requirement 10: Prompt Correlation Page — Architecture-Aware Comparison

**User Story:** As an eval developer, I want the Prompt Correlation page to show Verification-Builder-centric score deltas and per-agent evaluator deltas alongside the existing category deltas when comparing runs, so that I can see the full picture of what changed between two runs.

#### Acceptance Criteria

1. THE Prompt Correlation page SHALL display Verification_Builder_Centric_Score for both runs with a delta indicator, in addition to the existing overall pass rate delta.
2. THE Prompt Correlation page SHALL display per-agent evaluator score deltas (IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence) when both runs have per-agent aggregate data.
3. WHEN comparing runs across architectures, THE Prompt Correlation page SHALL group the delta display into "Architecture Effect" (evaluators that differ due to architecture) and "Prompt Effect" (evaluators that differ due to prompt changes), using the architecture and prompt_version_manifest fields to distinguish.
