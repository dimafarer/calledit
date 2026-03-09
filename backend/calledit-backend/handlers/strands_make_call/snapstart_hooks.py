"""
SnapStart Runtime Hooks for MakeCallStreamFunction

These hooks handle the SnapStart snapshot/restore lifecycle:
- @register_before_snapshot: Runs once when Lambda creates the snapshot
  (after INIT, before freezing). Used for logging/cleanup.
- @register_after_restore: Runs on every restore from snapshot
  (before handler execution). Used to refresh stale connections and
  validate the singleton graph.

WHY THIS MODULE EXISTS:
SnapStart snapshots the entire initialized execution environment, including
any boto3 clients created at module level. After restore, those clients may
have stale credentials or closed TCP connections. The after_restore hook
refreshes them and validates the graph.

For MakeCallStreamFunction specifically:
- The prediction_graph singleton is safe — it holds agent configs and graph
  structure, not network connections. Bedrock API calls are made fresh per
  invocation by the strands-agents library.
- The api_gateway_client is created per-invocation in async_handler(),
  so it's NOT affected by snapshot staleness.
- The graph validation is defensive — SnapStart should preserve Python
  objects faithfully, but we verify the 4 agent nodes are present.

IMPORT REQUIREMENT:
This module must be imported in the Lambda handler module
(strands_make_call_graph.py) for the hooks to register. The import
triggers decorator registration at module load time.

Library: snapshot_restore_py (included in Python 3.12+ managed runtime)
"""

import logging

from snapshot_restore_py import register_before_snapshot, register_after_restore

logger = logging.getLogger(__name__)


def validate_graph_after_restore():
    """
    Verify the singleton prediction_graph survived SnapStart restore.

    Checks that the 4 expected agent nodes exist in the graph. If validation
    fails, re-creates the graph and logs a warning. Returns True if the graph
    is valid (or was successfully re-created), False only if re-creation fails.

    WHY THIS EXISTS:
    SnapStart should preserve Python objects faithfully — graph corruption
    after restore would be an AWS service bug, not an expected failure mode.
    This is belt-and-suspenders: if it ever fires, we want to know about it
    via WARNING-level logging in CloudWatch.
    """
    try:
        import prediction_graph as pg_module
        from prediction_graph import prediction_graph, create_prediction_graph

        expected_nodes = {"parser", "categorizer", "verification_builder", "review"}

        # Access the graph's nodes dict directly.
        # Graph.nodes is a dict[str, GraphNode] — the keys are node IDs.
        actual_nodes = set(prediction_graph.nodes.keys())
        if expected_nodes.issubset(actual_nodes):
            logger.info(
                f"SnapStart: Graph validation passed — "
                f"{len(actual_nodes)} nodes present"
            )
            return True

        logger.warning(
            f"SnapStart: Graph validation failed — "
            f"expected {expected_nodes}, found {actual_nodes}. "
            f"Re-creating graph."
        )
        pg_module.prediction_graph = create_prediction_graph()
        return True

    except Exception as e:
        logger.error(
            f"SnapStart: Graph validation error: {e}. "
            f"Attempting re-creation.",
            exc_info=True
        )
        try:
            import prediction_graph as pg_module
            from prediction_graph import create_prediction_graph
            pg_module.prediction_graph = create_prediction_graph()
            return True
        except Exception as e2:
            logger.error(
                f"SnapStart: Graph re-creation failed: {e2}",
                exc_info=True
            )
            return False


@register_before_snapshot
def before_snapshot():
    """Called once when Lambda creates the SnapStart snapshot."""
    try:
        logger.info(
            "SnapStart: Creating snapshot. "
            "prediction_graph singleton is initialized."
        )
    except Exception as e:
        # Never propagate — snapshot creation must not fail due to our hook.
        logger.error(f"SnapStart: before_snapshot hook error: {e}")


@register_after_restore
def after_restore():
    """Called on every restore from snapshot, before handler execution."""
    try:
        logger.info("SnapStart: Restoring from snapshot.")
        validate_graph_after_restore()
        logger.info("SnapStart: Restore complete. Graph validated.")
    except Exception as e:
        # Never propagate — a failing hook must not prevent handler execution.
        # The handler creates api_gateway_client per-invocation anyway.
        logger.error(
            f"SnapStart: after_restore hook error: {e}",
            exc_info=True
        )
