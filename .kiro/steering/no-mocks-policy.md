---
inclusion: auto
---

# No Mocks Policy — MANDATORY

## Rule

**Default: NO mocks.** Mocks are not allowed unless two conditions are met:

1. **Proven value**: The agent must demonstrate a concrete, specific reason why a mock is necessary and what real value it provides that cannot be achieved through pure function tests or real integration tests.
2. **User approval**: The agent MUST flag the proposed mock to the user and get explicit approval BEFORE writing any mock code. Never implement a mock silently.

## Decision Protocol

When the agent believes a mock might be justified:

1. STOP — do not write the mock
2. Explain to the user:
   - What would be mocked and why
   - What specific value the mocked test provides
   - What the alternative is (skip the test, restructure the code, use a real service)
3. Wait for the user's decision
4. If the user says no, skip the test or find an alternative
5. If the user says yes, document the exception in the test file with a comment explaining why

## What To Do Instead of Mocking

- Write integration tests that call real services (Bedrock, MCP servers, DynamoDB)
- Test pure functions directly with real inputs and assert real outputs
- Use `agentcore invoke --dev` for manual integration validation
- Accept that tests calling Bedrock cost money and take time — that's the cost of testing the real thing
- If a test is too expensive to run frequently, mark it clearly and run it manually

## Why

Mocks hide real bugs. A test that passes with mocks but fails with real services is worse than no test — it gives false confidence. This project values real integration tests over fast fake ones.
