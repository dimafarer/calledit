"""AgentCore Backend — invokes the deployed creation agent via HTTPS with JWT.

Uses direct HTTPS requests (not boto3 SDK) because the agent is configured
for JWT bearer token auth (Decision 121). The boto3 SDK uses SigV4 which
is incompatible with JWT-configured agents.

Per AWS docs: "If you plan on integrating your agent with OAuth, you can't
use the AWS SDK to call InvokeAgentRuntime. Instead, make a HTTPS request."

Decision 96: No mocks — this hits the real deployed agent.
"""

import json
import logging
import os
import uuid

import boto3
import requests

logger = logging.getLogger(__name__)

CREATION_AGENT_ARN = (
    "arn:aws:bedrock-agentcore:us-west-2:894249332178:"
    "runtime/calleditv4_Agent-AJiwpKBxRW"
)
CREATION_AGENT_MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Cognito config (from calledit-backend stack)
COGNITO_USER_POOL_ID = os.environ.get(
    "COGNITO_USER_POOL_ID", "us-west-2_GOEwUjJtv"
)
COGNITO_CLIENT_ID = os.environ.get(
    "COGNITO_CLIENT_ID", "753gn25jle081ajqabpd4lbin9"
)
COGNITO_USERNAME = os.environ.get("COGNITO_USERNAME", "")
COGNITO_PASSWORD = os.environ.get("COGNITO_PASSWORD", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")


def get_cognito_token(
    username: str = None,
    password: str = None,
    client_id: str = None,
    region: str = None,
) -> str:
    """Get a Cognito access token via USER_PASSWORD_AUTH flow.

    Args:
        username: Cognito username (defaults to COGNITO_USERNAME env var)
        password: Cognito password (defaults to COGNITO_PASSWORD env var)
        client_id: Cognito app client ID (defaults to COGNITO_CLIENT_ID env var)
        region: AWS region (defaults to AWS_REGION env var)

    Returns:
        Access token string.

    Raises:
        RuntimeError: If authentication fails.
    """
    username = username or COGNITO_USERNAME
    password = password or COGNITO_PASSWORD
    client_id = client_id or COGNITO_CLIENT_ID
    region = region or AWS_REGION

    if not username or not password:
        raise RuntimeError(
            "Cognito credentials required. Set COGNITO_USERNAME and "
            "COGNITO_PASSWORD environment variables, or pass them directly."
        )

    cognito = boto3.client("cognito-idp", region_name=region)
    try:
        response = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        token = response["AuthenticationResult"]["AccessToken"]
        logger.info("Cognito token obtained successfully")
        return token
    except Exception as e:
        raise RuntimeError(f"Cognito authentication failed: {e}") from e


class AgentCoreBackend:
    """Invokes the deployed v4 creation agent via HTTPS with JWT bearer token."""

    def __init__(
        self,
        region: str = None,
        runtime_arn: str = None,
        bearer_token: str = None,
        table_name: str = None,
    ):
        self.region = region or AWS_REGION
        self.runtime_arn = runtime_arn or CREATION_AGENT_ARN
        self.bearer_token = bearer_token
        self.table_name = table_name  # Optional DDB table override for eval isolation
        # Build the HTTPS endpoint URL
        encoded_arn = requests.utils.quote(self.runtime_arn, safe="")
        self.invoke_url = (
            f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            f"/runtimes/{encoded_arn}/invocations"
        )

    def invoke(self, prediction_text: str, case_id: str = "") -> dict:
        """Invoke creation agent and return the prediction bundle.

        Args:
            prediction_text: The raw prediction text to process.
            case_id: Eval case id for error reporting.

        Returns:
            dict with keys: parsed_claim, verification_plan, plan_review,
                           prompt_versions, prediction_id

        Raises:
            RuntimeError: If flow_complete event is missing or invocation fails.
        """
        if not self.bearer_token:
            raise RuntimeError(
                "No bearer token set. Call set_token() or pass bearer_token "
                "to constructor. Use get_cognito_token() to obtain one."
            )

        payload = {
            "prediction_text": prediction_text,
            "user_id": "eval-runner",
            "timezone": "UTC",
        }
        if self.table_name:
            payload["table_name"] = self.table_name

        payload = json.dumps(payload)

        session_id = str(uuid.uuid4())

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        try:
            response = requests.post(
                self.invoke_url,
                data=payload,
                headers=headers,
                stream=True,
                timeout=300,  # 5 min timeout for agent processing
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"AgentCore invocation failed for case '{case_id}': "
                f"HTTP {response.status_code} — {response.text[:500]}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"AgentCore invocation failed for case '{case_id}': {e}"
            ) from e

        return self._parse_stream(response, case_id)

    def set_token(self, token: str) -> None:
        """Set the bearer token for subsequent invocations."""
        self.bearer_token = token

    def _parse_stream(self, response, case_id: str) -> dict:
        """Parse the SSE streaming response and extract the flow_complete bundle.

        AgentCore returns double-encoded SSE: data: "{\"type\": ...}"
        First json.loads returns a string, second json.loads returns the dict.
        """
        bundle = None

        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                decoded = decoded[6:]
            try:
                parsed = json.loads(decoded)
                # Handle double-encoding: if parsed is a string, parse again
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                if isinstance(parsed, dict) and parsed.get("type") == "flow_complete":
                    bundle = parsed.get("data", {})
                    break
            except json.JSONDecodeError:
                continue

        if bundle is None:
            raise RuntimeError(
                f"No flow_complete event in agent response for case "
                f"'{case_id}'"
            )

        return self._extract_bundle(bundle)

    @staticmethod
    def _extract_bundle(bundle: dict) -> dict:
        """Extract structured fields from the raw prediction bundle."""
        return {
            "parsed_claim": bundle.get("parsed_claim", {}),
            "verification_plan": bundle.get("verification_plan", {}),
            "plan_review": {
                "verifiability_score": bundle.get("verifiability_score"),
                "verifiability_reasoning": bundle.get(
                    "verifiability_reasoning"
                ),
                "reviewable_sections": bundle.get(
                    "reviewable_sections", []
                ),
                "score_tier": bundle.get("score_tier"),
                "score_label": bundle.get("score_label"),
                "score_guidance": bundle.get("score_guidance"),
                "dimension_assessments": bundle.get(
                    "dimension_assessments", []
                ),
            },
            "prompt_versions": bundle.get("prompt_versions", {}),
            "prediction_id": bundle.get("prediction_id"),
            "raw_bundle": bundle,
        }
