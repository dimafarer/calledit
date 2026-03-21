"""
Verification Store — DynamoDB storage utility for verification outcomes (Spec B2).

Shared module importable by both the Verification Scanner Lambda and the
eval runner (Spec B3). Writes Verification_Outcome dicts back to the
original Prediction_Record in calledit-db using UpdateExpression.

References:
  - Decision 81: Scanner-only in production, no immediate verification
  - Decision 80: Verification trigger is Log Call, not pipeline completion
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

TABLE_NAME = "calledit-db"

# Module-level DynamoDB resource — reused across warm Lambda invocations
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(TABLE_NAME)


def _convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    return obj


def store_verification_result(user_id: str, sort_key: str, outcome: dict) -> bool:
    """Write a Verification_Outcome back to the Prediction_Record in calledit-db.

    Uses UpdateExpression to modify only verification-related attributes,
    preserving all existing fields (prediction_statement, verification_method, etc.).

    Args:
        user_id: The user ID portion of the PK (without the "USER:" prefix —
                 the function constructs PK=USER:{user_id}).
        sort_key: The full SK value (e.g., "PREDICTION#2026-03-22T14:30:00").
        outcome: A Verification_Outcome dict from run_verification().

    Returns:
        True if the update succeeded, False if it failed.
        Never raises — logs errors at ERROR level.
    """
    try:
        if not isinstance(outcome, dict):
            logger.error(f"Invalid outcome type for USER:{user_id} / {sort_key}: expected dict, got {type(outcome)}")
            return False

        # Convert floats to Decimal for DynamoDB compatibility
        ddb_outcome = _convert_floats_to_decimal(outcome)

        _table.update_item(
            Key={
                "PK": f"USER:{user_id}",
                "SK": sort_key,
            },
            UpdateExpression="SET verification_result = :vr, #s = :status, updatedAt = :ts",
            ExpressionAttributeNames={
                "#s": "status",  # 'status' is a DynamoDB reserved word
            },
            ExpressionAttributeValues={
                ":vr": ddb_outcome,
                ":status": outcome.get("status", "inconclusive"),
                ":ts": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info(
            f"Stored verification result for USER:{user_id} / {sort_key}: "
            f"status={outcome.get('status', 'unknown') if isinstance(outcome, dict) else 'unknown'}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Failed to store verification result for USER:{user_id} / {sort_key}: {e}",
            exc_info=True,
        )
        return False
