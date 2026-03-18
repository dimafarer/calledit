"""
Standalone Test Graph for Prompt Evaluation Framework

This module provides a synchronous, non-Lambda version of the prediction graph
for local evaluation and testing. It decouples eval development from the
SnapStart/Lambda/WebSocket deployment lifecycle.

KEY DIFFERENCES FROM PRODUCTION (prediction_graph.py):
- Agents are created FRESH per invocation (not module-level singletons)
  → Allows testing different prompt versions without restarting
- Synchronous execution via graph.__call__() (not stream_async)
  → No WebSocket two-push delivery, no async event loop needed
- No SnapStart hooks, no Lambda handler, no API Gateway client
  → Runs locally with just Bedrock credentials
- Same agent factory functions and build_prompt() logic as production
  → Results are equivalent to what production would produce

SHARED CODE WITH PRODUCTION:
- create_parser_agent(), create_categorizer_agent(),
  create_verification_builder_agent(), create_review_agent()
- build_prompt() logic (inlined here to avoid importing Lambda handler)
- parse_pipeline_results(), parse_review_results(), parse_graph_results()

USAGE:
    from test_prediction_graph import run_test_graph

    # Round 1 — base prediction
    result = run_test_graph(
        prediction_text="Tomorrow the high in Central Park will reach 70°F",
        timezone="America/New_York"
    )

    # Round 2 — with clarifications
    result = run_test_graph(
        prediction_text="Tomorrow will be a beautiful day",
        timezone="America/New_York",
        round_num=2,
        clarifications=["I mean 70+ degrees and sunny in Central Park, New York"],
        prev_outputs={
            "prediction_statement": "Tomorrow will be a beautiful day",
            "verification_date": "2026-03-15 00:00:00",
            "date_reasoning": "Tomorrow relative to current date",
            "verifiable_category": "human_only",
            "category_reasoning": "Beautiful is subjective",
            "verification_method": {"source": [], "criteria": [], "steps": []}
        }
    )
"""

import json
import logging
from typing import Dict, Any, List, Optional

from strands.multiagent import GraphBuilder

from parser_agent import create_parser_agent
from categorizer_agent import create_categorizer_agent
from verification_builder_agent import create_verification_builder_agent
from review_agent import create_review_agent
from utils import get_current_datetime_in_timezones
from otel_instrumentation import init_otel, graph_trace_span

logger = logging.getLogger(__name__)


def _parse_node_result(result, node_id: str) -> str:
    """Extract text from a single node's result. Inlined from prediction_graph.py
    to avoid importing that module (which creates the production singleton and
    reads DynamoDB tool registry at import time)."""
    if node_id not in result.results:
        return ""
    node_result_obj = result.results[node_id]
    return str(node_result_obj.result) if hasattr(node_result_obj, 'result') else str(node_result_obj)


def _parse_pipeline_results(result) -> Dict[str, Any]:
    """Parse pipeline branch results (Parser + Categorizer + VB).
    Inlined from prediction_graph.py to avoid module-level singleton import."""
    parsed_data = {}

    parser_text = _parse_node_result(result, "parser")
    if parser_text:
        try:
            parser_data = json.loads(parser_text)
            parsed_data["prediction_statement"] = parser_data.get("prediction_statement", "")
            parsed_data["verification_date"] = parser_data.get("verification_date", "")
            parsed_data["date_reasoning"] = parser_data.get("date_reasoning", "")
        except json.JSONDecodeError:
            logger.error(f"Parser returned non-JSON: {parser_text[:200]}")
            parsed_data["prediction_statement"] = ""
            parsed_data["verification_date"] = ""
            parsed_data["date_reasoning"] = "Fallback: Could not parse parser response"

    cat_text = _parse_node_result(result, "categorizer")
    if cat_text:
        try:
            cat_data = json.loads(cat_text)
            parsed_data["verifiable_category"] = cat_data.get("verifiable_category", "human_only")
            parsed_data["category_reasoning"] = cat_data.get("category_reasoning", "")
        except json.JSONDecodeError:
            logger.error(f"Categorizer returned non-JSON: {cat_text[:200]}")
            parsed_data["verifiable_category"] = "human_only"
            parsed_data["category_reasoning"] = "Fallback: Could not parse categorizer response"

    vb_text = _parse_node_result(result, "verification_builder")
    if vb_text:
        try:
            vb_data = json.loads(vb_text)
            verification_method = vb_data.get("verification_method", {})
            if not isinstance(verification_method.get("source"), list):
                verification_method["source"] = [verification_method.get("source", "Manual verification")]
            if not isinstance(verification_method.get("criteria"), list):
                verification_method["criteria"] = [verification_method.get("criteria", "Human judgment required")]
            if not isinstance(verification_method.get("steps"), list):
                verification_method["steps"] = [verification_method.get("steps", "Manual review needed")]
            parsed_data["verification_method"] = verification_method
        except json.JSONDecodeError:
            logger.error(f"VB returned non-JSON: {vb_text[:200]}")
            parsed_data["verification_method"] = {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"],
            }

    return parsed_data


def _parse_review_results(result) -> Dict[str, Any]:
    """Parse review branch results (ReviewAgent).
    Inlined from prediction_graph.py to avoid module-level singleton import."""
    review_text = _parse_node_result(result, "review")
    if not review_text:
        return {"reviewable_sections": []}
    try:
        review_data = json.loads(review_text)
        return {"reviewable_sections": review_data.get("reviewable_sections", [])}
    except json.JSONDecodeError:
        logger.error(f"Review returned non-JSON: {review_text[:200]}")
        return {"reviewable_sections": []}


def _build_test_prompt(
    user_prompt: str,
    current_datetime_local: str,
    user_timezone: str,
    round_num: int = 1,
    clarifications: Optional[List[str]] = None,
    prev_outputs: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the graph input prompt. Same logic as build_prompt() in
    strands_make_call_graph.py, inlined here to avoid importing the
    Lambda handler module (which pulls in boto3 API Gateway client, etc.).

    Round 1: PREDICTION + DATE + TIMEZONE
    Round 2+: Same + PREVIOUS OUTPUT + USER CLARIFICATIONS
    """
    prompt = f"""PREDICTION: {user_prompt}
CURRENT DATE: {current_datetime_local}
TIMEZONE: {user_timezone}

Extract the prediction and parse the verification date."""

    if round_num > 1 and prev_outputs:
        prompt += f"\n\nPREVIOUS OUTPUT:\n{json.dumps(prev_outputs, indent=2)}"

        if clarifications:
            prompt += "\n\nUSER CLARIFICATIONS:"
            for c in clarifications:
                prompt += f"\n- {c}"

    return prompt


def _create_test_graph(tool_manifest: str = "", model_id: str = None) -> Any:
    """
    Create a fresh prediction graph instance. NOT a singleton — each call
    creates new agents, allowing different prompt versions per invocation.

    Args:
        tool_manifest: Tool manifest string for the categorizer.
                       Empty string = pure reasoning mode.
        model_id: Optional model override for all agents. If None, uses default.

    Returns:
        Compiled Strands graph ready for synchronous execution.
    """
    parser = create_parser_agent(model_id=model_id)
    categorizer = create_categorizer_agent(tool_manifest, model_id=model_id)
    vb = create_verification_builder_agent(model_id=model_id)
    review = create_review_agent(model_id=model_id)

    builder = GraphBuilder()
    builder.add_node(parser, "parser")
    builder.add_node(categorizer, "categorizer")
    builder.add_node(vb, "verification_builder")
    builder.add_node(review, "review")

    builder.add_edge("parser", "categorizer")
    builder.add_edge("categorizer", "verification_builder")
    builder.add_edge("verification_builder", "review")
    builder.set_entry_point("parser")
    builder.set_execution_timeout(120)  # 2 min for local testing

    return builder.build()


def run_test_graph(
    prediction_text: str,
    timezone: str = "UTC",
    tool_manifest: str = "",
    round_num: int = 1,
    clarifications: Optional[List[str]] = None,
    prev_outputs: Optional[Dict[str, Any]] = None,
    model_id: str = None,
) -> Dict[str, Any]:
    """
    Execute the prediction graph synchronously and return parsed results.

    This is the main entry point for the eval framework. It creates a fresh
    graph, builds the prompt, executes synchronously, and parses all results.

    Args:
        prediction_text: The prediction to process.
        timezone: User timezone (default "UTC").
        tool_manifest: Tool manifest for categorizer (default "" = no tools).
        round_num: Round number (1 = initial, 2+ = refinement).
        clarifications: List of user clarification strings (round 2+).
        prev_outputs: Dict of previous agent outputs (round 2+).
        model_id: Optional model override for all agents. If None, uses default.

    Returns:
        Dict with all parsed agent outputs:
        {
            "prediction_statement": str,
            "verification_date": str,
            "date_reasoning": str,
            "verifiable_category": str,
            "category_reasoning": str,
            "verification_method": {"source": [], "criteria": [], "steps": []},
            "reviewable_sections": [...],
            "error": str or None
        }
    """
    # Get current datetime for the prompt
    (_, _, _, formatted_datetime_local) = get_current_datetime_in_timezones(timezone)

    # Build the prompt (same logic as production)
    prompt = _build_test_prompt(
        user_prompt=prediction_text,
        current_datetime_local=formatted_datetime_local,
        user_timezone=timezone,
        round_num=round_num,
        clarifications=clarifications,
        prev_outputs=prev_outputs,
    )

    # Create a fresh graph (not a singleton), with optional model override
    graph = _create_test_graph(tool_manifest, model_id=model_id)

    # Initialize OTEL and create graph-level trace span
    # Prompt versions come from prompt_client (recorded during agent creation)
    tracer = init_otel()
    try:
        from prompt_client import get_prompt_version_manifest
        prompt_version_manifest = get_prompt_version_manifest()
    except ImportError:
        prompt_version_manifest = {}

    # Fill in defaults for any agents not yet tracked
    for name in ["parser", "categorizer", "vb", "review"]:
        if name not in prompt_version_manifest:
            prompt_version_manifest[name] = "hardcoded"

    logger.info(
        f"Test graph executing (round {round_num}): "
        f"{prediction_text[:60]}..."
    )

    try:
        # Wrap execution in OTEL parent span — Strands auto-creates child spans
        with graph_trace_span(tracer, prompt_version_manifest, round_num, prediction_text):
            result = graph(prompt)

        # Parse all results (pipeline + review)
        pipeline_data = _parse_pipeline_results(result)
        review_data = _parse_review_results(result)

        # Merge into single result dict
        output = {**pipeline_data, **review_data, "error": None}
        logger.info(
            f"Test graph complete — category: "
            f"{output.get('verifiable_category', 'unknown')}"
        )
        return output

    except Exception as e:
        logger.error(f"Test graph execution failed: {e}", exc_info=True)
        return {
            "prediction_statement": prediction_text,
            "verification_date": "",
            "date_reasoning": "Error during processing",
            "verifiable_category": "human_only",
            "category_reasoning": "Error during processing",
            "verification_method": {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed due to error"],
            },
            "reviewable_sections": [],
            "error": str(e),
        }
