# Implementation Plan: Verification Agent Core (V4-5a)

## Overview

Build the verification agent as a separate AgentCore project in `calleditv4-verification/`. Bottom-up: scaffold → models → bundle loader → prompt client → CFN prompt → entrypoint → tests → checkpoint. All tests exercise real code paths (Decision 96). Integration testing is manual via `agentcore invoke --dev`.

## Tasks

- [x] 1. Scaffold project and core configuration
  - [x] 1.1 Create `calleditv4-verification/` directory structure with `src/`, `tests/`, `pyproject.toml`, `.bedrock_agentcore.yaml`
    - `src/__init__.py`, `src/main.py`, `src/models.py`, `src/bundle_loader.py`, `src/prompt_client.py`
    - `tests/__init__.py`
    - `.bedrock_agentcore.yaml` with `default_agent: calleditv4_verification_Agent`, entrypoint pointing to `src/main.py`, source_path to `src`
    - `pyproject.toml` with dependencies: `strands-agents`, `strands-agents-tools`, `pydantic`, `boto3`, `bedrock-agentcore`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Implement Pydantic models
  - [x] 2.1 Create `src/models.py` with `EvidenceItem` and `VerificationResult` models
    - `EvidenceItem`: `source` (str), `finding` (str), `relevant_to_criteria` (str) — all with `Field(description=...)`
    - `VerificationResult`: `verdict` (str), `confidence` (float, ge=0.0, le=1.0), `evidence` (List[EvidenceItem]), `reasoning` (str) — all with `Field(description=...)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ]* 2.2 Write property test for VerificationResult model validation
    - **Property 4: VerificationResult Model Validation**
    - Test valid verdict+confidence combos succeed, invalid confidence (outside [0.0, 1.0]) raises ValidationError
    - Test all fields have `Field(description=...)` annotations
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [x] 3. Implement bundle loader
  - [x] 3.1 Create `src/bundle_loader.py` with `_convert_floats_to_decimal`, `load_bundle_from_ddb`, `update_bundle_with_verdict`
    - `_convert_floats_to_decimal`: duplicated from creation agent's `bundle.py` (Decision 106)
    - `load_bundle_from_ddb(table, prediction_id)`: get_item with `PK=PRED#{prediction_id}`, `SK=BUNDLE`, strip PK/SK, return dict or None
    - `update_bundle_with_verdict(table, prediction_id, result, prompt_versions)`: update_item with ConditionExpression `attribute_exists(PK) AND #s = :pending`, sets verdict/confidence/evidence/reasoning/verified_at/status/prompt_versions.verification. Returns True/False, catches ConditionalCheckFailedException
    - _Requirements: 2.1, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 3.2 Write property test for DDB key format
    - **Property 1: DDB Key Format**
    - For any prediction_id string, verify `PK=PRED#{prediction_id}` and `SK=BUNDLE` in both load and update functions
    - **Validates: Requirements 2.1, 2.4**
  - [ ]* 3.3 Write property test for float-to-Decimal conversion
    - **Property 2: Float-to-Decimal Round Trip**
    - For any nested structure with floats, verify all floats become Decimals with same numeric value, non-floats unchanged
    - **Validates: Requirements 2.5**
  - [ ]* 3.4 Write unit test for verdict-to-status mapping
    - **Property 5: Verdict-to-Status Mapping**
    - Test confirmed/refuted → "verified", inconclusive → "inconclusive"
    - **Validates: Requirements 5.1, 5.2**

- [x] 4. Implement prompt client
  - [x] 4.1 Create `src/prompt_client.py` duplicated from creation agent with verification-specific config
    - `PROMPT_IDENTIFIERS` with only `"verification_executor": "PLACEHOLDER"` (populated after CFN deploy)
    - No `_FALLBACK_PROMPTS` — verification agent has no fallbacks
    - Same `fetch_prompt()`, `_resolve_variables()`, `get_prompt_version_manifest()`, `reset_manifest()` functions
    - _Requirements: 3.2, 3.5_

- [x] 5. Add verification prompt to CloudFormation template
  - [x] 5.1 Add `VerificationExecutorPrompt` and `VerificationExecutorPromptVersion` resources to `infrastructure/prompt-management/template.yaml`
    - Prompt name: `calledit-verification-executor`
    - Temperature 0, MaxTokens 4000
    - Prompt text instructs agent to follow verification plan, gather evidence, produce structured verdict
    - Add Outputs for `VerificationExecutorPromptId` and `VerificationExecutorPromptArn`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 6. Implement entrypoint
  - [x] 6.1 Create `src/main.py` with `handler`, `_run_verification`, `_make_inconclusive`, `_build_user_message`, `_get_ddb_table`
    - `handler(payload, context)`: synchronous `def`, extracts prediction_id, loads bundle, validates status=="pending", calls `_run_verification`, updates DDB, returns JSON string
    - `_run_verification(prediction_id, bundle)`: fetches prompt, builds user message, creates Strands Agent with Browser+CodeInterpreter+current_time, invokes with `structured_output_model=VerificationResult`. Never raises — catches all exceptions → `_make_inconclusive()`
    - `_make_inconclusive(reasoning)`: returns `VerificationResult(verdict="inconclusive", confidence=0.0, evidence=[], reasoning=reasoning)`
    - `_build_user_message(bundle)`: constructs message from parsed_claim and verification_plan fields
    - Error zones: Zone 1 (payload validation) → error JSON, Zone 2 (DDB load) → error JSON, Zone 3 (agent execution) → inconclusive + DDB update attempt
    - _Requirements: 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4, 7.5_
  - [ ]* 6.2 Write unit tests for pure entrypoint functions
    - Test `_make_inconclusive` returns correct structure (verdict="inconclusive", confidence=0.0, empty evidence)
    - Test `_build_user_message` contains statement, verification_date, sources, criteria, steps from bundle
    - Test handler return value is valid JSON with required keys for error cases (missing prediction_id, etc.)
    - **Property 3: User Message Contains All Bundle Fields**
    - **Property 6: Handler Returns Valid JSON with Required Fields**
    - **Property 8: Exception Produces Inconclusive with Zero Confidence**
    - **Validates: Requirements 3.3, 7.1, 7.3, 7.4**

- [x] 7. Final checkpoint
  - Run all tests: `/home/wsluser/projects/calledit/venv/bin/python -m pytest calleditv4-verification/tests/ -v`
  - Deploy prompt: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
  - Update `PROMPT_IDENTIFIERS` in `src/prompt_client.py` with the deployed prompt ID from stack outputs
  - Manual integration test: `agentcore invoke --dev` with a test prediction_id
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Decision 96: NO MOCKS. All tests exercise real code paths. Pure function tests only for unit/property tests. Integration tests are manual via `agentcore invoke --dev`.
- Decision 106: ~20 lines of shared code (DDB key format, Decimal conversion) duplicated from creation agent
- Python venv: `/home/wsluser/projects/calledit/venv`
- Property tests use Hypothesis with `@settings(max_examples=100)`
- Prompt deploy: `aws cloudformation deploy --template-file template.yaml --stack-name calledit-prompts`
