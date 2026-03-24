"""
V4-5b Verification Scanner — EventBridge-triggered Lambda

Queries DDB GSI for pending predictions due for verification,
invokes the V4-5a verification agent for each one sequentially.

This is a plain Python 3.12 Lambda (zip package, boto3 only).
It does NOT run verification logic — it delegates to the
verification agent via AgentCoreRuntimeClient (prod) or HTTP (dev).
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-db")
GSI_NAME = os.environ.get("GSI_NAME", "status-verification_date-index")


# ---------------------------------------------------------------------------
# Prediction ID extraction
# ---------------------------------------------------------------------------

def extract_prediction_id(item: Dict[str, Any]) -> Optional[str]:
    """Extract prediction_id from a GSI result item.

    Tries the projected `prediction_id` attribute first, then parses
    from PK (PRED#pred-xxx → pred-xxx). Returns None if neither works.
    """
    if "prediction_id" in item:
        return item["prediction_id"]
    pk = item.get("PK", "")
    if pk.startswith("PRED#"):
        return pk[len("PRED#"):]
    return None


# ---------------------------------------------------------------------------
# GSI query
# ---------------------------------------------------------------------------

def query_due_predictions(
    table, index_name: str, now_iso: str
) -> List[Dict[str, Any]]:
    """Query the GSI for pending predictions due for verification.

    Args:
        table: boto3 DynamoDB Table resource
        index_name: GSI name (status-verification_date-index)
        now_iso: Current UTC time as ISO 8601 string

    Returns:
        List of GSI result items (may be empty).
    """
    items: List[Dict[str, Any]] = []
    query_kwargs = {
        "IndexName": index_name,
        "KeyConditionExpression": "#s = :pending AND verification_date <= :now",
        "ExpressionAttributeNames": {"#s": "status"},
        "ExpressionAttributeValues": {
            ":pending": "pending",
            ":now": now_iso,
        },
    }
    while True:
        response = table.query(**query_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return items


# ---------------------------------------------------------------------------
# Invocation client abstraction
# ---------------------------------------------------------------------------

class HttpInvoker:
    """Dev mode: HTTP POST to agentcore dev server."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    def invoke(self, prediction_id: str) -> Dict[str, Any]:
        payload = json.dumps({"prediction_id": prediction_id}).encode()
        req = Request(
            f"{self.endpoint}/invocations",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=600) as resp:
            body = resp.read().decode()
        return json.loads(body)


class AgentCoreInvoker:
    """Production: uses AgentCoreRuntimeClient."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.client = boto3.client("bedrock-agent-runtime")

    def invoke(self, prediction_id: str) -> Dict[str, Any]:
        response = self.client.invoke_agent(
            agentId=self.agent_id,
            inputText=json.dumps({"prediction_id": prediction_id}),
        )
        # Parse the agent response
        completion = response.get("completion", "")
        if isinstance(completion, str):
            return json.loads(completion)
        # Handle streaming response
        chunks = []
        for event in completion:
            if "chunk" in event:
                chunks.append(
                    event["chunk"].get("bytes", b"").decode()
                )
        return json.loads("".join(chunks))


def build_invocation_client():
    """Factory: returns HttpInvoker or AgentCoreInvoker based on env vars."""
    endpoint = os.environ.get("VERIFICATION_AGENT_ENDPOINT")
    if endpoint:
        logger.info(f"Using HttpInvoker → {endpoint}")
        return HttpInvoker(endpoint)

    agent_id = os.environ.get("VERIFICATION_AGENT_ID")
    if agent_id:
        logger.info(f"Using AgentCoreInvoker → {agent_id}")
        return AgentCoreInvoker(agent_id)

    raise RuntimeError(
        "Configuration error: set VERIFICATION_AGENT_ENDPOINT (dev) "
        "or VERIFICATION_AGENT_ID (prod)"
    )


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context) -> Dict[str, Any]:
    """EventBridge-triggered scanner. Finds due predictions, invokes verifier."""
    summary = {
        "total_found": 0,
        "total_invoked": 0,
        "total_succeeded": 0,
        "total_failed": 0,
        "failures": [],
    }

    # Build invocation client (fails fast on missing config)
    try:
        client = build_invocation_client()
    except RuntimeError as e:
        logger.error(f"Configuration error: {e}")
        return {"statusCode": 500, "body": {"error": str(e)}}

    # Query GSI for due predictions
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(DYNAMODB_TABLE_NAME)
        items = query_due_predictions(table, GSI_NAME, now_iso)
    except Exception as e:
        logger.error(f"GSI query failed: {e}", exc_info=True)
        return {"statusCode": 500, "body": {"error": f"GSI query failed: {e}"}}

    summary["total_found"] = len(items)

    if not items:
        logger.info("Zero predictions due for verification.")
        return {"statusCode": 200, "body": summary}

    logger.info(f"Found {len(items)} predictions due for verification.")

    # Process each prediction sequentially
    for item in items:
        prediction_id = extract_prediction_id(item)
        if not prediction_id:
            logger.warning(f"Could not extract prediction_id from item: {item.get('PK')}")
            summary["total_failed"] += 1
            summary["failures"].append({
                "prediction_id": None,
                "error": f"Bad PK: {item.get('PK')}",
            })
            continue

        summary["total_invoked"] += 1
        try:
            response = client.invoke(prediction_id)
            status = response.get("status", "unknown")
            if status == "error":
                logger.warning(
                    f"Verification agent returned error for {prediction_id}: "
                    f"{response.get('error', 'unknown')}"
                )
                summary["total_failed"] += 1
                summary["failures"].append({
                    "prediction_id": prediction_id,
                    "error": response.get("error", "Agent returned error status"),
                })
            else:
                logger.info(
                    f"Verified {prediction_id}: "
                    f"verdict={response.get('verdict')}, "
                    f"confidence={response.get('confidence')}"
                )
                summary["total_succeeded"] += 1
        except Exception as e:
            logger.error(
                f"Invocation failed for {prediction_id}: {e}",
                exc_info=True,
            )
            summary["total_failed"] += 1
            summary["failures"].append({
                "prediction_id": prediction_id,
                "error": str(e),
            })

    logger.info(f"Scanner complete: {json.dumps(summary)}")
    return {"statusCode": 200, "body": summary}
