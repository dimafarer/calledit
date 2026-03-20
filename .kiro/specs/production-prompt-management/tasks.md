# Implementation Plan: Production Prompt Management Wiring

## Overview

Wire the production MakeCallStreamFunction Lambda to use Bedrock Prompt Management by adding the missing IAM permission and environment variables to the SAM template, then updating the 4 hardcoded fallback constants to match the latest Prompt Management versions. No changes to `prompt_client.py` — it already has the fetch-and-fallback logic.

## Tasks

- [x] 1. Add IAM permission and environment variables to SAM template
  - [x] 1.1 Add `bedrock-agent:GetPrompt` IAM policy statement to MakeCallStreamFunction Policies
    - Add a new Statement block after the existing Bedrock InvokeModel statement
    - Effect: Allow, Action: `bedrock-agent:GetPrompt`, Resource: `'*'`
    - Must be a separate Statement because `bedrock-agent` is a different IAM service prefix than `bedrock`
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Add Environment variables block to MakeCallStreamFunction Properties
    - Add `Environment.Variables` with 4 version-pinned env vars:
      - `PROMPT_VERSION_PARSER: "1"`
      - `PROMPT_VERSION_CATEGORIZER: "2"`
      - `PROMPT_VERSION_VB: "2"`
      - `PROMPT_VERSION_REVIEW: "3"`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 1.3 Write unit tests for SAM template structure
    - Parse `template.yaml` as YAML and verify:
      - MakeCallStreamFunction Policies contains a statement with `bedrock-agent:GetPrompt` action
      - MakeCallStreamFunction Environment.Variables contains all 4 `PROMPT_VERSION_*` vars with correct values
    - Test file: `tests/strands_make_call/test_sam_template_prompt_management.py`
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Update fallback constants to match Prompt Management versions
  - [x] 2.1 Update `PARSER_SYSTEM_PROMPT` in `parser_agent.py` to match Prompt Management parser v1
    - Change JSON output instruction from "Do not wrap in markdown code blocks. Do not include any text before or after the JSON." to "No markdown code blocks, no backticks, no explanation text before or after the JSON. The first character of your response must be { and the last must be }."
    - _Requirements: 4.1_

  - [x] 2.2 Verify `CATEGORIZER_SYSTEM_PROMPT` in `categorizer_agent.py` matches Prompt Management categorizer v2
    - The current constant already matches v2 (expanded `human_only` definition)
    - Verify `{tool_manifest}` single-brace syntax is preserved for `.format()` fallback path
    - _Requirements: 4.2, 4.5_

  - [x] 2.3 Update `VERIFICATION_BUILDER_SYSTEM_PROMPT` in `verification_builder_agent.py` to match Prompt Management VB v2
    - Replace the short v1 prompt with the full v2 text that includes:
      - "HANDLING VAGUE OR SUBJECTIVE PREDICTIONS" section (Track 1 operationalization, Track 2 self-report)
      - "SPECIFICITY MATCHING" section
    - Copy the exact text from `infrastructure/prompt-management/template.yaml` VBPrompt variant
    - _Requirements: 4.3_

  - [x] 2.4 Update `REVIEW_SYSTEM_PROMPT` in `review_agent.py` to match Prompt Management review v3
    - Replace the generic "meta-analysis" prompt with the v3 "find specific assumptions in the Verification Builder's output" prompt
    - Copy the exact text from `infrastructure/prompt-management/template.yaml` ReviewPrompt variant
    - _Requirements: 4.4_

  - [ ]* 2.5 Write unit tests for fallback constant content
    - Verify each `*_SYSTEM_PROMPT` constant contains expected key phrases from its Prompt Management version:
      - Parser: "The first character of your response must be {"
      - Categorizer: contains `{tool_manifest}` (single-brace), does NOT contain `{{tool_manifest}}`
      - VB: contains "HANDLING VAGUE OR SUBJECTIVE PREDICTIONS" and "SPECIFICITY MATCHING"
      - Review: contains "find specific assumptions" and "Verification Builder"
    - Test file: `tests/strands_make_call/test_fallback_constants.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 3. Checkpoint - Verify template and constant changes
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Write property-based tests for prompt_client correctness properties
  - [ ]* 4.1 Write property test for env var passthrough (Property 1)
    - **Property 1: Environment variable passthrough to API call**
    - For any valid agent name and any version string in `PROMPT_VERSION_{AGENT_NAME}`, `fetch_prompt()` passes that version to the `get_prompt` API call
    - Mock `boto3` bedrock-agent client, use `hypothesis` strategies: `st.sampled_from(["parser", "categorizer", "vb", "review"])` × `st.from_regex(r'[1-9][0-9]{0,2}', fullmatch=True)`
    - Test file: `tests/strands_make_call/test_prompt_client_properties.py`
    - **Validates: Requirements 2.5**

  - [ ]* 4.2 Write property test for fallback on API failure (Property 2)
    - **Property 2: Fallback on API failure**
    - For any valid agent name and any exception type, `fetch_prompt()` returns the bundled fallback constant and records `"fallback"` in the manifest
    - Strategies: `st.sampled_from(agent_names)` × `st.sampled_from([Exception, ConnectionError, ValueError])`
    - Test file: `tests/strands_make_call/test_prompt_client_properties.py`
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 4.3 Write property test for variable substitution on both paths (Property 3)
    - **Property 3: Variable substitution on both paths**
    - For any variable name and value, `{{var}}` is replaced on the API path and `{var}` is replaced on the fallback path
    - Strategies: `st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=1)` for var names and values
    - Test file: `tests/strands_make_call/test_prompt_client_properties.py`
    - **Validates: Requirements 3.3, 3.4, 4.5**

  - [ ]* 4.4 Write property test for successful fetch records numeric version (Property 4)
    - **Property 4: Successful fetch records numeric version**
    - For any valid agent name, when `get_prompt` succeeds, the manifest records the numeric version (not `"fallback"`)
    - Strategies: `st.sampled_from(agent_names)` × `st.from_regex(r'[1-9][0-9]{0,2}', fullmatch=True)`
    - Test file: `tests/strands_make_call/test_prompt_client_properties.py`
    - **Validates: Requirements 5.1, 5.2**

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 6. Deploy and validate
  - Run `sam build` and `sam deploy` from `backend/calledit-backend/`
  - After deployment, invoke a test prediction and check CloudWatch logs for prompt version manifest showing numbered versions (e.g., `{"parser": "1", "categorizer": "2", "vb": "2", "review": "3"}`) instead of `"fallback"` entries
  - _Requirements: 5.1, 5.2, 5.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- No changes to `prompt_client.py` — it already handles fetch, fallback, variable substitution, and version manifest tracking
- The categorizer fallback constant already matches v2 — task 2.2 is a verification step, not a code change
- Property tests mock the boto3 client to avoid real Bedrock API calls
- Deploy task (6) is optional since it requires user action outside the coding agent
