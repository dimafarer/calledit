# Implementation Plan: Prompt Evaluation Framework

## Overview

Phased implementation of a prompt evaluation and observability system for the CalledIt prediction verification app. Layers three managed AWS services (OpenTelemetry + CloudWatch GenAI Observability, Bedrock Prompt Management, AgentCore Evaluations) onto the existing 4-agent Strands graph. All work happens on a `feature/prompt-eval-framework` git branch. A standalone test graph enables local iteration without Lambda/SnapStart deployment.

## Tasks

- [ ] 1. Phase 0 — Git branch setup and standalone test graph
  - [ ] 1.1 Create `feature/prompt-eval-framework` git branch and add eval dependencies to requirements.txt
    - Create the feature branch from main
    - Add `hypothesis`, `opentelemetry-api`, `opentelemetry-sdk`, `aws-opentelemetry-distro` to root `requirements.txt`
    - Add `opentelemetry-api`, `opentelemetry-sdk`, `aws-opentelemetry-distro` to `backend/calledit-backend/handlers/strands_make_call/requirements.txt`
    - _Requirements: 1.1, 1.3_

  - [ ] 1.2 Create standalone test graph (`test_prediction_graph.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/test_prediction_graph.py`
    - Reuse `create_parser_agent()`, `create_categorizer_agent()`, `create_verification_builder_agent()`, `create_review_agent()` factory functions
    - Reuse `build_prompt()` logic from `strands_make_call_graph.py`
    - Implement synchronous execution (no `stream_async`, no WebSocket, no SnapStart)
    - Expose `run_test_graph(prediction_text, timezone, tool_manifest, round, clarifications, prev_outputs)` function
    - Return parsed pipeline + review results as a dict
    - _Requirements: 1.1, 6.1_

- [ ] 2. Phase 1 — OTEL instrumentation and CloudWatch GenAI Observability
  - [ ] 2.1 Create OTEL instrumentation module (`otel_instrumentation.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/otel_instrumentation.py`
    - Implement `init_otel()` — initialize TracerProvider with CloudWatch exporter, return Tracer
    - Implement `create_graph_span(tracer, prompt_version_manifest)` — create parent span with manifest attributes
    - Implement `record_agent_span_attributes(span, agent_name, prompt_id, prompt_version, input_tokens, output_tokens, model_id)` — record per-agent attributes
    - Wrap OTEL export in fire-and-forget try/except (failures logged at WARN, never block graph)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [ ]* 2.2 Write property test for OTEL span attributes completeness
    - **Property 1: OTEL span attributes are complete**
    - **Validates: Requirements 1.1, 1.2, 1.4**
    - Create `tests/strands_make_call/test_otel_attributes.py`
    - For any valid agent name, model ID, non-negative token counts, and prompt version, verify all attributes are recorded and retrievable

  - [ ]* 2.3 Write property test for prompt version manifest round-trip through trace attributes
    - **Property 12: Prompt version manifest round-trip through trace attributes**
    - **Validates: Requirements 7.5**
    - In `tests/strands_make_call/test_otel_attributes.py`
    - For any manifest dict with parser/categorizer/vb/review version strings, verify recording as OTEL attributes and reading back produces identical dict

  - [ ] 2.4 Extend SnapStart `after_restore` hook for OTEL collector state
    - Modify `backend/calledit-backend/handlers/strands_make_call/snapstart_hooks.py`
    - Add OTEL collector state verification in `after_restore()`
    - Re-initialize TracerProvider if state is corrupted after restore
    - Log at ERROR if re-initialization fails, disable OTEL for that invocation
    - _Requirements: 1.5_

  - [ ] 2.5 Integrate OTEL instrumentation into graph execution
    - Modify `prediction_graph.py` to call `init_otel()` at module level
    - Modify `strands_make_call_graph.py` `execute_and_deliver()` to wrap execution in a parent trace span via `create_graph_span()`
    - Ensure Strands native OTEL support emits per-agent child spans automatically
    - _Requirements: 1.1, 1.2, 1.3_

- [ ] 3. Checkpoint — Verify OTEL instrumentation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Phase 2 — Bedrock Prompt Management migration
  - [ ] 4.1 Create prompt management client (`prompt_client.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/prompt_client.py`
    - Implement `fetch_prompt(prompt_identifier, prompt_version, variables)` — fetch from Bedrock Prompt Management API
    - Implement `get_prompt_version_manifest()` — return current `{parser, categorizer, vb, review}` version dict
    - Bundle `FALLBACK_PROMPTS` dict with current hardcoded constants from all 4 agent modules
    - On API failure: log at ERROR, return fallback prompt, record "fallback" in manifest
    - Handle categorizer special case: resolve `{tool_manifest}` variable via `variables` parameter
    - Read version numbers from environment variables, defaulting to "1"
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ]* 4.2 Write property test for prompt variable resolution
    - **Property 2: Prompt variable resolution preserves values**
    - **Validates: Requirements 3.4**
    - Create `tests/strands_make_call/test_prompt_client.py`
    - For any prompt template with variable placeholders and non-empty string values, verify resolved prompt contains every variable value as a substring

  - [ ] 4.3 Migrate agent factory functions to use Bedrock Prompt Management
    - Modify `create_parser_agent()` in `parser_agent.py` to call `fetch_prompt("calledit-parser", version)` instead of using `PARSER_SYSTEM_PROMPT`
    - Modify `create_categorizer_agent()` in `categorizer_agent.py` to call `fetch_prompt("calledit-categorizer", version, variables={"tool_manifest": manifest_text})`
    - Modify `create_verification_builder_agent()` in `verification_builder_agent.py` to call `fetch_prompt("calledit-vb", version)`
    - Modify `create_review_agent()` in `review_agent.py` to call `fetch_prompt("calledit-review", version)`
    - Keep existing `*_SYSTEM_PROMPT` constants as fallback copies
    - _Requirements: 3.3, 3.4, 3.5, 3.6_

  - [ ] 4.4 Verify SnapStart caching of fetched prompts
    - Ensure `fetch_prompt()` is called during INIT (at agent creation time in `prediction_graph.py`)
    - Fetched prompt text is baked into agent `system_prompt` attribute, included in SnapStart snapshot
    - Warm invocations do not make additional Bedrock Prompt Management API calls
    - _Requirements: 3.5_

- [ ] 5. Checkpoint — Verify Prompt Management migration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Phase 3 — Golden dataset and custom evaluators
  - [ ] 6.1 Create golden dataset schema and loader (`golden_dataset.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/golden_dataset.py`
    - Implement `ExpectedAgentOutputs`, `BasePrediction`, `FuzzyPrediction`, `GoldenDataset` dataclasses
    - Implement `load_golden_dataset(path)` — load JSON, validate schema_version, validate all required fields, cross-reference fuzzy→base IDs
    - Implement `filter_test_cases(dataset, name, category, layer, difficulty)` — return matching subset
    - Raise `ValueError` with descriptive message on invalid test cases
    - _Requirements: 4.1, 4.2, 4.3, 4.6_

  - [ ]* 6.2 Write property test for golden dataset round-trip serialization
    - **Property 3: Golden dataset round-trip serialization**
    - **Validates: Requirements 4.1**
    - Create `tests/eval/test_golden_dataset.py`
    - For any valid GoldenDataset object, verify serialize→deserialize produces equivalent object

  - [ ]* 6.3 Write property test for golden dataset structural validity
    - **Property 4: Golden dataset structural validity**
    - **Validates: Requirements 4.2, 4.3, 4.6**
    - In `tests/eval/test_golden_dataset.py`
    - For any test case, verify all required fields are present and correctly typed; fuzzy predictions reference existing base predictions

  - [ ] 6.4 Create the golden dataset JSON file
    - Create `eval/golden_dataset.json` with `schema_version: "1.0"`
    - Include at least 15 base predictions covering all 3 categories (≥3 per category: auto_verifiable, automatable, human_only)
    - Include at least 3 fuzzy predictions where clarification improves precision without changing category
    - Each base prediction: prediction_text, difficulty, tool_manifest_config, expected_per_agent_outputs (parser, categorizer, vb, review)
    - Each fuzzy prediction: fuzzy_text, base_prediction_id, simulated_clarifications, expected_clarification_topics, expected_post_clarification_outputs
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 6.5 Write property test for test case filtering
    - **Property 10: Test case filtering returns correct subset**
    - **Validates: Requirements 6.5**
    - Create `tests/eval/test_filtering.py`
    - For any dataset and filter criteria, verify every result matches all criteria and every matching case appears in result

  - [ ] 6.6 Create CategoryMatch evaluator (`evaluators/category_match.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/evaluators/__init__.py`
    - Create `backend/calledit-backend/handlers/strands_make_call/evaluators/category_match.py`
    - Implement `evaluate_category_match(span_output, expected)` — deterministic binary score (1.0 match, 0.0 mismatch)
    - Return `{"score": float, "evaluator": "CategoryMatch", "span_id": str}`
    - _Requirements: 5.1, 5.5_

  - [ ]* 6.7 Write property test for CategoryMatch evaluator
    - **Property 5: CategoryMatch evaluator is deterministic binary**
    - **Validates: Requirements 5.1, 5.5**
    - Create `tests/eval/test_evaluators.py`
    - For any pair of category strings from {auto_verifiable, automatable, human_only}, verify score is 1.0 when equal, 0.0 otherwise; result contains required fields

  - [ ] 6.8 Create JSONValidity evaluator (`evaluators/json_validity.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/evaluators/json_validity.py`
    - Implement `evaluate_json_validity(span_output, agent_name)` — structural score (0.0–1.0)
    - Parser: requires prediction_statement (str), verification_date (str), date_reasoning (str)
    - Categorizer: requires verifiable_category (str in VALID_CATEGORIES), category_reasoning (str)
    - VB: requires verification_method with source, criteria, steps as non-empty lists
    - Score = fields_present_and_correct / total_expected_fields; malformed JSON → 0.0 with error message
    - Return `{"score": float, "evaluator": "JSONValidity", "span_id": str, "error": str|None}`
    - _Requirements: 5.2, 5.5, 5.6_

  - [ ]* 6.9 Write property test for JSONValidity evaluator
    - **Property 6: JSONValidity evaluator scores field presence correctly**
    - **Validates: Requirements 5.2, 5.5, 5.6**
    - In `tests/eval/test_evaluators.py`
    - For any agent name and dict of fields (possibly missing/wrong-typed), verify score equals ratio of correct fields to expected; non-parseable input → 0.0 with error

  - [ ] 6.10 Create Convergence evaluator (`evaluators/convergence.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/evaluators/convergence.py`
    - Implement `evaluate_convergence(round2_outputs, base_expected)` — weighted score (0.0–1.0)
    - Weights: category match 0.5, prediction statement similarity 0.2, verification method overlap 0.2, date accuracy 0.1
    - When round2 equals base exactly → 1.0
    - Return `{"score": float, "evaluator": "Convergence", "span_id": str}`
    - _Requirements: 5.3, 5.5_

  - [ ]* 6.11 Write property test for Convergence evaluator
    - **Property 7: Convergence evaluator score bounds and identity**
    - **Validates: Requirements 5.3, 5.5**
    - In `tests/eval/test_evaluators.py`
    - For any pair of output dicts, verify score is in [0.0, 1.0]; identical inputs → 1.0; result contains required fields

  - [ ] 6.12 Create ClarificationQuality evaluator (`evaluators/clarification_quality.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/evaluators/clarification_quality.py`
    - Implement `evaluate_clarification_quality(review_output, expected_topics)` — keyword coverage score (0.0–1.0)
    - Score = proportion of expected keywords appearing (case-insensitive) in at least one question
    - All keywords found → 1.0; no keywords found → 0.0
    - Return `{"score": float, "evaluator": "ClarificationQuality", "span_id": str}`
    - _Requirements: 5.4, 5.5_

  - [ ]* 6.13 Write property test for ClarificationQuality evaluator
    - **Property 8: ClarificationQuality evaluator scores keyword coverage**
    - **Validates: Requirements 5.4, 5.5**
    - In `tests/eval/test_evaluators.py`
    - For any list of questions and expected keywords, verify score equals proportion of keywords found; all found → 1.0; none found → 0.0

- [ ] 7. Checkpoint — Verify golden dataset and evaluators
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Phase 3 (continued) — On-demand evaluation runner and online evaluation
  - [ ] 8.1 Create on-demand evaluation runner (`eval_runner.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/eval_runner.py`
    - Implement `run_on_demand_evaluation(dataset_path, filter_name, filter_category, filter_layer, filter_difficulty, dry_run)` 
    - Load golden dataset, execute each test case through OTEL-instrumented test graph
    - For base predictions: execute round 1, apply CategoryMatch + JSONValidity + ClarificationQuality evaluators
    - For fuzzy predictions: execute round 1, construct round 2 with simulated clarifications via `build_clarify_state()`, execute round 2, apply ConvergenceEvaluator
    - Record failed test cases with score 0.0 and error message; continue to next test case on failure
    - Produce report: per-test scores, per-agent aggregates, per-category accuracy, overall pass rate, prompt version manifest
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_

  - [ ]* 8.2 Write property test for evaluation report aggregation
    - **Property 9: Evaluation report aggregation is correct**
    - **Validates: Requirements 6.4**
    - Create `tests/eval/test_report_aggregation.py`
    - For any list of per-test-case score dicts, verify per-agent averages equal arithmetic mean, per-category accuracy equals mean CategoryMatch for that category, overall pass rate equals proportion where all scores > 0.5

  - [ ] 8.3 Implement dry-run mode for on-demand evaluation
    - In `eval_runner.py`, when `dry_run=True`: list test cases that would execute and estimated invocation count without making API calls
    - Estimated count = (base predictions × 1) + (fuzzy predictions × 2)
    - _Requirements: 8.6_

  - [ ]* 8.4 Write property test for dry-run invocation counting
    - **Property 15: Dry-run invocation count is accurate**
    - **Validates: Requirements 8.6**
    - Create `tests/eval/test_dry_run.py`
    - For any dataset and filter, verify listed test cases match filter and count = (base × 1) + (fuzzy × 2)

  - [ ] 8.5 Implement online evaluation sampling function
    - Add sampling logic to `otel_instrumentation.py` or a new `online_eval.py` module
    - Implement `should_sample_session(session_id, rate)` — deterministic sampling based on session ID hash
    - Default rate: 10% (0.1), configurable
    - Record prompt version manifest as trace attribute on every production trace
    - If AgentCore unavailable: continue serving predictions, log at WARN
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

  - [ ]* 8.6 Write property test for online evaluation sampling rate
    - **Property 11: Online evaluation sampling respects configured rate**
    - **Validates: Requirements 7.1**
    - Create `tests/eval/test_sampling.py`
    - For any rate in [0.0, 1.0] and deterministic seed, verify sampled proportion is within ±5% of configured rate over a large set

- [ ] 9. Checkpoint — Verify evaluation runner and online eval
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Phase 4 — Score tracking and regression detection
  - [ ] 10.1 Create score history module (`score_history.py`)
    - Create `backend/calledit-backend/handlers/strands_make_call/score_history.py`
    - Implement `append_score(report, manifest, path)` — append evaluation scores with prompt version manifest to JSON history file
    - Atomic write: write to temp file, then rename
    - Handle corrupted existing file: start new history, log at ERROR
    - Implement `compare_latest(path)` — compare current vs previous evaluation scores
    - Return delta indicators (improved/regressed/unchanged) per metric
    - Identify which prompt versions changed between evaluations
    - When regression exists: include changed prompt identifier and score delta
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 10.2 Write property test for score history append and read-back
    - **Property 13: Score history append and read-back**
    - **Validates: Requirements 8.1**
    - Create `tests/eval/test_score_history.py`
    - For any report and manifest, verify append then read contains entry with exact same scores, manifest, and valid timestamp

  - [ ]* 10.3 Write property test for score comparison deltas and prompt change detection
    - **Property 14: Score comparison correctly identifies deltas and prompt changes**
    - **Validates: Requirements 8.2, 8.3, 8.4**
    - In `tests/eval/test_score_history.py`
    - For any two reports with manifests, verify: metrics marked improved/regressed/unchanged correctly; changed prompt identifiers detected; regression includes changed prompt and delta

  - [ ] 10.4 Wire score history into eval runner
    - Modify `eval_runner.py` to call `append_score()` after each on-demand evaluation completes
    - Add `--compare` CLI flag to display comparison with previous evaluation
    - _Requirements: 8.1, 8.2_

- [ ] 11. Final checkpoint — Full integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Verify standalone test graph runs end-to-end with OTEL instrumentation
  - Verify prompt fetch → agent creation → graph execution flow
  - Verify golden dataset loads and passes structural validation
  - Verify all 4 evaluators produce correct scores on sample data

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All Python commands must use `/home/wsluser/projects/calledit/venv/bin/python`
- Dependencies must be tracked in requirements.txt files before installation
- The standalone test graph (task 1.2) enables local iteration without Lambda deployment
