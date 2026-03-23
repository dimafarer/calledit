"""DynamoDB operations for loading prediction bundles and writing verdicts.

Shared code (~20 lines) duplicated from calleditv4/src/bundle.py per
Decision 106: minimal duplication over shared packages.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    return obj


def load_bundle_from_ddb(
    table, prediction_id: str
) -> Optional[Dict[str, Any]]:
    """Load a prediction bundle from DynamoDB.

    Args:
        table: boto3 DynamoDB Table resource
        prediction_id: e.g. "pred-abc123..."

    Returns:
        Bundle dict if found, None otherwise.
    """
    response = table.get_item(
        Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"}
    )
    item = response.get("Item")
    if item is None:
        return None
    item.pop("PK", None)
    item.pop("SK", None)
    return item


def update_bundle_with_verdict(
    table,
    prediction_id: str,
    result,
    prompt_versions: Dict[str, str],
) -> bool:
    """Write verification result back to the prediction bundle.

    Uses ConditionExpression to prevent overwriting already-verified bundles.

    Args:
        table: boto3 DynamoDB Table resource
        prediction_id: The prediction ID
        result: VerificationResult Pydantic model instance
        prompt_versions: Dict of prompt name -> version used

    Returns:
        True if update succeeded, False if condition check failed.
    """
    now = datetime.now(timezone.utc).isoformat()
    new_status = (
        "verified"
        if result.verdict in ("confirmed", "refuted")
        else "inconclusive"
    )
    evidence_dicts = [e.model_dump() for e in result.evidence]

    try:
        table.update_item(
            Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"},
            UpdateExpression=(
                "SET verdict = :v, confidence = :c, evidence = :e, "
                "reasoning = :r, verified_at = :va, #s = :ns, "
                "prompt_versions.verification = :pv"
            ),
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":v": result.verdict,
                ":c": _convert_floats_to_decimal(result.confidence),
                ":e": _convert_floats_to_decimal(evidence_dicts),
                ":r": result.reasoning,
                ":va": now,
                ":ns": new_status,
                ":pv": prompt_versions.get(
                    "verification_executor", "unknown"
                ),
                ":pending": "pending",
            },
            ConditionExpression=(
                "attribute_exists(PK) AND #s = :pending"
            ),
        )
        return True
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning(
            f"Condition check failed for {prediction_id} "
            "— already verified or deleted"
        )
        return False
