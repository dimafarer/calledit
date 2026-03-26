"""
GetEvalReport Lambda — retrieves a full eval report including case_results.

GET /eval/report?agent={agent_type}&ts={timestamp}

Handles split case_results: if case_results_split=True, fetches companion
item at SK={timestamp}#CASES and reassembles.
API Gateway HTTP API validates the Cognito JWT before this Lambda runs.
"""

import json
import logging
import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVAL_REPORTS_TABLE = os.environ.get("EVAL_REPORTS_TABLE", "calledit-v4-eval-reports")


class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types from DynamoDB."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super().default(obj)


def _response(status_code: int, body) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    agent = params.get("agent")
    ts = params.get("ts")

    if not agent or not ts:
        return _response(400, {"error": "agent and ts query parameters required"})

    pk = f"AGENT#{agent}"
    logger.info(f"Getting eval report: {pk} / {ts}")

    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(EVAL_REPORTS_TABLE)

        resp = table.get_item(Key={"PK": pk, "SK": ts})
        item = resp.get("Item")

        if not item:
            return _response(404, {"error": "not found"})

        # Reassemble split case_results
        if item.get("case_results_split"):
            cases_resp = table.get_item(Key={"PK": pk, "SK": f"{ts}#CASES"})
            cases_item = cases_resp.get("Item")
            if cases_item:
                item["case_results"] = cases_item.get("case_results", [])
            else:
                logger.warning(f"Split case_results companion not found: {pk}/{ts}#CASES")
                item["case_results"] = []

        # Remove DDB keys and internal fields
        item.pop("PK", None)
        item.pop("SK", None)
        item.pop("case_results_split", None)

        return _response(200, item)

    except ClientError as e:
        logger.error(f"DynamoDB GetItem failed: {e}", exc_info=True)
        return _response(500, {"error": f"Database error: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _response(500, {"error": f"Unexpected error: {e}"})
