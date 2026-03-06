# CalledIt v2 — Feature Description for Kiro Spec

**Project:** CalledIt
**Feature:** Unified graph architecture with stateful multi-round refinement
**Status:** Design complete, implementation planned
**For:** Kiro spec generation

---

## What We Are Building

A redesign of the CalledIt prediction pipeline replacing the current two-Lambda architecture (strands_make_call + improve_call) with a single unified Strands GraphBuilder graph that includes all four agents, supports parallel branch delivery to the client, and carries full state history across multiple refinement rounds.

---

## Problem With the Current Design

The current architecture has three issues the v2 redesign fixes:

**1. ReviewAgent is outside the graph unnecessarily.**
It runs in a separate invocation with separate Lambda cold-start cost and no access to graph state. It only needs the final pipeline JSON, which can be passed to it as a graph node.

**2. The HITL loop uses hardcoded cascade logic.**
`improve_call.py` contains explicit rules: "if prediction_statement changes, also regenerate verification_date and verification_method." This is brittle. Agents are better positioned to decide whether new information requires them to update their section.

**3. State is not preserved across refinement rounds.**
Each HITL cycle starts from a partial regeneration rather than a full re-run with accumulated context. Agents have no awareness of what was decided in previous rounds or what the user has progressively clarified. The prediction cannot get smarter with each cycle.

---

## What the v2 Design Does

### 1. ReviewAgent joins the graph as a parallel branch

After the three pipeline agents complete (Parser → Categorizer → VerificationBuilder), the graph forks. One branch returns the pipeline JSON to the client immediately via WebSocket. ReviewAgent runs in the parallel branch and pushes its meta-analysis to the client when ready.

The client receives two pushes per round:
- `prediction_ready` — structured prediction, immediately submittable
- `review_ready` — improvable sections identified by ReviewAgent

The human has a usable, submittable result without waiting for review.

### 2. Full graph re-trigger replaces improve_call Lambda

When the user provides a clarification, the entire graph re-runs with an enriched initial state. The `improve_call` Lambda is eliminated. Agents receive their previous output plus the new clarification and decide for themselves whether to update their section.

Agent system prompt instruction: *"You are refining a prediction. Your previous output is provided. Review it in light of any new user clarifications — confirm it if it stands, update it if the new information makes a more precise version possible. We are iterating toward greater specificity with each round."*

### 3. PredictionGraphState carries full round history

The state schema gains three new fields:

```python
class PredictionGraphState(TypedDict):
    # Existing fields
    prompt: str
    timezone: str
    datetime: str
    prediction_statement: str
    verification_date: str
    date_reasoning: str
    verifiable_category: str
    category_reasoning: str
    verification_method: VerificationMethod
    reviewable_sections: list[ReviewableSection]

    # New fields for v2
    round: int                        # increments with each re-trigger, starts at 1
    user_clarifications: list[str]    # accumulates ALL clarifications across rounds
    prev_parser_output: dict          # parser output from previous round, None in round 1
    prev_categorizer_output: dict     # categorizer output from previous round
    prev_vb_output: dict              # verification builder output from previous round
```

### 4. Human can submit at any time

The first-round pipeline result is complete and submittable the moment `prediction_ready` arrives. Clarification rounds are opportunity, not requirement. The user can submit after zero, one, or multiple refinement cycles.

### 5. Social media blast is unchanged

Post-verification, if the prediction resolves as TRUE, a deterministic social media blast is triggered. This is outside the graph and unchanged from v1.

---

## Files to Create or Modify

### Modify
- `handlers/strands_make_call/graph_state.py` — add `round`, `user_clarifications`, `prev_parser_output`, `prev_categorizer_output`, `prev_vb_output` to PredictionGraphState TypedDict
- `handlers/strands_make_call/prediction_graph.py` — add ReviewAgent as parallel branch node after pipeline completes; implement two-push WebSocket delivery (pipeline first, review when ready)
- `handlers/strands_make_call/strands_make_call_graph.py` — update lambda_handler to accept and pass round + clarification history in initial state; remove improve_call routing logic
- `handlers/strands_make_call/parser_agent.py` — update system prompt to handle refinement mode (round > 1)
- `handlers/strands_make_call/categorizer_agent.py` — update system prompt to handle refinement mode
- `handlers/strands_make_call/verification_builder_agent.py` — update system prompt to handle refinement mode
- `handlers/strands_make_call/review_agent.py` — move into graph as a node; remove standalone invocation interface

### Delete
- `handlers/websocket/improve_call.py` — replaced entirely by graph re-trigger
- Any CDK/SAM config referencing the improve_call Lambda

### Frontend (React)
- Handle two WebSocket push types: `prediction_ready` (display immediately) and `review_ready` (display improvable sections when they arrive)
- On user clarification: send `{action: "clarify", user_input, current_state}` — backend re-triggers full graph
- Submit button available from `prediction_ready` onward regardless of review state

---

## Behavior Per Round

**Round 1 (initial submission):**
- State: prompt + timezone + datetime, all prev fields null, round=1, clarifications=[]
- Agents run from scratch
- Client receives `prediction_ready`, then `review_ready`

**Round 2+ (after clarification):**
- State: same prompt + all previous outputs + new clarification appended to list, round incremented
- Each agent sees its previous output and all clarifications to date
- Agents confirm or refine — they do not restart
- Client receives updated `prediction_ready`, then updated `review_ready`
- Previous round's result remains visible/submittable until new round completes

**Submission (any round):**
- User hits submit on any round's `prediction_ready` result
- Prediction saved to DynamoDB with status: pending, verification_date stored
- EventBridge triggers verification agent on that date

---

## What This Is Not

- This is not a streaming change — the two-push model uses existing WebSocket infrastructure
- This is not a DynamoDB schema change — prediction storage is unchanged
- This is not a verification pipeline change — EventBridge + verify_predictions Lambda unchanged
- The social media blast integration point is unchanged

---

## Definition of Done

- [ ] Single graph executes all four agents with ReviewAgent in parallel branch
- [ ] Client receives `prediction_ready` before ReviewAgent completes
- [ ] Client receives `review_ready` when ReviewAgent completes
- [ ] Re-trigger with clarification runs full graph with enriched state
- [ ] Each agent's system prompt handles round > 1 correctly (refine, not restart)
- [ ] `user_clarifications` list accumulates correctly across all rounds
- [ ] improve_call Lambda deleted, CDK config updated
- [ ] Submit available from round 1 `prediction_ready` onward
- [ ] Round 1 behavior identical to current v1 behavior (regression test)
