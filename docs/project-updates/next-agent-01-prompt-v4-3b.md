# Next Agent Prompt — Execute V4-3b (Clarification & Streaming)

**Date:** March 23, 2026
**Previous session:** V4-3a Creation Agent Core completed + V4-3b fully specced

---

## Session Goal

Execute the V4-3b spec (Clarification & Streaming). The spec is fully written — requirements, design, and tasks are all complete and approved. Your job is to execute the tasks.

## Read These Files FIRST

1. `.kiro/specs/clarification-streaming/tasks.md` — the task list you're executing
2. `.kiro/specs/clarification-streaming/design.md` — the technical design with code examples
3. `.kiro/specs/clarification-streaming/requirements.md` — 9 requirements with acceptance criteria
4. `docs/project-updates/24-project-update-v4-3a-creation-agent-core.md` — what just happened (V4-3a complete)
5. `docs/project-updates/v4-frontend-analysis.md` — frontend analysis that informed V4-3b design
6. `docs/project-updates/v4-agentcore-architecture.md` — MANDATORY architecture reference
7. `.kiro/steering/agentcore-architecture.md` — MANDATORY architecture guardrails
8. `calleditv4/src/main.py` — current working entrypoint (V4-3a: sync, 3-turn creation flow)
9. `calleditv4/src/bundle.py` — current bundle module (needs 3 new functions)
10. `calleditv4/src/models.py` — current Pydantic models (needs ClarificationAnswer)
11. `docs/project-updates/common-commands.md` — all current commands

## What V4-3b Delivers

The V4-3a entrypoint is synchronous and returns a single JSON string. V4-3b evolves it to:

1. **Async streaming** — `async def handler()` with `yield` for turn-by-turn progress events
2. **Clarification rounds** — user answers reviewer questions → agent re-runs 3-turn flow with context → DDB update_item
3. **User timezone from payload** — Decision 101, frontend sends timezone via `Intl.DateTimeFormat()`
4. **Stream event format** — `{type, prediction_id, data}` with 4 event types: flow_started, turn_complete, flow_complete, error

## Key Decisions

- Decision 96: NO MOCKS by default. Must prove value + get user approval before any mock.
- Decision 98: No fallbacks in dev (fail clearly), graceful fallback in production.
- Decision 99: 3 turns not 4 (merged score + review into plan-reviewer).
- Decision 100: LLM-native date resolution (current_time tool + Code Interpreter).
- Decision 101: User timezone from frontend payload takes priority over server timezone.
- 101 decisions total documented in `docs/project-updates/decision-log.md`.

## Import Gotchas Discovered in V4-3a

- `current_time`: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext`: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- AWS region: NO hardcoded default — boto3 resolves from CLI config
- Pydantic 2.11.3 available as transitive dep of strands-agents (no need to add to pyproject.toml)

## AgentCore Streaming Pattern (VERIFIED)

```python
@app.entrypoint
async def agent_invocation(payload, context):
    agent_stream = agent.stream_async(user_message)
    async for event in agent_stream:
        yield event
```

The AgentCore runtime detects async generators and wraps them in SSE (Server-Sent Events) format automatically.

## Testing

- 133 V4-3a tests currently passing
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- `agentcore dev` uses the project's `.venv/` — dependencies must be in `pyproject.toml`
- TTY errors in terminal: stop immediately and ask the user to run the command
- Property tests use Hypothesis with `@settings(max_examples=100)`

## CRITICAL — Project Documentation

After completing the spec, update the living documentation:
- Create `docs/project-updates/25-project-update-v4-3b-clarification-streaming.md`
- Update `docs/project-updates/decision-log.md` with any new decisions
- Update `docs/project-updates/project-summary.md` with new entry and refreshed Current State
- Update `docs/project-updates/backlog.md` if items are addressed or new ones identified
- Update `docs/project-updates/common-commands.md` with new v4 commands

## AgentCore Steering

The AgentCore steering doc (`.kiro/steering/agentcore-architecture.md`) requires you to FLAG any deviation from AgentCore recommended patterns. Use your Kiro AgentCore power to search docs and validate approaches.
