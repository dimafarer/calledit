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

DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-v4")
GSI_NAME = os.environ.get("GSI_NAME", "status-verification_date-index")

RECURRING_INTERVAL_SECONDS = {
    "every_scan": 0,
    "daily": 86400,
    "weekly": 604800,
}


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
# Mode-aware scheduling
# ---------------------------------------------------------------------------

def _seconds_since(iso_a: str, iso_b: str) -> float:
    """Return seconds between two ISO 8601 timestamps."""
    a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
    b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    return abs((b - a).total_seconds())


def should_invoke(item: dict, now_iso: str) -> tuple:
    """Determine whether to invoke the verification agent for this item.

    Returns (should_invoke: bool, reason: str).
    """
    mode = item.get("verification_mode", "immediate")
    verification_date = item.get("verification_date", "")

    if mode == "immediate":
        return True, "immediate mode"
    elif mode == "at_date":
        if now_iso >= verification_date:
            return True, "at_date: due"
        return False, "at_date: not yet due"
    elif mode == "before_date":
        return True, "before_date: periodic check"
    elif mode == "recurring":
        interval = item.get("recurring_interval", "daily")
        min_seconds = RECURRING_INTERVAL_SECONDS.get(interval, 86400)
        snapshots = item.get("verification_snapshots", [])
        if snapshots and min_seconds > 0:
            last_checked = snapshots[-1].get("checked_at", "")
            if last_checked and _seconds_since(last_checked, now_iso) < min_seconds:
                return False, f"recurring: last check too recent ({interval})"
        return True, "recurring: snapshot check"
    else:
        logger.warning(f"Unknown verification_mode: {mode}, treating as immediate")
        return True, f"unknown mode {mode}, defaulting to immediate"


def _append_verification_snapshot_inline(
    table, prediction_id: str, response: dict, checked_at: str,
    max_snapshots: int = 30,
) -> bool:
    """Append a verification snapshot for recurring predictions (inline scanner version).

    Uses DDB list_append. Prunes oldest if over max_snapshots.
    Does NOT change status from pending.
    """
    from decimal import Decimal

    def _to_decimal(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: _to_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_decimal(i) for i in obj]
        return obj

    snapshot = {
        "verdict": response.get("verdict", "inconclusive"),
        "confidence": _to_decimal(response.get("confidence", 0.0)),
        "evidence": _to_decimal(response.get("evidence", [])),
        "reasoning": response.get("reasoning", ""),
        "checked_at": checked_at,
    }
    try:
        table.update_item(
            Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"},
            UpdateExpression=(
                "SET verification_snapshots = list_append("
                "if_not_exists(verification_snapshots, :empty), :snap)"
            ),
            ExpressionAttributeValues={
                ":snap": [snapshot],
                ":empty": [],
            },
        )
        # Prune if over limit
        resp = table.get_item(
            Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"},
            ProjectionExpression="verification_snapshots",
        )
        snapshots = resp.get("Item", {}).get("verification_snapshots", [])
        if len(snapshots) > max_snapshots:
            trimmed = snapshots[-max_snapshots:]
            table.update_item(
                Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"},
                UpdateExpression="SET verification_snapshots = :trimmed",
                ExpressionAttributeValues={":trimmed": trimmed},
            )
        return True
    except Exception as e:
        logger.error(f"Snapshot append failed for {prediction_id}: {e}")
        return False


def handle_verification_result(
    table, prediction_id: str, response: dict, mode: str, now_iso: str,
) -> None:
    """Handle post-invocation logic based on verification mode.

    - recurring: append snapshot, keep status=pending
    - before_date + confirmed: let default status transition happen (agent already updated)
    - before_date + inconclusive before deadline: leave as pending (no action)
    - other modes: agent already handled status update
    """
    logger.info(
        f"handle_verification_result: prediction_id={prediction_id}, "
        f"verification_mode={mode}, verdict={response.get('verdict')}"
    )
    if mode == "recurring":
        max_snaps = 30  # default; could read from bundle if needed
        _append_verification_snapshot_inline(
            table, prediction_id, response, now_iso, max_snaps
        )
    elif mode == "before_date" and response.get("verdict") == "inconclusive":
        # Leave as pending for next scan cycle — no action needed
        logger.info(
            f"before_date inconclusive for {prediction_id}, leaving as pending"
        )
    else:
        # Default: verification agent already updated status via bundle_loader
        pass


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
    """Production: invokes AgentCore Runtime via HTTPS with SigV4 auth.

    The v4 verification agent runs on AgentCore Runtime, which uses a
    different API than Bedrock Agents (invoke_agent). AgentCore Runtime
    uses a REST endpoint with SigV4 signing.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.region = os.environ.get("AWS_REGION", "us-west-2")
        # Build the AgentCore Runtime ARN from the agent_id
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        runtime_arn = f"arn:aws:bedrock-agentcore:{self.region}:{account_id}:runtime/{agent_id}"
        # URL-encode the ARN for the endpoint
        from urllib.parse import quote
        encoded_arn = quote(runtime_arn, safe="")
        self.invoke_url = (
            f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            f"/runtimes/{encoded_arn}/invocations"
        )
        # Get credentials from Lambda execution role
        session = boto3.Session(region_name=self.region)
        self._credentials = session.get_credentials().get_frozen_credentials()

    def invoke(self, prediction_id: str) -> Dict[str, Any]:
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        import uuid
        import requests as http_requests

        payload = json.dumps({"prediction_id": prediction_id})
        session_id = str(uuid.uuid4())

        headers = {
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        aws_request = AWSRequest(
            method="POST",
            url=self.invoke_url,
            data=payload,
            headers=headers,
        )
        SigV4Auth(self._credentials, "bedrock-agentcore", self.region).add_auth(aws_request)

        response = http_requests.post(
            self.invoke_url,
            data=payload,
            headers=dict(aws_request.headers),
            timeout=600,
        )
        response.raise_for_status()

        result = response.json()
        if isinstance(result, str):
            result = json.loads(result)
        return result


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
        "total_skipped": 0,
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

    # Process each prediction sequentially with mode-aware dispatch
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

        # Fetch full bundle to get verification_mode, verification_snapshots, recurring_interval
        # (GSI projection may not include these fields)
        try:
            full_item_resp = table.get_item(
                Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"}
            )
            full_item = full_item_resp.get("Item", item)
        except Exception as e:
            logger.warning(
                f"Failed to fetch full bundle for {prediction_id}, "
                f"using GSI item: {e}"
            )
            full_item = item

        mode = full_item.get("verification_mode", "immediate")
        logger.info(f"Processing {prediction_id}: verification_mode={mode}")

        # Check if we should invoke based on mode
        invoke, reason = should_invoke(full_item, now_iso)
        if not invoke:
            logger.info(f"Skipping {prediction_id}: {reason}")
            summary["total_skipped"] += 1
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
                # Handle post-invocation logic based on mode
                handle_verification_result(
                    table, prediction_id, response, mode, now_iso
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
