# Project Update 27 — V4-5 Verification Agent Planning

**Date:** March 23, 2026
**Context:** Planning the verification agent — the second AgentCore runtime. Split into two specs after architecture review. Separate project directory per agent per AgentCore best practice.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-agent-core/` — Spec V4-5a (COMPLETE)
- `.kiro/specs/verification-triggers/` — Spec V4-5b (PENDING)

### Prerequisite Reading
- `docs/project-updates/26-project-update-v4-4-verifiability-scorer.md` — V4-4 (verifiability scorer)
- `docs/project-updates/v4-agentcore-architecture.md` — Architecture reference (two-agent design)

---

## What Happened This Session

### Architecture Review

Before speccing, did a thorough review using AgentCore power, Strands docs, the v3 verification system, and the current codebase. Key findings:

1. **AgentCore pattern: one entrypoint per BedrockAgentCoreApp** — The `@app.entrypoint` decorator registers exactly one handler. A second agent needs a second project with its own `BedrockAgentCoreApp`, `agentcore dev`, and `agentcore launch`.

2. **Separate project directory** — `calleditv4/` is the creation agent. The verification agent gets its own project: `calleditv4-verification/`. Same pattern: `src/main.py`, `src/models.py`, `pyproject.toml`, `.bedrock_agentcore.yaml`, `tests/`. Shared code (like DDB key format, bundle schema) can be imported across projects or duplicated minimally.

3. **v3 verification system reference** — The v3 `verification_executor_agent.py` used a Strands agent with MCP tools (brave_web_search, fetch) to verify predictions. It produced `confirmed`/`refuted`/`inconclusive` verdicts. V4-5a replaces this with AgentCore built-in tools (Browser + Code Interpreter) instead of MCP.

4. **EventBridge trigger is a separate concern** — The v3 `verification_triggers.py` used an EventBridge scanner Lambda that scanned DDB for due predictions. V4-5b replaces this with EventBridge → AgentCore Runtime API invocation (Deviation 2 in the steering doc).

### Spec Split Decision (Decision 104)

Split V4-5 into two specs:

- **V4-5a: Verification Agent Core** — The agent itself. Separate AgentCore project (`calleditv4-verification/`), entrypoint that loads a prediction bundle from DDB, uses Browser + Code Interpreter to gather evidence, produces a structured verdict, updates DDB with the result. Testable via `agentcore invoke --dev`.

- **V4-5b: Verification Triggers** — The scheduling layer. EventBridge rule that runs every 15 minutes, scans DDB for predictions where `verification_date <= now` and `status == "pending"`, invokes the verification agent via `AgentCoreRuntimeClient`. Requires the verification agent to be deployed first.

The split follows the same pattern as the v3 B1/B2 split (Decision 64) — agent logic first, triggers second.

### Project Structure Decision (Decision 105)

Each AgentCore agent gets its own project directory:

```
calleditv4/                    # Creation Agent (V4-1 through V4-4)
  src/main.py                  # @app.entrypoint for creation
  src/models.py
  src/bundle.py
  src/prompt_client.py
  tests/
  pyproject.toml
  .bedrock_agentcore.yaml

calleditv4-verification/       # Verification Agent (V4-5a)
  src/main.py                  # @app.entrypoint for verification
  src/models.py                # VerificationVerdict, EvidenceItem
  src/bundle_loader.py         # DDB load + update with verdict
  tests/
  pyproject.toml
  .bedrock_agentcore.yaml
```

This aligns with AgentCore's "one agent = one runtime" pattern (steering doc rule 1). Each project has its own `agentcore dev` server, its own `agentcore launch` deployment, its own scaling and observability.

### Shared Code Strategy

The two agents share:
- DDB key format (`PK=PRED#{id}`, `SK=BUNDLE`)
- Bundle schema (the prediction bundle dict structure)
- `_convert_floats_to_decimal()` utility
- Prompt Management client pattern

Options considered:
1. **Shared package** — Extract common code into a `calledit-common/` package. Clean but adds packaging complexity.
2. **Minimal duplication** — Copy the ~20 lines of shared code (DDB key format, Decimal conversion). Simple, no cross-project dependencies.
3. **Import from creation project** — `sys.path.insert` to import from `calleditv4/src/`. Fragile, couples the projects.

Decision: **Option 2 (minimal duplication)** for now. The shared code is tiny (~20 lines). If it grows, we'll extract a shared package. This keeps each agent project self-contained and independently deployable.

### What V4-5a Delivers

The verification agent:
1. Receives a payload with `prediction_id` (or the full bundle)
2. Loads the prediction bundle from DDB
3. Reads the verification plan (sources, criteria, steps)
4. Uses Browser to search for evidence (ESPN, NBA.com, etc.)
5. Uses Code Interpreter for calculations if needed
6. Produces a structured verdict: `confirmed`, `refuted`, or `inconclusive`
7. Updates the DDB bundle with the verdict, evidence, and timestamp
8. Returns the verdict as a stream event (or simple JSON for batch mode)

The verification prompt instructs the agent to:
- Follow the verification plan's steps
- Check the planned sources
- Evaluate against the planned criteria
- Produce a verdict with evidence and reasoning
- Handle cases where the event hasn't happened yet (inconclusive)

### What V4-5b Delivers (Future)

The trigger system:
1. EventBridge rule runs every 15 minutes
2. Scans DDB for `status == "pending"` and `verification_date <= now`
3. For each due prediction, invokes the verification agent via `AgentCoreRuntimeClient`
4. The verification agent runs independently and updates DDB

### Issues Flagged

1. **DDB GSI needed** — The verification scanner needs to efficiently query predictions by status + verification_date. Currently there's no GSI for this (backlog item 14). V4-5b will need this, but V4-5a doesn't (it receives the prediction_id directly).

2. **Bundle schema versioning** — V4-5a needs to handle bundles created by V4-3a (no V4-4 fields) and V4-4 (with score tier fields). The verification agent should gracefully handle missing optional fields.

3. **Verification prompt needs to be in Prompt Management** — A new `calledit-verification-executor` prompt resource in the CloudFormation template.

## Decisions Made

- **Decision 104:** Split V4-5 into V4-5a (Verification Agent Core) and V4-5b (Verification Triggers). Same pattern as v3 B1/B2 split. Agent logic first, triggers second.
- **Decision 105:** Separate project directory per AgentCore agent. `calleditv4/` for creation, `calleditv4-verification/` for verification. Each independently deployable with its own `agentcore dev` and `agentcore launch`.
- **Decision 106:** Minimal code duplication over shared packages for now. ~20 lines of shared code (DDB key format, Decimal conversion) copied to verification project. Extract shared package if duplication grows.

## Files Created

- `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — This file

## What the Next Agent Should Do

1. Create V4-5a spec (requirements → design → tasks) for the Verification Agent Core
2. Scaffold `calleditv4-verification/` project with `agentcore create`
3. After V4-5a is complete and tested, create V4-5b spec for triggers


## Execution Results

### V4-5a Implementation
All 7 tasks completed:
1. Scaffold: `calleditv4-verification/` with src/, tests/, pyproject.toml, .bedrock_agentcore.yaml
2. Models: `EvidenceItem` and `VerificationResult` Pydantic models
3. Bundle loader: `load_bundle_from_ddb()`, `update_bundle_with_verdict()`, `_convert_floats_to_decimal()`
4. Prompt client: Duplicated from creation agent, verification-specific config, no fallbacks
5. CFN prompt: `calledit-verification-executor` prompt + PromptVersion + Outputs
6. Entrypoint: sync `handler()`, `_run_verification()` (never raises), `_make_inconclusive()`, `_build_user_message()`
7. Tests: 22 pure function tests passing

### Test Results
- 22 verification agent tests passing
- 148 creation agent tests still passing (no regressions)
- 170 total tests across both projects

### Remaining
- Deploy verification prompt: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
- Update `PROMPT_IDENTIFIERS` in verification prompt_client.py with deployed prompt ID
- Integration test via `agentcore invoke --dev` in `calleditv4-verification/`
- V4-5b (Verification Triggers) — EventBridge scanner, DDB GSI

## Files Created/Modified

### Created
- `calleditv4-verification/` — Complete verification agent project
- `calleditv4-verification/.bedrock_agentcore.yaml`
- `calleditv4-verification/pyproject.toml`
- `calleditv4-verification/src/main.py` — Sync entrypoint with never-raise pattern
- `calleditv4-verification/src/models.py` — EvidenceItem, VerificationResult
- `calleditv4-verification/src/bundle_loader.py` — DDB load/update with ConditionExpression
- `calleditv4-verification/src/prompt_client.py` — No-fallback prompt client
- `calleditv4-verification/tests/test_verification.py` — 22 pure function tests
- `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — This file

### Modified
- `infrastructure/prompt-management/template.yaml` — VerificationExecutorPrompt + PromptVersion + Outputs
- `docs/project-updates/decision-log.md` — Decisions 104-106
- `docs/project-updates/project-summary.md` — Update 27 entry

## V4-5a Integration Test Results

### Prompt Deployment
- Deployed `calledit-verification-executor` prompt via CloudFormation
- Prompt ID: `ZQQNZIP6SK`
- Updated `PROMPT_IDENTIFIERS` in `calleditv4-verification/src/prompt_client.py`

### Test 1: Lakers Prediction (Browser-heavy)
- Prediction: "Lakers win tonight" (pred-3f52a1b2)
- Agent tried 6+ Browser tool calls to scrape NBA.com, ESPN, Lakers.com, CBS Sports, Yahoo Sports
- Browser returned large HTML pages that accumulated in conversation history
- Bedrock threw context window overflow error
- Agent recovered, produced inconclusive verdict with confidence 0.0
- DDB updated: status changed from `pending` to `inconclusive`, verdict/reasoning/verified_at written
- Total time: 408 seconds
- Finding: Browser tool is not suitable for sports score verification — returns too much HTML, overflows context. Confirms Phase 2 Gateway + Brave Search is needed.

### Test 2: "test" Prediction (Code Interpreter)
- Prediction: "test" (pred-80ac8e26)
- Agent used Code Interpreter and logical analysis (no Browser scraping)
- Correctly determined "test" is not a verifiable prediction
- Verdict: inconclusive, confidence: 0.95
- DDB updated: status changed from `pending` to `inconclusive`
- Total time: 30 seconds
- Clean end-to-end pipeline validation

### Pipeline Components Validated
- DDB load (get_item with PK/SK) ✅
- Prompt fetch from Bedrock Prompt Management ✅
- Strands Agent invocation with structured_output_model ✅
- VerificationResult Pydantic model extraction ✅
- DDB update with ConditionExpression ✅
- Status transition (pending → inconclusive) ✅
- JSON return with required fields ✅
- Never-raise error handling (context overflow caught) ✅

### Known Limitations
- Browser tool context overflow: scraping multiple sports sites fills the context window. The agent loses track of the original prediction data after too many Browser calls. This is the expected limitation documented in the architecture doc — Gateway + Brave Search (Phase 2) will address it.
- `agentcore invoke --dev` has a 180s read timeout. Browser-heavy verifications exceed this. The server continues processing, but the client disconnects. In production (V4-5b EventBridge trigger), this won't be an issue since the agent runs to completion independently.

## V4-5b Spec Created

Created the V4-5b (Verification Triggers) spec with fresh v4 content, replacing the old v3 Spec B2:
- `.kiro/specs/verification-triggers/requirements.md` — 5 requirements, 22 acceptance criteria
- `.kiro/specs/verification-triggers/design.md` — GSI design, scanner Lambda, dual invocation mode, 7 correctness properties
- `.kiro/specs/verification-triggers/tasks.md` — 8 top-level tasks

Key design decisions:
- Scanner at `infrastructure/verification-scanner/` (infrastructure, not an agent)
- GSI via CLI script (calledit-db not CloudFormation-managed)
- Dual invocation: AgentCoreRuntimeClient (prod) / HTTP POST (dev)
- Prerequisite: promote `verification_date` to top-level DDB attribute

## V4-5b Execution Results

### Implementation
All 6 required tasks completed (Tasks 1-6, 8). Optional test tasks (7.1-7.8) skipped for faster MVP.

1. Prerequisite: Promoted `verification_date` to top-level DDB attribute in `build_bundle()` and `format_ddb_update()`. Existing property test caught the new field — updated `REQUIRED_FIELDS` set.
2. GSI setup: Created `setup_gsi.sh`, ran it. GSI took ~7 minutes to become ACTIVE (normal for DynamoDB backfill). GSI shows 0 items because existing predictions don't have top-level `verification_date` — new predictions will be indexed.
3. Scanner Lambda: `extract_prediction_id()`, `query_due_predictions()` with pagination, `lambda_handler()` with fail-forward pattern.
4. Invocation clients: `HttpInvoker` (dev, HTTP POST to agentcore dev server) and `AgentCoreInvoker` (prod, AgentCoreRuntimeClient). Factory selects based on env vars.
5. SAM template: Python 3.12 zip Lambda, 900s timeout, EventBridge rate(15 minutes), DynamoDB + GSI query permissions, AgentCore invoke permissions.
6. Requirements.txt: boto3 only.

### Test Results
- 148 creation agent tests passing (no regressions from `verification_date` promotion)
- 22 verification agent tests passing
- 170 total tests across both projects

### DDB Table Stats
- 18 items, ~57KB total
- PAY_PER_REQUEST billing (essentially free at this scale)
- GSI `status-verification_date-index` ACTIVE, 0 items (sparse — existing items lack top-level `verification_date`)

### Files Created
- `infrastructure/verification-scanner/scanner.py` — Scanner Lambda handler
- `infrastructure/verification-scanner/setup_gsi.sh` — GSI creation script
- `infrastructure/verification-scanner/template.yaml` — SAM template
- `infrastructure/verification-scanner/requirements.txt` — boto3 dependency

### Files Modified
- `calleditv4/src/bundle.py` — `verification_date` promoted to top-level in `build_bundle()` and `format_ddb_update()`
- `calleditv4/tests/test_bundle.py` — Added `verification_date` to `REQUIRED_FIELDS`
- `calleditv4-verification/src/prompt_client.py` — Updated `PROMPT_IDENTIFIERS` with real prompt ID `ZQQNZIP6SK`
- `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — This file (integration + execution results)
- `docs/project-updates/project-summary.md` — Updated current state
- `docs/project-updates/common-commands.md` — Added verification agent commands
