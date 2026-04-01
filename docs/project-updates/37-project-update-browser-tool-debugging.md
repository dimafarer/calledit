# Project Update 37 — Browser Tool Debugging & Tool Configurability

**Date:** March 31, 2026
**Context:** Investigating the AgentCore Browser tool failure in the deployed runtime (backlog item 17). Building a PoC agent for diagnosis, making verification tools configurable, and planning full eval validation with Browser.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** `feat: Browser tool fix + configurable verification tools + eval baseline`

### Referenced Kiro Specs
- `.kiro/specs/browser-tool-fix/` — Browser Tool Fix spec (COMPLETE, tasks 1-10 done, optional property tests pending)

### Prerequisite Reading
- `docs/project-updates/36-project-update-dynamic-golden-dataset-execution.md` — Previous session context
- `docs/project-updates/backlog.md` — Item 17 (Browser debug) has full investigation history
- `docs/project-updates/decision-log.md` — Decision 144 (Browser IAM), Decision 145 (Brave Search workaround)

---

## What Happened

### The Problem
The AgentCore Browser tool has been broken in the deployed runtime since Update 34. It works perfectly when called directly from the local machine via the Kiro AgentCore MCP power — we successfully navigated to `fiscaldata.treasury.gov` and got full page content. But inside the deployed AgentCore Runtime container, the Strands `AgentCoreBrowser` wrapper fails silently with "unavailable due to access restrictions." Code Interpreter works fine in the same container, same role, same everything.

We'd added full Browser IAM permissions (Decision 144), added explicit `region="us-west-2"` to the constructor, relaunched — nothing changed. The error message was suspiciously vague, and no detailed error appeared in CloudWatch or OTEL logs.

### The Research Breakthrough
Before jumping into code, we activated both Kiro powers (Strands + AgentCore) and dug into the actual Browser tool architecture. This was the key insight:

**The Browser tool has a two-layer architecture that Code Interpreter doesn't have.**

- **Layer 1 (API)**: `BrowserClient` uses boto3 to call `bedrock-agentcore` data plane APIs (`start_browser_session`, etc.). This is the same pattern as Code Interpreter — standard boto3 calls with SigV4 signing.
- **Layer 2 (WebSocket + Playwright)**: After starting a session, `AgentCoreBrowser` calls `generate_ws_headers()` which creates a SigV4-signed WebSocket URL (`wss://{host}/browser-streams/{identifier}/sessions/{session_id}/automation`), then connects via **Playwright's Chrome DevTools Protocol (CDP)**.

Code Interpreter only uses Layer 1. Browser needs both layers. That's why Code Interpreter works and Browser doesn't — the failure is almost certainly in Layer 2 (WebSocket connection, Playwright availability, or network restrictions in the container).

This came from reading the actual `BrowserClient` source code via the AgentCore docs power and the `strands_tools.browser` module documentation. The `generate_ws_headers()` method uses `SigV4Auth` from `botocore.auth` to sign the WebSocket request, and Playwright connects via `chromium.connect_over_cdp(ws_url, headers=headers)`. None of this is needed for Code Interpreter.

### The PoC — Layer-by-Layer Diagnosis
Built `browser-poc/` — a minimal AgentCore agent that tests each Browser layer independently with full logging. No LLM, no Brave, no DDB. Just Browser.

**Local test (`agentcore dev`):** All 8 steps passed. Credentials from `shared-credentials-file`, navigated to Wikipedia, got "Wikipedia, the free encyclopedia." Strands wrapper initialized fine.

**Deployed test (`agentcore launch`):** Failed at Layer 1 — `StartBrowserSession` API call. Not Layer 2 like we hypothesized.

### The Root Cause (Decision 149)
The error was crystal clear once we had the PoC's diagnostic output:

```
AccessDeniedException: User is not authorized to perform: 
bedrock-agentcore:StartBrowserSession on resource: 
arn:aws:bedrock-agentcore:us-west-2:aws:browser/aws.browser.v1
```

The IAM policy from Decision 144 had the resource scoped to `arn:aws:bedrock-agentcore:us-west-2:894249332178:browser/*` (account-scoped). But the system browser `aws.browser.v1` is an **AWS-owned resource** with `aws` as the account portion: `arn:aws:bedrock-agentcore:us-west-2:aws:browser/aws.browser.v1`.

**Fix:** Added a second IAM statement covering `arn:aws:bedrock-agentcore:REGION:aws:browser/*` to `setup_agentcore_permissions.sh`. Applied the fix, relaunched the PoC, and it passed all 8 steps in the deployed runtime — including navigating to Wikipedia and returning the page title.

**Why this was missed originally:** The AgentCore Browser quickstart docs show `arn:aws:bedrock-agentcore:<region>:<account_id>:browser/*` which works for custom browsers but not for the system browser. Code Interpreter doesn't have this issue because its system resource permissions are included in the auto-created execution role. Our Layer 2 hypothesis was wrong — the PoC's layer-by-layer approach caught the real issue immediately at Layer 1.

### The Spec
Rather than diving straight into debugging, we built a proper spec. The user initially leaned toward skipping the spec for this exploratory work, but the scope grew: fix Browser, make tools configurable (Browser vs Brave vs both), synchronize tool awareness between both agents, and validate with eval runs. That's feature territory.

**8 requirements → 9 requirements** — the user caught a critical gap during requirements review. The creation agent (prediction agent) needs the exact same tool awareness as the verification agent. It doesn't *use* Browser to browse — but it needs to *know* what tools the verification agent has so the planner writes accurate verification plans and the reviewer scores verifiability correctly. If the verification agent has Browser but the creation agent's tool manifest says "Brave Search," the plans reference the wrong tool and verifiability scores are based on wrong assumptions.

We confirmed this by reading the creation agent code:
- `TOOLS = [browser_tool.browser, code_interpreter_tool.code_interpreter, current_time]` — passed to the Strands Agent so the LLM sees tool schemas
- `_get_tool_manifest()` — human-readable tool description injected into the `verification_planner` prompt via `{{tool_manifest}}`
- Both are currently hardcoded. Both need to be driven by the same `VERIFICATION_TOOLS` env var.

### The Design
The design introduces three shared functions driven by `VERIFICATION_TOOLS` env var:
- `build_tools(env_value)` → returns the Strands tool callable list (used by both agents)
- `build_tool_manifest(env_value)` → returns the human-readable manifest for the planner prompt (creation agent only)
- `build_simple_prompt_system(env_value)` → returns the backward-compat system prompt (creation agent only)

Three correctness properties:
1. AWS env var filtering masks secrets (for the PoC diagnostic logging)
2. Tool configuration correctness (for any VERIFICATION_TOOLS value, correct tools are returned)
3. Creation agent tool set equivalence (manifest and TOOLS list always match verification agent's tools)

### The Plan (12 Tasks)
1. Build Browser PoC agent with layer-by-layer diagnostics
2. Test locally vs deployed (user runs `agentcore dev`/`agentcore launch`)
3. Checkpoint — diagnosis complete
4. Apply root cause fix (exploratory — depends on what PoC reveals)
5. Checkpoint — fix verified
6. Build shared tool configuration (both agents)
7. Checkpoint — tests pass
8. Relaunch both agents with `VERIFICATION_TOOLS=browser`
9. Smoke test (base-013 Wikipedia refs, dyn-rec-003 Wikipedia accessibility)
10. Full eval suite (static + dynamic, all qualifying cases)
11. Documentation (decisions, project update, backlog)
12. Final checkpoint

## Files Created/Modified

### Created
- `.kiro/specs/browser-tool-fix/requirements.md` — 9 requirements, 42 acceptance criteria
- `.kiro/specs/browser-tool-fix/design.md` — Architecture, 3 correctness properties, testing strategy
- `.kiro/specs/browser-tool-fix/tasks.md` — 12 top-level tasks, ~25 sub-tasks
- `browser-poc/` — Minimal Browser PoC agent (entrypoint, pyproject.toml, .bedrock_agentcore.yaml)
- `browser-poc/tests/test_env_filter.py` — 4 property tests + 8 unit tests for env var filtering
- `docs/eval-framework-deep-dive.md` — Eval framework deep dive (new, standalone reference)
- `docs/project-updates/next-agent-11-prompt-dual-model-reflection.md` — Next session prompt
- `docs/project-updates/37-project-update-browser-tool-debugging.md` — This update

### Modified
- `infrastructure/agentcore-permissions/setup_agentcore_permissions.sh` — Added AWS-owned system browser resource ARN (Decision 149) + creation agent browser permissions
- `calleditv4-verification/src/main.py` — Replaced hardcoded TOOLS with `build_tools(VERIFICATION_TOOLS)` (Decision 150)
- `calleditv4/src/main.py` — Replaced hardcoded TOOLS, `_get_tool_manifest()`, `SIMPLE_PROMPT_SYSTEM` with dynamic `build_tools()`, `build_tool_manifest()`, `build_simple_prompt_system()` (Decision 150)
- `calleditv4/tests/test_builtin_tools.py` — Updated for dynamic tool configuration
- `calleditv4/tests/test_entrypoint.py` — Updated TOOLS length assertion for dynamic config
- `eval/golden_dataset.json` — base-013 `expected_verification_outcome` set to null (time-varying Wikipedia reference count)
- `docs/project-updates/decision-log.md` — Added Decisions 149, 150
- `docs/project-updates/project-summary.md` — Updated current state
- `docs/project-updates/backlog.md` — Item 17 status → IN PROGRESS; added item 20 (Multi-Model Reflection Architecture)

### Eval Results — Browser Baseline (22 cases, March 31, 2026)

| Metric | Previous (Brave, 23 cases) | Browser (22 cases) | Delta |
|--------|---------------------------|---------------------|-------|
| Creation T1 | 1.00 | 1.00 | — |
| Creation IP | 0.89 | 0.87 | -0.02 |
| Creation PQ | 0.88 | 0.81 | -0.07 |
| Verification T1 | 1.00 | 1.00 | — |
| Verification VA | 0.89 | 0.94 | +0.05 |
| Verification EQ | 0.59 | 0.73 | +0.14 |
| Calibration CA | ~0.91 | 0.95 | +0.04 |
| Duration | 2772s (~46 min) | 4521s (~75 min) | +63% |

Key observations:
- Verification improved across the board — Browser gives the agent better evidence than Brave alone
- VA jumped from 0.89 to 0.94, evidence quality from 0.59 to 0.73
- Calibration improved to 0.95 (from ~0.91)
- Creation PQ dropped 0.07 — likely because the tool manifest now says "Browser" instead of "Brave Search" and the planner writes plans differently
- Duration increased significantly (75 min vs 46 min) — Browser sessions are slower than Brave API calls
- 2 verification errors (dyn-atd-003, dyn-bfd-001) — agent invocation failures, not tool failures
- 1 inconclusive (dyn-rec-002) — agent couldn't resolve
- dyn-rec-003 (Wikipedia, previously broken) now works: confirmed with 0.95 confidence

## What the Next Agent Should Do

### Execute the remaining spec tasks
The Browser fix is validated. Remaining work: optional property tests (tasks 6.2, 6.3, 6.5, 6.6), and investigating the PQ regression.

### Investigate PQ regression
Plan quality dropped from 0.88 to 0.81 after switching from Brave to Browser. The creation agent's tool manifest now says "Browser" instead of "Brave Search" — the planner may be writing plans that reference Browser capabilities differently. Check if the plan-reviewer prompt needs updating to account for Browser's capabilities vs Brave's.

### Next major feature: Multi-Model Reflection Architecture (Backlog Item 20)
Fast draft with Haiku parsing + Sonnet plan/review, then optional deep reflection pass with reflection-specific prompts. Quality-gated clarification questions. See backlog item 20 for full design.

### Key gotchas
- `agentcore launch` and `agentcore invoke` require TTY — ask user to run and paste output
- All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`
- Both agents need `VERIFICATION_TOOLS` env var at launch time
- `BRAVE_API_KEY` must be passed to verification agent if using `brave` or `both` mode
- base-013 excluded from qualifying set (Wikipedia reference count is time-varying)

### Read the prompt file
`docs/project-updates/next-agent-10-prompt-browser-tool-debugging.md` has the full session prompt with all context, key values, and import gotchas.
