# Project Update 01 — v2 Spec Planning Session

**Date:** March 6, 2026
**Context:** Planning session for CalledIt v2 unified graph architecture
**Audience:** Future self for project narrative; next agent for context pickup

---

## What Happened

Started a Kiro spec session to plan the CalledIt v2 feature: replacing the current two-path architecture (3-agent graph + standalone ReviewAgent + separate HITL improvement loop) with a single unified Strands GraphBuilder graph that includes all four agents, supports parallel branch delivery, and carries full state history across multiple refinement rounds.

## The v2 Feature in Brief

The current v1 architecture has three problems:
1. ReviewAgent runs outside the graph as a standalone invocation — extra Bedrock call setup, no graph state access
2. The HITL improvement loop uses hardcoded cascade logic in `regenerate_section()` — brittle, developer-maintained dependency rules
3. State is not preserved across refinement rounds — agents can't learn from previous iterations

v2 fixes all three by:
- Moving ReviewAgent into the graph as a parallel branch (pipeline results delivered immediately, review arrives async)
- Replacing the HITL loop with full graph re-trigger on user clarification (agents decide whether to update, not hardcoded rules)
- Adding round tracking and clarification history to PredictionGraphState

## Key Decisions Made During the Session

### Decision 1: Drop backward compatibility on the wire protocol

The initial requirements doc (Requirement 9) said the v2 `prediction_ready` message should be "backward compatible with the existing `call_response` message format." We challenged this.

**The problem:** The frontend already needs changes for `prediction_ready`, `review_ready`, and the new `clarify` action. The existing `callService.ts` has v1 HITL cruft baked in — `data.improved || this.isImprovementInProgress` logic, handlers for `improvement_questions` and `improved_response` message types. All of that is dead the moment the HITL loop is replaced by graph re-trigger.

**The decision:** Clean break on the WebSocket protocol. New message types (`prediction_ready`, `review_ready`) only. Old types (`call_response`, `review_complete`, `improvement_questions`, `improved_response`) removed entirely. The only true backward compatibility constraint is the DynamoDB save format, since existing predictions must remain queryable.

**Why:** This is a demo/educational project with no external API consumers. We control both sides. Keeping old types alive creates two code paths for the same thing and confuses future readers.

### Decision 2: Identified and addressed additional architectural debt

After the initial 10 requirements were drafted, we did a deep code review and found several issues worth fixing now rather than carrying forward:

1. **`review_agent.py` imports a deleted module** — `from error_handling import safe_agent_call, with_agent_fallback` would crash on import because `error_handling.py` was deleted from `handlers/strands_make_call/` during the January 2026 cleanup. Only works today because nothing imports ReviewAgent in the graph path.

2. **Dead `*_node_function()` code in all three agent files** — `parser_node_function()`, `categorizer_node_function()`, `verification_builder_node_function()` are leftover from a custom-node architecture. The graph only uses the `create_*_agent()` factory functions. The node functions are never imported or called.

3. **120 lines of regex JSON extraction** — `parse_graph_results()` + `extract_json_from_text()` try 5 different regex strategies to find JSON in agent output. This is the exact anti-pattern the Strands best practices call out. Fix the prompts instead of masking bad output.

4. **Response building split across two files** — `execute_prediction_graph()` adds metadata and fallback defaults, then `lambda_handler()` builds a separate response dict with its own metadata and fallbacks. Two layers of "ensure fields exist" logic.

5. **No separate `improve_call.py` file** — The architecture diagrams reference it, but the actual code routes `improve_section` and `improvement_answers` actions to the same MakeCallStreamFunction Lambda. The HITL logic lives in ReviewAgent's methods. So "delete improve_call Lambda" is really "delete HITL methods from ReviewAgent and remove SAM routes."

These were added as Requirements 11-13 in the original combined spec.

### Decision 3: Split into two specs

The combined spec had 13 requirements touching every file in the prediction pipeline plus the SAM template plus the frontend. We assessed confidence at ~65% for a single spec vs ~90% for two focused specs.

**Spec 1: v2 Cleanup & Foundation** (`.kiro/specs/v2-cleanup-foundation/`)
- 5 requirements: dead code cleanup, ReviewAgent rewrite as factory function, simplified JSON parsing, consolidated response building, stale SAM route removal
- All refactoring — no new behavior. v1 continues to work exactly the same after deployment.
- Independently valuable even if Spec 2 is paused.

**Spec 2: v2 Unified Graph with Stateful Refinement** (`.kiro/specs/v2-unified-graph-refinement/`)
- 9 requirements: unified graph structure, two-push delivery, stateful round history, graph re-trigger, agent refinement mode, submit-anytime UX, clean v2 protocol, WebSocket routing, round 1 quality
- The actual architectural change — new behavior, new graph topology, new frontend protocol.
- Assumes Spec 1 is complete.

**Why split:**
- If Spec 2 goes sideways (parallel branch timing, state propagation surprises), you're debugging against clean code
- Spec 1 teaches Strands patterns (factory functions, clean JSON parsing) before Spec 2 extends them (parallel branches, state propagation)
- Context window pressure — 13 requirements with all the files is a lot for one execution pass

The original combined spec at `.kiro/specs/unified-graph-refinement/` was archived with an `ARCHIVED.md` marker.

## Current State of the Specs

### Spec 1: v2 Cleanup & Foundation
- **Location:** `.kiro/specs/v2-cleanup-foundation/`
- **Status:** Requirements complete, ready for design phase
- **Requirements:** 5 (dead code, ReviewAgent rewrite, JSON parsing, response building, SAM routes)
- **Next step:** Generate design.md, then tasks.md, then execute

### Spec 2: v2 Unified Graph with Stateful Refinement
- **Location:** `.kiro/specs/v2-unified-graph-refinement/`
- **Status:** Requirements complete, waiting for Spec 1 to finish before starting design
- **Requirements:** 9 (unified graph, two-push delivery, stateful rounds, re-trigger, refinement mode, submit UX, v2 protocol, routing, quality)
- **Next step:** After Spec 1 is deployed, generate design.md for Spec 2

### Archived: Original Combined Spec
- **Location:** `.kiro/specs/unified-graph-refinement/`
- **Status:** Archived — `ARCHIVED.md` explains the split
- **Note:** The `requirements.md` here is the original 13-requirement combined doc, preserved for reference

## User's Learning Goals

The user explicitly stated that learning is as important as building. All spec documents, code, and comments should:
- Explain the what AND why of every decision
- Discuss alternatives considered and why they were rejected
- Comment code verbosely to teach Strands patterns
- Explain graph orchestration and context propagation concepts as they come up

## Files Created/Modified in This Session

- `.kiro/specs/v2-cleanup-foundation/requirements.md` — Spec 1 requirements (5 reqs)
- `.kiro/specs/v2-cleanup-foundation/.config.kiro` — Spec 1 config
- `.kiro/specs/v2-unified-graph-refinement/requirements.md` — Spec 2 requirements (9 reqs)
- `.kiro/specs/v2-unified-graph-refinement/.config.kiro` — Spec 2 config
- `.kiro/specs/unified-graph-refinement/ARCHIVED.md` — Archive marker for original combined spec
- `.kiro/specs/unified-graph-refinement/requirements.md` — Modified during session (backward compat update, added reqs 11-13), now archived
- `docs/project-updates/01-project-update.md` — This file

## Key Reference Files for Next Agent

When picking up this project, the next agent should read:
1. `calledit-v2-feature-description.md` — The full v2 feature description with diagrams
2. `calledit-architecture-diagrams.md` — v1 and v2 architecture diagrams (Mermaid)
3. `.kiro/specs/v2-cleanup-foundation/requirements.md` — Spec 1 requirements (start here)
4. `.kiro/specs/v2-unified-graph-refinement/requirements.md` — Spec 2 requirements (after Spec 1)
5. `.kiro/steering/strands-best-practices.md` — Strands development patterns to follow
6. `.kiro/steering/aws-security-requirements.md` — AWS security rules (private S3 only, etc.)

The current codebase files that will be modified:
- `backend/calledit-backend/handlers/strands_make_call/` — All agent files, graph, handler, state
- `backend/calledit-backend/template.yaml` — SAM template (route changes)
- `frontend/src/services/callService.ts` — WebSocket message handling (Spec 2)

## Strands Power Available

The workspace has the Strands Kiro Power installed, which provides documentation search and fetch tools for Strands SDK. Use `kiroPowers` with `action="activate"`, `powerName="strands"` to access Strands documentation during implementation.

### Decision 4: Prompt-first approach to JSON parsing cleanup

After drafting the requirement to remove the defensive JSON parsing (120 lines of regex fallbacks), the user correctly pointed out: "The defensive JSON is a sign we had an issue. It's probably still there."

**Root cause:** The current agent prompts say `Return JSON:` followed by an example, but don't explicitly prohibit markdown wrapping or extra text. Claude models will often wrap output in ` ```json ``` ` blocks when they see that pattern. The `extract_json_from_text()` function exists because agents were actually returning malformed output.

**Updated approach (three steps, not one):**
1. Harden the prompts — add explicit "Return ONLY the raw JSON object. No markdown, no code blocks, no explanation text."
2. Build a prompt testing harness — invoke each agent multiple times, validate `json.loads(str(result))` succeeds without regex, report success rates
3. Only then simplify the parsing — remove `extract_json_from_text()` after the harness proves prompts work

This is captured in Spec 1 Requirement 3 (renamed from "Simplified JSON Parsing" to "Prompt Hardening and Simplified JSON Parsing"). The testing harness becomes a permanent part of the test suite for ongoing regression detection — if a model update or prompt change breaks clean JSON output, the tests catch it.

This is also a good learning moment: defensive code often exists for a reason. The fix isn't to delete the defense — it's to fix the root cause and then delete the defense once you've proven the fix works.

### Decision 5: Strands documentation review via Kiro Power

Late in the session, we activated the Strands Kiro Power and reviewed the official Graph documentation. This surfaced two critical findings that changed the Spec 2 requirements:

**Finding 1: Default edge behavior is "any one" not "all"**
The Strands Graph docs state: "When multiple nodes have edges to a target node, the target executes as soon as any one dependency completes." This means if we naively add edges from Parser, Categorizer, and Verification Builder to ReviewAgent, ReviewAgent would fire as soon as Parser completes — before the other two agents have run. The fix is conditional edges with an `all_dependencies_complete` check, which is documented in the Strands docs. Updated Spec 2 Requirement 1 AC #3.

**Finding 2: Graph doesn't support mid-execution message sending**
The Graph runs to completion and returns a `GraphResult`. There's no built-in way to send WebSocket messages when an intermediate node completes. The solution is `stream_async` with `multiagent_node_stop` events — listen for the `verification_builder` node completing and send `prediction_ready` at that point, then send `review_ready` when the `review` node completes. This is the official Strands streaming API. Updated Spec 2 Requirement 2 with the `stream_async` approach and documented the alternative (two separate graph executions) and why we rejected it.

These findings would have caused significant debugging time if discovered during implementation rather than during requirements. This validates the value of checking framework docs during spec creation, not just during coding.

### Decision 6: Model upgrade from Claude 3.5 Sonnet to Claude Sonnet 4

During design review, we noticed all four agents use `anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2, October 2024). The Strands SDK default is now Claude Sonnet 4 (`anthropic.claude-sonnet-4-20250514-v1:0`), confirmed via the Strands Kiro Power documentation.

**Why upgrade:**
- Better instruction following — directly relevant to the JSON output problem (our prompts need agents to return raw JSON without markdown wrapping)
- Same Sonnet tier — similar latency and cost, not a jump to Opus pricing
- Current Strands default — the framework is optimized for it
- Supports `Agent.structured_output()` if we ever want it

**When:** Before prompt hardening, as step 0 of Spec 1 Requirement 3. The four-step approach is now: (0) upgrade model, (1) harden prompts, (2) validate with testing harness, (3) simplify parsing. This way we validate against the model we'll actually run in production.

**Risk:** The model might need a `us.` prefix for cross-region inference depending on the AWS region. The testing harness will catch this immediately. Confidence: 85%.

Updated Spec 1 Requirement 3 (renamed to "Model Upgrade, Prompt Hardening, and Simplified JSON Parsing") and the design doc Component 3.

## Spec 1 Execution Complete — March 6, 2026

All 13 tasks executed successfully. Key milestones:

- Dead code removed (3 node functions, broken error_handling import)
- ReviewAgent rewritten as factory function matching other 3 agents
- Model upgraded from Claude 3.5 Sonnet to Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-20250514-v1:0`)
- Prompts hardened with explicit JSON output instructions
- Prompt testing harness validated 12/12 clean JSON parses across all 4 agents
- Mid-spec production deploy confirmed model upgrade works in production
- `extract_json_from_text()` removed (120 lines of regex → single `json.loads()` per agent)
- Response building consolidated from 2 files into 1 (Lambda handler only)
- Stale SAM routes removed (`improve_section`, `improvement_answers`)

Remaining: final `sam build && sam deploy` to push tasks 8, 10, 12 changes. Then Spec 1 is done and Spec 2 can begin.
