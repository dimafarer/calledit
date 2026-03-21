"""
Verification Scanner — EventBridge-triggered Lambda that verifies predictions (Spec B2).

Runs every 15 minutes via EventBridge schedule. Scans calledit-db for
auto_verifiable predictions with status=PENDING whose verification_date
has passed, then calls run_verification() for each and stores the result.

Uses the same Docker image as MakeCallStreamFunction (needs MCP tools +
Strands + Node.js). CMD override in SAM template points here instead of
strands_make_call_graph.lambda_handler.

References:
  - Decision 81: Scanner-only in production
  - Decision 80: Verification trigger is Log Call, not pipeline completion
  - Decision 78: No mocks — tests hit real services
"""

import json
import logging
import threading
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TABLE_NAME = "calledit-db"
VERIFICATION_TIMEOUT_SECONDS = 120


def _now_str() -> str:
    """Current UTC time in YYYY-MM-DD HH:MM:SS format (matches verification_date)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def is_eligible(item: dict, now_str: str) -> bool:
    """Check if a prediction record is eligible for verification.

    Extracted as a pure function for testability (Property 3).

    Args:
        item: A DynamoDB item dict.
        now_str: Current UTC time in YYYY-MM-DD HH:MM:SS format.

    Returns:
        True if the item should be verified now.
    """
    status = item.get("status", "")
    category = item.get("verifiable_category", "")
    verification_date = item.get("verification_date", "")

    if status != "PENDING":
        return False
    if category != "auto_verifiable":
        return False
    if not verification_date:
        return False
    # String comparison works for YYYY-MM-DD HH:MM:SS format
    return verification_date <= now_str


def _run_with_timeout(func, args, timeout_seconds=VERIFICATION_TIMEOUT_SECONDS):
    """Run func(*args) with a timeout. Returns (result, timed_out).

    Uses threading since signal.alarm doesn't work in Lambda.
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        return None, True
    if exception[0]:
        raise exception[0]
    return result[0], False


def _scan_pending_predictions() -> list:
    """Scan calledit-db for PENDING + auto_verifiable predictions.

    Handles DynamoDB pagination via LastEvaluatedKey.

    Returns:
        List of matching DynamoDB items.

    Raises:
        Exception on DynamoDB scan failure (caller handles).
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    items = []
    scan_kwargs = {
        "FilterExpression": (
            Attr("status").eq("PENDING")
            & Attr("verifiable_category").eq("auto_verifiable")
        ),
    }

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return items


def lambda_handler(event, context):
    """EventBridge-triggered scanner entry point.

    Scans for eligible predictions, verifies each sequentially,
    stores results, and logs a summary.
    """
    # Lazy imports to avoid triggering MCP connections until needed
    from verification_executor_agent import run_verification
    from verification_store import store_verification_result
    from verification_executor_agent import _make_inconclusive

    summary = {
        "total_scanned": 0,
        "eligible": 0,
        "verified": 0,
        "failed": 0,
        "outcomes": {"confirmed": 0, "refuted": 0, "inconclusive": 0},
    }

    # Step 1: Scan DynamoDB
    try:
        items = _scan_pending_predictions()
    except Exception as e:
        logger.error(f"DynamoDB scan failed — aborting: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    summary["total_scanned"] = len(items)
    now_str = _now_str()

    # Step 2: Filter eligible predictions
    eligible = [item for item in items if is_eligible(item, now_str)]
    summary["eligible"] = len(eligible)

    logger.info(
        f"Scanner found {summary['total_scanned']} PENDING/auto_verifiable items, "
        f"{summary['eligible']} eligible (verification_date <= {now_str})"
    )

    # Step 3: Verify each eligible prediction sequentially
    for item in eligible:
        pk = item.get("PK", "")
        sk = item.get("SK", "")
        user_id = pk.replace("USER:", "", 1)
        prediction_stmt = item.get("prediction_statement", "")[:80]

        logger.info(f"Verifying: {pk}/{sk} — {prediction_stmt}...")

        try:
            outcome, timed_out = _run_with_timeout(run_verification, (item,))

            if timed_out:
                logger.warning(f"Verification timed out for {pk}/{sk}")
                outcome = _make_inconclusive(
                    "Verification timed out after 120 seconds"
                )

            if outcome is None:
                outcome = _make_inconclusive("run_verification returned None")

        except Exception as e:
            logger.error(f"Verification failed for {pk}/{sk}: {e}", exc_info=True)
            outcome = _make_inconclusive(f"Verification error: {e}")

        # Store result
        status = outcome.get("status", "inconclusive")
        stored = store_verification_result(user_id, sk, outcome)

        if stored:
            summary["verified"] += 1
            summary["outcomes"][status] = summary["outcomes"].get(status, 0) + 1
        else:
            summary["failed"] += 1

    logger.info(f"Scanner complete: {json.dumps(summary)}")

    return {"statusCode": 200, "body": json.dumps(summary)}
