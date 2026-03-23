# Project Update 23 — V4-2 Built-in Tools Complete

**Date:** March 22, 2026
**Context:** Wired AgentCore Browser and Code Interpreter into the v4 agent. Both tools validated via agentcore invoke --dev. Discovered that playwright and nest-asyncio are required dependencies of strands_tools.browser (not optional as initially thought).
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/builtin-tools/` — Spec V4-2 (COMPLETE)
- `.kiro/specs/agentcore-foundation/` — Spec V4-1 (COMPLETE, prerequisite)

### Prerequisite Reading
- `docs/project-updates/22-project-update-v4-1-agentcore-foundation.md` — V4-1 (foundation)

---

## What Happened This Session

### V4-2 Spec Execution (8 tasks, all complete)

1. **Verified dependencies** — `strands-agents-tools` v0.2.19 already installed, provides both `AgentCoreBrowser` and `AgentCoreCodeInterpreter`. Both import and instantiate cleanly in the project venv.

2. **Updated entrypoint** — Added ~10 lines to `calleditv4/src/main.py`: tool imports, `AWS_REGION` from env var (default `us-west-2`), module-level tool instantiation, `TOOLS` list, updated system prompt describing both tools, `tools=TOOLS` in Agent constructor.

3. **Verified imports** — All module-level exports confirmed: TOOLS count 2, correct types, Browser and Code Interpreter in system prompt, region defaults to us-west-2.

4. **Wrote tests** — 9 tests in `calleditv4/tests/test_builtin_tools.py`: 8 pure-logic unit tests (tool list, callability, prompt content, region, types, regression) + 1 Hypothesis property test (error handling with user-approved mock — Decision 96 exception).

5. **Ran tests** — 15 passed (9 new + 6 from V4-1) in 1.64s.

6-8. **Manual validation** — All three test cases passed:
   - Browser: 22 tool calls, navigated multiple weather sites (hit CAPTCHAs on Google, eventually got Seattle weather from OpenWeatherMap — 11°C, overcast, 61% humidity). 321 seconds total.
   - Code Interpreter: Calculated compound interest correctly ($16,288.95 on $10K at 5% for 10 years). Fast response.
   - Error case: Missing prompt key returned `{"error": "Missing 'prompt' field in payload"}` as expected.

### Dependency Discovery: playwright + nest-asyncio ARE Required

Initially thought `playwright` and `nest-asyncio` were optional (only needed for the alternative Playwright integration path). Wrong — `strands_tools.browser.browser` imports both at module level:
- Line 17: `import nest_asyncio`
- Line 18: `from playwright.async_api import Browser as PlaywrightBrowser`

The imports worked in our project venv (which had them from other dependencies) but `agentcore dev` uses the project's `.venv/` which didn't have them. Added both to `calleditv4/pyproject.toml`. Decision 97 documents this.

### Zombie Process Observation

When the first browser invocation timed out (180s client timeout, but the AWS browser session kept running), killing and restarting the dev server caused the new server to pick up the still-running browser session and complete the original request. This is because the browser session runs in AWS (Firecracker microVM), not locally — killing the local dev server doesn't kill the AWS session. The session eventually completed on the new server instance. Not a bug, just an artifact of the AWS-hosted tool architecture.

### AgentCore Deviation Flag: None

No deviations from AgentCore recommended patterns. Using built-in tools exactly as documented — `AgentCoreBrowser` and `AgentCoreCodeInterpreter` from `strands_tools`, wired via the `tools` parameter.

## Decisions Made

- Decision 97: playwright and nest-asyncio are required dependencies of strands_tools.browser, not optional. Added to calleditv4/pyproject.toml. The AgentCoreBrowser Strands tool wrapper uses Playwright internally to communicate with the AWS-hosted Chromium session.

## Files Created/Modified

### Created
- `.kiro/specs/builtin-tools/requirements.md` — V4-2 requirements (3 requirements)
- `.kiro/specs/builtin-tools/design.md` — V4-2 design (architecture, entrypoint code, 2 correctness properties)
- `.kiro/specs/builtin-tools/tasks.md` — V4-2 tasks (8 tasks)
- `calleditv4/tests/test_builtin_tools.py` — 9 tests (8 unit + 1 property)
- `docs/project-updates/23-project-update-v4-2-builtin-tools.md` — This file

### Modified
- `calleditv4/src/main.py` — Added tool imports, instantiation, TOOLS list, updated system prompt
- `calleditv4/pyproject.toml` — Added nest-asyncio and playwright dependencies
- `docs/project-updates/decision-log.md` — Added Decision 97
- `docs/project-updates/project-summary.md` — Added Update 23 entry
- `docs/project-updates/backlog.md` — Updated item 13 status
- `docs/project-updates/common-commands.md` — Updated v4 commands

## What the Next Agent Should Do

### Immediate
1. Begin V4-3a spec (Creation Agent Core) — next on the critical path
2. V4-3a wires Prompt Management, implements the 4-turn creation flow, saves prediction bundle to DDB

### Key Files
- `calleditv4/src/main.py` — Working entrypoint with Browser + Code Interpreter
- `.kiro/specs/builtin-tools/` — Complete spec
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference (updated)

### Important Notes
- Browser tool is slow for web search (~5 min with CAPTCHA retries) — this validates Decision 93's note that Gateway with Brave Search should be added when browser becomes a bottleneck
- Code Interpreter is fast and accurate — good for numerical verification
- `agentcore dev` uses the project's `.venv/`, not the project-level venv — dependencies must be in `pyproject.toml`
- Browser sessions run in AWS even during local dev — killing the dev server doesn't kill the browser session
- The first approved mock in v4 is documented in `test_builtin_tools.py` (error handling property test)
