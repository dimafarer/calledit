# Implementation Plan: Clarification & Streaming (V4-3b)

## Overview

Evolve the V4-3a creation entrypoint from synchronous to async streaming with multi-round clarification support. Implementation follows a bottom-up approach: pure-function components first (model, bundle functions, event helper), then the async entrypoint rewrite that wires everything together, with property-based tests alongside each component.

All code goes in `calleditv4/` (Decision 95). No mocks (Decision 96). Python venv at `/home/wsluser/projects/calledit/venv`.

## Tasks

- [ ] 1. Add ClarificationAnswer Pydantic model
  - [ ] 1.1 Add `ClarificationAnswer` model to `calleditv4/src/models.py`
    - Add `ClarificationAnswer(BaseModel)` with `question: str` and `answer: str` fields, both with `Field(description=...)`
    - Import it in `calleditv4/src/main.py` alongside existing models
    - _Requirements: 1.4_

  - [ ]* 1.2 Write unit tests for ClarificationAnswer model in `calleditv4/tests/test_models.py`
    - Verify field structure, types, and Field descriptions match existing V4-3a model test patterns
    - _Requirements: 1.4_

- [ ] 2. Add bundle module functions for clarification
  - [ ] 2.1 Add `load_bundle_from_ddb()` to `calleditv4/src/bundle.py`
    - Queries DDB with Key `PK=PRED#{prediction_id}`, `SK=BUNDLE`
    - Returns clean dict (strips PK/SK) or None if not found
    - Add `Optional` and `List` to typing imports
    - _Requirements: 1.2, 1.3_

  - [ ] 2.2 Add `build_clarification_context()` to `calleditv4/src/bundle.py`
    - Pure function: combines `raw_prediction`, improvable `reviewable_sections`, and `clarification_answers` into a single context string
    - No I/O — takes existing bundle dict and answers list as inputs
    - _Requirements: 2.1, 2.2_

  - [ ] 2.3 Add `format_ddb_update()` to `calleditv4/src/bundle.py`
    - Pure function: returns kwargs dict for `table.update_item(**result)`
    - SET clause for `parsed_claim`, `verification_plan`, `verifiability_score`, `verifiability_reasoning`, `reviewable_sections`, `prompt_versions`, `updated_at`, `clarification_history`
    - ADD clause for `clarification_rounds :one`
    - ConditionExpression: `attribute_exists(PK)`
    - Conditional `user_timezone` in SET when provided
    - All floats converted to Decimal via `_convert_floats_to_decimal()`
    - `list_append` with `if_not_exists` for `clarification_history`
    - _Requirements: 2.4, 2.5, 2.6, 2.7, 2.8, 7.1, 7.2, 7.3, 7.6_

  - [ ] 2.4 Update `build_bundle()` to accept optional `user_timezone` parameter
    - When provided, include `user_timezone` field in the bundle dict
    - When None/omitted, do not include the field
    - _Requirements: 9.4_

  - [ ]* 2.5 Write property test for `build_clarification_context()` in `calleditv4/tests/test_clarification.py`
    - **Property 2: Clarification context contains all components**
    - **Validates: Requirements 2.1**

  - [ ]* 2.6 Write property test for `format_ddb_update()` in `calleditv4/tests/test_ddb_update.py`
    - **Property 4: DDB update format correctness**
    - **Validates: Requirements 2.4, 2.5, 2.6, 2.7, 2.8, 7.1, 7.2, 7.3, 7.6**

  - [ ]* 2.7 Write property test for `load_bundle_from_ddb()` key format in `calleditv4/tests/test_clarification.py`
    - **Property 7: DDB load key format**
    - **Validates: Requirements 1.2**
    - Note: Tests the key construction logic only (PK/SK format, stripping). Full DDB integration tested manually.

  - [ ]* 2.8 Write property test for `build_bundle()` timezone in `calleditv4/tests/test_bundle.py`
    - **Property 6: Bundle includes user_timezone when provided**
    - **Validates: Requirements 9.4**
    - Extend existing `test_bundle.py` with a new `TestBundleTimezone` class

- [ ] 3. Add stream event helper
  - [ ] 3.1 Add `_make_event()` function to `calleditv4/src/main.py`
    - Pure function: returns `json.dumps({"type": event_type, "prediction_id": prediction_id, "data": data})`
    - _Requirements: 5.1, 5.2, 5.3, 5.8_

  - [ ]* 3.2 Write property test for `_make_event()` in `calleditv4/tests/test_stream_events.py`
    - **Property 3: Stream event format invariant**
    - **Validates: Requirements 5.1, 5.3, 5.8, 6.3**

  - [ ]* 3.3 Write unit tests for stream event data shapes in `calleditv4/tests/test_stream_events.py`
    - Test `flow_started` data has `flow_type` + `clarification_round` (Req 5.4)
    - Test `turn_complete` data has `turn_number` + `turn_name` + `output` (Req 5.5)
    - Test `error` data has `message`, optionally `turn` (Req 5.7)
    - Test the 4 valid event types are `flow_started`, `turn_complete`, `flow_complete`, `error` (Req 5.2)
    - _Requirements: 5.2, 5.4, 5.5, 5.7_

- [ ] 4. Checkpoint — Verify pure function tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_bundle.py calleditv4/tests/test_models.py calleditv4/tests/test_clarification.py calleditv4/tests/test_stream_events.py calleditv4/tests/test_ddb_update.py -v`

- [ ] 5. Rewrite entrypoint to async streaming with clarification routing
  - [ ] 5.1 Add `_run_streaming_turn()` async helper to `calleditv4/src/main.py`
    - Wraps `agent.stream_async(prompt, structured_output_model=model_cls)`
    - Collects stream to completion, extracts `structured_output`
    - Returns `(structured_output, event_json)` tuple
    - _Requirements: 6.2_

  - [ ] 5.2 Rewrite `handler()` from sync to async with `yield`
    - Change `def handler()` to `async def handler()`
    - Add `MAX_CLARIFICATION_ROUNDS` constant from env var (default 5)
    - Extract `session_id` from `context` for observability logging
    - Extract `timezone` from payload (Decision 101)
    - _Requirements: 4.1, 6.1, 3.4, 8.1, 8.2, 9.1_

  - [ ] 5.3 Implement clarification route in `handler()`
    - Route when payload has `prediction_id` + `clarification_answers`
    - Validate payload: non-empty prediction_id, non-empty answers list, each answer has question + answer strings
    - Load bundle via `load_bundle_from_ddb()`
    - Check clarification cap
    - Build context via `build_clarification_context()`
    - yield `flow_started` event (type "clarification")
    - Run 3-turn streaming flow via `_run_streaming_turn()` × 3
    - yield `turn_complete` events after each turn
    - Call `table.update_item(**format_ddb_update(...))` with error handling for `ConditionalCheckFailedException`
    - yield `flow_complete` event with updated bundle
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 3.1, 3.2, 3.3, 4.2, 4.3, 4.4, 4.5, 4.7, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 5.4 Rewrite creation route to async streaming
    - Route when payload has `prediction_text`
    - yield `flow_started` event (type "creation")
    - Replace synchronous `agent()` calls with `_run_streaming_turn()` × 3
    - yield `turn_complete` events after each turn
    - Pass `user_timezone` to `build_bundle()` and `fetch_prompt()` variables
    - DDB `put_item` with error handling (bundle returned even on save failure)
    - yield `flow_complete` event with bundle
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.2, 6.3, 9.1, 9.2, 9.3, 9.4, 9.6_

  - [ ] 5.5 Update simple prompt mode to yield events
    - Route when payload has `prompt`
    - yield single `flow_complete` event with agent response
    - _Requirements: 6.4_

  - [ ] 5.6 Update missing-fields error to yield error event
    - When payload has none of `prediction_text`, `prediction_id`, `prompt`
    - yield single error event and stop
    - _Requirements: 6.5_

  - [ ]* 5.7 Write payload validation property test in `calleditv4/tests/test_clarification.py`
    - **Property 1: Clarification payload validation rejects invalid inputs**
    - **Validates: Requirements 1.4, 1.5, 1.6**

  - [ ]* 5.8 Write clarification cap property test in `calleditv4/tests/test_clarification.py`
    - **Property 5: Clarification cap enforcement**
    - **Validates: Requirements 3.1, 3.3**

- [ ] 6. Update entrypoint tests for async handler
  - [ ] 6.1 Update `calleditv4/tests/test_entrypoint.py` for async handler
    - Update `test_handler_is_async` — verify handler is `async def` (Req 4.1, 6.1)
    - Update `test_missing_fields_yields_error` — verify error event format instead of JSON string
    - Verify `MAX_CLARIFICATION_ROUNDS` constant defaults to 5 (Req 3.1, 3.4)
    - Verify `session_id` extraction pattern exists (Req 8.1, 8.2)
    - _Requirements: 3.1, 3.4, 4.1, 6.1, 6.5, 8.1_

- [ ] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)`
- Decision 96: NO MOCKS — all tests exercise real code paths (pure functions only, no AWS calls in tests)
- Integration testing (full streaming + clarification with real Bedrock/DDB) is done manually via `agentcore invoke --dev`
- The 3 new bundle.py functions are pure (no I/O) except `load_bundle_from_ddb()` which takes a table resource
