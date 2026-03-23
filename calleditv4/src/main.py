"""
CalledIt v4 — Prediction Creation Agent on AgentCore

Entrypoint for the creation agent. Supports two modes:
1. Creation flow: prediction_text → 3-turn creation → bundle → DDB save → return
2. Simple prompt: prompt → agent response (V4-1/V4-2 backward compatibility)

The creation flow uses a single Strands Agent with 3 sequential prompt turns:
  Turn 1 (Parse): Extract claim, resolve dates with timezone awareness
  Turn 2 (Plan): Build verification plan with sources, criteria, steps
  Turn 3 (Review): Score verifiability + identify assumptions for clarification

Each turn uses Strands structured_output_model for type-safe Pydantic extraction.
Conversation history accumulates naturally across agent() calls on the same instance.

Decisions:
  94 — Single agent, multi-turn prompts (originally 4, now 3 per Decision 99)
  98 — No fallbacks in dev, graceful fallback in production
  99 — 3 turns not 4 (merged score + review into plan-reviewer)
  100 — LLM-native date resolution (current_time tool + Code Interpreter)
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

from bedrock_agentcore import RequestContext
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools.browser import AgentCoreBrowser
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.current_time import current_time

import boto3

# Add src to path for sibling module imports (models, bundle, prompt_client)
sys.path.insert(0, os.path.dirname(__file__))

from models import ParsedClaim, PlanReview, VerificationPlan
from prompt_client import fetch_prompt, get_prompt_version_manifest
from bundle import (
    build_bundle,
    format_ddb_item,
    generate_prediction_id,
    serialize_bundle,
)

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-db")

# V4-1/V4-2 simple prompt mode system prompt (backward compatibility)
SIMPLE_PROMPT_SYSTEM = (
    "You are the CalledIt v4 agent. "
    "You have access to two tools:\n"
    "1. Browser — navigate URLs, search the web, extract content from web pages. "
    "Use this when you need to look up current information, verify facts, or read web content.\n"
    "2. Code Interpreter — execute Python code in a secure sandbox. "
    "Use this for calculations, date math, data analysis, or any task that benefits from running code.\n"
    "Use the appropriate tool when the user's request would benefit from it. "
    "Respond helpfully to any message."
)

# Tool instances — lightweight config objects, no connections until agent uses them
browser_tool = AgentCoreBrowser()
code_interpreter_tool = AgentCoreCodeInterpreter()

# 3 tools: Browser, Code Interpreter, current_time
# current_time gives the agent awareness of "now" + server timezone (Decision 100)
TOOLS = [browser_tool.browser, code_interpreter_tool.code_interpreter, current_time]


def _get_tool_manifest() -> str:
    """Build a tool manifest string describing available tools.

    This is substituted into the verification planner prompt via {{tool_manifest}}.
    The agent also sees the tool schemas from Strands automatically, but this
    human-readable description helps the agent reference tools by name in the plan.
    """
    return (
        "- Browser: navigate URLs, search the web, extract content from pages\n"
        "- Code Interpreter: execute Python code for calculations, "
        "date math, data analysis\n"
        "- current_time: get the current date and time with timezone info"
    )


def _run_creation_flow(prediction_text: str, user_id: str) -> str:
    """Execute the 3-turn creation flow and return the bundle as JSON.

    This is the core business logic of V4-3a. A single Strands Agent processes
    3 sequential prompt turns. Each turn:
    1. Fetches its prompt from Bedrock Prompt Management (with variable substitution)
    2. Calls agent() with a turn-specific Pydantic structured_output_model
    3. Gets back a validated, typed object via result.structured_output

    The agent sees its full conversation history at each step because we reuse
    the same Agent instance. Turn 2 sees Turn 1's context, Turn 3 sees both.
    This is the "no silo problem" advantage of the multi-turn approach (Decision 94).
    """
    prediction_id = generate_prediction_id()
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    tool_manifest = _get_tool_manifest()

    # Create a single agent — no system prompt. Per-turn prompts from Prompt
    # Management provide all instructions. Tools are available for all turns
    # but most useful in Turn 1 (current_time for date resolution) and
    # Turn 2 (Browser/Code Interpreter for plan-aware verification).
    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(model=model, tools=TOOLS)

    # ------------------------------------------------------------------
    # Turn 1: Parse — extract claim, resolve dates with timezone awareness
    # The prompt instructs the agent to call current_time first to get the
    # server timezone, then use it as the default for time-sensitive predictions.
    # ------------------------------------------------------------------
    parse_prompt = fetch_prompt(
        "prediction_parser",
        variables={"current_date": current_date},
    )
    parse_input = f"{parse_prompt}\n\nPrediction: {prediction_text}"
    parse_result = agent(parse_input, structured_output_model=ParsedClaim)
    parsed_claim = parse_result.structured_output

    # ------------------------------------------------------------------
    # Turn 2: Plan — build verification plan referencing available tools
    # The agent already has Turn 1 in its conversation history, so it knows
    # the parsed claim, verification date, and date reasoning.
    # ------------------------------------------------------------------
    plan_prompt = fetch_prompt(
        "verification_planner",
        variables={"tool_manifest": tool_manifest},
    )
    plan_result = agent(plan_prompt, structured_output_model=VerificationPlan)
    verification_plan = plan_result.structured_output

    # ------------------------------------------------------------------
    # Turn 3: Review — score verifiability AND identify assumptions
    # The agent has Turns 1-2 in history. It evaluates its own plan across
    # 5 dimensions and flags timezone/assumption issues for clarification.
    # This was originally 2 separate turns (Decision 94) but merged into
    # one (Decision 99) because scoring and reviewing are the same analysis.
    # ------------------------------------------------------------------
    review_prompt = fetch_prompt("plan_reviewer")
    review_result = agent(review_prompt, structured_output_model=PlanReview)
    plan_review = review_result.structured_output

    # ------------------------------------------------------------------
    # Assemble the prediction bundle from all 3 turn outputs
    # ------------------------------------------------------------------
    bundle = build_bundle(
        prediction_id=prediction_id,
        user_id=user_id,
        raw_prediction=prediction_text,
        parsed_claim=parsed_claim.model_dump(),
        verification_plan=verification_plan.model_dump(),
        verifiability_score=plan_review.verifiability_score,
        verifiability_reasoning=plan_review.verifiability_reasoning,
        reviewable_sections=[s.model_dump() for s in plan_review.reviewable_sections],
        prompt_versions=get_prompt_version_manifest(),
    )

    # ------------------------------------------------------------------
    # Save to DynamoDB — failure doesn't block the response (Req 4.5)
    # The bundle is returned to the caller regardless of save success.
    # ------------------------------------------------------------------
    try:
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(DYNAMODB_TABLE_NAME)
        table.put_item(Item=format_ddb_item(bundle))
    except Exception as e:
        logger.error(f"DDB save failed for {prediction_id}: {e}", exc_info=True)
        bundle["save_error"] = str(e)

    return serialize_bundle(bundle)


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> str:
    """Agent entrypoint — routes to creation flow or simple prompt mode.

    Routing logic:
    - payload has "prediction_text" → 3-turn creation flow → PredictionBundle JSON
    - payload has "prompt" (no prediction_text) → V4-1/V4-2 simple mode → string
    - neither field → structured error JSON
    """
    if "prediction_text" in payload:
        user_id = payload.get("user_id", "anonymous")
        try:
            return _run_creation_flow(payload["prediction_text"], user_id)
        except Exception as e:
            logger.error(f"Creation flow failed: {e}", exc_info=True)
            return json.dumps({
                "error": f"Creation flow failed: {str(e)}",
            })

    if "prompt" in payload:
        try:
            model = BedrockModel(model_id=MODEL_ID)
            agent = Agent(
                model=model, system_prompt=SIMPLE_PROMPT_SYSTEM, tools=TOOLS
            )
            response = agent(payload["prompt"])
            return str(response)
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}", exc_info=True)
            return json.dumps({"error": f"Agent invocation failed: {str(e)}"})

    return json.dumps(
        {"error": "Missing 'prediction_text' or 'prompt' field in payload"}
    )


if __name__ == "__main__":
    app.run()
