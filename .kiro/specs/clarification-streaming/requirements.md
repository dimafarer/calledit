# Requirements Document — Spec V4-3b: Clarification & Streaming

## Introduction

Add multi-round clarification and streaming response delivery to the V4-3a creation flow. V4-3a delivers a complete prediction bundle as a single JSON blob after the 3-turn flow finishes (15-30 seconds of silence). V4-3b solves two problems: (1) the user can answer clarification questions from the reviewer and re-run the creation flow with that context, improving the prediction bundle, and (2) the client gets turn-by-turn progress events as the 3-turn flow executes, so the user sees something happening instead of staring at a spinner.

The clarification pattern: V4-3a's review turn produces `reviewable_sections` with targeted clarification questions. V4-3b lets the user answer some or all of those questions and submit a clarification request. The agent re-runs the 3-turn flow with the original prediction text plus the clarification answers as additional context. The `clarification_rounds` counter increments. The existing DDB item is updated (not a new item). A cap prevents infinite clarification loops.

The streaming pattern: The entrypoint becomes `async def` and uses `yield` to stream events to the client. The AgentCore runtime handles WebSocket/HTTP streaming transport. Each turn completion is a discrete event the client can render. This follows the AgentCore streaming pattern where the entrypoint yields events and the runtime delivers them.

This spec builds directly on V4-3a's 3-turn creation flow. It modifies `calleditv4/src/main.py` (entrypoint), `calleditv4/src/bundle.py` (bundle update logic), and adds clarification context handling. It does NOT touch the CloudFormation prompts, Pydantic models, or prompt client — those are unchanged from V4-3a.

### Frontend Compatibility Analysis

The v3 React frontend was analyzed to inform these requirements. Key findings:

1. **Timezone from frontend**: The frontend already detects the user's timezone via `Intl.DateTimeFormat().resolvedOptions().timeZone` and sends it with every `makecall` request. V4-3a ignored this — the parser relied on `current_time` tool's server timezone. V4-3b adds timezone acceptance from the payload, which is a stronger signal than the server timezone (Decision 101).

2. **Stream event format alignment**: The v3 frontend routes WebSocket messages by `type` field via `messageHandlers.get(messageType)`. The V4-3b stream event format (`{type, prediction_id, data}`) is designed to be compatible with this routing pattern. The v3 message types (`prediction_ready`, `review_ready`, `text`, `tool`, `complete`, `status`, `error`) are replaced by v4's cleaner set (`flow_started`, `turn_complete`, `flow_complete`, `error`), but the routing mechanism is the same.

3. **Clarification payload change**: v3 sends `{action: "clarify", user_input: string, current_state: object}` where `user_input` is a formatted Q&A string and `current_state` is the entire prediction object (frontend-as-session pattern, Decision 8). V4-3b uses `{prediction_id, clarification_answers: [{question, answer}]}` — the backend loads state from DDB instead of receiving it from the frontend. This is cleaner (no stale state risk, smaller payloads) but requires a frontend update when connecting to v4.

4. **Technical debt flagged for v4 frontend spec**: (a) Two prediction paths exist — REST via PredictionInput and WebSocket via StreamingCall — v4 should consolidate to one. (b) The frontend sends the entire prediction object as `current_state` on clarification — v4 replaces this with `prediction_id` lookup. (c) The v3 category display (auto_verifiable/automatable/human_only) needs replacement with the verifiability score indicator (V4-4).

This spec does NOT cover: frontend/UI changes, Memory integration (V4-6), verifiability score indicator UI (V4-4), or production deployment (V4-8).

## Glossary

- **Clarification_Round**: A cycle where the user answers clarification questions from the reviewer and the agent re-runs the 3-turn creation flow with the original prediction text plus the user's clarification answers as additional context. Each round increments the `clarification_rounds` counter in the Prediction_Bundle
- **Clarification_Payload**: The JSON payload sent by the client to initiate a clarification round. Contains `prediction_id` (the existing prediction to clarify), `clarification_answers` (a list of question-answer pairs), and optionally `session_id`
- **Clarification_Context**: The combined text block injected into the parse turn prompt containing the original prediction, the previous round's reviewable sections (questions), and the user's answers. This gives the agent full context to produce an improved bundle
- **Clarification_Cap**: The maximum number of clarification rounds allowed per prediction. Set to 5. Prevents infinite clarification loops and bounds resource usage
- **Stream_Event**: A discrete JSON object yielded by the async entrypoint during the creation flow. Each event has a `type` field identifying what happened (e.g., `turn_complete`, `flow_complete`, `error`) and a `data` field with the event payload. The AgentCore runtime delivers these to the client over WebSocket or HTTP streaming
- **Async_Entrypoint**: The entrypoint function decorated with `@app.entrypoint` that is declared `async def` and uses `yield` to emit Stream_Events. This follows the AgentCore streaming pattern from the docs: `async for event in agent.stream_async(...)`: `yield event`
- **Session_ID**: An optional string in the `RequestContext` that identifies a conversation session across multiple requests. Used to associate clarification rounds with the original prediction. The client provides this; the agent uses it for logging and observability but does NOT use it for state lookup — the `prediction_id` in the Clarification_Payload is the primary key for loading the existing bundle
- **Bundle_Update**: A DDB `update_item` operation that modifies an existing prediction bundle in place rather than creating a new item. Used during clarification rounds to update the bundle fields and increment `clarification_rounds` while preserving the original `prediction_id`, `created_at`, and `user_id`
- **Creation_Agent**: (From V4-3a) A single Strands Agent instance that processes 3 sequential prompt turns to transform raw prediction text into a structured Prediction_Bundle
- **Prediction_Bundle**: (From V4-3a) The structured JSON object containing all outputs from the 3-turn creation flow. V4-3b adds `clarification_history` to track previous rounds
- **Entrypoint**: (From V4-3a) The Python function decorated with `@app.entrypoint` in `calleditv4/src/main.py`. V4-3b changes this from a synchronous function returning a string to an async generator yielding Stream_Events
- **DDB_Table**: (From V4-3a) The existing `calledit-db` DynamoDB table. V4-3b uses `update_item` in addition to V4-3a's `put_item`
- **RequestContext**: (From V4-3a) The AgentCore context object with `session_id`, `request_headers`, and `request` fields. V4-3b uses `session_id` for observability
- **User_Timezone**: The user's local timezone string (e.g., `"America/New_York"`, `"America/Los_Angeles"`) sent by the frontend via `Intl.DateTimeFormat().resolvedOptions().timeZone`. When present in the payload, it takes priority over the server timezone for date resolution. Stored in the Prediction_Bundle as `user_timezone` so the verification agent knows when to verify

## Requirements

### Requirement 1: Clarification Payload Handling

**User Story:** As a user, I want to submit answers to the reviewer's clarification questions and get an improved prediction bundle, so that my prediction has higher verifiability and fewer assumptions.

#### Acceptance Criteria

1. WHEN the Entrypoint receives a payload containing a `prediction_id` field and a `clarification_answers` field, THE Entrypoint SHALL treat the request as a Clarification_Round
2. THE Entrypoint SHALL load the existing Prediction_Bundle from the DDB_Table using PK `PRED#{prediction_id}` and SK `BUNDLE` before starting the clarification flow
3. IF the Prediction_Bundle does not exist in the DDB_Table for the given prediction_id, THEN THE Entrypoint SHALL yield an error Stream_Event with a message indicating the prediction was not found
4. THE `clarification_answers` field SHALL be a list of objects, each containing a `question` field (str) and an `answer` field (str), representing the user's responses to specific reviewer questions
5. IF the `clarification_answers` list is empty, THEN THE Entrypoint SHALL yield an error Stream_Event with a message indicating that at least one answer is required
6. THE Entrypoint SHALL validate that the `prediction_id` field is a non-empty string and that each item in `clarification_answers` contains both `question` and `answer` as non-empty strings

### Requirement 2: Clarification Round Execution

**User Story:** As a developer, I want the clarification round to re-run the 3-turn creation flow with the original prediction plus the user's answers as context, so that the agent produces an improved bundle informed by the clarification.

#### Acceptance Criteria

1. WHEN executing a Clarification_Round, THE Entrypoint SHALL build a Clarification_Context string containing: the original `raw_prediction` from the loaded bundle, the previous round's `reviewable_sections` (the questions that were asked), and the user's `clarification_answers` (the answers provided)
2. THE Entrypoint SHALL pass the Clarification_Context as the prediction input to Turn 1 (Parse), replacing the raw `prediction_text` used in the initial creation flow, so that the parser sees both the original prediction and the clarification answers
3. THE Entrypoint SHALL execute the same 3-turn flow (Parse → Plan → Review) used in V4-3a, with the same Prompt_Management prompts, the same Pydantic structured output models, and the same agent configuration
4. WHEN the 3-turn flow completes, THE Entrypoint SHALL update the existing Prediction_Bundle in the DDB_Table using a Bundle_Update operation that replaces `parsed_claim`, `verification_plan`, `verifiability_score`, `verifiability_reasoning`, `reviewable_sections`, and `prompt_versions` with the new values from the clarification round
5. THE Bundle_Update SHALL increment the `clarification_rounds` field by 1
6. THE Bundle_Update SHALL append the current round's clarification answers to a `clarification_history` list field in the bundle, preserving the full history of all clarification rounds
7. THE Bundle_Update SHALL preserve the original `prediction_id`, `user_id`, `raw_prediction`, and `created_at` fields unchanged
8. THE Bundle_Update SHALL set an `updated_at` field to the current UTC timestamp in ISO 8601 format

### Requirement 3: Clarification Round Cap

**User Story:** As a developer, I want a maximum number of clarification rounds per prediction, so that the system bounds resource usage and prevents infinite clarification loops.

#### Acceptance Criteria

1. THE Clarification_Cap SHALL be 5 rounds per prediction
2. WHEN the Entrypoint receives a Clarification_Round request, THE Entrypoint SHALL check the current `clarification_rounds` value in the loaded Prediction_Bundle before executing the flow
3. IF the current `clarification_rounds` value is greater than or equal to the Clarification_Cap, THEN THE Entrypoint SHALL yield an error Stream_Event with a message indicating the maximum number of clarification rounds has been reached, and SHALL NOT execute the 3-turn flow
4. THE Clarification_Cap value SHALL be configurable via the `MAX_CLARIFICATION_ROUNDS` environment variable, defaulting to 5 when the variable is not set

### Requirement 4: Streaming Turn-by-Turn Progress

**User Story:** As a user, I want to see progress as each turn of the creation flow completes, so that I know the system is working during the 15-30 second creation process instead of staring at a blank screen.

#### Acceptance Criteria

1. THE Entrypoint SHALL be an Async_Entrypoint declared as `async def` that yields Stream_Events instead of returning a single string
2. WHEN the creation flow starts (either initial creation or clarification round), THE Entrypoint SHALL yield a Stream_Event with type `flow_started` containing the `prediction_id` and the flow type (`creation` or `clarification`)
3. WHEN Turn 1 (Parse) completes, THE Entrypoint SHALL yield a Stream_Event with type `turn_complete` containing `turn_number` (1), `turn_name` (`parse`), and the `parsed_claim` data from the structured output
4. WHEN Turn 2 (Plan) completes, THE Entrypoint SHALL yield a Stream_Event with type `turn_complete` containing `turn_number` (2), `turn_name` (`plan`), and the `verification_plan` data from the structured output
5. WHEN Turn 3 (Review) completes, THE Entrypoint SHALL yield a Stream_Event with type `turn_complete` containing `turn_number` (3), `turn_name` (`review`), and the `verifiability_score`, `verifiability_reasoning`, and `reviewable_sections` data from the structured output
6. WHEN the full bundle is assembled and saved to DDB, THE Entrypoint SHALL yield a Stream_Event with type `flow_complete` containing the complete Prediction_Bundle
7. IF any turn raises an exception during the flow, THEN THE Entrypoint SHALL yield a Stream_Event with type `error` containing the error message and the turn that failed, and SHALL stop yielding further events

### Requirement 5: Stream Event Format

**User Story:** As a frontend developer, I want a consistent, predictable event format from the streaming endpoint, so that I can parse and render events without special-casing each event type.

#### Acceptance Criteria

1. EACH Stream_Event SHALL be a JSON-serializable dict with exactly three top-level fields: `type` (str), `prediction_id` (str), and `data` (dict)
2. THE `type` field SHALL be one of: `flow_started`, `turn_complete`, `flow_complete`, `error`
3. THE `prediction_id` field SHALL be the prediction ID for the current flow, present in every event so the client can correlate events to a prediction
4. FOR `flow_started` events, THE `data` field SHALL contain `flow_type` (str, either `creation` or `clarification`) and `clarification_round` (int, 0 for initial creation)
5. FOR `turn_complete` events, THE `data` field SHALL contain `turn_number` (int, 1-3), `turn_name` (str), and `output` (dict, the structured output from that turn serialized via `model_dump()`)
6. FOR `flow_complete` events, THE `data` field SHALL contain the complete Prediction_Bundle dict
7. FOR `error` events, THE `data` field SHALL contain `message` (str) and optionally `turn` (str, the turn name where the error occurred)
8. THE Entrypoint SHALL serialize each Stream_Event to a JSON string before yielding it

### Requirement 6: Async Entrypoint with AgentCore Streaming

**User Story:** As a developer, I want the entrypoint to follow the AgentCore async streaming pattern, so that the runtime handles WebSocket/HTTP transport and the agent code only concerns itself with yielding events.

#### Acceptance Criteria

1. THE Entrypoint SHALL be declared as `async def handler(payload: dict, context: RequestContext)` with the `@app.entrypoint` decorator, following the AgentCore streaming pattern
2. THE Entrypoint SHALL use `agent.stream_async(prompt)` for each turn instead of the synchronous `agent(prompt)` call used in V4-3a, collecting the streamed response and extracting the structured output after the stream completes
3. THE Entrypoint SHALL yield each Stream_Event as a JSON string, allowing the AgentCore runtime to deliver the events to the client over the appropriate transport (WebSocket or HTTP streaming)
4. THE simple prompt mode (payload with `prompt` field) SHALL continue to work, yielding a single Stream_Event with type `flow_complete` containing the agent response as a string in the `data` field — backward compatibility is preserved
5. IF the payload contains neither `prediction_text`, `prediction_id`, nor `prompt`, THEN THE Entrypoint SHALL yield a single error Stream_Event and stop

### Requirement 7: DynamoDB Update for Clarification Rounds

**User Story:** As a developer, I want clarification rounds to update the existing DDB item rather than creating a new one, so that the prediction_id remains stable across rounds and the verification agent always loads the latest version.

#### Acceptance Criteria

1. WHEN a Clarification_Round completes, THE Entrypoint SHALL use a DynamoDB `update_item` call (not `put_item`) to update the existing item at PK `PRED#{prediction_id}` and SK `BUNDLE`
2. THE `update_item` call SHALL use an UpdateExpression that sets `parsed_claim`, `verification_plan`, `verifiability_score`, `verifiability_reasoning`, `reviewable_sections`, `prompt_versions`, `updated_at`, and `clarification_history`, and adds 1 to `clarification_rounds`
3. THE `update_item` call SHALL include a ConditionExpression verifying that the item exists (attribute_exists(PK)), preventing phantom updates to non-existent items
4. IF the `update_item` call fails due to a condition check failure, THEN THE Entrypoint SHALL yield an error Stream_Event indicating the prediction was not found or was deleted between load and update
5. IF the `update_item` call fails for any other reason, THEN THE Entrypoint SHALL yield the complete updated bundle in a `flow_complete` event with an additional `save_error` field, matching V4-3a's behavior of returning the bundle even when the save fails
6. ALL float values in the update expression attribute values SHALL be converted to `Decimal` types before writing, consistent with V4-3a's float-to-Decimal conversion (Decision 82)

### Requirement 8: Session ID Observability

**User Story:** As a developer, I want session IDs logged and included in stream events, so that I can trace clarification rounds across requests in observability tools.

#### Acceptance Criteria

1. WHEN the RequestContext contains a non-null `session_id`, THE Entrypoint SHALL include the `session_id` in the `flow_started` Stream_Event data
2. WHEN the RequestContext contains a non-null `session_id`, THE Entrypoint SHALL log the `session_id` alongside the `prediction_id` at the start of each request for observability
3. THE Entrypoint SHALL NOT use `session_id` for state lookup or bundle retrieval — the `prediction_id` in the payload is the sole key for loading existing bundles from DDB
4. IF the RequestContext does not contain a `session_id` (null or missing), THE Entrypoint SHALL proceed normally without the session_id field in events — session_id is optional and its absence does not affect functionality

### Requirement 9: User Timezone from Payload (Decision 101)

**User Story:** As a user, I want the agent to use my actual timezone when resolving time-sensitive predictions, so that "tonight" and "tomorrow morning" are interpreted correctly for my location rather than the server's location.

#### Acceptance Criteria

1. WHEN the Entrypoint receives a payload containing a `timezone` field (e.g., `"America/New_York"`), THE Entrypoint SHALL pass the timezone value to the parser prompt via the `{{user_timezone}}` variable, giving the agent the user's actual timezone as the primary reference for date resolution
2. WHEN the Entrypoint receives a payload WITHOUT a `timezone` field, THE Entrypoint SHALL omit the `{{user_timezone}}` variable from the parser prompt, and the agent SHALL fall back to the `current_time` tool's server timezone (the existing V4-3a behavior)
3. THE `timezone` field SHALL be accepted in both creation payloads (`prediction_text` + `timezone`) and clarification payloads (`prediction_id` + `clarification_answers` + `timezone`)
4. THE Prediction_Bundle SHALL include a `user_timezone` field recording the timezone used for date resolution, enabling the verification agent to verify at the correct time
5. THE parser prompt's timezone priority chain SHALL be updated to: (1) `{{user_timezone}}` from payload (strongest — the user's actual timezone), (2) explicit location in prediction (e.g., "Lakers" → Pacific), (3) `current_time` tool's server timezone, (4) UTC as last resort
6. THIS requirement also applies retroactively to V4-3a's creation flow — the `timezone` field SHALL be accepted in the initial creation payload, not just clarification payloads. This is a V4-3a enhancement delivered as part of V4-3b
