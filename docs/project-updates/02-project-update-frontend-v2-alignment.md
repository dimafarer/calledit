# Project Update 02 — Spec 3 Design Session (Frontend v2 Protocol Alignment)

**Date:** March 9, 2026
**Context:** Design phase for Spec 3 — fixing the frontend to work with the v2 backend
**Audience:** Future self for project narrative; next agent for context pickup

### Referenced Kiro Specs
- `.kiro/specs/v3-frontend-v2-protocol/` — Spec 3: Frontend v2 Protocol Alignment
  - `requirements.md` — COMPLETE (created in previous session, see Update 01)
  - `design.md` — COMPLETE (created in this session)
  - `tasks.md` — NOT YET CREATED (next step)

### Referenced Git Commits
- `bea2d56` (HEAD) — Spec 2 complete (backend), Spec 3 created (frontend fixes)
- Note: No new commits in this session — design.md is uncommitted

### Prerequisite Reading
- `docs/project-updates/01-project-update.md` — Full narrative of Specs 1 and 2

---

## What Happened

Picked up the project from where Update 01 left off. Spec 1 (cleanup) and Spec 2 (unified graph backend) are complete and deployed. The backend works correctly — `prediction_ready` and `review_ready` messages arrive as confirmed via browser console logs. But the frontend has three categories of issues that need fixing, captured in Spec 3's requirements (5 requirements, created at the end of the previous session).

This session focused on generating the design document for Spec 3. The design required deep investigation into the Strands SDK streaming behavior, careful analysis of the existing frontend code, and tracing the exact data flow between backend and frontend to identify the real root causes.

## Key Investigation: The Streaming Text Mystery

The biggest question going into this session was Requirement 1: why doesn't streaming text display during agent processing? The previous session's handoff notes said the issue was in the backend's `execute_and_deliver()` function, but the exact cause was unclear.

### What We Investigated

We activated the Strands Kiro Power and pulled the official Graph streaming documentation. The key finding:

**`stream_async` DOES forward agent text events.** The Strands docs show this pattern explicitly:
```python
elif event.get("type") == "multiagent_node_stream":
    inner_event = event["event"]
    if "data" in inner_event:
        print(inner_event["data"], end="")
```

The current backend code in `execute_and_deliver()` matches this pattern exactly:
```python
if event_type == "multiagent_node_stream":
    inner_event = event_data.get("event", {})
    if "data" in inner_event:
        send_ws(api_gateway_client, connection_id, "text", content=inner_event["data"])
```

### The Wire Format Analysis

We then traced the full message path to check for format mismatches:

1. `send_ws(..., "text", content=inner_event["data"])` — `content` goes into `**extra` kwargs
2. `send_ws` builds: `{"type": "text"}` then `message.update(extra)` → `{"type": "text", "content": "..."}`
3. Frontend `websocket.ts` parses JSON, passes full message object to handler
4. `callService.ts` text handler: `onTextChunk(data.content)` where `data` IS the full message

The wire format is correct. `data.content` accesses the top-level `content` field. No nesting mismatch.

### The Conclusion

The previous session's handoff notes suggested the issue might be that `send_ws` puts extras at the top level instead of nesting under `data`. But after tracing the code, the frontend handler receives the full message object and accesses `.content` directly — which IS at the top level. The format should work.

This means the streaming text issue is likely one of:
1. `stream_async` in the Lambda async context doesn't yield `multiagent_node_stream` events with `data` in practice (maybe only lifecycle events get forwarded)
2. There's a buffering/timing issue in the Lambda async execution
3. The WebSocket sends are failing silently (send_ws catches all exceptions)

### Design Decision: Two-Track Investigation

Rather than guessing, the design proposes a two-track approach:

**Track A — Verify current code works:**
Add debug logging to `execute_and_deliver()` to log ALL events from `stream_async`. Make a test prediction, check CloudWatch. If `multiagent_node_stream` events with `data` appear, the code should work — look for WebSocket send failures. If no `data` events appear, `stream_async` doesn't forward text events in this context.

**Track B — Fallback to per-agent callbacks:**
If Track A fails, restore the v1 callback pattern. Create a `create_streaming_callback()` function, pass it to each agent's `callback_handler` when creating agents in `prediction_graph.py`. Text chunks go directly to WebSocket via callbacks, bypassing `stream_async`. The graph's `stream_async` still handles `node_stop` events for two-push delivery.

**Why callbacks work inside a graph:** Strands agents fire their `callback_handler` during execution regardless of whether they're running as graph nodes. The callback is an agent-level feature, not a graph-level feature. So `stream_async` and agent callbacks are independent channels — you can use both simultaneously.

This is a good learning moment: the Strands SDK has two independent streaming mechanisms (graph-level `stream_async` and agent-level `callback_handler`), and they can coexist. The graph doesn't suppress agent callbacks.

## Clarification UI Design

The second major design component was the clarification UI (Requirement 2). The key insight here was that most of the work is already done — we just need to reconnect existing pieces.

### What Already Exists
- `ImprovementModal.tsx` — Fully functional modal with questions + text inputs. Just commented out in `StreamingCall.tsx`.
- `ReviewableSection.tsx` — Clickable sections with ✨ badges. Already wired to `handleImprove()`.
- `useReviewState.ts` — Manages modal open/close state. Already works.
- `callService.sendClarification()` — Already implemented and sends the right WebSocket message.

### What Needs Wiring
The design specifies exactly what to change in `StreamingCall.tsx`:
1. Uncomment the `ImprovementModal` JSX
2. Import `ImprovementModal`
3. Add `handleClarificationSubmit` that formats answers as a Q&A string and calls `sendClarification()`
4. Add `handleModalCancel` that calls `cancelImprovement()` from `useReviewState`
5. Destructure `cancelImprovement` from the hook (it's returned but not currently destructured)

### Why Format Answers as a String

The backend's `build_clarify_state` puts `user_input` into the `user_clarifications` list, which gets appended to the agent prompt. Agents read natural language, not JSON. A formatted Q&A string like:
```
Q: What city are you in?
A: San Francisco
```
...is exactly what agents need. The backend doesn't parse the clarification — it passes it through to the prompt verbatim.

### Multi-Round Support Is Free

Each `prediction_ready` message includes `round` and `user_clarifications` in its data (added by `build_prediction_ready()`). When the user clarifies, the frontend sends this data back as `currentState`. The backend increments `round` and appends the new clarification. No special multi-round logic needed in the frontend — it's inherent in the data flow. This is the "frontend-as-session" pattern (Decision 8 from Update 01) paying off.

## LogCallButton Compatibility

We did a field-by-field analysis of the `prediction_ready` data shape vs what `LogCallButton` expects. Every required field matches: `prediction_statement`, `verification_date`, `verifiable_category`, `category_reasoning`, `verification_method`, `initial_status`, `prediction_date`, `local_prediction_date`, `date_reasoning`.

The v2 data includes two extra fields (`round`, `user_clarifications`) that v1 didn't have. These are harmless — the `/log-call` API and DynamoDB write ignore unknown fields.

**Verdict:** No changes needed. LogCallButton is already compatible.

## Correctness Properties

The design defines 5 correctness properties for property-based testing:

1. **send_ws text message format** — For any text string, `send_ws` with type "text" and content=text produces `{"type": "text", "content": text}`. Tests the wire format contract.

2. **Review sections state management** — For any list of ReviewableSection objects, `updateReviewSections(sections)` stores them faithfully and clears the review status.

3. **Clarification string formatting** — For any list of Q&A pairs, the formatted string contains every question and every non-empty answer. Tests that no user input is lost.

4. **Round state accumulation** — For any round N and clarification list, `build_clarify_state` produces round N+1 with the new clarification appended. Core multi-round correctness.

5. **prediction_ready contains all required fields** — For any valid pipeline_data and state, `build_prediction_ready` returns all fields the frontend and LogCallButton depend on.

Properties 1, 4, 5 are Python (Hypothesis). Properties 2, 3 are TypeScript (fast-check). The design also calls for extracting `formatClarification` into a pure utility function for independent testability.

## Dead Code Removal

Straightforward — 4 files to delete, 1 barrel export to clean up:
- `reviewWebSocket.ts` — v1 review handler, not imported
- `predictionService.ts` — v1 prediction service, replaced by `callService.ts`
- `useImprovementHistory.ts` — v1 improvement history, not imported
- `StreamingPrediction.tsx` — v1 streaming component, not rendered
- `services/index.ts` — remove `export * from './predictionService'`

`ImprovementModal.tsx` is explicitly NOT dead code — it's being re-enabled for v2.

## Current State

### Spec 3: Frontend v2 Protocol Alignment
- **Location:** `.kiro/specs/v3-frontend-v2-protocol/`
- **Status:** Requirements COMPLETE, Design COMPLETE, Tasks NOT YET CREATED
- **Next step:** Generate tasks.md, then execute

### What the Next Agent Should Do
1. Read this update and Update 01 for full context
2. Read `.kiro/specs/v3-frontend-v2-protocol/requirements.md` and `design.md`
3. Generate `tasks.md` from the design
4. Execute the tasks — start with Req 1 (streaming text investigation) since it determines whether backend changes are needed
5. Then Req 3 (dead code removal — quick win, reduces noise)
6. Then Req 2 (clarification UI — the main frontend work)
7. Then Req 4 (LogCallButton verification — likely no changes needed)
8. Finally Req 5 (end-to-end validation)

### Key Files for Next Agent

Backend (working, only change if streaming investigation requires it):
- `backend/calledit-backend/handlers/strands_make_call/strands_make_call_graph.py` — Lambda handler with `send_ws`, `execute_and_deliver`, state builders
- `backend/calledit-backend/handlers/strands_make_call/prediction_graph.py` — Graph with `stream_async`, parse functions

Frontend (needs fixes):
- `frontend/src/services/callService.ts` — v2 message handlers, `sendClarification()`
- `frontend/src/components/StreamingCall.tsx` — Main component, `ImprovementModal` commented out
- `frontend/src/components/ImprovementModal.tsx` — Modal component, needs rewiring
- `frontend/src/components/ReviewableSection.tsx` — Clickable sections (working)
- `frontend/src/hooks/useReviewState.ts` — Review state management (working)
- `frontend/src/components/LogCallButton.tsx` — Save button (compatible, verify only)

Dead v1 files to delete:
- `frontend/src/services/reviewWebSocket.ts`
- `frontend/src/services/predictionService.ts`
- `frontend/src/hooks/useImprovementHistory.ts`
- `frontend/src/components/StreamingPrediction.tsx`

### Strands Power Notes

The Strands Kiro Power was activated during this session and used to:
- Fetch the official Graph streaming documentation (confirmed `stream_async` forwards `multiagent_node_stream` events with `data` for text chunks)
- Fetch the callback handler documentation (confirmed agents fire callbacks independently of graph-level streaming)
- Review the streaming overview for all multi-agent event types

These findings directly shaped the two-track investigation approach in the design doc.

---

## Spec 3 Execution — March 9, 2026

All required tasks executed successfully. The spec is complete.

### Task 1: Streaming Text — The Stale Build Cache

The streaming text "issue" from Spec 2 was never a code problem. The debug logging was already in `execute_and_deliver()` from the previous session. When we deployed, the Lambda crashed with `No module named 'strands'` — the SAM build had a stale deps cache that never installed `strands-agents`.

The fix: `rm -rf .aws-sam/deps && rm -rf .aws-sam/build && sam build`. After a clean build, streaming worked perfectly. CloudWatch confirmed:
- `multiagent_node_stream: 542` events
- `text_chunks_sent=237`
- `tool_events_sent=11`
- All 4 nodes started and completed

Track A from the design was confirmed: `stream_async` DOES forward agent text events as `multiagent_node_stream` with `data`. No code changes needed for streaming.

### Task 3: Dead Code Removal

Deleted 4 files, removed 1 barrel export. Clean and uneventful:
- `reviewWebSocket.ts`, `predictionService.ts`, `useImprovementHistory.ts`, `StreamingPrediction.tsx` — all confirmed dead via grep
- Removed `export * from './predictionService'` from `services/index.ts`
- `setImprovementInProgress` in `useReviewState` kept — still used for clarification round state

### Task 4: Clarification UI — Two Bugs Found During Wiring

The ImprovementModal was uncommented and wired to `sendClarification()`. Two bugs surfaced during testing:

**Bug 1: ReviewAgent section names use dot notation**
The ReviewAgent returns sections like `verification_method.source`, `verification_method.criteria`, `verification_method.steps` — but the JSX was checking for exact matches like `verification_method`. No match → no ✨ badges.

Fix: Changed all section matching to use `startsWith` — `s.section === 'verification_method' || s.section.startsWith('verification_method.')`. Also aggregated questions from all matching sub-sections using `flatMap`. Same fix applied to `prediction_statement` and `verifiable_category` for consistency.

**Bug 2: Empty clarification string**
`handleClarificationSubmit` looked up questions from `reviewableSections` using `improvingSection`, but the section name was `"verification_method"` (the parent) while the actual sections in state were `verification_method.source` etc. The `find` returned `undefined`, so questions was `[]`, and `formatClarification([], answers)` produced an empty string. The backend rejected it with `"Missing required field: user_input"`.

Fix: Instead of looking up questions from `reviewableSections` (which had the sub-section mismatch), we now use `reviewState.currentQuestions` — which was already set by `startImprovement()` with the aggregated questions.

### Task 7: Build Check

`npm run build` passes with zero TypeScript errors. One unused variable (`section`) was caught and removed.

### End-to-End Verification

Full 3-round clarification flow verified manually:
1. "It will be 70 degrees tomorrow" → prediction with streaming text + structured result
2. Clicked ✨ badge → modal with ReviewAgent questions → answered "New York"
3. Round 2 processed → updated prediction → new review questions → answered "Central Park"
4. Round 3 processed → final prediction with specific location

### Decision 9: ReviewAgent Sub-Section Names

The ReviewAgent returns dot-notation section names (`verification_method.source`) instead of top-level names (`verification_method`). This is actually better — it gives more specific improvement suggestions. The frontend now handles both patterns with `startsWith` matching and question aggregation.

This is worth noting for future agents: the ReviewAgent's output format drives the frontend's badge rendering. If the prompt changes to return different section names, the `startsWith` matching will handle it gracefully.

### Decision 10: Single-Push vs Two-Push Delivery

During testing, the user observed that the ReviewAgent completes quickly after the pipeline (2-4 seconds). The two-push design (prediction_ready then review_ready) was built to avoid making the user wait for review. But if review time is negligible, a single push at graph completion would simplify the frontend.

This is a future consideration — the two-push pattern is working and is educationally interesting as a Strands streaming pattern. But for a production app where review time is consistently fast, single-push would be simpler.

## Updated File List

Files created:
- `frontend/src/utils/formatClarification.ts` — Pure utility for Q&A formatting

Files modified:
- `frontend/src/components/StreamingCall.tsx` — ImprovementModal wired, section matching fixed
- `frontend/src/services/index.ts` — Removed dead predictionService export

Files deleted:
- `frontend/src/services/reviewWebSocket.ts`
- `frontend/src/services/predictionService.ts`
- `frontend/src/hooks/useImprovementHistory.ts`
- `frontend/src/components/StreamingPrediction.tsx`

## Updated Git Commit Reference

- Previous: `bea2d56` (HEAD at session start)
- This session: uncommitted — recommend committing as "Spec 3: Frontend v2 protocol alignment complete"
