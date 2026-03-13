---
doc_index: 18
type: Feature Review & Implementation
date: 2026-02-23
git_commit: (post-implementation)
associated_spec: None (direct implementation)
---

# Lambda SnapStart — Implementation Review — February 23, 2026

## Context

The DontSpin streaming Lambda has noticeable cold start latency due to heavy initialization: Strands SDK imports, four agent singletons, boto3 client setup, and module loading. WebSocket users feel this directly — the first message after a cold start has multi-second latency before the agent begins streaming.

## What Is SnapStart

Lambda SnapStart takes a memory snapshot of the function after initialization completes. When a new execution environment is needed, Lambda restores from that snapshot instead of re-running init from scratch. The result is sub-second cold starts.

SnapStart is GA for Python 3.12 and 3.13. Our Lambda uses Python 3.12.

## Key Constraint: Perishable Resources

When Lambda takes a snapshot, everything in memory is frozen — including boto3 clients and their HTTP connection pools. When restored (potentially hours later), those connections are stale.

Our perishable resources:
- `_dynamodb` singleton in `db.py` — cached boto3 DynamoDB resource
- `_apigw_management_client` in `streaming_handler.py` — API Gateway Management API client
- Agent singletons — if they hold HTTP connections internally

The fix: a `@register_after_restore` hook that resets these to `None`, forcing lazy re-creation on the next request. Our existing code already handles `None` checks via `get_table()` and `get_management_client()`.

## SnapStart + WebSocket APIs

WebSocket API Gateway invokes Lambda synchronously for each message. SnapStart works fine with synchronous invocations — no fundamental incompatibility.

The API Gateway Management API client is constructed from the event context (domain + stage). After restore, the endpoint URL is still valid but the HTTP connection pool is stale. Resetting to `None` handles this.

SnapStart requires published versions (not `$LATEST`). The CDK change creates a version and alias, and points the WebSocket integrations at the alias.

## Changes Made

| File | Changes |
|---|---|
| `backend/agents/streaming_handler.py` | Added `@register_after_restore` hook to reset `_dynamodb`, `_apigw_management_client`, and agent singletons |
| `infrastructure/stacks/backend_stack.py` | Added `snap_start=SnapStartConf.ON_PUBLISHED_VERSIONS`, created alias `live`, pointed WebSocket integrations at alias |

## Deployment

After `cdk deploy`, SnapStart optimization runs automatically when the new version is published. First invocation after deploy may still be slow (snapshot creation), but subsequent cold starts will be sub-second.
