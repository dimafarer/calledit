# Verification System v1 (Archived)

> **Archived:** March 20, 2026 — Spec A1 (verification-teardown-docker)
> **Replaced by:** MCP-based tool discovery (Spec A2: mcp-tool-integration)

## What This Was

The old verification system was a primitive attempt at automated prediction verification. An EventBridge rule triggered a Lambda function (`VerificationFunction`) every 15 minutes to scan DynamoDB for pending predictions and verify them using a Strands agent with a datetime tool and reasoning.

It used a DynamoDB tool registry (`TOOL#{tool_id}` records in `calledit-db`) with only `web_search` registered — a custom `@tool` DuckDuckGo wrapper. The system could only verify trivially reasoned predictions and returned INCONCLUSIVE for everything else.

## Why It Was Replaced

The system never worked well. MCP-based tool discovery provides real, capable tool servers (fetch, web search, browser automation) that both the planning agents (Categorizer, Verification Builder) and the future execution agent share via Strands `MCPClient`. Adding a new MCP server immediately makes it available to both planning and execution — no DynamoDB records to manage.

## SAM Resources Removed

- `VerificationFunction` — Lambda + EventBridge 15-minute schedule
- `VerificationLogsBucket` — S3 bucket for verification logs
- `VerificationNotificationTopic` — SNS topic for email notifications
- `NotificationManagementFunction` — Lambda for SNS subscription management (depended on the removed SNS topic)

## Archived Files

### Verification Handler (`handlers/verification/`)
- `app.py` — Lambda handler entry point
- `verification_agent.py` — Strands agent for prediction verification
- `verify_predictions.py` — Verification orchestration logic
- `ddb_scanner.py` — DynamoDB scanner for pending predictions
- `status_updater.py` — Prediction status update logic
- `s3_logger.py` — S3 logging for verification results
- `email_notifier.py` — SNS email notification sender
- `verification_result.py` — Result data model
- `web_search_tool.py` — Custom `@tool` DuckDuckGo web search
- `seed_web_search_tool.py` — Script to register web_search in DDB tool registry
- `error_handling.py` — Error handling utilities
- `cleanup_predictions.py` — Script to backup and delete legacy predictions
- `inspect_data.py` — Data inspection utility
- `mock_strands.py` — Mock Strands module for testing
- `modernize_data.py` — Data migration utility
- `recategorize.py` — Re-categorization pipeline for automatable predictions
- `test_scanner.py` — Scanner tests
- `test_verification_result.py` — Result model tests
- `requirements.txt` — Python dependencies

### Notification Management (`handlers/notification_management/`)
- `app.py` — Lambda handler for SNS subscription management
- `snapstart_hooks.py` — SnapStart lifecycle hooks

### Tool Registry (`handlers/strands_make_call/tool_registry.py`)
- `tool_registry.py` — DynamoDB-based tool registry reader, replaced by MCP-native discovery via `mcp_manager.py` (Spec A2)

## Decision References

- **Decision 18:** Simplify to 3 verifiability categories (`auto_verifiable`, `automatable`, `human_only`)
- **Decision 19:** Tool registry in DynamoDB (`TOOL#{tool_id}` records)
- **Decision 20:** Web search as first registered tool
- **Decision 64:** Split MCP verification foundation into two specs (A1 teardown, A2 MCP integration)
- **Backlog item 7:** Verification pipeline via MCP tools
