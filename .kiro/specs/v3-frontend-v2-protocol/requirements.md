# Requirements Document — Spec 3: Frontend v2 Protocol Alignment

## Introduction

The backend was migrated to v2 (unified 4-agent graph with two-push delivery and stateful refinement) in Spec 2. The backend works correctly — `prediction_ready`, `review_ready`, and `complete` messages arrive as expected (confirmed via browser console logs). However, the frontend has three categories of issues: (1) streaming text doesn't display during agent processing, (2) the review/improvement UI is disabled with no replacement, and (3) dead v1 code remains.

### Prerequisite
- Spec 1 (v2 cleanup foundation) — COMPLETE, deployed
- Spec 2 (v2 unified graph refinement) — Backend COMPLETE, deployed. Frontend partially migrated.

### Context for Next Agent
Read `docs/project-updates/01-project-update.md` for the full narrative of decisions made during Specs 1 and 2. Key architectural decisions: frontend-as-session (Decision 8), single edge graph topology (Decision 7), stream_async for two-push delivery.

## Requirements

### Requirement 1: Restore Streaming Text Display

**User Story:** As a user, I want to see real-time agent reasoning text during prediction processing, so that I can follow the AI's thinking process.

**Current state:** Streaming text worked perfectly in v1. The frontend's `callService.ts` text handler, `StreamingCall.tsx` text display, and `AnimatedText` component are all correct and unchanged. The issue is purely on the backend side — the v2 Lambda handler uses `stream_async` on the Graph, which yields `multiagent_node_stream` events in a different format than the v1 per-agent callback handler sent. The frontend expects `{type: "text", content: "..."}` messages, which is exactly what v1 sent via the `create_streaming_callback` function.

**Root cause:** In v1, each agent had a `callback_handler` that sent text chunks directly to the WebSocket as `{type: "text", content: "..."}`. In v2, agents are graph nodes — the graph's `stream_async` wraps agent events in `multiagent_node_stream` events with a nested `event` dict. The Lambda handler attempted to forward these but the format may not match, OR `stream_async` may not forward individual text generation events at all (only tool events and lifecycle events). The Strands docs need to be checked.

**The fix is NOT a frontend change.** The frontend streaming code is correct. The fix is ensuring the backend sends `{type: "text", content: "..."}` messages during graph execution, matching the v1 format the frontend already handles. Options:
1. Fix the `multiagent_node_stream` event forwarding in `execute_and_deliver()` to correctly extract and send text chunks
2. If `stream_async` doesn't forward text events, pass per-agent callback handlers when creating agents (like v1 did) that send text directly to the WebSocket, bypassing `stream_async` for text streaming

#### Acceptance Criteria

1. DURING graph execution, the frontend SHALL display real-time text chunks from agent processing in the streaming text area — identical to v1 behavior.
2. THE backend SHALL send `{type: "text", content: "..."}` messages matching the v1 format that the frontend already handles.
3. THE streaming text SHALL show agent reasoning as it happens, not just a single "Processing..." status message.
4. THE streaming text display SHALL work for both round 1 (makecall) and round 2+ (clarify) actions.
5. NO changes to the frontend text streaming code (callService.ts text handler, StreamingCall.tsx onTextChunk, AnimatedText component) SHALL be needed — the fix is backend-only.

### Requirement 2: Build Clarification UI

**User Story:** As a user, I want to provide a free-text clarification after seeing my prediction and review suggestions, so that the prediction can be refined.

**Current state:** The backend supports the `clarify` WebSocket action and `callService.ts` has a `sendClarification()` method. But no UI exists to trigger it. The v1 `ImprovementModal` (per-section Q&A) is commented out. The v2 approach is simpler: show review sections as read-only context, let the user type a free-text clarification.

#### Acceptance Criteria

1. AFTER `prediction_ready` arrives, the UI SHALL display the structured prediction with a submit button enabled immediately.
2. AFTER `review_ready` arrives, the UI SHALL display the reviewable sections as read-only context (section name, reasoning, suggested questions) below the prediction.
3. THE UI SHALL provide a text input for the user to type a free-text clarification.
4. WHEN the user submits a clarification, THE frontend SHALL call `callService.sendClarification(userInput, currentState)` where `currentState` contains the current prediction data plus round context.
5. DURING a clarification round, THE previous prediction SHALL remain visible until the new `prediction_ready` arrives.
6. THE clarification UI SHALL be optional — the user can submit the prediction at any time without clarifying.

### Requirement 3: Remove Dead v1 Code

**User Story:** As a developer, I want all dead v1 frontend code removed, so that the codebase is clean and doesn't confuse future development.

**Dead code identified:**
- `frontend/src/services/reviewWebSocket.ts` — references old `review_complete` type, not imported anywhere active
- `frontend/src/services/predictionService.ts` — uses old v1 patterns, `StreamingPrediction` component not rendered in App.tsx
- `frontend/src/components/ImprovementModal.tsx` — commented out, replaced by clarification UI
- `frontend/src/hooks/useImprovementHistory.ts` — no longer imported after Spec 2 cleanup
- `frontend/src/components/StreamingPrediction.tsx` — legacy component not rendered in App.tsx
- Any remaining references to `call_response`, `review_complete`, `improvement_questions`, `improved_response` message types

#### Acceptance Criteria

1. THE files `reviewWebSocket.ts`, `predictionService.ts`, `ImprovementModal.tsx`, `useImprovementHistory.ts`, and `StreamingPrediction.tsx` SHALL be deleted.
2. ALL references to deleted files SHALL be removed from `services/index.ts` and any other barrel exports.
3. NO frontend code SHALL reference the old v1 message types: `call_response`, `review_complete`, `improvement_questions`, `improved_response`.
4. THE `useReviewState.ts` hook SHALL be cleaned up to remove v1 HITL artifacts (e.g., `setImprovementInProgress` if no longer needed after clarification UI is built).

### Requirement 4: Verify LogCallButton Compatibility

**User Story:** As a user, I want to save my prediction to the database after seeing the structured result, so that it's tracked for verification.

**Current state:** `LogCallButton` expects `response.results[0]` to contain the prediction data. The `prediction_ready` handler in `callService.ts` calls `onComplete(data.data)`, and `StreamingCall.tsx` wraps it as `{results: [parsedResponse]}`. The field names in `prediction_ready` may differ from what the `/log-call` API expects.

#### Acceptance Criteria

1. THE LogCallButton SHALL successfully save predictions from the v2 `prediction_ready` data format.
2. THE prediction data sent to `/log-call` SHALL contain all required fields: prediction_statement, verification_date, verifiable_category, category_reasoning, verification_method, date_reasoning.
3. THE DynamoDB save format SHALL remain unchanged from v1.

### Requirement 5: End-to-End Validation

**User Story:** As a developer, I want the complete prediction flow to work end-to-end: make prediction → see streaming text → see structured result → optionally clarify → log call.

#### Acceptance Criteria

1. THE user SHALL be able to make a prediction and see the structured result displayed.
2. THE user SHALL be able to log the prediction to DynamoDB via the LogCallButton.
3. THE user SHALL be able to submit a clarification and see the updated prediction.
4. `npm run build` SHALL complete with zero TypeScript errors.
5. No console errors SHALL appear during normal prediction flow (excluding browser extension noise).
