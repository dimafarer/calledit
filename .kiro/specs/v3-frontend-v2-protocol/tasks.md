# Implementation Plan: Frontend v2 Protocol Alignment

## Overview

Complete the v2 migration by fixing frontend-backend integration. The backend works correctly (Spec 2) — this spec fixes streaming text display (backend-only), re-enables the clarification UI, removes dead v1 code, and validates the full flow. Tasks follow the design's recommended execution order: streaming investigation first (determines backend changes), then dead code removal (quick win), then clarification UI (main work), then verification and validation.

## Tasks

- [x] 1. Investigate and fix streaming text display (Requirement 1)
  - [x] 1.1 Add debug logging to `execute_and_deliver()` in `strands_make_call_graph.py` to log ALL event types from `stream_async`
    - Log event type, event keys, and whether `data` is present for `multiagent_node_stream` events
    - This is Track A from the design — verify whether `stream_async` forwards agent text events
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Implement streaming text fix based on investigation results
    - If Track A shows `multiagent_node_stream` events with `data` arrive: verify `send_ws` forwarding is correct, fix any format issues
    - If Track A shows no text events from `stream_async`: implement Track B — create `create_streaming_callback(api_gateway_client, connection_id)` in `strands_make_call_graph.py` and pass callback to each agent in `prediction_graph.py`
    - Track B callback sends `{type: "text", content: "..."}` directly to WebSocket, bypassing `stream_async` for text
    - Ensure streaming works for both round 1 (`makecall`) and round 2+ (`clarify`) actions
    - No frontend changes — the frontend text handler is correct and unchanged from v1
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.3 Write property test for `send_ws` text message format (Property 1)
    - **Property 1: send_ws text message format**
    - For any text string, `send_ws` with type "text" and `content=text` produces `{"type": "text", "content": text}`
    - Test file: `tests/test_send_ws.py`
    - Use Hypothesis `st.text()` strategy including empty, unicode, multiline strings
    - Mock `api_gateway_client` and capture the posted JSON data
    - **Validates: Requirement 1.2**

- [x] 2. Checkpoint — Verify streaming text fix
  - Ensure all tests pass, ask the user if questions arise.
  - Deploy backend changes if any were made, verify streaming text appears in the frontend during agent processing

- [x] 3. Remove dead v1 frontend code (Requirement 3)
  - [x] 3.1 Delete dead v1 files
    - Delete `frontend/src/services/reviewWebSocket.ts`
    - Delete `frontend/src/services/predictionService.ts`
    - Delete `frontend/src/hooks/useImprovementHistory.ts`
    - Delete `frontend/src/components/StreamingPrediction.tsx`
    - _Requirements: 3.1_

  - [x] 3.2 Clean barrel exports and stale references
    - Remove `export * from './predictionService'` from `frontend/src/services/index.ts`
    - Remove any other imports or references to the deleted files in active code
    - Verify no active code references old v1 message types (`call_response`, `review_complete`, `improvement_questions`, `improved_response`) as code — comments explaining v2 changes are fine to keep
    - _Requirements: 3.2, 3.3_

  - [x] 3.3 Clean up `useReviewState.ts` v1 artifacts
    - Review `setImprovementInProgress` usage — keep if still used for clarification round state, remove if truly dead
    - The function is still called when `review_ready` arrives to clear the "improving" indicator — keep it but verify the semantic context is correct for v2
    - _Requirements: 3.4_

- [x] 4. Build clarification UI (Requirement 2)
  - [x] 4.1 Extract `formatClarification` utility function
    - Create `frontend/src/utils/formatClarification.ts`
    - Pure function: takes `questions: string[]` and `answers: string[]`, returns formatted Q&A string
    - Format: `Q: {question}\nA: {answer}` pairs separated by `\n\n`
    - Handle edge cases: empty answers become `(no answer)`, mismatched array lengths
    - This is extracted for independent testability per the design doc
    - _Requirements: 2.4_

  - [ ]* 4.2 Write property test for clarification string formatting (Property 3)
    - **Property 3: Clarification string formatting**
    - For any list of Q&A pairs, the formatted string contains every question and every non-empty answer
    - Test file: `frontend/src/utils/__tests__/formatClarification.test.ts`
    - Use fast-check `fc.array(fc.record({ question: fc.string({ minLength: 1 }), answer: fc.string() }))` strategy
    - 100 runs minimum
    - **Validates: Requirement 2.4**

  - [x] 4.3 Wire `ImprovementModal` in `StreamingCall.tsx`
    - Uncomment the `ImprovementModal` JSX at the bottom of the component
    - Add `import ImprovementModal from './ImprovementModal'` (or re-enable existing import)
    - Destructure `cancelImprovement` from `useReviewState` hook
    - Add `handleClarificationSubmit(answers: string[])` handler:
      - Use `formatClarification()` to build the clarification string from questions + answers
      - Build `currentState` from the current `call` state + `prompt`
      - Call `cancelImprovement()` to close modal
      - Set `isProcessing(true)`, clear streaming text
      - Call `callService.sendClarification(clarification, currentState)`
    - Add `handleModalCancel()` handler that calls `cancelImprovement()`
    - Wire `onSubmit={handleClarificationSubmit}` and `onCancel={handleModalCancel}` on the modal
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7_

  - [ ]* 4.4 Write property test for review sections state management (Property 2)
    - **Property 2: Review sections state management**
    - For any list of ReviewableSection objects, `updateReviewSections(sections)` stores them faithfully and clears review status
    - Test file: `frontend/src/hooks/__tests__/useReviewState.test.ts`
    - Use fast-check to generate arbitrary section lists with varying names, question counts, and reasoning
    - 100 runs minimum
    - **Validates: Requirement 2.2**

  - [ ]* 4.5 Write property test for round state accumulation (Property 4)
    - **Property 4: Round state accumulation**
    - For any valid `current_state` with round N and clarification list of length M, `build_clarify_state` produces round N+1 and clarifications of length M+1
    - Test file: `tests/test_build_clarify_state.py`
    - Use Hypothesis with `st.integers(min_value=1, max_value=100)` for round, `st.lists(st.text(min_size=1))` for existing clarifications, `st.text(min_size=1)` for new input
    - **Validates: Requirement 2.6**

- [x] 5. Checkpoint — Verify clarification UI
  - Ensure all tests pass, ask the user if questions arise.
  - Verify the full clarification flow: see review questions → click ✨ badge → modal opens → answer questions → submit → see processing → see updated prediction

- [x] 6. Verify LogCallButton compatibility (Requirement 4)
  - [x] 6.1 Verify field mapping between `prediction_ready` data and LogCallButton
    - Trace the data flow: `prediction_ready` → `callService.onComplete` → `StreamingCall` state → `LogCallButton` → `/log-call` API
    - Confirm all required fields are present: `prediction_statement`, `verification_date`, `verifiable_category`, `category_reasoning`, `verification_method`, `date_reasoning`
    - Confirm extra v2 fields (`round`, `user_clarifications`) are harmless (ignored by API)
    - If any field mapping issues found, fix them; if compatible (as design predicts), document the verification
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 6.2 Write property test for prediction_ready required fields (Property 5)
    - **Property 5: prediction_ready contains all required fields**
    - For any valid `pipeline_data` and `state` dicts, `build_prediction_ready` returns all required fields
    - Test file: `tests/test_build_prediction_ready.py`
    - Use Hypothesis to generate pipeline_data with varying field values
    - **Validates: Requirement 4.2**

- [x] 7. End-to-end validation (Requirement 5)
  - [x] 7.1 Run `npm run build` and fix any TypeScript errors
    - Execute `npm run build` in the `frontend/` directory
    - Fix any TypeScript compilation errors introduced by the changes
    - Ensure zero errors on clean build
    - _Requirements: 5.4_

  - [x] 7.2 Verify complete prediction flow works end-to-end
    - Verify via automated checks: no broken imports, no type errors, all referenced components exist
    - The full manual flow (make prediction → streaming text → structured result → clarify → log call) should be verified by the user
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - All property-based tests pass (Python: Hypothesis, TypeScript: fast-check)
  - `npm run build` completes with zero errors
  - Recommend user run the full manual E2E flow and deploy

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- The streaming text fix (Task 1) is investigative — Track A or Track B will be chosen based on debug logging results
- The clarification UI (Task 4) is the main frontend work but mostly reconnects existing components
- LogCallButton verification (Task 6) is expected to require no code changes based on the design analysis
- Use `/home/wsluser/projects/calledit/venv/bin/python` for all Python test commands
- Use `vitest --run` for TypeScript tests (not watch mode)
