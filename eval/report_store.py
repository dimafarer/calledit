"""Shared DDB report store for all eval runners and dashboard.

Provides read/write access to the calledit-v4-eval-reports table.
All three eval runners (creation, verification, calibration) write here.
The React dashboard reads from here via the AWS SDK.

Table schema:
    PK (String): AGENT#{agent_type}  (creation, verification, calibration)
    SK (String): ISO 8601 timestamp

Each item contains run_metadata, aggregate_scores, and case_results.
Items exceeding 400KB are split: case_results stored in a separate
item with SK={timestamp}#CASES.
"""

import json
import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

REPORTS_TABLE_NAME = os.environ.get(
    "EVAL_REPORTS_TABLE", "calledit-v4-eval-reports"
)
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

# DDB item size limit (bytes). We use 390KB as threshold to leave headroom.
_MAX_ITEM_BYTES = 390_000


# ---------------------------------------------------------------------------
# Float <-> Decimal conversion
# ---------------------------------------------------------------------------

def _float_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DDB write.

    NaN and Inf are replaced with None (DDB doesn't support them).
    """
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            logger.warning(f"Replacing non-finite float ({obj}) with None")
            return None
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(v) for v in obj]
    return obj


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal values to float for read."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Table management
# ---------------------------------------------------------------------------

def _get_ddb_resource():
    """Get a boto3 DynamoDB resource."""
    return boto3.resource("dynamodb", region_name=AWS_REGION)


def _ensure_table_exists(ddb=None) -> object:
    """Create calledit-v4-eval-reports table if it doesn't exist.

    Returns the Table resource.
    """
    if ddb is None:
        ddb = _get_ddb_resource()

    client = ddb.meta.client
    try:
        client.describe_table(TableName=REPORTS_TABLE_NAME)
        logger.debug(f"Reports table '{REPORTS_TABLE_NAME}' already exists")
    except client.exceptions.ResourceNotFoundException:
        logger.info(f"Creating reports table '{REPORTS_TABLE_NAME}'...")
        try:
            ddb.create_table(
                TableName=REPORTS_TABLE_NAME,
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=REPORTS_TABLE_NAME)
            logger.info(f"Reports table '{REPORTS_TABLE_NAME}' created")
        except Exception as e:
            raise RuntimeError(
                f"Failed to create reports table '{REPORTS_TABLE_NAME}': {e}. "
                "Check IAM permissions for dynamodb:CreateTable."
            ) from e

    return ddb.Table(REPORTS_TABLE_NAME)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def _estimate_item_size(item: dict) -> int:
    """Rough estimate of DDB item size in bytes via JSON serialization."""
    return len(json.dumps(item, default=str).encode("utf-8"))


def write_report(agent_type: str, report: dict) -> None:
    """Write an eval report to the Reports_Table.

    PK = AGENT#{agent_type}
    SK = report['run_metadata']['timestamp']

    If the item exceeds ~390KB, case_results is split into a separate
    item with SK={timestamp}#CASES.

    Args:
        agent_type: One of 'creation', 'verification', 'calibration'
        report: Full report dict with run_metadata, aggregate_scores, case_results
    """
    table = _ensure_table_exists()
    timestamp = report["run_metadata"]["timestamp"]
    pk = f"AGENT#{agent_type}"

    # Convert floats to Decimal for DDB
    converted = _float_to_decimal(report)

    item = {
        "PK": pk,
        "SK": timestamp,
        "run_metadata": converted.get("run_metadata", {}),
        "aggregate_scores": converted.get("aggregate_scores", {}),
        "case_results": converted.get("case_results", []),
    }
    # Copy any extra top-level keys (e.g., bias_warning)
    for key in converted:
        if key not in ("run_metadata", "aggregate_scores", "case_results"):
            item[key] = converted[key]

    # Check size and split if needed
    if _estimate_item_size(item) > _MAX_ITEM_BYTES:
        logger.info(f"Report exceeds {_MAX_ITEM_BYTES}B — splitting case_results")
        case_results = item.pop("case_results")
        item["case_results_split"] = True

        # Write main item (without case_results)
        table.put_item(Item=item)

        # Write case_results as separate item
        cases_item = {
            "PK": pk,
            "SK": f"{timestamp}#CASES",
            "case_results": case_results,
        }
        table.put_item(Item=cases_item)
    else:
        table.put_item(Item=item)

    logger.info(f"Report written: {pk} / {timestamp}")


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def list_reports(agent_type: str) -> list[dict]:
    """Query all reports for an agent type. Returns metadata + scores only.

    Results are sorted by timestamp descending (newest first).
    case_results is excluded to minimize read cost.
    """
    table = _ensure_table_exists()
    pk = f"AGENT#{agent_type}"

    response = table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": pk},
        ProjectionExpression="PK, SK, run_metadata, aggregate_scores, creation_scores, verification_scores, calibration_scores",
        ScanIndexForward=False,  # newest first
    )

    results = []
    for item in response.get("Items", []):
        entry = {
            "run_metadata": _decimal_to_float(item.get("run_metadata", {})),
        }
        # Support both old format (aggregate_scores) and new (creation/verification/calibration)
        if "creation_scores" in item:
            entry["creation_scores"] = _decimal_to_float(item.get("creation_scores", {}))
            entry["verification_scores"] = _decimal_to_float(item.get("verification_scores", {}))
            entry["calibration_scores"] = _decimal_to_float(item.get("calibration_scores", {}))
        if "aggregate_scores" in item:
            entry["aggregate_scores"] = _decimal_to_float(item.get("aggregate_scores", {}))
        results.append(entry)

    return results


def get_report(agent_type: str, timestamp: str) -> dict | None:
    """Get a full report including case_results.

    Reassembles split items if case_results was stored separately.
    Returns None if not found.
    """
    table = _ensure_table_exists()
    pk = f"AGENT#{agent_type}"

    response = table.get_item(Key={"PK": pk, "SK": timestamp})
    item = response.get("Item")
    if not item:
        return None

    report = _decimal_to_float(item)

    # Remove DDB keys from the report
    report.pop("PK", None)
    report.pop("SK", None)

    # Reassemble split case_results if needed
    if report.pop("case_results_split", False):
        cases_response = table.get_item(
            Key={"PK": pk, "SK": f"{timestamp}#CASES"}
        )
        cases_item = cases_response.get("Item")
        if cases_item:
            report["case_results"] = _decimal_to_float(
                cases_item.get("case_results", [])
            )
        else:
            logger.warning(f"Split case_results item not found for {pk}/{timestamp}")
            report["case_results"] = []

    return report


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------

def backfill_from_files(directory: str) -> dict:
    """Import historical JSON reports from a directory into the Reports_Table.

    Detects agent_type from run_metadata.agent or filename pattern.
    Idempotent: skips items that already exist via conditional put.

    Returns: {"imported": N, "skipped": M, "errors": [...]}
    """
    import glob

    table = _ensure_table_exists()
    stats = {"imported": 0, "skipped": 0, "errors": []}

    patterns = [
        os.path.join(directory, "creation-eval-*.json"),
        os.path.join(directory, "verification-eval-*.json"),
        os.path.join(directory, "calibration-eval-*.json"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    for filepath in sorted(files):
        try:
            with open(filepath, "r") as f:
                report = json.load(f)

            # Detect agent type
            agent_type = report.get("run_metadata", {}).get("agent")
            if not agent_type:
                basename = os.path.basename(filepath)
                if basename.startswith("creation-"):
                    agent_type = "creation"
                elif basename.startswith("verification-"):
                    agent_type = "verification"
                elif basename.startswith("calibration-"):
                    agent_type = "calibration"
                else:
                    stats["errors"].append(f"{filepath}: cannot detect agent type")
                    continue

            timestamp = report.get("run_metadata", {}).get("timestamp")
            if not timestamp:
                stats["errors"].append(f"{filepath}: missing run_metadata.timestamp")
                continue

            pk = f"AGENT#{agent_type}"
            converted = _float_to_decimal(report)

            item = {
                "PK": pk,
                "SK": timestamp,
                "run_metadata": converted.get("run_metadata", {}),
                "aggregate_scores": converted.get("aggregate_scores", {}),
                "case_results": converted.get("case_results", []),
            }
            for key in converted:
                if key not in ("run_metadata", "aggregate_scores", "case_results"):
                    item[key] = converted[key]

            # Handle oversized items
            if _estimate_item_size(item) > _MAX_ITEM_BYTES:
                case_results = item.pop("case_results")
                item["case_results_split"] = True

                # Conditional put — skip if exists
                try:
                    table.put_item(
                        Item=item,
                        ConditionExpression="attribute_not_exists(PK)",
                    )
                    table.put_item(Item={
                        "PK": pk,
                        "SK": f"{timestamp}#CASES",
                        "case_results": case_results,
                    })
                    stats["imported"] += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                        stats["skipped"] += 1
                    else:
                        raise
            else:
                try:
                    table.put_item(
                        Item=item,
                        ConditionExpression="attribute_not_exists(PK)",
                    )
                    stats["imported"] += 1
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                        stats["skipped"] += 1
                    else:
                        raise

        except Exception as e:
            stats["errors"].append(f"{filepath}: {e}")
            logger.warning(f"Backfill error for {filepath}: {e}")

    logger.info(
        f"Backfill complete: {stats['imported']} imported, "
        f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
    )
    return stats
