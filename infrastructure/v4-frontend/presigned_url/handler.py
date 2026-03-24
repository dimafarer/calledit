"""
Presigned URL Lambda — Cognito JWT → presigned WSS URL for AgentCore Runtime.

API Gateway HTTP API validates the Cognito JWT before this Lambda runs.
We extract the user_id (sub claim), call generate_presigned_url(), and
return the wss:// URL to the frontend.
"""

import json
import logging
import os
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CREATION_AGENT_RUNTIME_ARN = os.environ["CREATION_AGENT_RUNTIME_ARN"]


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def extract_user_id(event: dict) -> str:
    """Extract user_id (sub) from API Gateway HTTP API JWT claims."""
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def lambda_handler(event, context):
    try:
        user_id = extract_user_id(event)
        logger.info(f"Generating presigned URL for user: {user_id}")
    except (KeyError, TypeError) as e:
        logger.error(f"Failed to extract user_id from JWT claims: {e}")
        return _response(401, {"error": "Invalid or missing JWT claims"})

    try:
        from bedrock_agentcore.runtime import AgentCoreRuntimeClient

        client = AgentCoreRuntimeClient(os.environ.get("AWS_REGION", "us-west-2"))
        session_id = str(uuid.uuid4())
        url = client.generate_presigned_url(
            runtime_arn=CREATION_AGENT_RUNTIME_ARN,
            session_id=session_id,
        )
        logger.info(f"Presigned URL generated for session: {session_id}")
        return _response(200, {"url": url, "session_id": session_id})

    except Exception as e:
        logger.error(f"generate_presigned_url failed: {e}", exc_info=True)
        return _response(502, {"error": f"Failed to generate presigned URL: {e}"})
