"""
Prediction Verification Graph — v2 Unified 4-Agent Architecture

This module implements the unified 4-agent graph for prediction verification:
Parser → Categorizer → Verification Builder → Review (parallel branch)

v2 ARCHITECTURE OVERVIEW:
The graph has two logical branches that share a single execution:

  Pipeline Branch (sequential): Parser → Categorizer → Verification Builder
  Review Branch (parallel):     Verification Builder → ReviewAgent

The first three agents form the Pipeline Branch — they run sequentially, each
receiving the original task plus all prior agents' outputs (Strands' automatic
context propagation). When Verification Builder completes, the pipeline results
are ready for the user.

ReviewAgent runs as a parallel branch after VB completes. It receives the
original task plus ALL three pipeline agents' outputs and performs meta-analysis
to identify improvable sections.

WHY A SINGLE EDGE FROM VB TO REVIEW (not conditional edges from all 3):
The pipeline is sequential (Parser → Cat → VB). When VB completes, Parser and
Categorizer have already completed by definition. So a single edge from VB to
Review is sufficient — no conditional edges or all_dependencies_complete check
needed. This is the idiomatic Strands "Sequential Pipeline with Parallel Branch"
pattern. The initial design proposed conditional edges, but after reading the
Strands Graph source code, we realized it's unnecessary for sequential pipelines.

HOW THIS DIFFERS FROM v1:
- v1: 3-agent graph (Parser → Cat → VB) + standalone ReviewAgent invocation
- v2: 4-agent graph with ReviewAgent as a graph node
- v1: Synchronous execution, single response after everything completes
- v2: stream_async for two-push delivery (prediction_ready when VB stops,
      review_ready when Review stops)
- v1: execute_prediction_graph() returns Dict[str, Any]
- v2: execute_prediction_graph_async() yields stream events as AsyncIterator

SINGLETON PATTERN:
The graph is compiled once at module level (prediction_graph) and reused across
warm Lambda invocations. This saves agent creation and graph compilation time on
warm starts (provisioned concurrency). The graph structure is static — round
state flows through the initial prompt and invocation_state, not through graph
construction.

Based on official Strands Graph documentation:
https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/
"""

import logging
import json
import asyncio
from typing import Dict, Any, AsyncIterator

from strands.multiagent import GraphBuilder

from parser_agent import create_parser_agent
from categorizer_agent import create_categorizer_agent
from verification_builder_agent import create_verification_builder_agent
from review_agent import create_review_agent

logger = logging.getLogger(__name__)


# =============================================================================
# TASK 4.1: Build the unified graph with GraphBuilder
# =============================================================================


def create_prediction_graph():
    """
    Create the unified 4-agent prediction verification graph.

    v2 GRAPH TOPOLOGY:
    Parser → Categorizer → Verification Builder → Review (parallel branch)

    The first three agents form the Pipeline Branch (sequential).
    ReviewAgent runs as a parallel branch after VB completes.

    WHY A SINGLE EDGE FROM VB TO REVIEW:
    The pipeline is sequential (Parser → Cat → VB). When VB completes,
    Parser and Categorizer have already completed by definition. So a
    single edge from VB to Review is sufficient — no conditional edges
    or all_dependencies_complete check needed. This is the idiomatic
    Strands "Sequential Pipeline with Parallel Branch" pattern.

    AUTOMATIC CONTEXT PROPAGATION:
    Strands Graph automatically builds input for each node:
    - Entry nodes (Parser) receive the original task
    - Dependent nodes receive: original task + results from all completed dependencies
    - ReviewAgent receives: original task + Parser output + Categorizer output + VB output
    No manual state threading needed!

    SINGLETON PATTERN:
    The graph is compiled once at module level and reused across warm Lambda
    invocations. This saves agent creation and graph compilation time on
    warm starts (provisioned concurrency). The graph structure is static —
    round state flows through the initial prompt and invocation_state, not
    through graph construction.

    Returns:
        Compiled graph ready for execution via __call__ or stream_async
    """
    # Create all 4 agents using factory functions.
    # Each factory returns a configured strands.Agent instance with:
    # - Explicit model selection (Claude Sonnet 4 via Bedrock)
    # - Focused system prompt (single responsibility)
    # - Tools where needed (Parser has parse_relative_date + current_time)
    parser = create_parser_agent()
    categorizer = create_categorizer_agent()
    vb = create_verification_builder_agent()
    review = create_review_agent()

    builder = GraphBuilder()

    # Add all 4 nodes — agent first, then node ID string.
    # Node IDs are used to reference nodes in edges and to look up results
    # in the GraphResult.results dict after execution.
    builder.add_node(parser, "parser")
    builder.add_node(categorizer, "categorizer")
    builder.add_node(vb, "verification_builder")
    builder.add_node(review, "review")

    # Pipeline branch: sequential edges.
    # Each agent receives the original task + all prior agents' outputs.
    # Parser → Categorizer: Categorizer sees the original prediction + Parser's JSON
    # Categorizer → VB: VB sees original prediction + Parser JSON + Categorizer JSON
    builder.add_edge("parser", "categorizer")
    builder.add_edge("categorizer", "verification_builder")

    # Review branch: single edge from VB.
    # Because the pipeline is sequential, VB completing guarantees all 3
    # pipeline agents are done. No conditional edge needed.
    #
    # ReviewAgent receives: original task + Parser output + Categorizer output + VB output
    # This is Strands' automatic context propagation — all completed upstream
    # nodes' outputs are included in the input to downstream nodes.
    builder.add_edge("verification_builder", "review")

    # Set entry point — Parser is the first agent to execute.
    # It receives the raw initial prompt (prediction text + date + timezone).
    builder.set_entry_point("parser")

    # Set execution timeout.
    # Lambda timeout is 300s (5 minutes). We set the graph timeout to 270s
    # to leave 30s margin for Lambda cleanup, WebSocket sends, and logging.
    # The 4-agent graph typically completes in 5-10 seconds, so this is a
    # safety net for Bedrock latency spikes, not a normal constraint.
    builder.set_execution_timeout(270)

    graph = builder.build()
    logger.info(
        "Unified prediction graph created with 4 agent nodes "
        "(Parser → Cat → VB → Review)"
    )
    return graph


# Module-level singleton — compiled once, reused across warm Lambda invocations.
# Agent creation and graph compilation happen at import time (Lambda cold start).
# Subsequent warm invocations reuse this graph instance, saving ~1-2s per call.
prediction_graph = create_prediction_graph()


# =============================================================================
# TASK 4.2: Parse graph results — restructured for two-push delivery
# =============================================================================
#
# In v1, parse_graph_results() handled 3 agents and returned everything at once.
# In v2, we split parsing into:
#   - parse_node_result(): DRY helper to extract text from a single node
#   - parse_pipeline_results(): Parser + Categorizer + VB (for prediction_ready)
#   - parse_review_results(): ReviewAgent (for review_ready)
#   - parse_graph_results(): Convenience wrapper that calls both (backward compat)
#
# WHY SEPARATE FUNCTIONS:
# The Lambda handler sends two WebSocket messages at different times:
#   1. prediction_ready — when VB node stops (pipeline complete)
#   2. review_ready — when Review node stops (review complete)
# Each message needs different parsed data. Separate functions let the handler
# call the right parser at the right time without re-parsing everything.


def parse_node_result(result, node_id: str) -> str:
    """
    Extract the text content from a single node's result.

    This is a DRY helper that handles the common pattern of:
    1. Check if node_id exists in result.results
    2. Get the AgentResult object
    3. Extract the text via str(obj.result) or str(obj)

    The hasattr check handles both AgentResult objects (which have a .result
    attribute) and raw string results (which don't). In practice, Strands
    always returns AgentResult objects, but defensive coding costs nothing.

    Args:
        result: The GraphResult (or MultiAgentResult) from graph execution
        node_id: The node ID string (e.g., "parser", "review")

    Returns:
        The text content as a string, or empty string if node not found
    """
    if node_id not in result.results:
        return ""
    node_result_obj = result.results[node_id]
    return str(node_result_obj.result) if hasattr(node_result_obj, 'result') else str(node_result_obj)


def parse_pipeline_results(result) -> Dict[str, Any]:
    """
    Parse the pipeline branch results (Parser + Categorizer + VB).

    Returns raw agent outputs for the prediction_ready message.
    This is the same parsing logic as v1's parse_graph_results(), just
    renamed for clarity and scoped to the 3 pipeline agents.

    PARSING PATTERN (same as v1, established in Spec 1):
    Each agent block follows the same pattern:
    - Try json.loads(str(result)) directly
    - On JSONDecodeError: log at ERROR level (unexpected after prompt hardening),
      fall back to safe defaults so the user still gets a response
    - No regex extraction, no retry — if an agent regresses to non-JSON output,
      we WANT to know about it via ERROR-level logging in CloudWatch

    Args:
        result: The GraphResult from graph execution (must have .results dict)

    Returns:
        Dictionary with parsed pipeline outputs. Keys are a subset of:
        {prediction_statement, verification_date, date_reasoning,
         verifiable_category, category_reasoning, verification_method}
    """
    parsed_data = {}

    # -------------------------------------------------------------------------
    # Parse parser output
    # Fallback defaults: empty strings for prediction_statement and
    # verification_date, descriptive message for date_reasoning.
    # These ensure the user still gets a response even if parsing fails.
    # -------------------------------------------------------------------------
    parser_text = parse_node_result(result, "parser")
    if parser_text:
        logger.info(f"Parser raw output (first 200 chars): {parser_text[:200]}")
        try:
            # Direct json.loads() — no regex extraction needed.
            # Prompt hardening + Sonnet 4 ensures clean JSON output,
            # validated by the prompt testing harness (12/12 clean parses).
            parser_data = json.loads(parser_text)
            parsed_data["prediction_statement"] = parser_data.get("prediction_statement", "")
            parsed_data["verification_date"] = parser_data.get("verification_date", "")
            parsed_data["date_reasoning"] = parser_data.get("date_reasoning", "")
            logger.info("Parser JSON parsed successfully")
        except json.JSONDecodeError:
            # ERROR level because after prompt hardening, this is unexpected.
            # If this fires, it means the prompt or model regressed — check
            # CloudWatch logs and re-run the prompt testing harness.
            logger.error(f"Parser returned non-JSON output: {parser_text[:500]}")
            parsed_data["prediction_statement"] = ""
            parsed_data["verification_date"] = ""
            parsed_data["date_reasoning"] = "Fallback: Could not parse parser response"

    # -------------------------------------------------------------------------
    # Parse categorizer output
    # Fallback defaults: "human_verifiable_only" is the safest category
    # (requires human judgment), with a descriptive reasoning message.
    # -------------------------------------------------------------------------
    cat_text = parse_node_result(result, "categorizer")
    if cat_text:
        logger.info(f"Categorizer raw output (first 200 chars): {cat_text[:200]}")
        try:
            # Direct json.loads() — same pattern as parser above.
            cat_data = json.loads(cat_text)
            parsed_data["verifiable_category"] = cat_data.get("verifiable_category", "human_verifiable_only")
            parsed_data["category_reasoning"] = cat_data.get("category_reasoning", "")
            logger.info("Categorizer JSON parsed successfully")
        except json.JSONDecodeError:
            # ERROR level — unexpected after prompt hardening.
            logger.error(f"Categorizer returned non-JSON output: {cat_text[:500]}")
            parsed_data["verifiable_category"] = "human_verifiable_only"
            parsed_data["category_reasoning"] = "Fallback: Could not parse categorizer response"

    # -------------------------------------------------------------------------
    # Parse verification builder output
    # Fallback defaults: manual verification method — the safest option that
    # tells the user to verify manually. The verification_method dict must
    # have source, criteria, and steps as lists (enforced below).
    # -------------------------------------------------------------------------
    vb_text = parse_node_result(result, "verification_builder")
    if vb_text:
        logger.info(f"Verification builder raw output (first 200 chars): {vb_text[:200]}")
        try:
            # Direct json.loads() — same pattern as parser and categorizer.
            vb_data = json.loads(vb_text)
            verification_method = vb_data.get("verification_method", {})

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
        except json.JSONDecodeError:
            # ERROR level — unexpected after prompt hardening.
            logger.error(f"Verification builder returned non-JSON output: {vb_text[:500]}")
            parsed_data["verification_method"] = {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"]
            }

    return parsed_data


def parse_review_results(result) -> Dict[str, Any]:
    """
    Parse the review branch results (ReviewAgent).

    Returns reviewable_sections for the review_ready message.

    If ReviewAgent fails or returns non-JSON, returns empty reviewable_sections.
    This is intentional — the prediction is still valid without review.
    ReviewAgent failure is a degraded experience (no improvement suggestions),
    not a broken experience (no prediction at all).

    Args:
        result: The GraphResult from graph execution (must have .results dict)

    Returns:
        Dictionary with key "reviewable_sections" containing a list of
        ReviewableSection dicts, each with: section, improvable, questions, reasoning.
        Empty list on parse failure.
    """
    review_text = parse_node_result(result, "review")
    if not review_text:
        logger.warning("Review node produced no output — returning empty reviewable_sections")
        return {"reviewable_sections": []}

    logger.info(f"Review raw output (first 200 chars): {review_text[:200]}")
    try:
        review_data = json.loads(review_text)
        reviewable_sections = review_data.get("reviewable_sections", [])
        logger.info(f"Review JSON parsed successfully — {len(reviewable_sections)} sections")
        return {"reviewable_sections": reviewable_sections}
    except json.JSONDecodeError:
        # ERROR level — unexpected after prompt hardening, but non-fatal.
        # The user gets their prediction without review suggestions.
        logger.error(f"Review agent returned non-JSON output: {review_text[:500]}")
        return {"reviewable_sections": []}


def parse_graph_results(result) -> Dict[str, Any]:
    """
    Parse all graph results (pipeline + review) — backward compatibility wrapper.

    This function calls both parse_pipeline_results() and parse_review_results()
    and merges the results. It exists for backward compatibility with code that
    expects a single parse call returning everything.

    The v2 Lambda handler uses parse_pipeline_results() and parse_review_results()
    separately (at different times during stream_async processing). This wrapper
    is for tests and any code that wants all results at once.

    Args:
        result: The GraphResult from graph execution

    Returns:
        Merged dictionary with all pipeline + review parsed outputs
    """
    parsed_data = parse_pipeline_results(result)
    review_data = parse_review_results(result)
    parsed_data.update(review_data)
    return parsed_data


# =============================================================================
# TASK 4.3: Async execution with stream_async + sync backward-compat wrapper
# =============================================================================


async def execute_prediction_graph_async(
    initial_prompt: str,
    invocation_state: Dict[str, Any] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Execute the unified prediction graph and yield stream events.

    v2 CHANGE: This function is now async and yields stream events from
    the graph's stream_async method. The Lambda handler consumes these
    events to implement two-push WebSocket delivery:
    - When verification_builder node stops → send prediction_ready
    - When review node stops → send review_ready

    WHY stream_async INSTEAD OF SYNCHRONOUS EXECUTION:
    The Graph runs to completion and returns a GraphResult — it doesn't
    natively support sending WebSocket messages mid-execution. stream_async
    yields events as nodes complete, letting the Lambda handler send
    prediction_ready as soon as the pipeline branch finishes, without
    waiting for ReviewAgent. This is the idiomatic Strands approach.

    WHY invocation_state:
    Round context (round number, clarifications, previous outputs) is passed
    via invocation_state, not baked into the prompt. invocation_state is
    available to tools via ToolContext but doesn't appear in agent prompts.
    The round context is in the prompt (built by the Lambda handler) for
    agents to reason about, and in invocation_state for tools that need it.

    Args:
        initial_prompt: The formatted prompt for the parser agent.
            Round 1: "PREDICTION: ...\nCURRENT DATE: ...\nTIMEZONE: ..."
            Round 2+: Same + "\n\nPREVIOUS OUTPUT:\n...\n\nUSER CLARIFICATIONS:\n..."
        invocation_state: Round context dict with round, user_clarifications,
            prev_parser_output, prev_categorizer_output, prev_vb_output.
            Passed to graph via stream_async for tool access.

    Yields:
        Stream event dicts from the graph. Key event types:
        - {"type": "multiagent_node_stop", "node_id": "verification_builder", ...}
        - {"type": "multiagent_node_stop", "node_id": "review", ...}
        - {"type": "multiagent_result", "result": GraphResult}
        The Lambda handler filters for node_stop events to trigger WebSocket sends.
    """
    if invocation_state is None:
        invocation_state = {}

    round_num = invocation_state.get('round', 1)
    logger.info(
        f"Executing unified graph (round {round_num}): "
        f"{initial_prompt[:80]}..."
    )

    # stream_async yields events as nodes execute and complete.
    # The Lambda handler consumes these to detect when specific nodes finish.
    # Each event is a dict with a "type" key — the handler filters for
    # "multiagent_node_stop" events with specific node_id values.
    async for event in prediction_graph.stream_async(
        initial_prompt, invocation_state=invocation_state
    ):
        yield event


def execute_prediction_graph(
    user_prompt: str,
    user_timezone: str,
    current_datetime_utc: str,
    current_datetime_local: str,
    callback_handler=None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for backward compatibility.

    This function maintains the v1 interface for existing tests and the
    current Lambda handler. It runs the graph synchronously and returns
    the parsed pipeline results (same as v1).

    NOTE: The v2 Lambda handler uses execute_prediction_graph_async() directly
    with stream_async for two-push delivery. This wrapper is kept for:
    - Existing integration tests that expect synchronous execution
    - Gradual migration path

    RAW AGENT OUTPUTS ONLY (v2 cleanup, Spec 1 Req 4):
    This function returns ONLY the raw parsed agent outputs — no metadata
    fields (user_timezone, current_datetime_utc, current_datetime_local)
    and no fallback defaults. The Lambda handler is the SINGLE location for
    adding metadata and applying fallback defaults.

    Args:
        user_prompt: User's prediction text
        user_timezone: User's timezone (e.g., "America/New_York")
        current_datetime_utc: Current datetime in UTC
        current_datetime_local: Current datetime in user's local timezone
        callback_handler: Optional callback for streaming events (ignored in v2,
            kept for signature compatibility)

    Returns:
        Dictionary with raw agent outputs only. Keys are a subset of:
        {prediction_statement, verification_date, date_reasoning,
         verifiable_category, category_reasoning, verification_method, error}
    """
    # Build the initial prompt — same format as v1 for round 1.
    # This ensures round 1 prediction quality matches v1 (Req 9.1, 9.2).
    initial_prompt = f"""PREDICTION: {user_prompt}
CURRENT DATE: {current_datetime_local}
TIMEZONE: {user_timezone}

Extract the prediction and parse the verification date."""

    logger.info(f"Executing prediction graph (sync wrapper): {user_prompt[:50]}...")

    try:
        # Synchronous execution — calls the graph directly (not stream_async).
        # The graph returns a GraphResult with .results dict and .status.
        result = prediction_graph(initial_prompt)
        logger.info(f"Graph execution completed with status: {result.status}")

        # Parse pipeline results only (same as v1 behavior).
        # The sync wrapper doesn't return review results because v1 callers
        # don't expect them. The v2 Lambda handler uses the async path
        # which handles review results separately via stream events.
        return parse_pipeline_results(result)

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
