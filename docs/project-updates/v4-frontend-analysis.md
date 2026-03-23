# CalledIt v4: Frontend Analysis & Technical Debt

> Analysis of the v3 React PWA frontend to inform v4 backend design decisions.
> Conducted during V4-3b (Clarification & Streaming) spec creation.

**Date:** March 23, 2026

---

## Current Frontend Architecture

The v3 frontend is a React PWA (mobile-first) with:
- WebSocket streaming via `CallService` + `WebSocketService`
- REST API via `PredictionInput` (axios to strands-make-call endpoint)
- Cognito authentication via `AuthContext`
- Clarification UI via `ImprovementModal` + `useReviewState` hook
- Local state management (no Redux/Zustand — hooks + refs)

## WebSocket Message Protocol (v3)

### Client → Server
| Action | Payload | When |
|--------|---------|------|
| `makecall` | `{prompt, timezone}` | Round 1 — user submits prediction |
| `clarify` | `{user_input, current_state}` | Round 2+ — user answers clarification questions |

### Server → Client
| Type | Data | Purpose |
|------|------|---------|
| `text` | `{content}` | Real-time text streaming from agents |
| `tool` | `{name}` | Agent tool usage notification |
| `prediction_ready` | `{data: prediction}` | Pipeline complete, structured result |
| `review_ready` | `{data: review}` | ReviewAgent questions for clarification |
| `complete` | `{status}` | Graph execution finished |
| `status` | `{status, message}` | Processing indicator |
| `error` | `{message}` | Backend error |

### v4 Stream Event Mapping
| v3 Type | v4 Equivalent | Notes |
|---------|---------------|-------|
| `text` | (not needed) | v4 streams turn completions, not token-by-token text |
| `tool` | (not needed) | Tool usage is internal to the agent |
| `prediction_ready` | `flow_complete` | Contains the full bundle |
| `review_ready` | `turn_complete` (turn 3) | Review data is part of the bundle |
| `complete` | (implicit after `flow_complete`) | No separate completion signal needed |
| `status` | `flow_started` | Processing indicator |
| `error` | `error` | Same concept, cleaner format |

## Clarification Flow (v3)

1. User submits prediction → `makecall` action with `{prompt, timezone}`
2. Backend streams `text` chunks, then sends `prediction_ready` + `review_ready`
3. Frontend renders `ReviewableSection` components with "Improve" buttons
4. User clicks "Improve" on a section → `ImprovementModal` opens with questions
5. User answers questions → `formatClarification()` creates Q&A string
6. Frontend calls `sendClarification(userInput, currentState)` → `clarify` action
7. Backend re-runs graph with enriched state → same message flow repeats
8. User can "Log Call" when satisfied → REST POST to `/log-call`

### Key Pattern: Frontend-as-Session (Decision 8)
The frontend holds ALL session state:
- Round number
- Accumulated clarifications
- Latest agent outputs (the entire prediction object)
- The `current_state` sent on clarification is the full prediction object

The backend is completely stateless — it doesn't look up previous state.

## Technical Debt Identified

### 1. Two Prediction Paths (HIGH)
**Problem:** `PredictionInput` uses REST (`axios.get` to strands-make-call), while `StreamingCall` uses WebSocket. Both exist in the codebase.
**Impact:** Confusing for developers, inconsistent UX (REST path has no streaming feedback).
**v4 Recommendation:** Consolidate to one path. The AgentCore streaming entrypoint replaces both — the client connects to AgentCore Runtime which handles transport.

### 2. Frontend Sends Entire Prediction Object on Clarification (MEDIUM)
**Problem:** `sendClarification(userInput, currentState)` sends the full prediction object as `current_state`. This is ~2-5KB per clarification round.
**Impact:** Stale state risk (if another client modified the prediction), unnecessary payload size, frontend complexity.
**v4 Recommendation:** Send `prediction_id` only. Backend loads current state from DDB. Eliminates stale state risk and reduces payload to ~50 bytes.

### 3. Clarification Answers as Unstructured String (MEDIUM)
**Problem:** `formatClarification()` converts Q&A pairs into a plain text string (`"Q: ...\nA: ..."`). The backend receives this as `user_input` — a single string, not structured data.
**Impact:** Backend can't programmatically identify which questions were answered. The agent has to parse natural language to understand the clarification.
**v4 Recommendation:** Send structured `[{question, answer}]` pairs. The backend can format them however the agent needs, and can also store them structured in `clarification_history`.

### 4. Timezone Sent but Ignored by v4 (HIGH — fixed in V4-3b)
**Problem:** The frontend sends `timezone` (e.g., `"America/New_York"`) with every `makecall` request. V4-3a's entrypoint ignores it — the parser relies on `current_time` tool's server timezone.
**Impact:** "Tonight" could be interpreted as server time (UTC or us-west-2) instead of the user's local time. This directly affects verification timing.
**v4 Fix:** V4-3b Requirement 9 adds `timezone` acceptance from the payload. Decision 101: user timezone from payload takes priority over server timezone.

### 5. Category Display Needs Replacement (LOW — V4-4)
**Problem:** `getVerifiabilityDisplay()` in StreamingCall.tsx renders `auto_verifiable`/`automatable`/`human_only` badges. v4 replaces categories with a continuous verifiability score (Decision 87).
**Impact:** Frontend will show stale category badges when connected to v4 backend.
**v4 Fix:** V4-4 (Verifiability Scorer) spec will add the green/yellow/red score indicator UI.

### 6. No Loading State Between Turns (LOW — V4-3b fixes)
**Problem:** v3 streams text chunks token-by-token, which gives continuous feedback. But the structured pipeline has 15-30 seconds of silence between `makecall` and `prediction_ready`.
**Impact:** User stares at a spinner with no indication of progress.
**v4 Fix:** V4-3b streams `turn_complete` events after each of the 3 turns, giving the user incremental feedback.

## Files Analyzed

| File | Purpose |
|------|---------|
| `frontend/src/services/websocket.ts` | WebSocket connection management, message routing by type |
| `frontend/src/services/callService.ts` | Prediction pipeline client, makecall/clarify actions |
| `frontend/src/components/StreamingCall.tsx` | Main prediction UI with streaming + clarification |
| `frontend/src/components/ImprovementModal.tsx` | Clarification question/answer modal |
| `frontend/src/components/PredictionInput.tsx` | REST-based prediction submission (non-streaming) |
| `frontend/src/components/LogCallButton.tsx` | Save prediction to DDB via REST |
| `frontend/src/hooks/useReviewState.ts` | Clarification round state management |
| `frontend/src/utils/formatClarification.ts` | Q&A pair → string formatter |
| `frontend/src/types/review.ts` | ReviewableSection, ReviewState types |
