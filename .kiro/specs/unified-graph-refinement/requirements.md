# Requirements Document

## Introduction

CalledIt v2 replaces the current two-Lambda prediction pipeline architecture with a single unified Strands GraphBuilder graph. The redesign solves three problems with v1: (1) ReviewAgent runs outside the graph in a separate invocation with no access to graph state, (2) the HITL improvement loop uses hardcoded cascade logic in a separate `improve_call` Lambda, and (3) state is not preserved across refinement rounds so agents can't learn from previous iterations.

The v2 architecture brings ReviewAgent into the graph as a parallel branch, eliminates the `improve_call` Lambda by re-triggering the full graph with enriched state on each clarification, and introduces a stateful `PredictionGraphState` that carries full round history. The client receives two WebSocket pushes per round — `prediction_ready` (immediately submittable) and `review_ready` (when ReviewAgent finishes) — so the human is never blocked waiting for review.

### Why This Matters (Learning Context)

This redesign is a case study in a common agent architecture pattern: **replacing brittle orchestration code with agent judgment**. In v1, `improve_call.py` contains explicit rules like "if prediction_statement changes, also regenerate verification_date and verification_method." That's the developer doing the agent's job. In v2, agents receive their previous output plus new clarifications and decide for themselves whether to update. This is more robust, more extensible, and teaches a key Strands pattern: let the graph carry state, let agents make decisions.

The parallel branch pattern (pipeline agents → immediate delivery, ReviewAgent → async delivery) is also a common real-world pattern for keeping UIs responsive while background analysis completes.

## Glossary

- **Unified_Graph**: The single Strands GraphBuilder graph containing all four agents (Parser, Categorizer, Verification Builder, ReviewAgent) that replaces the previous two-Lambda architecture
- **Pipeline_Branch**: The sequential portion of the Unified_Graph: Parser → Categorizer → Verification Builder, which produces the structured prediction
- **Review_Branch**: The parallel portion of the Unified_Graph where ReviewAgent performs meta-analysis of the pipeline output
- **PredictionGraphState**: The TypedDict schema that carries all state through the graph, including round history, user clarifications, and previous agent outputs
- **Round**: An integer (starting at 1) representing how many times the graph has executed for a given prediction — round 1 is the initial submission, round 2+ are clarification-driven re-runs
- **Clarification**: A user-provided text input that enriches the prediction context, triggering a full graph re-run with incremented round number
- **prediction_ready**: A WebSocket message type sent to the client as soon as the Pipeline_Branch completes, containing the structured prediction JSON that is immediately submittable
- **review_ready**: A WebSocket message type sent to the client when the Review_Branch completes, containing reviewable sections identified by ReviewAgent
- **Refinement_Mode**: The agent behavior when round > 1 — agents receive their previous output and all accumulated clarifications, then confirm or update their section rather than starting from scratch
- **Lambda_Handler**: The `strands_make_call_graph.py` entry point that receives WebSocket events, builds initial state, executes the Unified_Graph, and delivers results via WebSocket
- **improve_call_Lambda**: The existing separate Lambda (`improve_call.py`) that handles HITL improvement with hardcoded cascade logic — to be deleted in v2
- **Cascade_Logic**: The v1 pattern in `improve_call.py` where changing one field (e.g., prediction_statement) triggers hardcoded regeneration of dependent fields — replaced by agent judgment in v2

## Requirements

### Requirement 1: Unified Graph Structure

**User Story:** As a developer, I want all four agents (Parser, Categorizer, Verification Builder, ReviewAgent) in a single Strands GraphBuilder graph, so that the entire prediction pipeline runs in one invocation with shared state and no separate Lambda cold-start cost for review.

**Why this requirement exists:** In v1, ReviewAgent runs as a standalone invocation after the graph completes. This means a separate Bedrock call setup, no access to graph-level state, and an extra Lambda cold-start if it's in a different function. Bringing it into the graph means it participates in the same execution context and can leverage Strands' automatic context propagation.

#### Acceptance Criteria

1. THE Unified_Graph SHALL contain exactly four agent nodes: Parser, Categorizer, Verification_Builder, and ReviewAgent.
2. THE Pipeline_Branch SHALL execute agents in sequential order: Parser, then Categorizer, then Verification_Builder.
3. WHEN the Verification_Builder node completes, THE Unified_Graph SHALL fork execution so that the Review_Branch runs in parallel with the pipeline result delivery.
4. THE Unified_Graph SHALL be compiled once as a module-level singleton and reused across warm Lambda invocations.
5. THE Unified_Graph SHALL use Strands GraphBuilder's automatic context propagation so that each sequential agent receives the original task plus all prior agents' outputs without manual state threading.

### Requirement 2: Two-Push WebSocket Delivery

**User Story:** As a user, I want to see my structured prediction immediately when the pipeline agents finish, without waiting for ReviewAgent's analysis, so that I can start reviewing and optionally submit right away.

**Why this requirement exists:** In v1, the client waits for all processing (including review) before seeing anything. ReviewAgent's meta-analysis is useful but not blocking — the prediction is complete and submittable without it. Two-push delivery keeps the UI responsive and gives the user a usable result faster.

#### Acceptance Criteria

1. WHEN the Pipeline_Branch completes (Parser, Categorizer, Verification_Builder all done), THE Lambda_Handler SHALL send a WebSocket message with type `prediction_ready` containing the complete structured prediction JSON.
2. WHEN the Review_Branch completes, THE Lambda_Handler SHALL send a WebSocket message with type `review_ready` containing the list of reviewable sections identified by ReviewAgent.
3. THE `prediction_ready` message SHALL contain all fields needed for submission: prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, and verification_method.
4. THE `review_ready` message SHALL contain a list of ReviewableSection objects, each with section name, improvable flag, questions list, and reasoning.
5. IF the Review_Branch fails, THEN THE Lambda_Handler SHALL send a `review_ready` message with an empty reviewable_sections list and log the error, so that the prediction remains submittable.

### Requirement 3: Stateful PredictionGraphState with Round History

**User Story:** As a developer, I want the graph state to carry full round history (round number, accumulated clarifications, previous agent outputs), so that agents can make informed refinement decisions based on everything that has happened across all rounds.

**Why this requirement exists:** In v1, each HITL cycle starts from a partial regeneration with no memory of prior rounds. An agent in round 3 has no idea what was decided in round 1 or what the user clarified in round 2. Carrying full history means agents get progressively smarter — they stand on previous work rather than redoing it.

**Alternative considered:** We could carry only the latest round's output (not full history). We chose to carry the full clarification list because agents benefit from seeing the progression of user intent, and the data is small (a few strings per round).

#### Acceptance Criteria

1. THE PredictionGraphState SHALL include a `round` field of type integer, starting at 1 for initial submissions and incrementing by 1 for each clarification-triggered re-run.
2. THE PredictionGraphState SHALL include a `user_clarifications` field of type list of strings that accumulates all user clarifications across all rounds.
3. THE PredictionGraphState SHALL include `prev_parser_output`, `prev_categorizer_output`, and `prev_vb_output` fields of type optional dictionary that hold the previous round's output for each pipeline agent.
4. WHEN round equals 1, THE PredictionGraphState SHALL have `user_clarifications` as an empty list and all `prev_*_output` fields as None.
5. WHEN round is greater than 1, THE PredictionGraphState SHALL have `prev_parser_output` populated with the parser's output from the immediately preceding round, `prev_categorizer_output` with the categorizer's output, and `prev_vb_output` with the verification builder's output.
6. THE PredictionGraphState SHALL preserve all existing v1 fields (user_prompt, user_timezone, current_datetime_utc, current_datetime_local, prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, verification_method, reviewable_sections) to maintain backward compatibility.

### Requirement 4: Full Graph Re-Trigger on Clarification

**User Story:** As a user, I want to provide a clarification and have the entire prediction pipeline re-run with my new information, so that all agents can refine their outputs based on accumulated context rather than just patching one field.

**Why this requirement exists:** The v1 `improve_call` Lambda uses hardcoded cascade logic: "if prediction_statement changes, also regenerate verification_date and verification_method." This is brittle — it assumes the developer knows all the dependencies between fields. In v2, the full graph re-runs and each agent decides for itself whether the new clarification affects its output. This is more robust and extensible.

**Alternative considered:** We could re-run only the affected agents (e.g., if the user clarifies the date, only re-run Parser). We chose full re-run because (a) it's simpler to implement, (b) agents are fast enough that selective re-run isn't needed, and (c) a date clarification might affect categorization or verification method too — agents are better at judging this than hardcoded rules.

#### Acceptance Criteria

1. WHEN the Lambda_Handler receives a WebSocket message with action `clarify`, THE Lambda_Handler SHALL extract the user_input and current_state from the message body.
2. WHEN a clarification is received, THE Lambda_Handler SHALL build a new PredictionGraphState with round incremented by 1, the new clarification appended to user_clarifications, and previous agent outputs populated from current_state.
3. WHEN a clarification is received, THE Lambda_Handler SHALL execute the full Unified_Graph with the enriched PredictionGraphState.
4. WHEN the re-triggered graph completes, THE Lambda_Handler SHALL deliver results using the same two-push WebSocket pattern (prediction_ready, then review_ready).
5. THE Lambda_Handler SHALL support unlimited clarification rounds — there is no maximum round count.

### Requirement 5: Agent Refinement Mode (Round > 1)

**User Story:** As a developer, I want each pipeline agent's system prompt to handle refinement mode when round > 1, so that agents confirm or update their previous output based on new clarifications rather than starting from scratch.

**Why this requirement exists:** Without refinement mode, re-running the graph would produce a completely new prediction that ignores what was already decided. Refinement mode means agents see their previous output and the new clarification, then make a judgment call: "does this new information change my answer?" This is the core of the v2 design — replacing hardcoded cascade logic with agent judgment.

#### Acceptance Criteria

1. WHEN round is greater than 1, THE Parser agent SHALL receive its previous output (prev_parser_output) and all accumulated user_clarifications in its prompt, and SHALL either confirm or update its prediction_statement, verification_date, and date_reasoning.
2. WHEN round is greater than 1, THE Categorizer agent SHALL receive its previous output (prev_categorizer_output) and all accumulated user_clarifications in its prompt, and SHALL either confirm or update its verifiable_category and category_reasoning.
3. WHEN round is greater than 1, THE Verification_Builder agent SHALL receive its previous output (prev_vb_output) and all accumulated user_clarifications in its prompt, and SHALL either confirm or update its verification_method.
4. WHEN round equals 1, THE Parser, Categorizer, and Verification_Builder agents SHALL operate identically to v1 behavior — processing from scratch with no previous output context.
5. THE system prompt refinement instructions for each agent SHALL include the directive: "Review your previous output in light of any new user clarifications — confirm it if it stands, update it if the new information makes a more precise version possible."

### Requirement 6: Submit Available from Round 1

**User Story:** As a user, I want to submit my prediction at any time after the first prediction_ready message arrives, regardless of whether review has completed or clarification rounds have occurred, so that I am never blocked from saving my prediction.

**Why this requirement exists:** In v1, the improvement loop can feel like a gate — users might think they need to go through review before submitting. In v2, the first-round result is complete and submittable immediately. Clarification rounds are opportunity, not requirement. This is a UX principle: give users control over when they're done.

#### Acceptance Criteria

1. WHEN the client receives a `prediction_ready` message, THE client SHALL enable the submit button so the user can save the prediction immediately.
2. WHEN the user submits a prediction, THE Lambda_Handler SHALL save the prediction to DynamoDB with status `pending` and the verification_date from the most recent prediction_ready data.
3. WHILE a clarification round is in progress (graph re-running), THE client SHALL keep the previous round's prediction_ready result visible and submittable until the new round's prediction_ready arrives.
4. THE submit action SHALL work regardless of whether zero, one, or multiple clarification rounds have occurred.

### Requirement 7: Eliminate improve_call Lambda

**User Story:** As a developer, I want to remove the improve_call Lambda and its associated SAM/WebSocket configuration, so that the codebase has a single prediction processing path through the Unified_Graph with no dead code.

**Why this requirement exists:** The `improve_call` Lambda and its hardcoded cascade logic in `regenerate_section()` are entirely replaced by the full graph re-trigger pattern. Keeping dead code around creates confusion and maintenance burden. The WebSocket routes (`improve_section`, `improvement_answers`) that routed to this Lambda also need to be replaced with the new `clarify` action.

#### Acceptance Criteria

1. THE `improve_call.py` file SHALL be deleted from the codebase.
2. THE SAM template SHALL remove the `ImproveSectionRoute` and `ImprovementAnswersRoute` WebSocket routes.
3. THE SAM template SHALL add a new `ClarifyRoute` WebSocket route that maps the `clarify` action to the MakeCallStreamFunction.
4. THE SAM template SHALL remove the `ImproveSectionFunctionPermission` and `ImprovementAnswersFunctionPermission` Lambda permission resources.
5. THE Lambda_Handler SHALL handle the `clarify` action in its WebSocket event routing, replacing the previous `improve_section` and `improvement_answers` actions.

### Requirement 8: ReviewAgent Graph Integration

**User Story:** As a developer, I want ReviewAgent to operate as a graph node rather than a standalone class with multiple methods (review_prediction, generate_improvement_questions, regenerate_section), so that it participates in Strands' automatic context propagation and its interface is consistent with the other agents.

**Why this requirement exists:** In v1, ReviewAgent is a class with three methods that each create separate agent invocations. In v2, it becomes a graph node that receives the full pipeline state through Strands' automatic propagation. The `generate_improvement_questions` and `regenerate_section` methods are no longer needed because the HITL loop is replaced by full graph re-trigger. ReviewAgent's only job in the graph is meta-analysis: identify which sections could be improved and what questions to ask.

#### Acceptance Criteria

1. THE ReviewAgent SHALL be refactored from a standalone class to a Strands Agent created by a `create_review_agent()` factory function, consistent with the pattern used by Parser, Categorizer, and Verification_Builder agents.
2. THE ReviewAgent graph node SHALL receive the complete pipeline output (prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, verification_method) through Strands' automatic context propagation.
3. THE ReviewAgent SHALL return a JSON object containing a `reviewable_sections` list, where each entry has section name, improvable flag, questions list, and reasoning.
4. THE ReviewAgent SHALL remove the `generate_improvement_questions()` and `regenerate_section()` methods, as these are replaced by the full graph re-trigger pattern.
5. IF the ReviewAgent encounters an error, THEN THE ReviewAgent SHALL return an empty reviewable_sections list rather than failing the entire graph execution.

### Requirement 9: Round 1 Prediction Quality and Clean v2 Protocol

**User Story:** As a developer, I want round 1 agent outputs to match v1 prediction quality (same prompts, same structured output), while adopting a clean v2 WebSocket protocol and frontend — no backward-compatible shims for the old `call_response` / `improve_section` / `improvement_answers` message types.

**Why this requirement exists:** The v2 redesign changes how agents are orchestrated and how state flows, but it should not change what agents produce on a fresh prediction. If round 1 produces different results than v1, that's a regression. However, the WebSocket message types and frontend handlers should be a clean break — not a backward-compatible layer on top of v1. This is a demo/educational project with no external API consumers. We control both sides (backend + frontend), and the frontend already needs changes for `prediction_ready`, `review_ready`, and `clarify`. Keeping the old `call_response` type alive would mean maintaining dead code paths (e.g., the `data.improved || this.isImprovementInProgress` logic in `callService.ts`) that no longer serve a purpose.

**Alternative considered:** We could keep `call_response` as the message type and add `prediction_ready` as an alias. We rejected this because it creates two code paths for the same thing, confuses future readers, and the frontend HITL code (`improve_section`, `improvement_answers` handlers) is dead anyway once `improve_call` Lambda is deleted.

#### Acceptance Criteria

1. WHEN round equals 1, THE Pipeline_Branch agents SHALL produce output equivalent to v1 for the same input prompt, timezone, and datetime.
2. WHEN round equals 1, THE initial prompt format sent to the Parser agent SHALL match the v1 format: "PREDICTION: {prompt}\nCURRENT DATE: {datetime}\nTIMEZONE: {timezone}".
3. THE backend SHALL use the new v2 WebSocket message types (`prediction_ready`, `review_ready`) exclusively — the old `call_response`, `review_complete`, `improvement_questions`, and `improved_response` message types SHALL be removed.
4. THE frontend SHALL be updated to handle `prediction_ready` and `review_ready` message types, replacing all v1 HITL message handlers (`call_response`, `improvement_questions`, `improved_response`, `review_complete`).
5. THE frontend SHALL remove the `isImprovementInProgress` flag and `data.improved` check logic, as these are v1 HITL artifacts replaced by the round-based clarification model.
6. THE DynamoDB save format for submitted predictions SHALL remain unchanged from v1 — this is the only true backward compatibility constraint, since existing saved predictions must remain queryable.

### Requirement 10: WebSocket Action Routing

**User Story:** As a developer, I want the Lambda handler to route WebSocket actions correctly for both initial predictions and clarifications, so that the single Lambda handles the complete prediction lifecycle.

**Why this requirement exists:** In v1, two Lambdas handle different actions. In v2, the single Lambda needs to handle both `makecall` (initial prediction) and `clarify` (refinement round). The routing logic needs to be clean and extensible.

#### Acceptance Criteria

1. WHEN the Lambda_Handler receives a WebSocket message with action `makecall`, THE Lambda_Handler SHALL build a round-1 PredictionGraphState and execute the Unified_Graph.
2. WHEN the Lambda_Handler receives a WebSocket message with action `clarify`, THE Lambda_Handler SHALL build a round-N PredictionGraphState (where N > 1) with enriched state and execute the Unified_Graph.
3. WHEN the Lambda_Handler receives a WebSocket message with action `clarify` that is missing required fields (user_input or current_state), THE Lambda_Handler SHALL return a WebSocket error message with a descriptive error and status code 400.
4. THE Lambda_Handler SHALL send a `status` message with status `processing` before executing the graph for both `makecall` and `clarify` actions.

### Requirement 11: Dead Code Cleanup

**User Story:** As a developer, I want all dead code from the v1 architecture removed during the v2 refactor, so that the codebase has a single clear code path with no orphaned functions or stale imports.

**Why this requirement exists:** The codebase currently has several pieces of dead code left over from earlier architecture iterations. Since v2 is already touching every file in the prediction pipeline, this is the right time to clean house rather than carrying debt forward.

**What's dead and why:**
- `parser_node_function()`, `categorizer_node_function()`, `verification_builder_node_function()` — These are leftover from a custom-node architecture that was replaced by the plain Agent pattern. The graph uses `create_*_agent()` factory functions; the node functions are never imported or called.
- `review_agent.py` imports `from error_handling import safe_agent_call, with_agent_fallback` — but `error_handling.py` was deleted from `handlers/strands_make_call/` during the January 2026 cleanup. This import would crash if anything tried to load the module. ReviewAgent is being rewritten from scratch in Requirement 8, so this is covered, but worth calling out explicitly.

#### Acceptance Criteria

1. THE `parser_node_function()` function SHALL be deleted from `parser_agent.py`.
2. THE `categorizer_node_function()` function SHALL be deleted from `categorizer_agent.py`.
3. THE `verification_builder_node_function()` function SHALL be deleted from `verification_builder_agent.py`.
4. THE `review_agent.py` file SHALL be completely rewritten per Requirement 8, eliminating the stale `error_handling` import and all v1 HITL methods.
5. NO agent file SHALL contain functions that are not imported or called by any other module in the codebase.

### Requirement 12: Simplified JSON Parsing

**User Story:** As a developer, I want agent output parsing to follow the Strands best practice of a single `json.loads()` call per agent result, so that the code is simple, debuggable, and doesn't mask prompt issues with regex fallbacks.

**Why this requirement exists:** The current `parse_graph_results()` function in `prediction_graph.py` is 90 lines of defensive JSON extraction with a 30-line `extract_json_from_text()` helper that tries 5 different regex strategies to find JSON in agent output. This is the exact anti-pattern the Strands best practices call out: "Complex JSON parsing: Regex fallbacks and multiple parsing attempts." If an agent isn't returning clean JSON, the fix is to improve the prompt, not to add more regex.

**Alternative considered:** Keep `extract_json_from_text()` as a safety net. We rejected this because it masks prompt quality issues — if an agent wraps its JSON in markdown code blocks, that's a prompt problem, not a parsing problem. Better to fix the prompt and fail fast if the output is malformed.

#### Acceptance Criteria

1. THE `extract_json_from_text()` function SHALL be removed from `prediction_graph.py`.
2. THE `parse_graph_results()` function SHALL use a single `json.loads(str(result))` call per agent result, with a simple fallback to default values on `JSONDecodeError`.
3. IF an agent returns malformed JSON, THE parsing logic SHALL log the raw output at ERROR level and use fallback defaults — not attempt regex extraction.
4. THE agent system prompts SHALL include explicit instructions to return raw JSON with no markdown wrapping (no ` ```json ` blocks).

### Requirement 13: Single Response Building Location

**User Story:** As a developer, I want the WebSocket response to be assembled in one place (the Lambda handler), not split across `execute_prediction_graph()` and `lambda_handler()`, so that there's a single source of truth for what the client receives.

**Why this requirement exists:** Currently, `execute_prediction_graph()` adds metadata fields (`user_timezone`, `current_datetime_utc`, `current_datetime_local`) and applies fallback defaults, then `lambda_handler()` builds a separate `response_data` dict with its own field mapping and additional metadata (`prediction_date`, `timezone`, `local_prediction_date`, `initial_status`). This means two layers of "ensure fields exist" logic in two files. In v2, the graph execution function should return the raw agent outputs, and the Lambda handler should be the single place that assembles the WebSocket response.

#### Acceptance Criteria

1. THE `execute_prediction_graph()` function SHALL return only the parsed agent outputs (prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, verification_method) without adding metadata fields or applying fallback defaults.
2. THE Lambda_Handler SHALL be the single location that assembles the `prediction_ready` WebSocket message, adding metadata fields (prediction_date, timezone, user_timezone, local_prediction_date, initial_status, round) and applying fallback defaults.
3. THERE SHALL be exactly one code path that builds the WebSocket response payload — not two layers of field assembly across different files.
