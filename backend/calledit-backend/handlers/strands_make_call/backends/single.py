"""Single-agent backend — one agent, four prompt-managed steps in conversation.

Uses one Strands Agent that receives the same 4 prompts from Bedrock Prompt
Management as the serial graph, but as sequential turns in a single conversation.
The agent maintains its own context across turns, so it naturally sees what it
produced in step 1 when it does step 2 — no silo problem by design.

This is a fairer architecture comparison than a single mega-prompt because:
- Same prompts as serial (from Prompt Management)
- Same model (configurable via model_id)
- Same tools (web_search etc.)
- Only variable: graph context propagation vs natural conversation context

Context window concern: 3 rounds × 4 prompts = 12 turns max, well within limits.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from strands import Agent

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def metadata(model_id: Optional[str] = None) -> dict:
    """Return backend metadata for reports and discovery."""
    model = model_id or DEFAULT_MODEL
    return {
        "name": "single",
        "description": (
            "Single agent, 4 prompt-managed steps in conversation — "
            "same prompts as serial, natural context propagation"
        ),
        "model_config": {
            "agent": model,
        },
    }


def _fetch_prompts(tool_manifest: str = "") -> dict:
    """Fetch all 4 agent prompts from Bedrock Prompt Management.

    Falls back to bundled constants if Prompt Management is unavailable.
    Returns dict with keys: parser, categorizer, vb, review.
    """
    prompts = {}

    try:
        from prompt_client import fetch_prompt
        prompts["parser"] = fetch_prompt("parser")
        prompts["categorizer"] = fetch_prompt(
            "categorizer",
            variables={"tool_manifest": tool_manifest or "No tools currently registered."},
        )
        prompts["vb"] = fetch_prompt("vb")
        prompts["review"] = fetch_prompt("review")
    except Exception as e:
        logger.warning(f"Prompt Management unavailable, using bundled prompts: {e}")
        from parser_agent import PARSER_SYSTEM_PROMPT
        from categorizer_agent import CATEGORIZER_SYSTEM_PROMPT
        from verification_builder_agent import VERIFICATION_BUILDER_SYSTEM_PROMPT
        from review_agent import REVIEW_SYSTEM_PROMPT

        manifest_text = tool_manifest or "No tools currently registered."
        prompts["parser"] = PARSER_SYSTEM_PROMPT
        prompts["categorizer"] = CATEGORIZER_SYSTEM_PROMPT.format(
            tool_manifest=manifest_text
        )
        prompts["vb"] = VERIFICATION_BUILDER_SYSTEM_PROMPT
        prompts["review"] = REVIEW_SYSTEM_PROMPT

    return prompts


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code block wrapping from JSON responses."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].rstrip()
    return cleaned


def _safe_parse_json(text: str, step_name: str) -> dict:
    """Parse JSON from agent response, stripping markdown if needed."""
    cleaned = _strip_markdown_json(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Single agent {step_name} returned invalid JSON: {e}")
        logger.debug(f"Raw response: {text[:500]}")
        return {}


def run(prediction_text: str, tool_manifest: str = "",
        model_id: Optional[str] = None) -> dict:
    """Execute prediction analysis: one agent, four sequential prompt steps.

    The agent receives each prompt as a new user turn in the same conversation.
    It naturally maintains context — when doing step 2 (categorization), it
    already sees its step 1 (parsing) output in the conversation history.

    Args:
        prediction_text: The raw prediction to process.
        tool_manifest: Tool manifest string for categorization context.
        model_id: Model to use. If None, uses DEFAULT_MODEL.

    Returns:
        OutputContract dict with final_output, agent_outputs, and metadata.
    """
    model = model_id or DEFAULT_MODEL
    start_ms = int(time.time() * 1000)

    # Fetch the same prompts the serial graph uses
    prompts = _fetch_prompts(tool_manifest)

    # Import parser tools so the agent can resolve dates
    from parser_agent import parse_relative_date
    from strands_tools import current_time

    # Create one agent with a minimal system prompt — the real instructions
    # come as user turns (the 4 managed prompts)
    agent = Agent(
        name="single_multi_prompt_agent",
        model=model,
        system_prompt=(
            "You are a prediction analysis system. You will receive a series "
            "of tasks to perform on a user's prediction. Complete each task "
            "and return ONLY the raw JSON object as instructed. Do not wrap "
            "in markdown code blocks."
        ),
        tools=[current_time, parse_relative_date],
    )

    # Build datetime context (same as serial backend)
    now = datetime.now(timezone.utc)
    formatted_dt = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    date_context = (
        f"PREDICTION: {prediction_text}\n"
        f"CURRENT DATE: {formatted_dt}\n"
        f"TIMEZONE: UTC"
    )

    agent_outputs = {}
    all_data = {}

    try:
        # Step 1: Parser — extract claim, resolve dates
        parser_prompt = (
            f"TASK: Parse this prediction.\n\n"
            f"{date_context}\n\n"
            f"INSTRUCTIONS:\n{prompts['parser']}"
        )
        parser_response = agent(parser_prompt)
        parser_data = _safe_parse_json(str(parser_response), "parser")
        agent_outputs["parser"] = parser_data
        all_data.update(parser_data)

        # Step 2: Categorizer — classify verifiability
        cat_prompt = (
            f"TASK: Now categorize the prediction you just parsed.\n\n"
            f"INSTRUCTIONS:\n{prompts['categorizer']}"
        )
        cat_response = agent(cat_prompt)
        cat_data = _safe_parse_json(str(cat_response), "categorizer")
        agent_outputs["categorizer"] = cat_data
        all_data.update(cat_data)

        # Step 3: Verification Builder — create verification plan
        vb_prompt = (
            f"TASK: Now build a verification plan for the prediction "
            f"you parsed and categorized.\n\n"
            f"INSTRUCTIONS:\n{prompts['vb']}"
        )
        vb_response = agent(vb_prompt)
        vb_data = _safe_parse_json(str(vb_response), "verification_builder")
        agent_outputs["verification_builder"] = vb_data
        all_data.update(vb_data)

        # Step 4: Review — identify clarification opportunities
        review_prompt = (
            f"TASK: Now review the complete prediction analysis you've "
            f"produced across the previous steps. Identify what clarification "
            f"questions would improve the verification plan.\n\n"
            f"INSTRUCTIONS:\n{prompts['review']}"
        )
        review_response = agent(review_prompt)
        review_data = _safe_parse_json(str(review_response), "review")
        agent_outputs["review"] = review_data
        all_data.update(review_data)

    except Exception as e:
        logger.error(f"Single agent execution failed: {e}", exc_info=True)
        all_data["error"] = str(e)

    elapsed_ms = int(time.time() * 1000) - start_ms

    # Build final_output — merge all step outputs, add defaults for missing fields
    final_output = {
        "prediction_statement": all_data.get("prediction_statement", prediction_text),
        "prediction_date": all_data.get("prediction_date", now.strftime("%Y-%m-%d")),
        "local_prediction_date": all_data.get("local_prediction_date", now.strftime("%Y-%m-%d")),
        "date_reasoning": all_data.get("date_reasoning", ""),
        "verifiable_category": all_data.get("verifiable_category", "human_only"),
        "category_reasoning": all_data.get("category_reasoning", ""),
        "verification_method": all_data.get("verification_method", {
            "source": [], "criteria": [], "steps": [],
        }),
        "verification_date": all_data.get("verification_date", ""),
        "initial_status": all_data.get("initial_status", "pending"),
        "reviewable_sections": all_data.get("reviewable_sections", []),
        "error": all_data.get("error"),
    }

    return {
        "final_output": final_output,
        "agent_outputs": agent_outputs,
        "metadata": {
            "architecture": "single",
            "model_config": metadata(model)["model_config"],
            "execution_time_ms": elapsed_ms,
        },
    }
