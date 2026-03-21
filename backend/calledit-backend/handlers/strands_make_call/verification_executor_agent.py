"""
Verification Executor Agent for Prediction Verification System (Spec B1)

This agent receives a verification plan (from the Verification Builder) and
executes it by invoking MCP tools to gather evidence, evaluate it against
criteria, and produce a structured verification outcome.

Key difference from other agents: this agent receives actual MCP tool objects
via Agent(tools=[...]) for direct invocation, rather than just a tool manifest
string in its system prompt. The executor *uses* tools, while other agents
only *reference* them.

Following Strands best practices:
- Single responsibility (verification execution only)
- Focused system prompt (~25 lines)
- Explicit model specification
- Direct MCP tool invocation via Agent(tools=[...])

References:
  - Decision 74: Verification pipeline roadmap
  - Decision 75: Spec B split (B1 agent, B2 triggers, B3 eval)
  - Decision 76: Two-mode verification trigger
"""

import json
import logging
from datetime import datetime, timezone

from strands import Agent

logger = logging.getLogger(__name__)


VERIFICATION_EXECUTOR_SYSTEM_PROMPT = """You are a verification executor. You receive a verification plan and execute it using your available tools to determine whether a prediction is true or false.

PROCESS:
1. Read the verification plan (prediction, criteria, sources, steps)
2. Execute each step by invoking the appropriate tool (brave_web_search, fetch, etc.)
3. Record what each tool returned as evidence
4. Evaluate the gathered evidence against each criterion
5. Determine the verdict: confirmed, refuted, or inconclusive

VERDICT RULES:
- confirmed: Evidence clearly supports the prediction meeting ALL criteria
- refuted: Evidence clearly shows the prediction failed one or more criteria
- inconclusive: Insufficient or contradictory evidence to make a determination

CONFIDENCE:
- 0.9-1.0: Strong, unambiguous evidence from multiple sources
- 0.7-0.8: Good evidence from at least one reliable source
- 0.5-0.6: Partial evidence, some criteria unclear
- 0.1-0.4: Weak evidence, mostly reasoning-based

If a tool call fails, note the failure in evidence and continue with remaining steps.
If no tools are available, return inconclusive with reasoning explaining the limitation.

Return ONLY the raw JSON object. No markdown code blocks, no backticks, no explanation text before or after the JSON. The first character of your response must be { and the last must be }.

{
    "status": "confirmed|refuted|inconclusive",
    "confidence": 0.0,
    "evidence": [
        {"source": "tool or URL used", "content": "relevant extracted content", "relevance": "how this relates to criteria"}
    ],
    "reasoning": "explanation of how evidence maps to criteria and why this verdict was chosen",
    "tools_used": ["tool_name_1", "tool_name_2"]
}
"""


USER_PROMPT_TEMPLATE = """PREDICTION: __PREDICTION_STATEMENT__
CATEGORY: __VERIFIABLE_CATEGORY__

VERIFICATION PLAN:
Sources: __SOURCES__
Criteria: __CRITERIA__
Steps: __STEPS__

Execute this verification plan. Use your tools to gather evidence, then evaluate the evidence against each criterion to determine the verdict."""


def _make_inconclusive(reasoning: str) -> dict:
    """Build a standard inconclusive outcome."""
    return {
        "status": "inconclusive",
        "confidence": 0.0,
        "evidence": [],
        "reasoning": reasoning,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "tools_used": [],
    }


def _validate_outcome(raw: dict) -> dict:
    """Validate and normalize a parsed Verification_Outcome dict.

    Ensures all required fields exist with correct types. Applies defensive
    defaults so Property 1 (structural validity) holds even if the agent
    produces slightly malformed output.
    """
    VALID_STATUSES = {"confirmed", "refuted", "inconclusive"}

    status = raw.get("status", "inconclusive")
    if status not in VALID_STATUSES:
        status = "inconclusive"

    confidence = raw.get("confidence", 0.0)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    evidence = raw.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []
    validated_evidence = []
    for item in evidence:
        if isinstance(item, dict):
            validated_evidence.append({
                "source": str(item.get("source", "")),
                "content": str(item.get("content", "")),
                "relevance": str(item.get("relevance", "")),
            })

    reasoning = raw.get("reasoning", "")
    if not isinstance(reasoning, str) or not reasoning:
        reasoning = str(reasoning) if reasoning else "No reasoning provided"

    tools_used = raw.get("tools_used", [])
    if not isinstance(tools_used, list):
        tools_used = []
    tools_used = [str(t) for t in tools_used]

    return {
        "status": status,
        "confidence": confidence,
        "evidence": validated_evidence,
        "reasoning": reasoning,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "tools_used": tools_used,
    }


def create_verification_executor_agent(model_id: str = None) -> Agent:
    """Create the Verification Executor Agent.

    Unlike other agent factories that accept tool_manifest: str, this factory
    obtains actual MCP tool objects from mcp_manager.get_mcp_tools() and passes
    them to Agent(tools=[...]). The executor invokes tools directly, not just
    reasons about them.

    Args:
        model_id: Optional model override. If None, uses Claude Sonnet 4 via Bedrock.

    Returns:
        Configured Verification Executor Agent with MCP tools wired.
    """
    try:
        from mcp_manager import mcp_manager
        tools = mcp_manager.get_mcp_tools()
    except Exception as e:
        logger.warning(f"MCP Manager unavailable, operating in reasoning-only mode: {e}")
        tools = []

    agent = Agent(
        name="verification_executor",
        model=model_id or "us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=VERIFICATION_EXECUTOR_SYSTEM_PROMPT,
        tools=tools,
    )

    mode = f"{len(tools)} MCP tools" if tools else "reasoning-only mode"
    logger.info(f"Verification Executor Agent created with {mode}")
    return agent


def run_verification(prediction_record: dict) -> dict:
    """Execute verification for a prediction record.

    Extracts the verification plan, builds a user prompt, invokes the executor
    agent, and parses the response. Never raises — returns inconclusive on any error.

    Args:
        prediction_record: A dict containing at minimum:
            - prediction_statement (str)
            - verification_method (dict with source, criteria, steps)
            - verifiable_category (str)

    Returns:
        A Verification_Outcome dict with status, confidence, evidence,
        reasoning, verified_at, and tools_used.
    """
    try:
        # Guard against non-dict input
        if not isinstance(prediction_record, dict):
            return _make_inconclusive("Invalid input: prediction_record is not a dict")

        # Extract fields with safe defaults
        prediction_statement = str(prediction_record.get("prediction_statement", ""))
        verifiable_category = str(prediction_record.get("verifiable_category", "unknown"))
        verification_method = prediction_record.get("verification_method")

        # Missing or empty verification plan → immediate inconclusive
        if not verification_method or not isinstance(verification_method, dict):
            return _make_inconclusive("No verification plan available")

        sources = verification_method.get("source", [])
        criteria = verification_method.get("criteria", [])
        steps = verification_method.get("steps", [])

        if not sources and not criteria and not steps:
            return _make_inconclusive("Verification plan is empty (no sources, criteria, or steps)")

        # Build user prompt using .replace() (Decision 72)
        user_prompt = USER_PROMPT_TEMPLATE
        user_prompt = user_prompt.replace("__PREDICTION_STATEMENT__", prediction_statement)
        user_prompt = user_prompt.replace("__VERIFIABLE_CATEGORY__", verifiable_category)
        user_prompt = user_prompt.replace("__SOURCES__", json.dumps(sources))
        user_prompt = user_prompt.replace("__CRITERIA__", json.dumps(criteria))
        user_prompt = user_prompt.replace("__STEPS__", json.dumps(steps))

        # Invoke the executor agent
        response = _get_executor_agent()(user_prompt)
        response_str = str(response)

        # Parse JSON response (Decision 4: simple try/except)
        raw = json.loads(response_str)
        return _validate_outcome(raw)

    except json.JSONDecodeError as e:
        logger.error(f"Verification executor returned non-JSON: {e}", exc_info=True)
        return _make_inconclusive(f"Failed to parse verification result: {e}")
    except Exception as e:
        logger.error(f"Verification execution failed: {e}", exc_info=True)
        return _make_inconclusive(f"Verification execution error: {e}")


# Module-level singleton — lazy initialization to avoid triggering MCP connections
# at import time (important for testing). First call to run_verification() or
# direct access creates the agent. Same warm-Lambda reuse pattern as other agents.
_verification_executor_agent = None


def _get_executor_agent() -> Agent:
    """Get or create the module-level singleton executor agent."""
    global _verification_executor_agent
    if _verification_executor_agent is None:
        _verification_executor_agent = create_verification_executor_agent()
    return _verification_executor_agent
