# Implementation Plan: Category Simplification & Tool Registry

## Overview

Simplify the CalledIt verifiability system from 5 categories to 3 (`auto_verifiable`, `automatable`, `human_only`), introduce a DynamoDB tool registry, add a web search tool, build a re-categorization pipeline, upgrade the verification agent to Sonnet 4, and clean up legacy data. Data cleanup runs first (clean slate), then core code changes, then tool registration and validation.

## Tasks

- [x] 1. Data cleanup — backup and delete legacy prediction records
  - [x] 1.1 Add backup step to `cleanup_predictions.py` — before deleting, export all matching prediction records to JSON and upload to the existing `VerificationLogsBucket` S3 bucket under key `backups/predictions-backup-{timestamp}.json`
  - [x] 1.2 Create `cleanup_predictions.py` script
    - Create new file at `backend/calledit-backend/handlers/verification/cleanup_predictions.py`
    - Implement `cleanup_predictions(table_name="calledit-db", dry_run=True)` that scans for items where PK starts with `USER:` and SK starts with `PREDICTION#`, then batch-deletes them
    - Default to `dry_run=True` for safety — prints count and sample keys without deleting
    - When `dry_run=False`, delete each matching item and report count of successes/failures
    - Must NOT delete items where PK starts with `TOOL#` or any non-prediction records
    - Include `if __name__ == "__main__"` block that runs dry_run first, prints results, then prompts for confirmation before real delete
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ]* 1.2 Write property test for cleanup filter logic (Property 11)
    - **Property 11: Cleanup deletes only prediction records**
    - Create test in `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate mixed DDB items (USER:/PREDICTION#, TOOL#/METADATA, CONNECTION#/*, random PK/SK patterns)
    - Assert cleanup logic only targets items where PK starts with `USER:` AND SK starts with `PREDICTION#`
    - **Validates: Requirements 11.2**

- [x] 2. Checkpoint — Data cleanup ready
  - Ensure cleanup script works with dry_run. Ask the user to run it against the real table before proceeding. Ensure all tests pass, ask the user if questions arise.

- [x] 3. Category simplification — update categorizer, pipeline fallbacks, and constants
  - [x] 3.1 Update `VALID_CATEGORIES` and system prompt in `categorizer_agent.py`
    - Replace `VALID_CATEGORIES` set with `{"auto_verifiable", "automatable", "human_only"}`
    - Rewrite `CATEGORIZER_SYSTEM_PROMPT` with 3-category descriptions and examples per design Component 1
    - Add `tool_manifest` parameter to `create_categorizer_agent(tool_manifest: str = "") -> Agent`
    - Append tool manifest section to system prompt when `tool_manifest` is non-empty; use "No tools currently registered" fallback when empty
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.2 Update pipeline fallbacks in `prediction_graph.py`
    - In `parse_pipeline_results()`: change all `"human_verifiable_only"` fallback strings to `"human_only"`
    - In `execute_prediction_graph()` sync wrapper: change error fallback category from `"human_verifiable_only"` to `"human_only"`
    - _Requirements: 8.1, 8.3_

  - [x] 3.3 Update fallback in `strands_make_call_graph.py`
    - In `build_prediction_ready()`: change `"human_verifiable_only"` fallback to `"human_only"`
    - _Requirements: 8.1_

  - [ ]* 3.4 Write property test for category output validity (Property 1)
    - **Property 1: Category output is always valid**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate arbitrary strings as categorizer output, feed through `parse_pipeline_results()` parsing logic
    - Assert resulting `verifiable_category` is always one of `auto_verifiable`, `automatable`, `human_only`
    - **Validates: Requirements 1.1, 1.5**

  - [ ]* 3.5 Write property test for pipeline fallback (Property 7)
    - **Property 7: Pipeline fallback always produces a valid category**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate invalid JSON, empty strings, malformed data as raw categorizer output
    - Assert `parse_pipeline_results()` always produces a `verifiable_category` in the valid set, defaulting to `human_only`
    - **Validates: Requirements 8.1, 8.3**

  - [ ]* 3.6 Write unit tests for categorizer constants and prompt
    - Add to `testing/active/test_category_simplification.py`
    - Assert `VALID_CATEGORIES` contains exactly 3 values: `auto_verifiable`, `automatable`, `human_only`
    - Assert `CATEGORIZER_SYSTEM_PROMPT` contains all 3 category names
    - Assert `create_categorizer_agent(tool_manifest="- web_search: ...")` produces an agent whose system prompt includes the manifest text
    - Assert `create_categorizer_agent()` with no args produces an agent whose system prompt includes "No tools currently registered"
    - _Requirements: 1.5, 1.6, 5.2, 5.5_

- [x] 4. Tool registry reader — new module
  - [x] 4.1 Create `tool_registry.py` in `handlers/strands_make_call/`
    - Implement `read_active_tools(table_name: str = "calledit-db") -> list[dict]` — scans DDB for items where PK starts with `TOOL#` and `status == "active"`, returns list of tool dicts
    - Implement `build_tool_manifest(tools: list[dict]) -> str` — builds human-readable manifest string from tool records (name + description + capabilities per tool), returns empty string if no tools
    - Each returned tool dict must contain: `name`, `description`, `capabilities`, `input_schema`, `output_schema`, `status`, `added_date`
    - Handle DDB read failures gracefully: log error, return empty list (categorizer falls back to pure reasoning mode)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2_

  - [ ]* 4.2 Write property test for active tool filtering (Property 3)
    - **Property 3: Active tool filtering excludes inactive tools**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate lists of tool dicts with mixed `status` values (`active`, `inactive`, random strings)
    - Mock DDB scan to return the generated list, call `read_active_tools()`, assert result contains only `status == "active"` records
    - **Validates: Requirements 4.4, 4.5**

  - [ ]* 4.3 Write property test for tool record schema completeness (Property 4)
    - **Property 4: Tool record schema completeness**
    - Add to `testing/active/test_category_simplification.py`
    - For any tool record returned by `read_active_tools()`, assert it contains all required fields: `name`, `description`, `capabilities`, `input_schema`, `output_schema`, `status`, `added_date`
    - **Validates: Requirements 4.3**

  - [ ]* 4.4 Write property test for tool manifest content (Property 5)
    - **Property 5: Tool manifest contains all active tool information**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate lists of tool dicts with `name` and `description` fields
    - Assert `build_tool_manifest(tools)` output contains each tool's `name` and `description`
    - Assert `build_tool_manifest([])` returns empty string
    - **Validates: Requirements 5.2**

- [x] 5. Categorizer tool awareness — inject tool manifest at graph creation
  - [x] 5.1 Update `create_prediction_graph()` in `prediction_graph.py`
    - Import `read_active_tools` and `build_tool_manifest` from `tool_registry`
    - Call `read_active_tools()` and `build_tool_manifest()` at graph creation time (module level, cached by SnapStart)
    - Pass resulting `tool_manifest` string to `create_categorizer_agent(tool_manifest)`
    - Wrap tool registry read in try/except: on failure, log error and pass empty string (pure reasoning fallback)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Checkpoint — Category simplification and tool registry wired
  - Ensure all tests pass, ask the user if questions arise. Verify that `create_prediction_graph()` reads tools and injects manifest into categorizer.

- [x] 7. Verification agent overhaul
  - [x] 7.1 Rewrite `verification_agent.py` with new 3-category routing
    - Upgrade model from `claude-3-sonnet-20241022` to `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - Replace `from strands_agents import Agent` with `from strands import Agent`
    - Remove `from error_handling import safe_agent_call, ToolFallbackManager` (module is legacy)
    - Remove `from mock_strands import MockStrandsModule, MockStrandsToolsModule` (use real SDK)
    - Keep `from verification_result import VerificationResult, VerificationStatus, create_tool_gap_result`
    - Simplify `verify_prediction()` routing to 3 categories + unknown fallback:
      - `auto_verifiable` → `_verify_with_tools()` using all active registry tools
      - `automatable` → `_mark_tool_gap()` returning inconclusive with tool gap indication
      - `human_only` → `_mark_human_required()` returning inconclusive indicating human assessment
      - unknown → `_handle_unknown_category()` returning inconclusive fallback
    - Load active tools from tool registry in `__init__` (import `read_active_tools` from `tool_registry` — add to `sys.path` or use relative import)
    - On tool execution failure during `auto_verifiable` verification: catch exception, log error, fall back to reasoning-based verification
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 6.1, 6.2, 6.3_

  - [ ]* 7.2 Write property test for verification agent routing (Property 2)
    - **Property 2: Verification agent routes correctly by category**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate prediction dicts with `verifiable_category` drawn from `auto_verifiable`, `automatable`, `human_only`, and random strings
    - Assert routing logic maps each category to the correct verification method (tool-based, tool-gap inconclusive, human-required inconclusive, unknown fallback)
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [ ]* 7.3 Write unit tests for verification agent model and routing
    - Add to `testing/active/test_category_simplification.py`
    - Assert verification agent model string is `us.anthropic.claude-sonnet-4-20250514-v1:0`
    - Assert routing covers exactly 3 categories plus unknown fallback
    - _Requirements: 3.1, 3.2, 2.5_

- [x] 8. Web search tool
  - [x] 8.1 Create `web_search_tool.py` in `handlers/verification/`
    - Implement `@tool` decorated `web_search(query: str) -> str` function using Python `requests`
    - Use DuckDuckGo instant answer API or similar free endpoint
    - Timeout: 10 seconds
    - Return structured JSON string: `{"results": [...], "query": "...", "status": "success"}` on success
    - Return `{"error": "...", "query": "...", "status": "error"}` on any failure (timeout, HTTP error, network error)
    - Must never raise an exception — all errors caught and returned as structured error response
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 8.2 Create tool registry seed script `seed_web_search_tool.py`
    - Create script at `backend/calledit-backend/handlers/verification/seed_web_search_tool.py`
    - Writes the web_search Tool_Record to DDB with PK=`TOOL#web_search`, SK=`METADATA`, status=`active`, and all required fields (name, description, capabilities, input_schema, output_schema, added_date)
    - Include `if __name__ == "__main__"` block for manual execution
    - _Requirements: 7.3, 7.4_

  - [ ]* 8.3 Write property test for web search tool error handling (Property 6)
    - **Property 6: Web search tool returns structured output without raising**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate arbitrary query strings (including empty, unicode, very long)
    - Mock `requests.get` to return various responses (success, timeout, HTTP errors, connection errors)
    - Assert return value is always valid JSON with `status` and `query` fields
    - Assert the function never raises an exception
    - **Validates: Requirements 7.2, 7.5**

- [x] 9. Checkpoint — Core implementation complete
  - Ensure all tests pass, ask the user if questions arise. Verify categorizer, tool registry, verification agent, and web search tool are all wired correctly.

- [x] 10. Re-categorization pipeline
  - [x] 10.1 Create `recategorize.py` in `handlers/verification/`
    - Implement `scan_automatable_predictions(table_name="calledit-db") -> list[dict]` — scans DDB for predictions with `verifiable_category == "automatable"`
    - Implement `recategorize_prediction(prediction: dict) -> dict` — re-runs a single prediction through the full prediction graph (import and call `execute_prediction_graph` from `prediction_graph`)
    - Implement `run_recategorization(table_name="calledit-db", dry_run=False) -> dict` — main entry point that scans, re-runs each prediction, updates DDB if category changed, returns `{"scanned": N, "recategorized": N, "unchanged": N, "errors": N}`
    - On individual prediction failure: log error, increment error count, continue to next prediction
    - On DDB write failure: log error, increment error count, continue (prediction retains original category)
    - Update DDB record only when new `verifiable_category` differs from original
    - Add `sys.path` manipulation to import from `handlers/strands_make_call/` directory
    - Include `if __name__ == "__main__"` block for manual execution
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 10.2 Write property test for re-categorization scan filter (Property 8)
    - **Property 8: Re-categorization scan returns only automatable predictions**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate lists of prediction dicts with mixed `verifiable_category` values
    - Mock DDB scan, call `scan_automatable_predictions()`, assert all returned records have `verifiable_category == "automatable"`
    - **Validates: Requirements 9.1**

  - [ ]* 10.3 Write property test for re-categorization update logic (Property 9)
    - **Property 9: Re-categorization updates if and only if category changed**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate prediction dicts and mock pipeline outputs with various category results
    - Assert DDB update is called only when new category differs from original
    - Assert DDB update is NOT called when category remains `automatable`
    - **Validates: Requirements 9.3, 9.4**

  - [ ]* 10.4 Write property test for re-categorization count consistency (Property 10)
    - **Property 10: Re-categorization counts are consistent**
    - Add to `testing/active/test_category_simplification.py`
    - Use Hypothesis to generate batches of predictions with various re-categorization outcomes
    - Assert `scanned == recategorized + unchanged + errors` for every run
    - **Validates: Requirements 9.6**

- [x] 11. SAM template verification
  - [x] 11.1 Verify existing DynamoDB policies cover tool registry access
    - Confirm `MakeCallStreamFunction` has `DynamoDBCrudPolicy` for `calledit-db` (covers tool registry reads)
    - Confirm `VerificationFunction` has `DynamoDBCrudPolicy` for `calledit-db` (covers tool registry reads)
    - No template changes needed — document this in a code comment if desired
    - _Requirements: 10.1, 10.2, 10.3_

- [ ] 12. Final checkpoint — All tests pass, end-to-end validation ready
  - Ensure all tests pass, ask the user if questions arise. All code changes are complete. The user should now:
    1. Run `cleanup_predictions.py` against the real DDB table (dry_run first, then real delete)
    2. Deploy the updated code via `sam build && sam deploy`
    3. Run `seed_web_search_tool.py` to register the web search tool in DDB
    4. Make a few test predictions via the frontend to verify new 3-category system
    5. Run `recategorize.py` to re-evaluate any `automatable` predictions
    6. Verify graduated predictions show `auto_verifiable` with web search tool awareness

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Data cleanup (task 1) runs BEFORE deploying new code for a clean slate
- Web search tool registration in DDB (task 8.2) is a manual script step run after deployment
- Re-categorization pipeline (task 10) is exercised as part of post-deployment validation
- SAM template needs no changes — existing `DynamoDBCrudPolicy` covers tool registry reads
- All Python commands use venv: `/home/wsluser/projects/calledit/venv/bin/python`
- Tests go in `testing/active/test_category_simplification.py`
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
