# Project Update 24 — V4-3a Creation Agent Core Complete

**Date:** March 23, 2026
**Context:** Implemented the 3-turn creation flow (parse → plan → review) with Strands structured output, Bedrock Prompt Management, DynamoDB save. First v4 spec with real business logic.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/creation-agent-core/` — Spec V4-3a (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/23-project-update-v4-2-builtin-tools.md` — V4-2 (built-in tools)

---

## What Happened This Session

### Spec Creation with Strands/AgentCore Power Validation

Used the Strands and AgentCore Kiro powers to validate patterns against current docs before writing the spec. Key findings from the power validation:

- **Strands `structured_output_model` parameter** enables type-safe Pydantic extraction per `agent()` call. You pass a Pydantic BaseModel class and get back a validated object via `result.structured_output`. This eliminates the v3 regex JSON parsing problem entirely.
- **Conversation history accumulates naturally** across multiple `agent()` calls on the same Agent instance. Turn 2 sees Turn 1's context, Turn 3 sees both. No manual state threading needed.
- **Per-invocation `structured_output_model` overrides supported** — each `agent()` call can pass a different Pydantic model. The same agent instance handles ParsedClaim on Turn 1, VerificationPlan on Turn 2, and PlanReview on Turn 3.
- **`StructuredOutputException`** fires on validation failures with auto-retry. Strands handles the retry loop internally — the caller just catches the exception if all retries fail.

### 4 Turns Collapsed to 3 (Decision 99)

The original architecture doc (Decision 94) described 4 turns: Parse → Plan → Score → Review. After analysis during spec requirements review, scoring and reviewing were merged into a single `calledit-plan-reviewer` turn. The reasoning: scoring verifiability and identifying assumptions are two perspectives on the same analysis of the verification plan. The reviewer already needs to deeply understand the plan to generate targeted questions — scoring requires the same deep analysis. Two separate LLM calls doing overlapping analysis wastes tokens and latency. The merged `PlanReview` Pydantic model produces `verifiability_score`, `verifiability_reasoning`, and `reviewable_sections` in one call. This reduces latency by ~1 Bedrock call per prediction and simplifies the flow without losing output quality.

### Descriptive Prompt Names

Chose descriptive prompt names over generic ones: `calledit-prediction-parser`, `calledit-verification-planner`, `calledit-plan-reviewer` (not `calledit-creation-parse`, `calledit-creation-plan`, `calledit-creation-review`). The descriptive names communicate what each prompt does without needing to look at the prompt text. When you see `calledit-plan-reviewer` in a CloudFormation output or Prompt Management console, you know exactly what it does.

### LLM-Native Date Resolution (Decision 100)

Replaced v3's custom `parse_relative_date` tool (which used the `dateparser` library + `pytz` for deterministic date parsing) with LLM-native date reasoning. The creation agent gets three tools for date work:

1. **`current_time`** from `strands_tools` — returns current date/time with server timezone
2. **Code Interpreter** — for complex date math when needed
3. **Timezone-aware prompt instructions** — the parser prompt instructs the agent to:
   - Call `current_time` first for server timezone as default reference
   - Infer timezone from location context (e.g., "Lakers" → Pacific)
   - Always store `verification_date` in UTC
   - Record timezone assumptions in `date_reasoning`

The reviewer then flags timezone assumptions as high-priority clarification questions. This eliminates `dateparser` and `pytz` dependencies, makes timezone reasoning transparent (visible in `date_reasoning`), and leverages the model's strong date arithmetic capabilities. The tradeoff: occasional model errors on complex date math, mitigated by Code Interpreter availability and reviewer catch.

### Prompt Client Ported

Clean v3 port of `prompt_client.py` into `calleditv4/src/`. Key differences from v3:
- No lazy-loaded fallback imports from v3 agent modules
- No v3 prompt identifiers (parser/categorizer/vb/review)
- Decision 98 behavior: non-production raises exceptions (fail fast, fail visibly); production falls back to hardcoded defaults, logs a warning, records "fallback" in the version manifest
- `_resolve_variables()` uses `{{name}}` consistently (v3 mixed `{{name}}` and `{name}`)
- `_is_production()` checks `CALLEDIT_ENV` env var

### 3 CloudFormation Prompts Deployed

Three new prompt resources added to `infrastructure/prompt-management/template.yaml`, alongside the existing v3 prompts (which remain untouched per Decision 95):

| Prompt | Prompt ID | Description |
|--------|-----------|-------------|
| `calledit-prediction-parser` | GESWTI1IAB | Turn 1 — extract claim, resolve dates with timezone awareness |
| `calledit-verification-planner` | ZTCOSG04KQ | Turn 2 — build verification plan with tool references |
| `calledit-plan-reviewer` | 6OOF6PHFRF | Turn 3 — score verifiability + identify assumptions |

All v1 versions created via `AWS::Bedrock::PromptVersion` resources. Each prompt tagged with `Project: calledit` and `Agent: creation`. Stack outputs include Prompt ID and ARN for each.

### Pydantic Models

Four models in `calleditv4/src/models.py`, all with `Field(description=...)` for Strands structured output:

- **`ParsedClaim`** — Turn 1: `statement`, `verification_date` (ISO 8601), `date_reasoning`
- **`VerificationPlan`** — Turn 2: `sources` (list), `criteria` (list), `steps` (list)
- **`ReviewableSection`** — Nested: `section`, `improvable` (bool), `questions` (list), `reasoning`
- **`PlanReview`** — Turn 3: `verifiability_score` (float, 0.0-1.0 with Pydantic constraints), `verifiability_reasoning`, `reviewable_sections` (list of ReviewableSection)

Pydantic's `Field(ge=0.0, le=1.0)` handles score clamping automatically — no manual validation needed.

### Bundle Construction

Pure functions in `calleditv4/src/bundle.py`:
- `generate_prediction_id()` — `pred-{uuid4}` format
- `build_bundle()` — assembles all 3 turn outputs + metadata into a single dict
- `serialize_bundle()` / `deserialize_bundle()` — JSON round-trip
- `_convert_floats_to_decimal()` — recursive float→Decimal for DynamoDB (Decision 82)
- `format_ddb_item()` — adds `PK=PRED#{id}` and `SK=BUNDLE`

### Entrypoint Updated

`calleditv4/src/main.py` now supports two modes:
1. **Creation flow** — `prediction_text` in payload → 3-turn creation → bundle → DDB save → return JSON
2. **Simple prompt** — `prompt` in payload → V4-1/V4-2 agent response (backward compatibility)
3. **Neither** → structured error JSON

Key design choices:
- `context: RequestContext` from `bedrock_agentcore` (not `bedrock_agentcore.context`) — enables future `session_id` support for V4-3b
- Single agent instance across 3 turns — conversation history accumulates naturally
- No system prompt on creation agent — per-turn prompts from Prompt Management provide all instructions
- DDB save failure doesn't block return — bundle returned with `save_error` field
- `current_time` added as third tool (3 tools total: Browser, Code Interpreter, current_time)

### Import Discoveries

Two import paths that weren't obvious from the docs:

1. **`current_time`**: `from strands_tools.current_time import current_time` — you need to import the *function*, not the module. `from strands_tools import current_time` gives you the module object, which isn't callable as a tool.

2. **`RequestContext`**: `from bedrock_agentcore import RequestContext` — it's a top-level export, not in `bedrock_agentcore.context`. `RequestContext` is a Pydantic model with `session_id`, `request_headers`, and `request` fields.

### 133 Automated Tests Passing

| Test File | Count | Type |
|-----------|-------|------|
| `test_models.py` | 25 | Unit + property (Pydantic model validation) |
| `test_bundle.py` | 14 | All property-based (bundle construction, serialization, DDB formatting) |
| `test_prompt_client.py` | 18 | Unit + property (fetch, fallback, variable substitution) |
| `test_cfn_prompts.py` | 65 | CloudFormation template validation |
| `test_entrypoint.py` | 11 | Entrypoint routing, imports, constants |

All property-based tests use Hypothesis with `@settings(max_examples=100)`.

### Integration Tests — All 5 Passed

1. **Lakers prediction**: `"Lakers win tonight"` with `user_id: "test-user"` — score 0.82, correctly inferred Pacific timezone from "Lakers", reviewer flagged timezone clarification as high-priority question
2. **Seattle rain**: `"It will rain tomorrow in Seattle"` — `user_id` defaulted to `anonymous`, score 0.85, inferred Pacific from Seattle location context
3. **Simple prompt**: `"2 + 2 = 4"` — backward compatibility confirmed, returned agent response string (not bundle JSON)
4. **Missing fields**: `{"foo": "bar"}` — returned error JSON: `{"error": "Missing 'prediction_text' or 'prompt' field in payload"}`
5. **DDB save**: Both Lakers and Seattle bundles saved with correct `PK=PRED#{id}`, `SK=BUNDLE`, and Decimal scores (not floats)

### AWS Region Cleanup

Removed all hardcoded `us-west-2` defaults. Region comes from AWS CLI config via boto3's standard resolution chain (`~/.aws/config` → `AWS_REGION` env var → `AWS_DEFAULT_REGION` → instance metadata). The V4-2 entrypoint had `AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")` — this is gone. No hardcoded region anywhere in v4 code.

### V4-2 Test Regression Fixed

`test_builtin_tools.py` needed updates for V4-3a changes:
- Renamed constant: `SYSTEM_PROMPT` → `SIMPLE_PROMPT_SYSTEM`
- Removed `AWS_REGION` import (no longer exists)
- Updated `TOOLS` count: 2 → 3 (added `current_time`)
- Updated handler context type: `dict` → `RequestContext`

All 15 V4-2 tests still pass after the fixes.

### AgentCore Deviation Flag: None

All patterns align with the AgentCore steering doc. Using `BedrockAgentCoreApp` + `@app.entrypoint` + `app.run()`. No hardcoded prompts in agent code. No local MCP subprocesses. No custom OTEL. Agent created per-request. Fail clearly on dependency failure in non-production.

## Decisions Made

- **Decision 98:** No fallbacks in dev, graceful fallback in production (`CALLEDIT_ENV=production`)
- **Decision 99:** 3 turns not 4 — merged score + review into `calledit-plan-reviewer`
- **Decision 100:** LLM-native date resolution with timezone awareness (replaces v3's `dateparser` + `pytz`)

## Files Created/Modified

### Created
- `calleditv4/src/models.py` — Pydantic models (ParsedClaim, VerificationPlan, ReviewableSection, PlanReview)
- `calleditv4/src/bundle.py` — Bundle construction, serialization, DDB formatting
- `calleditv4/src/prompt_client.py` — Bedrock Prompt Management client with Decision 98 behavior
- `calleditv4/tests/test_models.py` — 25 model tests (unit + property)
- `calleditv4/tests/test_bundle.py` — 14 bundle tests (all property-based)
- `calleditv4/tests/test_prompt_client.py` — 18 prompt client tests (unit + property)
- `calleditv4/tests/test_cfn_prompts.py` — 65 CloudFormation template validation tests
- `.kiro/specs/creation-agent-core/` — Complete spec (requirements, design, tasks)
- `docs/project-updates/24-project-update-v4-3a-creation-agent-core.md` — This file

### Modified
- `calleditv4/src/main.py` — 3-turn creation flow + backward-compatible routing
- `infrastructure/prompt-management/template.yaml` — 3 new creation prompts + versions + outputs
- `calleditv4/tests/test_entrypoint.py` — Updated for RequestContext, new routing
- `calleditv4/tests/test_builtin_tools.py` — Updated for renamed constants, new TOOLS count
- `docs/project-updates/decision-log.md` — Decisions 98-100
- `docs/project-updates/project-summary.md` — Update 24 entry
- `docs/project-updates/backlog.md` — Updated item 13 status
- `docs/project-updates/common-commands.md` — New v4 creation flow commands

## What the Next Agent Should Do

### Immediate
1. **V4-3b (Clarification & Streaming)** or **V4-4 (Verifiability Scorer)** — both can proceed in parallel
2. V4-3b adds multi-round clarification using `RequestContext.session_id` and WebSocket streaming
3. V4-4 adds the verifiability score indicator UI (green/yellow/red)
4. Pin prompt versions (currently using DRAFT) after prompt iteration with eval framework

### Key Files
- `calleditv4/src/main.py` — Working entrypoint with 3-turn creation flow
- `calleditv4/src/prompt_client.py` — Prompt Management client
- `calleditv4/src/models.py` — Pydantic models for structured output
- `calleditv4/src/bundle.py` — Bundle construction
- `.kiro/specs/creation-agent-core/` — Complete spec

### Important Notes
- Prompts are using DRAFT versions — pin to v1 after prompt iteration
- `current_time` import: `from strands_tools.current_time import current_time` (function, not module)
- `RequestContext` import: `from bedrock_agentcore import RequestContext` (top-level, not `.context`)
- No hardcoded AWS region anywhere — boto3 resolves from CLI config
- The creation flow takes ~15-30s per prediction (3 Bedrock calls)
