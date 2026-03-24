"""
ListPredictions Lambda — queries v4 DDB GSI for a user's predictions.

API Gateway HTTP API validates the Cognito JWT before this Lambda runs.
We extract user_id (sub claim), query the user_id-created_at-index GSI,
and return formatted predictions sorted by creation date descending.
"""

import json
import logging
import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-v4")
GSI_NAME = "user_id-created_at-index"


class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types from DynamoDB."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super().default(obj)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def extract_user_id(event: dict) -> str:
    """Extract user_id (sub) from API Gateway HTTP API JWT claims."""
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def format_prediction(item: dict) -> dict:
    """Format a DDB item into the API response shape."""
    result = {
        "prediction_id": item.get("prediction_id", ""),
        "raw_prediction": item.get("raw_prediction", ""),
        "status": item.get("status", "pending"),
        "verification_date": item.get("verification_date", ""),
        "verifiability_score": item.get("verifiability_score"),
        "created_at": item.get("created_at", ""),
    }
    # Include verification result if available
    if item.get("verdict"):
        result["verification_result"] = {
            "verdict": item.get("verdict"),
            "confidence": item.get("confidence"),
            "reasoning": item.get("reasoning"),
        }

    # Include parsed claim statement if available
    parsed_claim = item.get("parsed_claim", {})
    if isinstance(parsed_claim, dict) and parsed_claim.get("statement"):
        result["prediction_statement"] = parsed_claim["statement"]

    return result


def lambda_handler(event, context):
    try:
        user_id = extract_user_id(event)
        logger.info(f"Listing predictions for user: {user_id}")
    except (KeyError, TypeError) as e:
        logger.error(f"Failed to extract user_id from JWT claims: {e}")
        return _response(401, {"error": "Invalid or missing JWT claims"})

    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(DYNAMODB_TABLE_NAME)

        items = []
        query_kwargs = {
            "IndexName": GSI_NAME,
            "KeyConditionExpression": "user_id = :uid",
            "ExpressionAttributeValues": {":uid": user_id},
            "ScanIndexForward": False,  # Descending by created_at
        }
        while True:
            resp = table.query(**query_kwargs)
            items.extend(resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                break
            query_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

        results = [format_prediction(item) for item in items]
        logger.info(f"Returning {len(results)} predictions for user {user_id}")
        return _response(200, {"results": results})

    except ClientError as e:
        logger.error(f"DynamoDB query failed: {e}", exc_info=True)
        return _response(500, {"error": f"Database error: {e}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _response(500, {"error": f"Unexpected error: {e}"})
