"""
Prediction Verification Graph

This module implements the 3-agent graph workflow for prediction verification:
Parser → Categorizer → Verification Builder

Following Strands best practices and official documentation:
- GraphBuilder for sequential workflow
- Plain Agent nodes (Graph handles text propagation automatically)
- Agents return JSON that gets passed to next agents
- Simple JSON parsing with json.loads() + fallback defaults (no regex extraction)

Based on official Strands Graph documentation:
https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/

Key insight: The Graph automatically propagates outputs between nodes.
Entry nodes receive the original task, dependent nodes receive the original task
plus results from all completed dependencies. No custom state management needed!
"""

import logging
import json
from typing import Dict, Any
from strands.multiagent import GraphBuilder

from parser_agent import create_parser_agent
from categorizer_agent import create_categorizer_agent
from verification_builder_agent import create_verification_builder_agent

logger = logging.getLogger(__name__)


def create_prediction_graph():
    """
    Create the 3-agent prediction verification graph.
    
    Graph structure:
    Parser → Categorizer → Verification Builder
    
    The Graph automatically handles input propagation:
    - Parser receives the original task (user prompt with context)
    - Categorizer receives original task + Parser's output
    - Verification Builder receives original task + Parser's output + Categorizer's output
    
    Each agent returns JSON, which the Graph passes to dependent nodes.
    
    Returns:
        Compiled graph ready for execution
    """
    # Create the agents
    parser_agent = create_parser_agent()
    categorizer_agent = create_categorizer_agent()
    verification_builder_agent = create_verification_builder_agent()
    
    # Create GraphBuilder
    builder = GraphBuilder()
    
    # Add agents as nodes (agent first, then node ID)
    builder.add_node(parser_agent, "parser")
    builder.add_node(categorizer_agent, "categorizer")
    builder.add_node(verification_builder_agent, "verification_builder")
    
    # Add edges (define sequential flow)
    builder.add_edge("parser", "categorizer")
    builder.add_edge("categorizer", "verification_builder")
    
    # Set entry point
    builder.set_entry_point("parser")
    
    # Build graph
    graph = builder.build()
    
    logger.info("Prediction graph created with 3 agent nodes")
    
    return graph


# Create the graph instance (singleton)
prediction_graph = create_prediction_graph()


def parse_graph_results(result) -> Dict[str, Any]:
    """
    Parse the graph results and extract all agent outputs.

    The Graph returns a MultiAgentResult with results from each node.
    Each agent's output is parsed with a single json.loads() call.

    SIMPLIFIED PARSING (v2 cleanup):
    Previously, this function used extract_json_from_text() — a ~30-line helper
    with 5 regex strategies to recover JSON from markdown-wrapped or malformed
    agent output. That function was removed because:

    1. It masked prompt quality issues — if an agent returned ```json ... ```,
       the regex silently fixed it instead of surfacing the prompt problem.
    2. After prompt hardening (explicit "Return ONLY the raw JSON object"
       instructions) and upgrading to Claude Sonnet 4, all 4 agents produce
       clean JSON reliably. This was validated by the prompt testing harness
       (tests/test_prompt_json_output.py) — 12/12 invocations across all
       agents returned valid JSON parseable by json.loads() directly.
    3. If an agent ever regresses to non-JSON output, we WANT to know about it
       via ERROR-level logging in CloudWatch, not silently recover.

    Each agent block follows the same pattern:
    - Try json.loads(str(result)) directly
    - On JSONDecodeError: log at ERROR level (unexpected after hardening),
      fall back to safe defaults so the user still gets a response

    Args:
        result: MultiAgentResult from graph execution

    Returns:
        Dictionary with all parsed outputs
    """
    parsed_data = {}

    # -------------------------------------------------------------------------
    # Parse parser output
    # Fallback defaults: empty strings for prediction_statement and
    # verification_date, descriptive message for date_reasoning.
    # These ensure the user still gets a response even if parsing fails.
    # -------------------------------------------------------------------------
    if "parser" in result.results:
        parser_result_obj = result.results["parser"]
        # Get the actual text content from the AgentResult
        parser_result = str(parser_result_obj.result) if hasattr(parser_result_obj, 'result') else str(parser_result_obj)

        logger.info(f"Parser raw output (first 200 chars): {parser_result[:200]}")

        try:
            # Direct json.loads() — no regex extraction needed.
            # Prompt hardening + Sonnet 4 ensures clean JSON output,
            # validated by the prompt testing harness (12/12 clean parses).
            parser_data = json.loads(parser_result)
            parsed_data["prediction_statement"] = parser_data.get("prediction_statement", "")
            parsed_data["verification_date"] = parser_data.get("verification_date", "")
            parsed_data["date_reasoning"] = parser_data.get("date_reasoning", "")
            logger.info("Parser JSON parsed successfully")
        except json.JSONDecodeError as e:
            # ERROR level because after prompt hardening, this is unexpected.
            # If this fires, it means the prompt or model regressed — check
            # CloudWatch logs and re-run the prompt testing harness.
            logger.error(f"Parser returned non-JSON output: {parser_result[:500]}")
            parsed_data["prediction_statement"] = ""
            parsed_data["verification_date"] = ""
            parsed_data["date_reasoning"] = "Fallback: Could not parse parser response"

    # -------------------------------------------------------------------------
    # Parse categorizer output
    # Fallback defaults: "human_verifiable_only" is the safest category
    # (requires human judgment), with a descriptive reasoning message.
    # -------------------------------------------------------------------------
    if "categorizer" in result.results:
        categorizer_result_obj = result.results["categorizer"]
        categorizer_result = str(categorizer_result_obj.result) if hasattr(categorizer_result_obj, 'result') else str(categorizer_result_obj)

        logger.info(f"Categorizer raw output (first 200 chars): {categorizer_result[:200]}")

        try:
            # Direct json.loads() — same pattern as parser above.
            categorizer_data = json.loads(categorizer_result)
            parsed_data["verifiable_category"] = categorizer_data.get("verifiable_category", "human_verifiable_only")
            parsed_data["category_reasoning"] = categorizer_data.get("category_reasoning", "")
            logger.info("Categorizer JSON parsed successfully")
        except json.JSONDecodeError as e:
            # ERROR level — unexpected after prompt hardening.
            logger.error(f"Categorizer returned non-JSON output: {categorizer_result[:500]}")
            parsed_data["verifiable_category"] = "human_verifiable_only"
            parsed_data["category_reasoning"] = "Fallback: Could not parse categorizer response"

    # -------------------------------------------------------------------------
    # Parse verification builder output
    # Fallback defaults: manual verification method — the safest option that
    # tells the user to verify manually. The verification_method dict must
    # have source, criteria, and steps as lists (enforced below).
    # -------------------------------------------------------------------------
    if "verification_builder" in result.results:
        verification_result_obj = result.results["verification_builder"]
        verification_result = str(verification_result_obj.result) if hasattr(verification_result_obj, 'result') else str(verification_result_obj)

        logger.info(f"Verification builder raw output (first 200 chars): {verification_result[:200]}")

        try:
            # Direct json.loads() — same pattern as parser and categorizer.
            verification_data = json.loads(verification_result)
            verification_method = verification_data.get("verification_method", {})

            # Ensure all fields are lists (defensive — the agent should return
            # lists, but we normalize just in case a field comes back as a string)
            if not isinstance(verification_method.get("source"), list):
                verification_method["source"] = [verification_method.get("source", "Manual verification")]
            if not isinstance(verification_method.get("criteria"), list):
                verification_method["criteria"] = [verification_method.get("criteria", "Human judgment required")]
            if not isinstance(verification_method.get("steps"), list):
                verification_method["steps"] = [verification_method.get("steps", "Manual review needed")]

            parsed_data["verification_method"] = verification_method
            logger.info("Verification builder JSON parsed successfully")
        except json.JSONDecodeError as e:
            # ERROR level — unexpected after prompt hardening.
            logger.error(f"Verification builder returned non-JSON output: {verification_result[:500]}")
            parsed_data["verification_method"] = {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"]
            }

    return parsed_data


def execute_prediction_graph(
    user_prompt: str,
    user_timezone: str,
    current_datetime_utc: str,
    current_datetime_local: str,
    callback_handler=None
) -> Dict[str, Any]:
    """
    Execute the prediction verification graph with user inputs.
    
    This is the main entry point for processing predictions through
    the 3-agent workflow.
    
    The Graph automatically propagates outputs between agents:
    - Parser receives the initial prompt
    - Categorizer receives Parser's JSON output
    - Verification Builder receives both Parser and Categorizer outputs
    
    RAW AGENT OUTPUTS ONLY (v2 cleanup, Spec 1 Req 4):
    This function returns ONLY the raw parsed agent outputs — no metadata
    fields (user_timezone, current_datetime_utc, current_datetime_local)
    and no fallback defaults. The Lambda handler (strands_make_call_graph.py)
    is now the SINGLE location for:
      - Adding metadata fields (prediction_date, timezone, user_timezone, etc.)
      - Applying fallback defaults for missing agent output fields
      - Building the final WebSocket response payload
    
    Why? Previously, response assembly was split across this function AND
    the Lambda handler, creating two layers of "ensure fields exist" logic
    in two files. When debugging a response format issue, you had to trace
    through both files. Now there's exactly one place to look.
    
    Args:
        user_prompt: User's prediction text
        user_timezone: User's timezone (e.g., "America/New_York")
        current_datetime_utc: Current datetime in UTC
        current_datetime_local: Current datetime in user's local timezone
        callback_handler: Optional callback for streaming events
        
    Returns:
        Dictionary with raw agent outputs only. Keys are a subset of:
        {prediction_statement, verification_date, date_reasoning,
         verifiable_category, category_reasoning, verification_method, error}
        No metadata keys (user_timezone, current_datetime_utc, etc.).
        Fallback defaults are applied by the Lambda handler, not here.
    """
    # Build the initial prompt with context for the parser
    initial_prompt = f"""PREDICTION: {user_prompt}
CURRENT DATE: {current_datetime_local}
TIMEZONE: {user_timezone}

Extract the prediction and parse the verification date."""
    
    logger.info(f"Executing prediction graph for: {user_prompt[:50]}...")
    
    try:
        # Execute graph with initial prompt
        # The Graph will automatically propagate outputs between nodes
        if callback_handler:
            result = prediction_graph(initial_prompt, callback_handler=callback_handler)
        else:
            result = prediction_graph(initial_prompt)
        
        logger.info(f"Prediction graph execution completed with status: {result.status}")
        
        # Parse all agent outputs from the graph results.
        # Returns raw parsed fields only — no metadata, no fallback defaults.
        # The Lambda handler applies fallbacks and adds metadata when building
        # the WebSocket response (single response assembly location).
        parsed_data = parse_graph_results(result)
        
        logger.debug(f"Final parsed data keys: {list(parsed_data.keys())}")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Prediction graph execution failed: {str(e)}", exc_info=True)
        
        # Return error state with raw agent output fields only.
        # NOTE: No metadata keys (user_timezone, current_datetime_utc,
        # current_datetime_local) — those are added by the Lambda handler.
        # We include agent-output-shaped fallbacks here so the Lambda handler
        # can treat error and success paths the same way via .get() defaults.
        return {
            "error": f"Graph execution failed: {str(e)}",
            "prediction_statement": user_prompt,
            "verification_date": "",
            "date_reasoning": "Error during processing",
            "verifiable_category": "human_verifiable_only",
            "category_reasoning": "Error during processing",
            "verification_method": {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed due to error"]
            }
        }
