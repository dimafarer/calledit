# Requirements Document

## Introduction

An interactive Streamlit dashboard for exploring CalledIt eval results, replacing the static PNG chart generator (`eval/generate_charts.py`) and Jupyter notebook (`eval/eval_explorer.ipynb`). The dashboard reads from DynamoDB as its primary data source (with local JSON fallback) and provides 6 views: Trends, Heatmap, Prompt Correlation, Reasoning Explorer, Coherence View, and Fuzzy Convergence. A persistent sidebar enables run selection, comparison, and filtering by layer, category, and dataset version. The dashboard surfaces the data needed to understand how prompt changes, dataset versions, and agent interactions affect eval scores — making it possible to trace regressions, explore agent reasoning, and compare runs across architectures.

## Glossary

- **Eval_Run**: A single execution of the eval runner against the golden dataset, producing per-test-case scores, agent outputs, and aggregate metrics. Identified by a unique `eval_run_id`.
- **Score_History**: The local JSON file (`eval/score_history.json`) containing summary-level metrics for all eval runs — pass rates, per-category accuracy, prompt version manifests, and dataset versions.
- **Eval_Report**: A per-run JSON file (`eval/reports/eval-*.json`) containing full per-test-case scores, evaluator breakdowns, and aggregate metrics for a single eval run.
- **Prompt_Version_Manifest**: A dict mapping each agent name (parser, categorizer, vb, review) to its prompt version string (e.g., "DRAFT", "1", "2"). Recorded per eval run for traceability.
- **Deterministic_Evaluator**: An evaluator that produces scores through exact-match or structural checks (CategoryMatch, JSONValidity). Scores are reproducible across runs.
- **Judge_Evaluator**: An evaluator that uses an LLM-as-judge (ReasoningQuality) to score agent reasoning quality. Scores may vary across runs due to model non-determinism.
- **Reasoning_Trace**: The full text output from an agent (parser, categorizer, verification_builder, review) for a specific test case, stored in DynamoDB.
- **Judge_Reasoning**: The LLM judge's explanation text, numeric score, and judge model ID for a specific agent's output on a specific test case, stored in DynamoDB.
- **Architecture**: The execution backend used for an eval run — "serial" (4-agent pipeline), "swarm" (collaborative multi-round), or "single" (one-shot single agent). Defaults to "serial" for existing runs.
- **Model_Config**: A dict mapping agent names to model identifiers (e.g., `{"parser": "sonnet-4", "categorizer": "sonnet-4"}`). Records which models were used per agent in a run.
- **Dataset_Version**: An explicit version string (e.g., "v2.0") identifying which revision of the golden dataset was used for an eval run.
- **Fuzzy_Prediction**: A degraded variant of a base prediction with intentional ambiguity. Evaluated in two rounds: round 1 (before clarification) and round 2 (after simulated clarification).
- **Convergence**: A measure of how much a fuzzy prediction's scores improve between round 1 and round 2 after clarification.
- **EvalDataLoader**: The unified data layer class that loads eval data from DynamoDB (primary) with local file fallback, providing cached access to run summaries, per-test details, agent outputs, judge reasoning, and token counts.

## Requirements

### Requirement 1: Trend Lines Over Time

**User Story:** As a developer, I want to see overall pass rate, per-category accuracy, and per-agent scores plotted over time with prompt version annotations, so that I can identify whether the eval suite is improving or regressing across runs and correlate score changes with specific prompt updates.

#### Acceptance Criteria

1. WHEN the Trends page loads with multiple Eval_Runs, THE dashboard SHALL display a Plotly line chart with x-axis = run timestamp and y-axis = overall pass rate, showing one data point per run
2. WHEN the Trends page loads with multiple Eval_Runs, THE dashboard SHALL display a Plotly grouped bar or line chart showing per-category accuracy (auto_verifiable, automatable, human_only) over time, with each category as a separate series
3. WHEN the Prompt_Version_Manifest changes between consecutive runs, THE Trends page SHALL annotate the trend line at that run's timestamp indicating which agent prompts changed (e.g., "categorizer: DRAFT → 2")
4. WHEN a user hovers over a data point on the trend chart, THE dashboard SHALL display a tooltip showing the Prompt_Version_Manifest, Dataset_Version, total test count, and pass/fail counts for that run
5. WHEN sidebar filters are active (layer, category, or dataset_version), THE Trends page SHALL recalculate and display trend data reflecting only the filtered subset of test cases or runs

### Requirement 2: Per-Test-Case Heatmap

**User Story:** As a developer, I want a heatmap showing every test case scored by every evaluator with color-coded scores, grouped by deterministic vs judge evaluators and sorted worst-first, so that I can quickly identify which test cases and evaluators are problematic.

#### Acceptance Criteria

1. WHEN the Heatmap page loads for a selected Eval_Run, THE dashboard SHALL display a Plotly heatmap where rows = test case IDs, columns = evaluator names, and cell color = score value
2. WHEN the heatmap renders scores, THE dashboard SHALL use a color scale from red (0.0) through yellow (0.5) to green (1.0), with grey for NaN (evaluator not applied to that test case)
3. WHEN the heatmap renders evaluator columns, THE dashboard SHALL group Deterministic_Evaluator columns (CategoryMatch, JSONValidity, etc.) on the left and Judge_Evaluator columns (ReasoningQuality) on the right, with a visual separator between groups
4. WHEN the heatmap renders evaluator columns, THE dashboard SHALL classify any evaluator whose name contains "ReasoningQuality" as a Judge_Evaluator and all others as Deterministic_Evaluators
5. WHEN the heatmap renders test case rows, THE dashboard SHALL sort rows by ascending average evaluator score so that the worst-performing test cases appear at the top
6. WHEN a user clicks on a test case row in the heatmap, THE dashboard SHALL navigate to or link to the Reasoning Explorer page for that test case

### Requirement 3: Prompt Version Correlation

**User Story:** As a developer, I want to compare two eval runs side-by-side to see which prompts changed, how each category's accuracy shifted, and whether the change caused regressions or improvements, so that I can make data-driven decisions about prompt iterations.

#### Acceptance Criteria

1. WHEN the Prompt Correlation page loads with two selected Eval_Runs, THE dashboard SHALL display a prompt version diff showing which agent prompts changed between the two runs (from version → to version) and which remained unchanged
2. WHEN the Prompt Correlation page computes category deltas, THE dashboard SHALL display a table with one row per category showing: current accuracy, previous accuracy, delta (current minus previous), and a status indicator — green for improved (delta > 0), red for regressed (delta < 0), grey for unchanged (delta = 0)
3. WHEN the Prompt Correlation page computes the overall pass rate delta, THE dashboard SHALL display the delta with a directional indicator (↑ improved, ↓ regressed, = unchanged)
4. WHEN the two selected runs have different Dataset_Version values, THE Prompt Correlation page SHALL display a warning banner: "Dataset versions differ between runs — score comparisons may not be meaningful"

### Requirement 4: Reasoning Explorer

**User Story:** As a developer, I want to drill into individual test cases to see full agent outputs, judge reasoning, and token counts from DynamoDB, so that I can understand exactly why a test case scored the way it did and identify specific agent failure modes.

#### Acceptance Criteria

1. WHEN the Reasoning Explorer page loads for a selected Eval_Run, THE dashboard SHALL display a test case selector (dropdown or clickable table) listing all test cases in the run
2. WHEN a test case is selected, THE dashboard SHALL display a summary table of all evaluator scores for that test case
3. WHEN a test case is selected and DynamoDB is available, THE dashboard SHALL load and display the full Reasoning_Trace from each agent, showing the complete text output
4. WHEN a test case is selected and DynamoDB is available, THE dashboard SHALL load and display Judge_Reasoning for each judged agent, showing the judge's explanation text, numeric score, and judge model ID
5. WHEN agent outputs are displayed, THE dashboard SHALL order them in the fixed pipeline sequence: parser → categorizer → verification_builder → review, regardless of the order returned from DynamoDB
6. WHEN a test case is selected and DynamoDB is available, THE dashboard SHALL display token counts (input tokens and output tokens) per agent invocation
7. WHEN DynamoDB is unavailable for a selected test case, THE dashboard SHALL display evaluator scores from the local Eval_Report and show a message: "Reasoning traces not available — DDB unavailable"

### Requirement 5: Cross-Agent Coherence View

**User Story:** As a developer, I want to see whether deterministic evaluators and judge evaluators agree on test case quality, and whether agents build on each other's output coherently, so that I can identify cases where the pipeline produces individually correct but collectively incoherent results.

#### Acceptance Criteria

1. WHEN the Coherence View page loads for a selected Eval_Run, THE dashboard SHALL display for each test case whether Deterministic_Evaluator scores and Judge_Evaluator scores agree (both pass, both fail) or disagree (deterministic passes but judge fails, or vice versa)
2. WHEN disagreements exist between deterministic and judge scores, THE dashboard SHALL highlight those test cases and show the specific score values from each evaluator group
3. WHEN the Coherence View page loads, THE dashboard SHALL display summary statistics: percentage of test cases where deterministic and judge evaluators agree, and the most common disagreement patterns
4. WHEN a user selects a disagreement case, THE dashboard SHALL provide a drill-down link to the Reasoning Explorer for that test case to inspect agent outputs and judge reasoning
5. WHEN DynamoDB agent outputs are available, THE dashboard SHALL extract key fields from each agent's JSON output (parser: prediction, categorizer: verifiable_category, verification_builder: verification_steps, review: reviewable_sections) to show the chain of reasoning across agents

### Requirement 6: Architecture Comparison Schema

**User Story:** As a developer, I want the eval report schema and dashboard to support comparing runs across different execution backends (serial graph, agent swarm, single agent), so that when alternative architectures are implemented, the eval framework can measure their relative performance using the same golden dataset and evaluators.

#### Acceptance Criteria

1. WHEN an Eval_Report is loaded, THE EvalDataLoader SHALL read the `architecture` field if present; IF the field is absent, THE loader SHALL default to "serial"
2. WHEN an Eval_Report is loaded, THE EvalDataLoader SHALL read the `model_config` field if present; IF the field is absent, THE loader SHALL default to an empty dict and display "Not recorded" in the UI
3. WHEN sidebar filters include an architecture filter, THE dashboard SHALL filter runs to show only those matching the selected architecture value (using the default "serial" for runs without an explicit architecture field)
4. WHEN the Eval_Report schema includes `architecture` and `model_config` fields, THE dashboard SHALL display these values in run summary views and tooltips so that users can distinguish runs by execution backend and model selection

### Requirement 7: Fuzzy Convergence View

**User Story:** As a developer, I want to see round 1 vs round 2 scores for fuzzy predictions, clarification quality, and per-category convergence, so that I can measure whether the ReviewAgent's clarifications actually improve prediction processing quality.

#### Acceptance Criteria

1. WHEN the Fuzzy Convergence page loads, THE dashboard SHALL filter to fuzzy test cases only and display round 1 scores (evaluator keys prefixed with "R1_") separately from round 2 scores (evaluator keys prefixed with "R2_" plus the "Convergence" evaluator)
2. WHEN the Fuzzy Convergence page displays scores, THE dashboard SHALL show clarification quality scores separately (evaluator key "ClarificationQuality" or "R1_ClarificationQuality")
3. WHEN the Fuzzy Convergence page renders a convergence visualization, THE dashboard SHALL display a bar chart comparing round 1 vs round 2 scores per fuzzy test case, making it visually clear which cases improved and which degraded after clarification
4. WHEN the Fuzzy Convergence page displays per-category data, THE dashboard SHALL group fuzzy test cases by their expected category and show convergence trends within each category

### Requirement 8: Dataset Version Tracking

**User Story:** As a developer, I want the dashboard to show which dataset version was used for each eval run and flag when I'm comparing runs across different dataset versions, so that I don't draw incorrect conclusions from score changes caused by dataset content differences rather than prompt improvements.

#### Acceptance Criteria

1. WHEN the dashboard displays run summaries (sidebar, trends, tooltips), THE dashboard SHALL show the Dataset_Version for each run; IF the Dataset_Version field is absent, THE dashboard SHALL display "Unknown"
2. WHEN two runs are compared (Prompt Correlation page), THE dashboard SHALL flag a dataset version mismatch if and only if the two runs have different Dataset_Version values (treating missing as empty string)
3. WHEN sidebar filters include a dataset version filter, THE dashboard SHALL filter runs to show only those matching the selected Dataset_Version value

### Requirement 9: Data Loading and Compatibility

**User Story:** As a developer, I want the dashboard to load eval data from DynamoDB as its primary source with local JSON files as fallback, handle missing or optional fields gracefully, and skip malformed reports without crashing, so that the dashboard works reliably regardless of data availability or quality.

#### Acceptance Criteria

1. WHEN the dashboard starts, THE EvalDataLoader SHALL attempt to load run summaries from DynamoDB (`report_summary#SUMMARY` records) first; IF DynamoDB is unavailable (connection error, missing boto3, or table not found), THE loader SHALL fall back to reading `eval/score_history.json`
2. WHEN the dashboard loads per-test-case detail for a run, THE EvalDataLoader SHALL attempt to load from DynamoDB (`test_result#{test_case_id}` records) first; IF DynamoDB is unavailable, THE loader SHALL fall back to the matching `eval/reports/eval-*.json` local file
3. WHEN DynamoDB is unavailable, THE dashboard SHALL display a banner: "DDB unavailable — using local data. Reasoning traces not available." and disable DDB-only features (agent output viewer, judge reasoning viewer, token counts)
4. WHEN loading local Eval_Report files, THE EvalDataLoader SHALL skip any file that contains invalid JSON or is missing required fields (timestamp, per_test_case_scores), log a warning, and continue loading remaining files without affecting valid reports
5. WHEN an Eval_Report contains score values outside the [0, 1] range, THE EvalDataLoader SHALL clamp them to [0, 1] for display and log a warning
6. WHEN both DynamoDB and local files contain no eval data, THE dashboard SHALL display an empty state: "No eval runs found. Run an evaluation first."

### Requirement 10: Run Navigation and Filtering

**User Story:** As a developer, I want a sidebar with run selection, comparison selection, and filters for layer, category, and dataset version, so that I can quickly navigate between runs and focus on the specific subset of data I care about.

#### Acceptance Criteria

1. WHEN the dashboard loads, THE sidebar SHALL display a run selector dropdown populated from all available Eval_Runs, sorted by timestamp descending (most recent first)
2. WHEN the dashboard loads, THE sidebar SHALL display an optional comparison run selector for selecting a second run to use on the Prompt Correlation page
3. WHEN the sidebar renders filters, THE dashboard SHALL provide a layer filter (base / fuzzy / all), a category filter (auto_verifiable / automatable / human_only / all), and a dataset version filter (populated from available Dataset_Version values across loaded runs)
4. WHEN sidebar filter selections change, THE dashboard SHALL store the selections in `st.session_state` and all active pages SHALL re-render using the filtered data
5. WHEN the sidebar run selector or filters change, THE dashboard SHALL provide page navigation (tabs or selectbox) for the 6 dashboard pages: Trends, Heatmap, Prompt Correlation, Reasoning Explorer, Coherence View, and Fuzzy Convergence
