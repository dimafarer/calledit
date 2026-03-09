# Implementation Plan: Unified Graph with Stateful Refinement (v2)

## Overview

Transform CalledIt's prediction pipeline from a 3-agent sequential graph + standalone ReviewAgent into a single 4-agent graph with parallel review branch, two-push WebSocket delivery via `stream_async`, and stateful multi-round refinement. Implementation follows the dependency chain: state → agents → graph → handler → routing → SAM → frontend.

## Tasks

- [x] 1. Extend PredictionGraphState with v2 fields
  - [x] 1.1 Add round tracking and history fields to PredictionGraphState TypedDict
    - Add `round: int`, `user_clarifications: List[str]`, `prev_parser_output: Optional[Dict[str, str]]`, `prev_categorizer_output: Optional[Dict[str, str]]`, `prev_vb_output: Optional[Dict[str, Any]]` to `graph_state.py`
    - Preserve all existing fields for backward compatibility (`total=False` already set)
    - Add verbose code comments explaining each new field's purpose, when it's populated, and why `List[str]` for clarifications
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ]* 1.2 Write property test for round 1 state invariant
    - **Property 4: Round 1 state invariant**
    - Generate random prompt + timezone, call `build_round1_state`, assert `round == 1`, `user_clarifications == []`, all `prev_*_output` fields are `None`
    - **Validates: Requirements 3.4, 8.1**

  - [ ]* 1.3 Write property test for state enrichment round trip
    - **Property 3: State enrichment round trip**
    - Generate random current_state + clarification string, call `build_clarify_state`, assert round incremented, clarification appended, prev outputs populated correctly
    - Must hold for sequential enrichments (round 2, 3, ..., N)
    - **Validates: Requirements 3.1, 3.2, 3.5, 4.1, 4.2, 4.5**

- [x] 2. Add refinement mode to pipeline agent system prompts
  - [x] 2.1 Add refinement instruction block to Parser agent system prompt
    - Append the refinement block to `parser_agent.py` system prompt: "REFINEMENT MODE (when previous output is provided)..." per design
    - Add code comments explaining static prompt with conditional activation pattern and why not dynamic prompt construction
    - _Requirements: 5.1, 5.2, 5.4, 9.1_

  - [x] 2.2 Add refinement instruction block to Categorizer agent system prompt
    - Append the same refinement block to `categorizer_agent.py` system prompt
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 2.3 Add refinement instruction block to Verification Builder agent system prompt
    - Append the same refinement block to `verification_builder_agent.py` system prompt
    - _Requirements: 5.1, 5.2, 5.4_

  - [x] 2.4 Update ReviewAgent factory to drop callback_handler parameter
    - Remove `callback_handler` param from `create_review_agent()` in `review_agent.py` (graph handles streaming)
    - Add comment explaining why ReviewAgent has no refinement mode (it always analyzes fresh pipeline output)
    - _Requirements: 1.1_

- [x] 3. Checkpoint — Verify state and agent changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Rewrite prediction_graph.py for unified 4-node graph
  - [x] 4.1 Build the unified graph with GraphBuilder
    - Create `create_prediction_graph()` with 4 nodes: parser, categorizer, verification_builder, review
    - Add sequential edges: parser → categorizer → verification_builder
    - Add single edge: verification_builder → review (with verbose comment explaining why single edge works for sequential pipeline)
    - Set entry point to parser, build as module-level singleton
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 4.2 Update parse_graph_results to handle 4 agents
    - Extend result parsing to include review node output (single `json.loads()`, ERROR log on failure, safe defaults)
    - Return reviewable_sections in the parsed result dict
    - Add comments explaining the parsing pattern and error handling strategy
    - _Requirements: 1.1, 2.5, 2.6_

  - [x] 4.3 Convert execute_prediction_graph to async with stream_async
    - Replace synchronous graph execution with `async for event in graph.stream_async(...)`
    - Accept `invocation_state` parameter for round context propagation
    - Yield or return events for the Lambda handler to process
    - Add verbose comments explaining stream_async pattern, why async, and how invocation_state carries round context
    - _Requirements: 2.1, 1.5_

  - [ ]* 4.4 Write unit tests for graph structure
    - Verify 4 nodes exist with expected IDs
    - Verify sequential edges parser → categorizer → verification_builder
    - Verify single edge from verification_builder to review
    - Verify module-level singleton reuse
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 5. Rewrite Lambda handler for async execution and two-push delivery
  - [x] 5.1 Implement action routing (makecall vs clarify)
    - Parse `action` from request body, route to `build_round1_state()` or `build_clarify_state()`
    - Return 400 for unknown actions
    - Add comments explaining the routing pattern and stateless backend design
    - _Requirements: 8.1, 8.2_

  - [x] 5.2 Implement build_round1_state function
    - Build initial PredictionGraphState with `round=1`, empty clarifications, None prev outputs
    - Populate user_prompt, user_timezone, current_datetime_utc, current_datetime_local
    - _Requirements: 3.4, 8.1, 9.2_

  - [x] 5.3 Implement build_clarify_state function
    - Extract current_state and user_input from request body
    - Increment round, append clarification, populate prev_*_output from current_state
    - Validate required fields (user_input, current_state), return 400 if missing
    - Add comments explaining state enrichment pattern and why frontend holds session state
    - _Requirements: 4.1, 4.2, 4.5, 8.2, 8.3_

  - [x] 5.4 Implement execute_and_deliver with two-push WebSocket delivery
    - Build initial prompt (round 1 format vs round 2+ format with previous output and clarifications)
    - Build invocation_state dict with round context
    - Iterate `stream_async` events, detect `multiagent_node_stop` for `verification_builder` → send `prediction_ready`
    - Detect `multiagent_node_stop` for `review` → send `review_ready`
    - Handle ReviewAgent failure gracefully (empty reviewable_sections)
    - Add verbose comments explaining stream_async event detection, two-push pattern, and error handling
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.3, 4.4_

  - [x] 5.5 Implement async Lambda handler wrapper
    - Create `async_handler(event, context)` with full async logic
    - Wrap with `lambda_handler` using `asyncio.run(async_handler(event, context))`
    - Send `{type: "status", status: "processing"}` before graph execution
    - Add comments explaining asyncio.run() in Lambda, event loop lifecycle
    - _Requirements: 8.4_

  - [x] 5.6 Implement round-aware prompt building
    - Round 1: `"PREDICTION: {prompt}\nCURRENT DATE: {datetime}\nTIMEZONE: {timezone}\n\nExtract the prediction and parse the verification date."`
    - Round 2+: Same base + `"\n\nPREVIOUS OUTPUT:\n{json}\n\nUSER CLARIFICATIONS:\n- {clarification_1}\n- ..."`
    - Add comments explaining why prompt varies per round while system prompt stays static
    - _Requirements: 5.1, 5.3, 9.2_

  - [x] 5.7 Remove v1 message types and old handler logic
    - Remove `call_response`, `review_complete`, `improvement_questions`, `improved_response` sending logic
    - Remove standalone ReviewAgent invocation (now a graph node)
    - Remove any `regenerate_section` or `improve_call` logic
    - _Requirements: 7.1_

  - [ ]* 5.8 Write property test for prediction_ready message completeness
    - **Property 1: prediction_ready message completeness**
    - Generate random pipeline output dicts, build prediction_ready message, assert all 6 agent output fields + all metadata fields present
    - **Validates: Requirements 2.2, 2.4**

  - [ ]* 5.9 Write property test for review_ready section completeness
    - **Property 2: review_ready section completeness**
    - Generate random reviewable section lists, build review_ready message, assert each section has section/improvable/questions/reasoning
    - **Validates: Requirements 2.3, 2.5**

  - [ ]* 5.10 Write property test for round 1 prompt format
    - **Property 5: Round 1 prompt format matches v1**
    - Generate random prompt + datetime + timezone, build round 1 prompt, assert exact v1 format with no previous output or clarifications section
    - **Validates: Requirements 5.3, 9.2**

  - [ ]* 5.11 Write property test for round > 1 prompt content
    - **Property 6: Round > 1 prompt contains previous output and clarifications**
    - Generate random round > 1 state, build prompt, assert contains PREVIOUS OUTPUT section and all clarifications listed
    - **Validates: Requirements 5.1**

  - [ ]* 5.12 Write property test for clarify action validation
    - **Property 7: Clarify action validation rejects missing fields**
    - Generate request bodies missing user_input or current_state, assert 400 response
    - **Validates: Requirements 8.3**

- [x] 6. Checkpoint — Verify backend is complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Add ClarifyRoute to SAM template
  - [x] 7.1 Add ClarifyRoute WebSocket route to template.yaml
    - Add `ClarifyRoute` resource mapping `clarify` action to `MakeCallStreamIntegration`
    - Add `ClarifyRoute` to `WebSocketDeployment` DependsOn list
    - Add comments explaining why no new Lambda is needed (handler routes internally)
    - _Requirements: 8.5_

- [x] 8. Update frontend for v2 protocol
  - [x] 8.1 Replace v1 message handlers with v2 handlers in callService.ts
    - Remove `call_response`, `review_complete`, `improvement_questions`, `improved_response` handlers
    - Remove `isImprovementInProgress` flag and `data.improved` check logic
    - Add `prediction_ready` handler → calls `onComplete` with parsed pipeline data
    - Add `review_ready` handler → calls `onReviewComplete` with reviewable sections
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 8.2 Add sendClarification method to callService.ts
    - Implement `sendClarification(userInput: string, currentState: object)` that sends `{action: "clarify", user_input, current_state}` over WebSocket
    - _Requirements: 4.1, 8.2_

  - [x] 8.3 Enable submit from round 1
    - Ensure submit button is enabled on `prediction_ready` receipt
    - Previous round's result remains visible and submittable during clarification
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 9. Final checkpoint — Verify end-to-end
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `max_examples=100` — test file: `tests/strands_make_call/test_v2_properties.py`
- Unit tests go in `tests/strands_make_call/test_v2_unit.py`
- All Python commands use venv at `/home/wsluser/projects/calledit/venv`
- Frontend tests are manual/E2E (not automated in this spec)
- DynamoDB save format is unchanged — the only true backward compatibility constraint (Req 7.4)
- Verbose code comments are required per user's learning goals — explain what, why, and alternatives
