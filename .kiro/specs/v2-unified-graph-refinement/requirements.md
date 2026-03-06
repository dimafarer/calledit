# Requirements Document — Spec 2: Unified Graph with Stateful Refinement

## Introduction

This spec covers the core v2 feature: replacing the current 3-agent sequential graph with a unified 4-agent graph that includes ReviewAgent as a parallel branch, supports multi-round stateful refinement via full graph re-trigger, and delivers results to the client in two pushes (prediction_ready + review_ready).

### Prerequisite

This spec assumes `.kiro/specs/v2-cleanup-foundation/` (Spec 1) is complete. Spec 1 delivers:
- ReviewAgent as a `create_review_agent()` factory function (not a class)
- Dead node functions removed from all agent files
- Simplified JSON parsing (single `json.loads()` per agent)
- Response building consolidated in the Lambda handler
- Stale SAM routes (`improve_section`, `improvement_answers`) removed

### Why This Matters (Learning Context)

This spec is a case study in two key Strands patterns:

1. **Parallel branches in a graph** — The pipeline agents (Parser → Categorizer → Verification Builder) run sequentially, then the graph forks: one path delivers results immediately, while ReviewAgent runs in parallel. This is a common pattern for keeping UIs responsive while background analysis completes.

2. **Replacing brittle orchestration with agent judgment** — In v1, `regenerate_section()` contains hardcoded rules like "if prediction_statement changes, also regenerate verification_date and verification_method." In v2, agents receive their previous output plus new clarifications and decide for themselves whether to update. The graph carries state; agents make decisions.

## Glossary

- **Unified_Graph**: The single Strands GraphBuilder graph containing all four agents (Parser, Categorizer, Verification Builder, ReviewAgent)
- **Pipeline_Branch**: The sequential portion: Parser → Categorizer → Verification Builder
- **Review_Branch**: The parallel portion where ReviewAgent performs meta-analysis
- **PredictionGraphState**: The TypedDict schema carrying all state through the graph, including round history
- **Round**: Integer (starting at 1) representing graph execution count for a prediction
- **Clarification**: User-provided text that triggers a full graph re-run with incremented round
- **prediction_ready**: WebSocket message sent when Pipeline_Branch completes — immediately submittable
- **review_ready**: WebSocket message sent when Review_Branch completes — improvable sections
- **Refinement_Mode**: Agent behavior when round > 1 — confirm or update previous output based on new clarifications

## Requirements

### Requirement 1: Unified Graph Structure

**User Story:** As a developer, I want all four agents (Parser, Categorizer, Verification Builder, ReviewAgent) in a single Strands GraphBuilder graph, so that the entire prediction pipeline runs in one invocation with shared state and no separate invocation cost for review.

**Why this requirement exists:** In v1 (even after Spec 1 cleanup), ReviewAgent is invoked standalone after the graph completes. Bringing it into the graph means it participates in the same execution context and can leverage Strands' automatic context propagation. The parallel branch pattern lets us deliver pipeline results immediately while review runs in the background.

**Critical Strands Graph behavior (from official docs):** "When multiple nodes have edges to a target node, the target executes as soon as **any one** dependency completes." This means if we naively add edges from all three pipeline agents to ReviewAgent, it would fire as soon as Parser completes — before Categorizer and Verification Builder have run. We MUST use conditional edges with an `all_dependencies_complete` check so ReviewAgent waits for all three pipeline agents to finish. This is documented in the Strands Graph docs under "Waiting for All Dependencies."

#### Acceptance Criteria

1. THE Unified_Graph SHALL contain exactly four agent nodes: Parser, Categorizer, Verification_Builder, and ReviewAgent.
2. THE Pipeline_Branch SHALL execute agents in sequential order: Parser, then Categorizer, then Verification_Builder.
3. THE ReviewAgent node SHALL use conditional edges with an `all_dependencies_complete` check to ensure it only executes after ALL three pipeline agents (Parser, Categorizer, Verification_Builder) have completed — not after any single one completes.
4. THE Unified_Graph SHALL be compiled once as a module-level singleton and reused across warm Lambda invocations.
5. THE Unified_Graph SHALL use Strands GraphBuilder's automatic context propagation so that each sequential agent receives the original task plus all prior agents' outputs.

### Requirement 2: Two-Push WebSocket Delivery

**User Story:** As a user, I want to see my structured prediction immediately when the pipeline agents finish, without waiting for ReviewAgent's analysis, so that I can start reviewing and optionally submit right away.

**Why this requirement exists:** ReviewAgent's meta-analysis is useful but not blocking — the prediction is complete and submittable without it. Two-push delivery keeps the UI responsive and gives the user a usable result faster.

**Critical Strands Graph behavior (from official docs):** The Graph runs to completion and returns a `GraphResult` — it does not natively support sending results mid-execution. To achieve two-push delivery, we use `stream_async` with `multiagent_node_stop` events: when the `verification_builder` node completes, we send `prediction_ready`; when the `review` node completes, we send `review_ready`. This uses the official Strands streaming API rather than trying to hack mid-execution WebSocket sends.

**Alternative considered:** Run two separate graph executions (pipeline first, then ReviewAgent separately). We chose `stream_async` because it keeps everything in one graph execution, avoids duplicate Bedrock setup, and is the idiomatic Strands approach for monitoring graph progress.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL execute the Unified_Graph using `stream_async` to receive real-time node completion events.
2. WHEN a `multiagent_node_stop` event is received for the `verification_builder` node, THE Lambda_Handler SHALL send a `prediction_ready` WebSocket message containing the parsed pipeline results from the completed Parser, Categorizer, and Verification_Builder nodes.
3. WHEN a `multiagent_node_stop` event is received for the `review` node, THE Lambda_Handler SHALL send a `review_ready` WebSocket message containing the reviewable sections.
4. THE `prediction_ready` message SHALL contain all fields needed for submission: prediction_statement, verification_date, date_reasoning, verifiable_category, category_reasoning, and verification_method.
5. THE `review_ready` message SHALL contain a list of ReviewableSection objects, each with section name, improvable flag, questions list, and reasoning.
6. IF the Review_Branch fails, THE Lambda_Handler SHALL send a `review_ready` message with an empty reviewable_sections list and log the error.

### Requirement 3: Stateful PredictionGraphState with Round History

**User Story:** As a developer, I want the graph state to carry full round history (round number, accumulated clarifications, previous agent outputs), so that agents can make informed refinement decisions based on everything that has happened across all rounds.

**Why this requirement exists:** Carrying full history means agents get progressively smarter — they stand on previous work rather than redoing it. An agent in round 3 sees what was decided in round 1 and what the user clarified in round 2.

**Alternative considered:** Carry only the latest round's output. We chose full clarification list because agents benefit from seeing the progression of user intent, and the data is small.

#### Acceptance Criteria

1. THE PredictionGraphState SHALL include a `round` field of type integer, starting at 1 and incrementing by 1 for each clarification.
2. THE PredictionGraphState SHALL include a `user_clarifications` field of type list of strings that accumulates all clarifications across all rounds.
3. THE PredictionGraphState SHALL include `prev_parser_output`, `prev_categorizer_output`, and `prev_vb_output` fields of type optional dictionary.
4. WHEN round equals 1, all `prev_*_output` fields SHALL be None and `user_clarifications` SHALL be empty.
5. WHEN round > 1, `prev_*_output` fields SHALL hold the previous round's output for each pipeline agent.
6. THE PredictionGraphState SHALL preserve all existing fields to maintain backward compatibility.

### Requirement 4: Full Graph Re-Trigger on Clarification

**User Story:** As a user, I want to provide a clarification and have the entire prediction pipeline re-run with my new information, so that all agents can refine their outputs based on accumulated context rather than just patching one field.

**Why this requirement exists:** Full re-run is simpler to implement, agents are fast enough that selective re-run isn't needed, and a date clarification might affect categorization or verification method too — agents are better at judging this than hardcoded rules.

#### Acceptance Criteria

1. WHEN the Lambda_Handler receives action `clarify`, it SHALL extract user_input and current_state from the message body.
2. THE Lambda_Handler SHALL build a new PredictionGraphState with round incremented, new clarification appended, and previous outputs populated.
3. THE Lambda_Handler SHALL execute the full Unified_Graph with the enriched state.
4. Results SHALL be delivered using the same two-push pattern (prediction_ready, then review_ready).
5. THE Lambda_Handler SHALL support unlimited clarification rounds.

### Requirement 5: Agent Refinement Mode (Round > 1)

**User Story:** As a developer, I want each pipeline agent's system prompt to handle refinement mode when round > 1, so that agents confirm or update their previous output based on new clarifications rather than starting from scratch.

**Why this requirement exists:** This is the core of v2 — replacing hardcoded cascade logic with agent judgment. Agents see their previous output and the new clarification, then decide: "does this new information change my answer?"

#### Acceptance Criteria

1. WHEN round > 1, each pipeline agent SHALL receive its previous output and all accumulated user_clarifications in its prompt.
2. Each agent SHALL either confirm or update its output based on the new information.
3. WHEN round equals 1, agents SHALL operate identically to v1 behavior — processing from scratch.
4. THE refinement instruction SHALL include: "Review your previous output in light of any new user clarifications — confirm it if it stands, update it if the new information makes a more precise version possible."

### Requirement 6: Submit Available from Round 1

**User Story:** As a user, I want to submit my prediction at any time after the first prediction_ready message arrives, regardless of whether review has completed or clarification rounds have occurred.

**Why this requirement exists:** Clarification rounds are opportunity, not requirement. The user controls when they're done.

#### Acceptance Criteria

1. WHEN the client receives `prediction_ready`, the submit button SHALL be enabled immediately.
2. Submission SHALL save to DynamoDB with status `pending` and the verification_date from the most recent prediction_ready.
3. WHILE a clarification round is in progress, the previous round's result SHALL remain visible and submittable.
4. Submit SHALL work regardless of how many clarification rounds have occurred.

### Requirement 7: Clean v2 WebSocket Protocol

**User Story:** As a developer, I want the v2 WebSocket protocol to use new message types (`prediction_ready`, `review_ready`) exclusively, with no backward-compatible shims for the old `call_response` / `review_complete` / `improvement_questions` / `improved_response` types.

**Why this requirement exists:** This is a demo/educational project with no external API consumers. We control both sides. The frontend already needs changes for the new message types and clarify action. Keeping old types alive creates dead code paths.

#### Acceptance Criteria

1. THE backend SHALL use `prediction_ready` and `review_ready` message types exclusively.
2. THE frontend SHALL handle `prediction_ready` and `review_ready`, replacing all v1 handlers.
3. THE frontend SHALL remove the `isImprovementInProgress` flag and `data.improved` check logic.
4. THE DynamoDB save format SHALL remain unchanged — the only true backward compatibility constraint.

### Requirement 8: WebSocket Action Routing

**User Story:** As a developer, I want the Lambda handler to route WebSocket actions correctly for both initial predictions (`makecall`) and clarifications (`clarify`).

#### Acceptance Criteria

1. Action `makecall` SHALL build a round-1 PredictionGraphState and execute the Unified_Graph.
2. Action `clarify` SHALL build a round-N state (N > 1) with enriched state and execute the Unified_Graph.
3. Action `clarify` with missing required fields SHALL return a 400 error.
4. Both actions SHALL send a `status: processing` message before graph execution.
5. THE SAM template SHALL add a `ClarifyRoute` WebSocket route mapping `clarify` to MakeCallStreamFunction.

### Requirement 9: Round 1 Prediction Quality

**User Story:** As a developer, I want round 1 agent outputs to match v1 prediction quality, so that the v2 redesign is a pure architectural improvement with no regression.

#### Acceptance Criteria

1. WHEN round equals 1, pipeline agents SHALL produce output equivalent to v1 for the same inputs.
2. THE initial prompt format SHALL match v1: "PREDICTION: {prompt}\nCURRENT DATE: {datetime}\nTIMEZONE: {timezone}".
