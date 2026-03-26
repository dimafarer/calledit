"""Verification Agent Backend — invokes the deployed verification agent via HTTPS with SigV4.

The verification agent uses SigV4 auth (the AgentCore default) — unlike the
creation agent which uses JWT for browser WebSocket connections (Decision 121).
The eval runner runs from a machine with AWS credentials, so SigV4 is the
natural auth method here.

The verification agent returns a synchronous JSON response (not SSE streaming).
Response body may be double-encoded: outer JSON is a string containing another JSON string.
"""

import json
import logging
import uuid

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
import requests as http_requests

logger = logging.getLogger(__name__)

VERIFICATION_AGENT_ARN = (
    "arn:aws:bedrock-agentcore:us-west-2:894249332178:"
    "runtime/calleditv4_verification_Agent-77DiT7GHdH"
)
EVAL_TABLE_NAME = "calledit-v4-eval"
AWS_REGION = "us-west-2"


class VerificationBackend:
    """Invokes the deployed v4 verification agent via HTTPS with SigV4."""

    def __init__(
        self,
        region: str = None,
        runtime_arn: str = None,
    ):
        self.region = region or AWS_REGION
        self.runtime_arn = runtime_arn or VERIFICATION_AGENT_ARN
        encoded_arn = http_requests.utils.quote(self.runtime_arn, safe="")
        self.invoke_url = (
            f"https://bedrock-agentcore.{self.region}.amazonaws.com"
            f"/runtimes/{encoded_arn}/invocations"
        )
        # Get credentials from default chain (AWS CLI config, env vars, etc.)
        session = boto3.Session(region_name=self.region)
        self._credentials = session.get_credentials().get_frozen_credentials()

    def set_token(self, token: str) -> None:
        """No-op for API compatibility with creation backend pattern.

        The verification backend uses SigV4, not JWT. This method exists
        so the eval runner can call set_token() without branching.
        """
        pass  # SigV4 uses AWS credentials, not bearer tokens

    def invoke(
        self,
        prediction_id: str,
        table_name: str = None,
        case_id: str = "",
    ) -> dict:
        """Invoke verification agent and return verdict dict.

        Args:
            prediction_id: The prediction to verify.
            table_name: DDB table override. Pass EVAL_TABLE_NAME for golden mode,
                        None for ddb mode (agent uses its own env var).
            case_id: For error reporting.

        Returns:
            dict with keys: verdict, confidence, status, prediction_id

        Raises:
            RuntimeError: On HTTP error, parse failure, or missing fields.
        """
        payload = {"prediction_id": prediction_id}
        if table_name:
            payload["table_name"] = table_name

        body = json.dumps(payload)
        session_id = str(uuid.uuid4())

        # Build SigV4-signed request
        headers = {
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        aws_request = AWSRequest(
            method="POST",
            url=self.invoke_url,
            data=body,
            headers=headers,
        )
        SigV4Auth(self._credentials, "bedrock-agentcore", self.region).add_auth(aws_request)

        try:
            response = http_requests.post(
                self.invoke_url,
                data=body,
                headers=dict(aws_request.headers),
                timeout=300,
            )
            response.raise_for_status()
        except http_requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"Verification agent invocation failed for case '{case_id}' "
                f"(prediction_id={prediction_id}): "
                f"HTTP {response.status_code} — {response.text[:500]}"
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Verification agent invocation failed for case '{case_id}' "
                f"(prediction_id={prediction_id}): {e}"
            ) from e

        result = self._parse_response(response, prediction_id, case_id)

        # The handler only returns a summary. Read full verdict (evidence + reasoning)
        # from DDB where update_bundle_with_verdict() wrote it.
        if table_name:
            ddb_data = self._read_full_verdict_from_ddb(prediction_id, table_name)
            if ddb_data.get("evidence"):
                result["evidence"] = ddb_data["evidence"]
            if ddb_data.get("reasoning"):
                result["reasoning"] = ddb_data["reasoning"]

        return result

    def _read_full_verdict_from_ddb(self, prediction_id: str, table_name: str) -> dict:
        """Read the full verdict (with evidence + reasoning) from DDB after agent invocation.

        The handler only returns a summary (verdict, confidence, status, prediction_id).
        The full VerificationResult (including evidence list and reasoning) is written
        to DDB by update_bundle_with_verdict(). We read it back here.
        """
        try:
            ddb = boto3.resource("dynamodb", region_name=self.region)
            table = ddb.Table(table_name)
            response = table.get_item(
                Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"}
            )
            item = response.get("Item", {})
            evidence = item.get("evidence", [])
            # Convert Decimal values back to float for JSON serialization
            evidence = json.loads(json.dumps(evidence, default=str))
            return {
                "evidence": evidence,
                "reasoning": item.get("reasoning"),
            }
        except Exception as e:
            logger.warning(f"Failed to read full verdict from DDB for {prediction_id}: {e}")
            return {"evidence": [], "reasoning": None}

    def _parse_response(self, response, prediction_id: str, case_id: str) -> dict:
        """Parse the synchronous JSON response.

        The verification agent may return a double-encoded JSON string.
        """
        try:
            outer = response.json()
            result = json.loads(outer) if isinstance(outer, str) else outer
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(
                f"Failed to parse verification agent response for case '{case_id}' "
                f"(prediction_id={prediction_id}): {e}"
            ) from e

        if "verdict" not in result:
            # Check if it's an error response
            if "error" in result:
                raise RuntimeError(
                    f"Verification agent returned error for case '{case_id}' "
                    f"(prediction_id={prediction_id}): {result['error']}"
                )
            raise RuntimeError(
                f"Missing 'verdict' field in verification agent response "
                f"for case '{case_id}' (prediction_id={prediction_id}): {result}"
            )

        return {
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "status": result.get("status"),
            "prediction_id": result.get("prediction_id", prediction_id),
            "reasoning": result.get("reasoning"),
            "evidence": result.get("evidence", []),
        }
