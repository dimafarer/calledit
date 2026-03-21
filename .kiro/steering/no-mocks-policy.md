---
inclusion: auto
---

# No Mocks Policy — MANDATORY

## Rule

**DO NOT use mocks, MagicMock, patch, or any test doubles in this project.**

Tests must exercise the real code path — real MCP servers, real Bedrock calls, real DynamoDB. If a test can't run without mocking, it's testing the wrong thing or the code needs to be restructured.

## What This Means

- ❌ `from unittest.mock import patch, MagicMock` — NEVER
- ❌ `@patch("module.function")` — NEVER
- ❌ `mock_agent = MagicMock()` — NEVER
- ❌ Any test double, fake, stub, or spy — NEVER

## What To Do Instead

- Write integration tests that call real services (Bedrock, MCP servers, DynamoDB)
- Test pure functions directly with real inputs and assert real outputs
- Use test scripts (like `test_mcp_local.py`) for manual integration validation
- Accept that tests calling Bedrock cost money and take time — that's the cost of testing the real thing
- If a test is too expensive to run frequently, mark it clearly and run it manually

## Before Writing Any Test

1. Check: does this test use mocks? If yes, STOP and inform the user
2. If you see existing mocks in the codebase, inform the user immediately
3. Ask the user before introducing any test isolation pattern

## Why

Mocks hide real bugs. A test that passes with mocks but fails with real services is worse than no test — it gives false confidence. This project values real integration tests over fast fake ones.
