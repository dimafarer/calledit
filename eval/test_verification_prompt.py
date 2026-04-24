"""Quick smoke test for verification agent prompt changes.

Loads a prediction bundle from DDB, builds the user message exactly like
the deployed handler, creates a local Strands Agent with the prompt, and
invokes it. No AgentCore runtime needed — just Bedrock + tools.

Usage:
    source .env
    PYTHONPATH=. /home/wsluser/projects/calledit/venv/bin/python eval/test_verification_prompt.py

Defaults to base-004 (S&P 500) which returns "No prediction statement" on the current prompt.
"""

import json
import os
import sys
import boto3
from decimal import Decimal

# Ensure region
if not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

from strands import Agent
from strands.models.bedrock import BedrockModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PREDICTION_ID = os.environ.get(
    "TEST_PREDICTION_ID", "pred-181e27d7-2ead-4692-96e2-91419fcf6432"
)
TABLE_NAME = os.environ.get("TEST_TABLE", "calledit-v4-eval")
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def load_bundle(prediction_id: str, table_name: str) -> dict:
    ddb = boto3.resource("dynamodb", region_name="us-west-2")
    table = ddb.Table(table_name)
    resp = table.get_item(Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"})
    item = resp.get("Item")
    if not item:
        raise ValueError(f"Bundle not found: {prediction_id}")
    item.pop("PK", None)
    item.pop("SK", None)
    return decimal_to_float(item)


def build_user_message(bundle: dict) -> str:
    """Exact copy of calleditv4-verification/src/main.py _build_user_message."""
    parsed_claim = bundle.get("parsed_claim", {})
    plan = bundle.get("verification_plan", {})
    verification_mode = bundle.get("verification_mode", "immediate")
    return (
        f"PREDICTION: {parsed_claim.get('statement', '')}\n"
        f"VERIFICATION DATE: {parsed_claim.get('verification_date', '')}\n"
        f"VERIFICATION MODE: {verification_mode}\n\n"
        f"VERIFICATION PLAN:\n"
        f"Sources: {json.dumps(plan.get('sources', []))}\n"
        f"Criteria: {json.dumps(plan.get('criteria', []))}\n"
        f"Steps: {json.dumps(plan.get('steps', []))}\n\n"
        f"Execute this verification plan now."
    )


def fetch_prompt() -> str:
    """Fetch the verification_executor prompt from Bedrock Prompt Management."""
    client = boto3.client("bedrock-agent")
    resp = client.get_prompt(promptIdentifier="ZQQNZIP6SK", promptVersion="2")
    return resp["variants"][0]["templateConfiguration"]["text"]["text"]


def main():
    import sys as _sys
    def p(msg):
        print(msg, flush=True)

    p(f"Loading bundle: {PREDICTION_ID} from {TABLE_NAME}")
    bundle = load_bundle(PREDICTION_ID, TABLE_NAME)

    parsed = bundle.get("parsed_claim", {})
    p(f"  statement: {parsed.get('statement', 'MISSING')}")
    p(f"  verification_date: {parsed.get('verification_date', 'MISSING')}")
    p(f"  verification_mode: {bundle.get('verification_mode', 'MISSING')}")
    p(f"  status: {bundle.get('status', 'MISSING')}")

    user_message = build_user_message(bundle)
    p(f"\n--- User message ({len(user_message)} chars) ---")
    p(user_message[:500])
    p("---\n")

    p("Fetching prompt from Bedrock Prompt Management...")
    system_prompt = fetch_prompt()
    p(f"  Prompt length: {len(system_prompt)} chars")

    # Use brave_web_search + current_time (no Browser — faster for smoke test)
    brave_path = os.path.join("/home/wsluser/projects/calledit",
                              "calleditv4-verification/src")
    if brave_path not in sys.path:
        sys.path.insert(0, brave_path)
    from brave_search import brave_web_search
    from strands_tools.current_time import current_time

    tools = [brave_web_search, current_time]
    p(f"  Tools: {[t.__name__ if hasattr(t, '__name__') else str(t) for t in tools]}")

    p("\nInvoking Strands Agent (this may take 30-120s)...")
    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(model=model, system_prompt=system_prompt, tools=tools)

    result = agent(user_message)
    response_text = str(result)

    p(f"\n--- Agent response ({len(response_text)} chars) ---")
    p(response_text[:2000])
    p("---")


if __name__ == "__main__":
    main()
