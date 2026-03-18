# Tasks: Architecture Backend Abstraction + Per-Agent Evaluators

## Task Group 1: Foundation — Output Contract + Backend Interface

- [x] 1. Define OutputContract and backend interface
  - [x] 1.1 Create `backends/__init__.py` with `OutputContract` TypedDict, `OutputMetadata` TypedDict, and `discover_backends()` function per Component 2 design
  - [x] 1.2 Create `backends/serial.py` wrapping existing `run_test_graph()` — implement `run()` and `metadata()` per Component 2 design. Populate `final_output` from pipeline result, `agent_outputs` with keys `parser`, `categorizer`, `verification_builder`, `review`
  - [x] 1.3 Validate serial backend returns correct OutputContract shape by running it against one golden dataset prediction and checking all required `final_output` fields exist

## Task Group 2: New Evaluators — Per-Agent LLM Judges

- [x] 2. Implement IntentExtraction evaluator (Parser)
  - [x] 2.1 Create `evaluators/intent_extraction.py` with `evaluate_intent_extraction()` function per Component 3 design. Use Strands Evals SDK `OutputEvaluator` with the `INTENT_EXTRACTION_RUBRIC`. Accept raw prediction text, parser output dict, and expected criteria
  - [x] 2.2 Test IntentExtraction evaluator against 3 golden dataset predictions: one where parser strips framing correctly, one where temporal resolution matters, one edge case. Verify scores are in [0.0, 1.0] and judge_reasoning is populated

- [x] 3. Implement CategorizationJustification evaluator (Categorizer)
  - [x] 3.1 Create `evaluators/categorization_justification.py` with `evaluate_categorization_justification()` function per Component 4 design. Accept parser output, categorizer output, tool manifest, and final_output. Rubric focuses on whether routing enables the Verification Builder to build the best plan
  - [x] 3.2 Test CategorizationJustification evaluator against 3 golden dataset predictions: one auto_verifiable (routing should enable tool-based plan), one human_only (routing should enable graceful degradation), one boundary case. Verify scores and reasoning

- [x] 4. Implement ClarificationRelevance evaluator (ReviewAgent)
  - [x] 4.1 Create `evaluators/clarification_relevance.py` with `evaluate_clarification_relevance()` function per Component 5 design. Accept prediction text, Verification Builder criteria, and review output. Rubric focuses on whether questions target specific Verification Builder assumptions
  - [x] 4.2 Test ClarificationRelevance evaluator against 3 golden dataset predictions: one where review questions are targeted, one where they're generic, one with operationalized vague terms. Verify scores and reasoning

- [x] 5. Implement PipelineCoherence evaluator (Cross-Agent)
  - [x] 5.1 Create `evaluators/pipeline_coherence.py` with `evaluate_pipeline_coherence()` function per Component 6 design. Accept prediction text, agent_outputs dict (any keys), and final_output. Rubric adapts to number of agents present
  - [x] 5.2 Test PipelineCoherence evaluator against 2 golden dataset predictions using serial backend output. Verify it scores inter-agent coherence and judge_reasoning references specific agents

## Task Group 3: Eval Runner Integration

- [x] 6. Integrate pluggable backends into eval runner
  - [x] 6.1 Add `--backend` CLI argument to eval runner that accepts any registered backend name, defaulting to `serial`. Add `--list-backends` flag that prints available backends from `discover_backends()` and exits
  - [x] 6.2 Refactor `_evaluate_base_prediction()` to accept an `OutputContract` dict instead of a flat result dict. Extract `final_output` and `agent_outputs` from the contract. Keep existing deterministic evaluators (CategoryMatch, JSONValidity, ClarificationQuality) working against the flat `final_output`
  - [x] 6.3 Add `_evaluate_with_judges()` function per Component 7 design — dispatches all 6 LLM judge evaluators based on which agent keys exist in `agent_outputs`. Log which evaluators were skipped and why

- [x] 7. Add Verification-Builder-centric composite score and report schema
  - [x] 7.1 Implement `compute_vb_centric_score()` with the `EVALUATOR_WEIGHTS` dict per Component 7 design. Missing evaluators reduce the weight denominator, not the score
  - [x] 7.2 Update report schema to include `architecture`, `model_config`, `vb_centric_score`, `evaluator_groups`, and `skipped_evaluators` fields per Component 9 design
  - [x] 7.3 Update DDB reasoning store writes to include all judge evaluator results per test case (judge_reasoning for each)
  - [x] 7.4 Update `print_report()` to display the Verification-Builder-centric composite score, evaluator groups, and skipped evaluators

- [x] 8. Validate eval runner integration end-to-end
  - [x] 8.1 Run `python eval_runner.py --list-backends` and verify serial backend is listed
  - [x] 8.2 Run `python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend serial --judge --dry-run` (or against 3 test cases with `--name`) and verify: all 6 judge evaluators fire, Verification-Builder-centric score is computed, report includes architecture/model_config/evaluator_groups/skipped_evaluators, DDB writes include judge reasoning
  - [x] 8.3 Verify that running without `--judge` still works with only deterministic evaluators (no judge calls)

## Task Group 4: Additional Backends

- [x] 9. Implement single-agent backend
  - [x] 9.1 Create `backends/single.py` with `run()` and `metadata()` per Component 2 design. Use Opus 4.6 with the comprehensive prompt covering all four pipeline steps. Parse JSON response into `final_output` and `agent_outputs` with single `agent` key
  - [x] 9.2 Test single-agent backend against 3 golden dataset predictions. Verify OutputContract shape is correct, `final_output` has all required fields, and the response covers parsing, categorization, verification building, and review

- [ ]* 10. Implement swarm backend
  - [ ]* 10.1 Create `backends/swarm.py` with `run()` and `metadata()`. Use Strands Swarm pattern with multiple collaborating agents. Record `collaboration_rounds` in metadata
  - [ ]* 10.2 Test swarm backend against 3 golden dataset predictions. Verify OutputContract shape and collaboration_rounds metadata

## Task Group 5: Dashboard Architecture Comparison

- [x] 11. Add architecture filtering to dashboard
  - [x] 11.1 Add "Architecture" multiselect to sidebar in `eval/dashboard/sidebar.py`, populated from `architecture` field across loaded runs
  - [x] 11.2 Update Trends page to filter by architecture — show separate color-coded lines per architecture when multiple selected
  - [x] 11.3 Update Prompt Correlation page to show architecture alongside prompt version diffs. Add banner when comparing different architectures: "Comparing different architectures — score differences may reflect architecture effects, not just prompt changes"
  - [x] 11.4 Update Heatmap page to include architecture column and support filtering by architecture

## Task Group 6: Comparative Eval Run

- [ ] 12. Run comparative eval: serial vs single-agent
  - [ ] 12.1 Run full eval with serial backend + judge: `python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend serial --judge`
  - [ ] 12.2 Run full eval with single-agent backend + judge: `python eval_runner.py --dataset ../../../../eval/golden_dataset.json --backend single --judge`
  - [ ] 12.3 Compare results using `--compare` flag. Document findings: which architecture scores higher on IntentPreservation, CriteriaMethodAlignment, PipelineCoherence? Does the single agent avoid the silo problem? What's the cost/latency tradeoff?
  - [ ] 12.4 Update project update doc with comparative eval results and analysis
