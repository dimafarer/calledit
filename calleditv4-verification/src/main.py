"""
CalledIt v4 — Verification Agent on AgentCore

Synchronous batch handler. Receives prediction_id, loads bundle from DDB,
gathers evidence using Browser + Code Interpreter, produces a structured
verdict (confirmed/refuted/inconclusive), updates DDB.

This is the second AgentCore runtime (Decision 86). It runs at
verification_date, triggered by EventBridge (V4-5b). No user interaction,
no streaming, no memory.

Never raises unhandled exceptions — returns inconclusive on any error.
"""

import json
import logging
import os
import sys

# Ensure AWS region is set for all boto3 calls in AgentCore Runtime
if not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

import boto3
from bedrock_agentcore import RequestContext
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools.browser import AgentCoreBrowser
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.current_time import current_time

sys.path.insert(0, os.path.dirname(__file__))

from models import VerificationResult
from bundle_loader import load_bundle_from_ddb, update_bundle_with_verdict
from prompt_client import fetch_prompt, get_prompt_version_manifest

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-v4")

browser_tool = AgentCoreBrowser()
code_interpreter_tool = AgentCoreCodeInterpreter()
TOOLS = [browser_tool.browser, code_interpreter_tool.code_interpreter, current_time]


def _make_inconclusive(reasoning: str) -> VerificationResult:
    """Build a standard inconclusive result for error cases."""
    return VerificationResult(
        verdict="inconclusive",
        confidence=0.0,
        evidence=[],
        reasoning=reasoning,
    )


def _build_user_message(bundle: dict) -> str:
    """Construct the user message from bundle fields."""
    parsed_claim = bundle.get("parsed_claim", {})
    plan = bundle.get("verification_plan", {})
    return (
        f"PREDICTION: {parsed_claim.get('statement', '')}\n"
        f"VERIFICATION DATE: {parsed_claim.get('verification_date', '')}\n\n"
        f"VERIFICATION PLAN:\n"
        f"Sources: {json.dumps(plan.get('sources', []))}\n"
        f"Criteria: {json.dumps(plan.get('criteria', []))}\n"
        f"Steps: {json.dumps(plan.get('steps', []))}\n\n"
        f"Execute this verification plan now."
    )


def _run_verification(
    prediction_id: str, bundle: dict
) -> VerificationResult:
    """Run the Strands agent. Never raises — returns inconclusive on error."""
    try:
        system_prompt = fetch_prompt("verification_executor")
    except Exception as e:
        logger.error(f"Prompt fetch failed: {e}", exc_info=True)
        return _make_inconclusive(f"Prompt Management unavailable: {e}")

    try:
        user_message = _build_user_message(bundle)
        model = BedrockModel(model_id=MODEL_ID)
        agent = Agent(model=model, system_prompt=system_prompt, tools=TOOLS)
        result = agent(
            user_message, structured_output_model=VerificationResult
        )
        return result.structured_output
    except Exception as e:
        logger.error(
            f"Agent invocation failed for {prediction_id}: {e}",
            exc_info=True,
        )
        return _make_inconclusive(f"Agent invocation error: {e}")


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> str:
    """Verification agent entrypoint — receives prediction_id, returns verdict JSON."""
    prediction_id = payload.get("prediction_id")
    if not prediction_id:
        return json.dumps({
            "prediction_id": None,
            "status": "error",
            "error": "Missing 'prediction_id' in payload",
        })

    # Optional table_name override for eval isolation (Decision 130)
    table_name = payload.get("table_name", DYNAMODB_TABLE_NAME)

    # Zone 1: Load bundle from DDB
    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(table_name)
        bundle = load_bundle_from_ddb(table, prediction_id)
    except Exception as e:
        logger.error(
            f"DDB load failed for {prediction_id}: {e}", exc_info=True
        )
        return json.dumps({
            "prediction_id": prediction_id,
            "status": "error",
            "error": f"DDB load failed: {e}",
        })

    if bundle is None:
        return json.dumps({
            "prediction_id": prediction_id,
            "status": "error",
            "error": "Prediction bundle not found",
        })

    if bundle.get("status") != "pending":
        return json.dumps({
            "prediction_id": prediction_id,
            "status": "error",
            "error": f"Prediction already processed "
            f"(status={bundle.get('status')})",
        })

    # Zone 2: Run verification (never raises)
    result = _run_verification(prediction_id, bundle)

    # Zone 3: Update DDB (best-effort)
    prompt_versions = get_prompt_version_manifest()
    try:
        update_bundle_with_verdict(
            table, prediction_id, result, prompt_versions
        )
    except Exception as e:
        logger.error(
            f"DDB update failed for {prediction_id}: {e}", exc_info=True
        )

    # Return verdict summary
    new_status = (
        "verified"
        if result.verdict in ("confirmed", "refuted")
        else "inconclusive"
    )
    return json.dumps({
        "prediction_id": prediction_id,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "status": new_status,
    })


if __name__ == "__main__":
    app.run()
