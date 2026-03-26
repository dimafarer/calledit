"""
ListEvalReports Lambda — queries eval reports table for report summaries.

GET /eval/reports?agent={agent_type}

Returns JSON array of {run_metadata, aggregate_scores} — no case_results.
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

    if not agent:
        return _response(400, {"error": "agent query parameter required"})

    logger.info(f"Listing eval reports for agent: {agent}")

    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(EVAL_REPORTS_TABLE)

        items = []
        query_kwargs = {
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": f"AGENT#{agent}"},
            "ProjectionExpression": "run_metadata, aggregate_scores",
            "ScanIndexForward": False,
        }
        while True:
            resp = table.query(**query_kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            query_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

        logger.info(f"Returning {len(items)} reports for agent {agent}")
        return _response(200, items)

    except ClientError as e:
        logger.error(f"DynamoDB query failed: {e}", exc_info=True)
        return _response(500, {"error": f"Database error: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _response(500, {"error": f"Unexpected error: {e}"})
