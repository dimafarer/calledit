# Implementation Plan: Creation Agent Core (V4-3a)

## Overview

Implement the 3-turn creation flow that transforms raw prediction text into a structured prediction bundle. Builds on V4-1 (AgentCore Foundation) and V4-2 (Built-in Tools). Delivers: Pydantic models, bundle construction, prompt client, 3 CloudFormation creation prompts, updated entrypoint with creation flow + backward-compatible simple prompt mode, and DynamoDB save. All Python commands use `/home/wsluser/projects/calledit/venv/bin/python`. Decision 96: NO MOCKS. Decision 95: v3 Lambda backend untouched.

## Tasks

- [x] 1. Create Pydantic models (`calleditv4/src/models.py`)
  - [x] 1.1 Create `calleditv4/src/models.py` with `ParsedClaim`, `VerificationPlan`, `ReviewableSection`, and `PlanReview` models
    - `ParsedClaim`: `statement` (str), `verification_date` (str), `date_reasoning` (str) — all with `Field(description=...)`
    - `VerificationPlan`: `sources` (list[str]), `criteria` (list[str]), `steps` (list[str]) — all with `Field(description=...)`
    - `ReviewableSection`: `section` (str), `improvable` (bool), `questions` (list[str]), `reasoning` (str) — all with `Field(description=...)`
    - `PlanReview`: `verifiability_score` (float, ge=0.0, le=1.0), `verifiability_reasoning` (str), `reviewable_sections` (list[ReviewableSection]) — all with `Field(description=...)`
    - Pydantic `Field(description=...)` on every field enables Strands structured output extraction
    - Add `pydantic` to `calleditv4/pyproject.toml` dependencies if not already present
    - _Requirements: 5.2, 5.3, 5.4, 5.10_

  - [x]* 1.2 Write unit tests for Pydantic model structure (`calleditv4/tests/test_models.py`)
    - Test `ParsedClaim` has fields: statement, verification_date, date_reasoning
    - Test `VerificationPlan` has fields: sources, criteria, steps (all `list[str]`)
    - Test `PlanReview` has fields: verifiability_score, verifiability_reasoning, reviewable_sections
    - Test `ReviewableSection` has fields: section, improvable, questions, reasoning
    - Test all Pydantic model fields have `Field(description=...)` (Req 5.10)
    - _Requirements: 5.2, 5.3, 5.4, 5.10_

  - [x]* 1.3 Write property test for PlanReview score validation (Property 8)
    - **Property 8: PlanReview score validation**
    - **Validates: Requirements 5.4**
    - For any float outside [0.0, 1.0], constructing `PlanReview` should raise `ValidationError`
    - For any float within [0.0, 1.0], construction should succeed
    - Use `st.floats()` partitioned by range, `@settings(max_examples=100)`

- [x] 2. Create bundle construction module (`calleditv4/src/bundle.py`)
  - [x] 2.1 Create `calleditv4/src/bundle.py` with `generate_prediction_id()`, `build_bundle()`, `serialize_bundle()`, `deserialize_bundle()`, `format_ddb_item()`, and `_convert_floats_to_decimal()`
    - `generate_prediction_id()` returns `pred-{uuid4}` string
    - `build_bundle()` assembles all 3-turn outputs + metadata, sets `status="pending"`, `clarification_rounds=0`, `created_at` as ISO 8601 UTC
    - `serialize_bundle()` converts bundle dict to JSON string via `json.dumps(bundle, default=str)`
    - `deserialize_bundle()` parses JSON string back to dict via `json.loads()`
    - `_convert_floats_to_decimal()` recursively converts floats to `Decimal(str(value))` for DynamoDB
    - `format_ddb_item()` adds `PK=PRED#{prediction_id}` and `SK=BUNDLE`, applies float→Decimal conversion
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.5, 5.6, 5.8, 5.9_

  - [x]* 2.2 Write property test for prediction ID format (Property 7)
    - **Property 7: Prediction ID format**
    - **Validates: Requirements 5.1**
    - For any call to `generate_prediction_id()`, result matches `pred-{uuid4}` pattern (36-char UUID with correct hyphen positions)
    - `@settings(max_examples=100)`

  - [x]* 2.3 Write property test for bundle assembly invariants (Property 3)
    - **Property 3: Bundle assembly invariants**
    - **Validates: Requirements 3.5, 5.5, 5.6**
    - For any valid inputs, `build_bundle()` returns dict with all required fields, `status="pending"`, `clarification_rounds=0`, `created_at` is valid ISO 8601 UTC
    - Use `st.text()` for strings, `st.floats(0, 1)` for score, `st.dictionaries()` for nested dicts

  - [x]* 2.4 Write property test for bundle serialization round-trip (Property 4)
    - **Property 4: Bundle serialization round-trip**
    - **Validates: Requirements 5.8, 4.6**
    - For any valid bundle dict, `serialize_bundle()` then `deserialize_bundle()` produces equivalent dict

  - [x]* 2.5 Write property test for DDB item format (Property 5)
    - **Property 5: DDB item format**
    - **Validates: Requirements 4.1, 4.2**
    - For any valid bundle, `format_ddb_item()` produces dict with `PK=PRED#{prediction_id}`, `SK=BUNDLE`, plus all original fields

  - [x]* 2.6 Write property test for float-to-Decimal conversion (Property 6)
    - **Property 6: Float-to-Decimal conversion preserves value**
    - **Validates: Requirements 4.3**
    - For any float (no NaN/Inf), `_convert_floats_to_decimal()` produces `Decimal` that round-trips to the original float
    - For nested dict/list structures, all floats become Decimals, non-floats unchanged
    - Use `st.floats(allow_nan=False, allow_infinity=False)`, `st.recursive()` for nested structures

- [x] 3. Checkpoint — Models and bundle tests pass
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_models.py calleditv4/tests/test_bundle.py -v`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create prompt client (`calleditv4/src/prompt_client.py`)
  - [x] 4.1 Create `calleditv4/src/prompt_client.py` with `fetch_prompt()`, `get_prompt_version_manifest()`, `reset_manifest()`, and Decision 98 fallback behavior
    - `fetch_prompt(prompt_name, version, variables)` fetches from Bedrock Prompt Management via `bedrock-agent` client `get_prompt()` API
    - Extracts text from `variants[0].templateConfiguration.text.text`
    - Version resolution: env var `PROMPT_VERSION_{NAME}` → defaults to `DRAFT`
    - Variable substitution: replaces `{{variable_name}}` placeholders
    - `_prompt_version_manifest` dict tracks actual versions returned
    - Decision 98: `CALLEDIT_ENV != "production"` → raise on failure; `"production"` → fallback to hardcoded defaults, log warning, record `"fallback"` in manifest
    - `PROMPT_IDENTIFIERS` dict with empty strings — populated after CloudFormation deploy
    - `_FALLBACK_PROMPTS` dict with minimal hardcoded defaults for each prompt
    - No imports from v3 agent modules, no v3 prompt identifiers
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x]* 4.2 Write property test for variable substitution (Property 1)
    - **Property 1: Variable substitution replaces all placeholders**
    - **Validates: Requirements 1.3**
    - For any prompt text with `{{name}}` placeholders and matching variable dict, resolved text contains no original placeholders and contains all substituted values
    - Use `st.dictionaries(st.text(), st.text())` for variables

  - [x]* 4.3 Write property test for Decision 98 fallback behavior (Property 2)
    - **Property 2: Decision 98 fallback behavior**
    - **Validates: Requirements 1.5, 1.6**
    - For any known prompt name and any exception: non-production raises, production returns non-empty fallback and records `"fallback"` in manifest
    - Use `st.sampled_from(["prediction_parser", "verification_planner", "plan_reviewer"])`

  - [x]* 4.4 Write unit tests for prompt client (`calleditv4/tests/test_prompt_client.py`)
    - Test `prompt_client.py` does not import from v3 agent modules (Req 1.8)
    - Test version resolution defaults to `DRAFT` when env var not set (Req 1.2)
    - Test version manifest records prompt versions after fetch (Req 1.4)
    - Test unknown prompt name raises `ValueError` in non-production mode
    - _Requirements: 1.2, 1.4, 1.8_

- [x] 5. Checkpoint — Prompt client tests pass
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_prompt_client.py -v`
  - Also re-run model and bundle tests to verify no regressions: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/test_models.py calleditv4/tests/test_bundle.py -v`
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Add CloudFormation creation prompts
  - [x] 6.1 Add 3 new prompt resources to `infrastructure/prompt-management/template.yaml`
    - `PredictionParserPrompt` (`calledit-prediction-parser`): Turn 1 parse instructions with `{{current_date}}` variable, timezone handling, time resolution rules. Tags: `Project: calledit`, `Agent: creation`
    - `VerificationPlannerPrompt` (`calledit-verification-planner`): Turn 2 plan instructions with `{{tool_manifest}}` variable, specificity matching rules. Tags: `Project: calledit`, `Agent: creation`
    - `PlanReviewerPrompt` (`calledit-plan-reviewer`): Turn 3 combined review + scoring instructions, 5 scoring dimensions with weights, assumption identification, timezone clarification. Tags: `Project: calledit`, `Agent: creation`
    - Each prompt gets a corresponding `AWS::Bedrock::PromptVersion` resource (v1)
    - Add 6 new Outputs (Id + Arn for each prompt)
    - Existing v3 prompts (ParserPrompt, CategorizerPrompt, VBPrompt, ReviewPrompt) remain unchanged
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x]* 6.2 Write CloudFormation template validation tests (`calleditv4/tests/test_cfn_prompts.py`)
    - Test template has `calledit-prediction-parser` resource with `{{current_date}}` variable
    - Test template has `calledit-verification-planner` resource with `{{tool_manifest}}` variable
    - Test template has `calledit-plan-reviewer` resource
    - Test each new prompt has a PromptVersion resource (Req 2.4)
    - Test each new prompt has `Project: calledit` and `Agent: creation` tags (Req 2.5)
    - Test template outputs include new prompt IDs and ARNs (Req 2.6)
    - Test existing v3 prompts still present and unchanged (Req 2.7)
    - Parse the YAML template file directly — no AWS calls needed
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 7. Deploy CloudFormation prompts
  - User runs: `cd /home/wsluser/projects/calledit/infrastructure/prompt-management && aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
  - After deploy, retrieve the 3 new Prompt IDs from stack outputs: `aws cloudformation describe-stacks --stack-name calledit-prompts --query "Stacks[0].Outputs"`
  - Update `PROMPT_IDENTIFIERS` dict in `calleditv4/src/prompt_client.py` with the actual 10-character Prompt IDs
  - This is a manual task — requires AWS CLI access
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update entrypoint with creation flow (`calleditv4/src/main.py`)
  - [x] 8.1 Update `calleditv4/src/main.py` with creation flow routing and 3-turn orchestration
    - Add imports: `RequestContext` from `bedrock_agentcore.context`, `boto3`, Pydantic models, prompt client functions, bundle functions, `current_time` from `strands_tools`
    - Add `DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-db")`
    - Add `current_time` to `TOOLS` list (3 tools total: browser, code_interpreter, current_time)
    - Add `_get_tool_manifest()` helper returning tool descriptions string
    - Add `_run_creation_flow(prediction_text, user_id)` function implementing the 3-turn flow:
      - Generate `prediction_id` via `generate_prediction_id()`
      - Turn 1: `fetch_prompt("prediction_parser", variables={"current_date": ...})` → `agent(prompt, structured_output_model=ParsedClaim)`
      - Turn 2: `fetch_prompt("verification_planner", variables={"tool_manifest": ...})` → `agent(prompt, structured_output_model=VerificationPlan)`
      - Turn 3: `fetch_prompt("plan_reviewer")` → `agent(prompt, structured_output_model=PlanReview)`
      - `build_bundle()` with all outputs → `format_ddb_item()` → DynamoDB `put_item()`
      - DDB save failure adds `save_error` field but still returns bundle
    - Update `handler()` signature: `context: RequestContext` instead of `context: dict`
    - Update routing: `prediction_text` → creation flow, `prompt` → simple mode, neither → error
    - Rename `SYSTEM_PROMPT` to `SIMPLE_PROMPT_SYSTEM` (only used for simple prompt mode)
    - No system prompt on creation agent — per-turn prompts from Prompt Management have full control
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x]* 8.2 Update entrypoint tests (`calleditv4/tests/test_entrypoint.py`)
    - Update existing tests to account for new routing (prediction_text vs prompt vs neither)
    - Test `DYNAMODB_TABLE_NAME` defaults to `calledit-db` (Req 4.4)
    - Test entrypoint uses `BedrockAgentCoreApp` + `@app.entrypoint` + `app.run()` (Req 6.4)
    - Test handler accepts `context: RequestContext` type annotation (Req 6.6)
    - Test `TOOLS` list now has 3 elements (browser, code_interpreter, current_time)
    - _Requirements: 4.4, 6.3, 6.4, 6.6_

  - [x]* 8.3 Write property test for missing payload fields (Property 9)
    - **Property 9: Missing payload fields produce structured error**
    - **Validates: Requirements 6.3, 3.6**
    - For any payload dict without `prediction_text` or `prompt` keys, handler returns JSON with `error` key
    - Use `st.dictionaries()` filtered to exclude target keys

  - [x]* 8.4 Write property test for user ID default (Property 10)
    - **Property 10: User ID defaults to anonymous**
    - **Validates: Requirements 3.7**
    - For any payload with `prediction_text` but no `user_id`, the default should be `"anonymous"`
    - For any payload with both `prediction_text` and `user_id`, the value should pass through
    - Note: This property tests the routing logic and default extraction, not the full creation flow (which requires Bedrock). Test the `user_id` extraction/default logic in isolation.

- [x] 9. Checkpoint — All automated tests pass
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v` from the project root
  - This runs all test files: test_models, test_bundle, test_prompt_client, test_cfn_prompts, test_entrypoint, test_builtin_tools
  - Verify no regressions in V4-1 and V4-2 tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Manual integration testing
  - User starts dev server: `cd /home/wsluser/projects/calledit/calleditv4 && agentcore dev`
  - In another terminal, run each test:
  - Creation flow — basic prediction: `agentcore invoke --dev '{"prediction_text": "Lakers win tonight", "user_id": "test-user"}'`
    - Expected: JSON bundle with parsed_claim, verification_plan, verifiability_score, reviewable_sections, status=pending
  - Creation flow — no user_id (defaults to anonymous): `agentcore invoke --dev '{"prediction_text": "It will rain tomorrow in Seattle"}'`
    - Expected: JSON bundle with `user_id: "anonymous"`
  - Backward compatibility — simple prompt mode: `agentcore invoke --dev '{"prompt": "What is 2 + 2?"}'`
    - Expected: Agent response string (not a bundle)
  - Missing fields error: `agentcore invoke --dev '{"foo": "bar"}'`
    - Expected: Error JSON about missing prediction_text or prompt
  - DDB save verification: After a successful creation flow, check DynamoDB: `aws dynamodb get-item --table-name calledit-db --key '{"PK": {"S": "PRED#<prediction_id>"}, "SK": {"S": "BUNDLE"}}'`
  - This is a manual task — `agentcore dev` and `agentcore invoke --dev` require TTY
  - _Requirements: 3.1, 3.5, 3.7, 4.1, 6.1, 6.2, 6.3_

- [x] 11. Final checkpoint — All tests pass, integration verified
  - Run `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4/tests/ -v`
  - Confirm manual integration tests from task 10 passed
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Decision 96: NO MOCKS. All tests exercise pure logic or real behavior. The only approved mock in v4 is in `test_builtin_tools.py` (V4-2, already approved).
- Decision 98: Non-production raises on Prompt Management failure; production falls back to hardcoded defaults.
- Decision 99: 3 turns not 4 — score and review merged into plan-reviewer turn.
- Decision 100: LLM-native date resolution — model uses `current_time` tool + Code Interpreter + timezone-aware prompts instead of custom `parse_relative_date`.
- `PROMPT_IDENTIFIERS` in prompt_client.py start empty — populated after CloudFormation deploy in task 7.
- Task ordering: models (no deps) → bundle (depends on models) → prompt client (independent) → CloudFormation (independent, but IDs needed for prompt client) → entrypoint (depends on all).
- Tasks 7 and 10 are manual — require AWS CLI and `agentcore dev` TTY access.
- All pip/python commands use the venv at `/home/wsluser/projects/calledit/venv`.
- `calleditv4/.venv/` exists but is NOT used — `agentcore dev` uses it, so dependencies must also be in `pyproject.toml`.
- Property tests use Hypothesis with `@settings(max_examples=100)`.
- Each property test references its property number and the requirements it validates.
