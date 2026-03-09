"""
Lambda Handler for Prediction Verification — v2 Unified Graph

v2 ARCHITECTURE:
This handler orchestrates the unified 4-agent graph with two-push WebSocket delivery
and multi-round stateful refinement.

ACTIONS:
- makecall: Initial prediction (round 1). Builds round-1 state, runs graph, sends
  prediction_ready + review_ready.
- clarify: Refinement round (round 2+). Builds enriched state from frontend's
  current_state, re-runs full graph, sends updated prediction_ready + review_ready.

TWO-PUSH DELIVERY:
The graph runs via stream_async. When the verification_builder node completes,
we send prediction_ready immediately (user can submit). When the review node
completes, we send review_ready (improvement suggestions). The user never waits
for review to see their prediction.

STATELESS BACKEND:
The Lambda doesn't hold state between invocations. Round history (previous outputs,
clarifications) is held by the frontend and sent back with each clarify action.
The Lambda builds the enriched PredictionGraphState from the frontend's current_state.
See Decision 8 in docs/project-updates/01-project-update.md.

ASYNC EXECUTION:
Lambda Python 3.12 supports asyncio.run(). The sync lambda_handler wraps the
async async_handler. The event loop is created fresh per invocation — no
long-running process concerns.
"""

import json
import boto3
import logging
import asyncio
from datetime import datetime, timezone

from prediction_graph import (
    execute_prediction_graph_async,
    parse_pipeline_results,
    parse_review_results,
)
from utils import get_current_datetime_in_timezones, convert_local_to_utc

# SnapStart runtime hooks — must be imported at module level so the
# @register_before_snapshot and @register_after_restore decorators
# register during INIT (before the snapshot is taken). The hooks handle
# graph validation on restore and logging for observability.
import snapstart_hooks  # noqa: F401 — imported for side effects (hook registration)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# WEBSOCKET HELPER — Task 5.4
#
# Small helper for sending typed WebSocket messages. Extracted to reduce
# duplication in the async handler and make error handling consistent.
#
# WHY TRY/EXCEPT AROUND EVERY SEND:
# The client may disconnect at any time (browser tab closed, network drop).
# If post_to_connection fails, we log a warning but don't crash — the graph
# result is still valid even if the client never receives it. This is the
# standard pattern for WebSocket-backed Lambda handlers.
# ---------------------------------------------------------------------------


def send_ws(api_gateway_client, connection_id, message_type, data=None, **extra):
    """
    Send a typed WebSocket message to the client.

    Wraps post_to_connection with consistent JSON formatting and error
    handling. If the client disconnected, we log a warning but don't crash.

    Args:
        api_gateway_client: API Gateway Management API client
        connection_id: WebSocket connection ID
        message_type: Message type string (e.g., "prediction_ready", "status")
        data: Optional data payload (dict) — goes into message["data"]
        **extra: Additional top-level fields (e.g., status="processing")
    """
    message = {"type": message_type}
    if data is not None:
        message["data"] = data
    # Extra kwargs become top-level fields in the message.
    # Used for status messages: send_ws(..., "status", status="processing", message="...")
    message.update(extra)

    try:
        api_gateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except Exception as e:
        # Client may have disconnected — log but don't crash.
        # The graph continues running and the result is still valid.
        logger.warning(f"Failed to send WebSocket message ({message_type}): {str(e)}")


# ---------------------------------------------------------------------------
# STATE BUILDERS — Tasks 5.2 and 5.3
#
# These functions build the PredictionGraphState dict for each action type.
# The state carries everything the graph needs: user input, round context,
# and previous agent outputs (for refinement mode).
#
# WHY TWO SEPARATE BUILDERS:
# makecall and clarify have fundamentally different inputs:
# - makecall: raw user prompt + timezone (round 1, no history)
# - clarify: previous state + new clarification (round N, full history)
# Separate functions make the contract explicit and testable.
# ---------------------------------------------------------------------------


def build_round1_state(body):
    """
    Build initial PredictionGraphState for round 1 (makecall action).

    Round 1 is identical to v1 behavior — no previous outputs, no
    clarifications. The state is a clean slate for the graph.

    Calls get_current_datetime_in_timezones() internally to capture the
    current time at the moment of request processing. This keeps the
    caller (async_handler) clean — it just passes the body.

    Args:
        body: Parsed WebSocket request body with 'prompt' and 'timezone'

    Returns:
        PredictionGraphState dict with round=1 and all prev_* fields as None
    """
    user_timezone = body.get('timezone', 'UTC')

    # Get current datetime in both UTC and user's local timezone.
    # This is called here (not in the caller) so the state builder owns
    # all state construction — single responsibility.
    (formatted_date_utc, formatted_datetime_utc,
     formatted_date_local, formatted_datetime_local) = (
        get_current_datetime_in_timezones(user_timezone)
    )

    return {
        "user_prompt": body.get('prompt', ''),
        "user_timezone": user_timezone,
        "current_datetime_utc": formatted_datetime_utc,
        "current_datetime_local": formatted_datetime_local,
        # v2 round tracking — round 1 starts clean.
        # All prev_* fields are None because there's no previous round.
        # user_clarifications is empty because the user hasn't clarified anything yet.
        "round": 1,
        "user_clarifications": [],
        "prev_parser_output": None,
        "prev_categorizer_output": None,
        "prev_vb_output": None,
    }


def build_clarify_state(body):
    """
    Build enriched PredictionGraphState for round 2+ (clarify action).

    This is the core of v2's stateful refinement. The frontend sends back
    the previous round's complete state (current_state) plus the user's
    new clarification (user_input). We:
    1. Increment the round counter
    2. Append the new clarification to the accumulated list
    3. Extract previous agent outputs from current_state
    4. Get fresh current datetime (time has passed since round 1)

    WHY FRONTEND HOLDS SESSION STATE:
    The backend is stateless — no DynamoDB reads, no session store.
    The frontend sends everything the backend needs in each request.
    This is simpler, cheaper, and avoids race conditions. The tradeoff
    is larger WebSocket messages, but the data is small (~2KB).

    WHY FRESH DATETIME:
    Time passes between rounds. If the user clarifies 5 minutes after
    round 1, the agents should see the current time, not the stale time
    from round 1. This matters for predictions like "in 30 minutes" where
    the relative time reference shifts.

    Args:
        body: Parsed WebSocket request body with 'user_input' and 'current_state'

    Returns:
        Tuple of (state_dict, error_message):
        - (dict, None) on success — the enriched PredictionGraphState
        - (None, str) on failure — error message for the 400 response
    """
    current_state = body.get('current_state')
    new_clarification = body.get('user_input', '')

    # Validate required fields — both must be present and non-empty.
    # Missing user_input means the client sent a clarify without text.
    # Missing current_state means the client has no previous round data.
    if not new_clarification:
        return None, "Missing required field: user_input"
    if not current_state:
        return None, "Missing required field: current_state"

    prev_round = current_state.get('round', 1)
    user_timezone = current_state.get('user_timezone', 'UTC')

    # Get FRESH current datetime — time has passed since the previous round.
    # The agents need the current time for relative date parsing (e.g.,
    # "in 30 minutes" means something different now than 5 minutes ago).
    (formatted_date_utc, formatted_datetime_utc,
     formatted_date_local, formatted_datetime_local) = (
        get_current_datetime_in_timezones(user_timezone)
    )

    return {
        # Carry forward the original user prompt and timezone.
        # The prompt doesn't change across rounds — it's the original prediction.
        "user_prompt": current_state.get('user_prompt', ''),
        "user_timezone": user_timezone,
        # Fresh datetime — NOT carried forward from previous round.
        "current_datetime_utc": formatted_datetime_utc,
        "current_datetime_local": formatted_datetime_local,
        # Increment round and accumulate clarifications.
        # The clarification list grows with each round — agents see the full
        # history of what the user has clarified across all rounds.
        "round": prev_round + 1,
        "user_clarifications": current_state.get('user_clarifications', []) + [new_clarification],
        # Extract previous agent outputs for refinement mode.
        # Agents see these in the prompt and decide whether to confirm or update.
        # Each prev_*_output dict contains exactly the fields that agent produces.
        "prev_parser_output": {
            "prediction_statement": current_state.get('prediction_statement', ''),
            "verification_date": current_state.get('verification_date', ''),
            "date_reasoning": current_state.get('date_reasoning', ''),
        },
        "prev_categorizer_output": {
            "verifiable_category": current_state.get('verifiable_category', ''),
            "category_reasoning": current_state.get('category_reasoning', ''),
        },
        "prev_vb_output": {
            "verification_method": current_state.get('verification_method', {}),
        },
    }, None


# ---------------------------------------------------------------------------
# PROMPT BUILDER — Task 5.6
#
# Builds the initial prompt for the graph entry point (Parser agent).
# Round 1 uses the exact v1 format. Round 2+ appends previous output
# and clarifications so agents can refine.
#
# WHY PROMPT VARIES BUT SYSTEM PROMPT STAYS STATIC:
# Agents are module-level singletons (created once, reused across warm
# Lambda invocations). Dynamic system prompts would require creating new
# agents per invocation, losing the singleton benefit. Instead, the
# system prompt has a static refinement instruction block that activates
# when the user prompt includes previous output (round > 1).
# ---------------------------------------------------------------------------


def build_prompt(state):
    """
    Build the initial prompt for the graph based on round number.

    Round 1 format (identical to v1 — Req 9.2):
        PREDICTION: {prompt}
        CURRENT DATE: {datetime}
        TIMEZONE: {timezone}

        Extract the prediction and parse the verification date.

    Round 2+ format (v1 base + previous output + clarifications):
        [same as round 1]

        PREVIOUS OUTPUT:
        {json of previous agent outputs}

        USER CLARIFICATIONS:
        - clarification 1
        - clarification 2

    WHY MERGE ALL PREVIOUS OUTPUTS INTO ONE DICT:
    Agents see the complete picture — not just their own previous output.
    This lets the categorizer see the parser's previous prediction_statement,
    and the VB see the categorizer's previous category. Cross-agent context
    helps agents make better refinement decisions.

    Args:
        state: PredictionGraphState dict with all round context

    Returns:
        Formatted prompt string for the parser agent
    """
    # Base prompt — identical to v1 for round 1.
    # This ensures round 1 prediction quality matches v1 (Req 9.1, 9.2).
    prompt = f"""PREDICTION: {state['user_prompt']}
CURRENT DATE: {state['current_datetime_local']}
TIMEZONE: {state['user_timezone']}

Extract the prediction and parse the verification date."""

    # Round 2+: append previous output and clarifications.
    # Agents see this in their user prompt and activate refinement mode
    # (the static instruction block in their system prompt).
    if state.get('round', 1) > 1:
        # Merge all previous agent outputs into one dict for the prompt.
        prev_output = {}
        if state.get('prev_parser_output'):
            prev_output.update(state['prev_parser_output'])
        if state.get('prev_categorizer_output'):
            prev_output.update(state['prev_categorizer_output'])
        if state.get('prev_vb_output'):
            prev_output.update(state['prev_vb_output'])

        prompt += f"\n\nPREVIOUS OUTPUT:\n{json.dumps(prev_output, indent=2)}"

        # List each clarification as a bullet point.
        # Agents see the full history — round 3 sees clarifications from
        # both round 2 and round 3, giving progressive context.
        clarifications = state.get('user_clarifications', [])
        if clarifications:
            prompt += "\n\nUSER CLARIFICATIONS:"
            for c in clarifications:
                prompt += f"\n- {c}"

    return prompt


# ---------------------------------------------------------------------------
# PREDICTION READY BUILDER — Task 5.4 (extracted helper)
#
# Builds the prediction_ready WebSocket message payload from parsed pipeline
# data and the current state. Extracted as a separate function for:
# 1. Testability — can be property-tested independently (Property 1)
# 2. Readability — execute_and_deliver stays focused on stream event handling
# 3. Reusability — same payload structure for round 1 and round 2+
# ---------------------------------------------------------------------------


def build_prediction_ready(pipeline_data, state):
    """
    Build the prediction_ready WebSocket message payload.

    Applies fallback defaults for missing agent outputs using the `or` pattern
    (handles both missing keys AND empty strings). Adds metadata fields that
    the frontend needs for display and for building clarify requests.

    WHY `or` INSTEAD OF `get(key, default)`:
    `get(key, default)` only applies the default when the key is missing.
    `or` also applies the default when the value is an empty string "".
    Agents sometimes return empty strings for fields they couldn't determine —
    we want the fallback in both cases.

    Args:
        pipeline_data: Dict from parse_pipeline_results() with raw agent outputs
        state: PredictionGraphState dict with round context and metadata

    Returns:
        Complete data dict for the prediction_ready WebSocket message
    """
    # Convert verification_date from local to UTC for the wire format.
    # The Parser returns a local datetime string; we convert to UTC ISO format
    # for consistent storage and display. Same pattern as v1.
    verification_date_utc = pipeline_data.get("verification_date", "")
    if verification_date_utc and not verification_date_utc.endswith("Z"):
        converted = convert_local_to_utc(
            verification_date_utc, state["user_timezone"]
        )
        if converted:
            verification_date_utc = converted

    return {
        # --- Agent outputs (with fallback defaults) ---
        "prediction_statement": (
            pipeline_data.get("prediction_statement")
            or state["user_prompt"]
        ),
        "verification_date": (
            verification_date_utc
            or state.get("current_datetime_utc", "")
        ),
        "date_reasoning": (
            pipeline_data.get("date_reasoning")
            or "No reasoning provided"
        ),
        "verifiable_category": (
            pipeline_data.get("verifiable_category")
            or "human_verifiable_only"
        ),
        "category_reasoning": (
            pipeline_data.get("category_reasoning")
            or "No reasoning provided"
        ),
        "verification_method": (
            pipeline_data.get("verification_method")
            or {
                "source": ["Manual verification"],
                "criteria": ["Human judgment required"],
                "steps": ["Manual review needed"],
            }
        ),
        # --- Metadata (added by Lambda handler, not by agents) ---
        "prediction_date": state.get("current_datetime_utc", ""),
        "timezone": "UTC",
        "user_timezone": state.get("user_timezone", "UTC"),
        "local_prediction_date": state.get("current_datetime_local", ""),
        "initial_status": "pending",
        # --- v2 round context (frontend needs these for clarify requests) ---
        "round": state["round"],
        "user_clarifications": state.get("user_clarifications", []),
    }


# ---------------------------------------------------------------------------
# RESULT ACCUMULATOR — Helper for stream_async event processing
#
# stream_async yields events as nodes complete. The parse_pipeline_results
# and parse_review_results functions expect a GraphResult-like object with
# a .results dict. We accumulate node results as they arrive so we can
# pass a compatible object to the parsers at the right moment.
#
# WHY NOT PARSE DIRECTLY FROM node_result:
# The parsers already handle all the JSON parsing, error logging, and
# fallback defaults. Reusing them avoids duplicating that logic. We just
# need a lightweight container that mimics GraphResult's .results interface.
# ---------------------------------------------------------------------------


class AccumulatedResults:
    """
    Lightweight container that mimics GraphResult.results for the parsers.

    As stream_async yields multiagent_node_stop events, we store each
    node's result here. When verification_builder stops, we have all 3
    pipeline results. When review stops, we have the review result.

    The parse_pipeline_results and parse_review_results functions access
    result.results[node_id].result — this class provides that interface.

    WHY NOT SimpleNamespace:
    SimpleNamespace would work too, but a named class is clearer in logs
    and stack traces. The class is 4 lines — simplicity over cleverness.
    """

    def __init__(self):
        self.results = {}

    def add_node_result(self, node_id, node_result):
        """Store a node's result from a multiagent_node_stop event."""
        self.results[node_id] = node_result


# ---------------------------------------------------------------------------
# EXECUTE AND DELIVER — Task 5.4
#
# The core async function that runs the graph and sends WebSocket messages
# at the right moments. This is where two-push delivery happens:
#
# 1. Parser completes → accumulate result
# 2. Categorizer completes → accumulate result
# 3. Verification Builder completes → parse all 3 pipeline results,
#    build prediction_ready message, send via WebSocket
# 4. ReviewAgent completes → parse review results, send review_ready
#
# WHY stream_async:
# The Graph runs to completion and returns a GraphResult — it doesn't
# natively support sending WebSocket messages mid-execution. stream_async
# yields events as nodes complete, letting us send prediction_ready as
# soon as the pipeline branch finishes, without waiting for ReviewAgent.
# This is the idiomatic Strands approach for monitoring graph progress.
# ---------------------------------------------------------------------------


async def execute_and_deliver(state, connection_id, api_gateway_client):
    """
    Execute the unified graph and deliver results via two-push WebSocket.

    This function:
    1. Builds the round-aware prompt (round 1 = v1 format, round 2+ = enriched)
    2. Builds invocation_state for round context propagation to tools
    3. Iterates stream_async events from the graph
    4. On verification_builder node_stop → parse pipeline, send prediction_ready
    5. On review node_stop → parse review, send review_ready
    6. On multiagent_result → send complete message

    ERROR HANDLING:
    - Graph execution failure: catch, send error WS message, re-raise
    - ReviewAgent parse failure: send review_ready with empty sections (non-fatal)
    - WebSocket send failure: log warning, continue (client may have disconnected)

    Args:
        state: PredictionGraphState dict (from build_round1_state or build_clarify_state)
        connection_id: WebSocket connection ID
        api_gateway_client: API Gateway Management API client
    """
    # Build the prompt — round 1 matches v1 format exactly,
    # round 2+ appends previous output and clarifications.
    initial_prompt = build_prompt(state)

    # invocation_state carries round context for tools that need it.
    # It's separate from the prompt — the prompt is what agents reason about,
    # invocation_state is what tools access via ToolContext.invocation_state.
    # Both carry the same round data, but for different consumers.
    invocation_state = {
        "round": state["round"],
        "user_clarifications": state.get("user_clarifications", []),
        "prev_parser_output": state.get("prev_parser_output"),
        "prev_categorizer_output": state.get("prev_categorizer_output"),
        "prev_vb_output": state.get("prev_vb_output"),
    }

    logger.info(
        f"Starting graph execution (round {state['round']}): "
        f"{state['user_prompt'][:50]}..."
    )

    # Accumulate node results as they arrive from stream_async.
    # This lets us pass a GraphResult-compatible object to the parsers
    # when specific nodes complete (VB → prediction_ready, Review → review_ready).
    accumulated = AccumulatedResults()

    # --- DEBUG COUNTERS for streaming diagnosis (Task 1.1) ---
    # These counters track every event type from stream_async to diagnose
    # whether text events arrive at all, and if so, whether they're forwarded.
    event_counts = {}
    text_chunks_sent = 0
    tool_events_sent = 0

    try:
        async for event_data in execute_prediction_graph_async(
            initial_prompt, invocation_state
        ):
            event_type = event_data.get("type", "")

            # --- DEBUG: Log every event type and its keys (Task 1.1) ---
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if event_counts[event_type] <= 3:
                # Log first 3 of each type to avoid flooding CloudWatch
                logger.info(
                    f"[STREAM_DEBUG] event_type={event_type}, "
                    f"keys={list(event_data.keys())}"
                )

            # ----- AGENT STREAMING EVENTS -----
            # multiagent_node_stream forwards individual agent events (text
            # chunks, tool calls) as they happen during node execution.
            # We forward these to the WebSocket so the frontend can show
            # real-time agent reasoning — the "thinking" stream the user sees.
            if event_type == "multiagent_node_stream":
                inner_event = event_data.get("event", {})

                # --- DEBUG: Log inner event structure (Task 1.1) ---
                inner_keys = list(inner_event.keys()) if isinstance(inner_event, dict) else [f"type={type(inner_event).__name__}"]
                has_data = "data" in inner_event if isinstance(inner_event, dict) else False
                if event_counts[event_type] <= 5:
                    logger.info(
                        f"[STREAM_DEBUG] node_stream inner_keys={inner_keys}, "
                        f"has_data={has_data}, "
                        f"node_id={event_data.get('node_id', 'unknown')}"
                    )

                # Text generation — stream to frontend as "text" type
                if has_data:
                    text_chunks_sent += 1
                    send_ws(
                        api_gateway_client, connection_id,
                        "text", content=inner_event["data"]
                    )
                # Tool usage — stream to frontend as "tool" type
                elif "current_tool_use" in inner_event and inner_event["current_tool_use"].get("name"):
                    tool_events_sent += 1
                    send_ws(
                        api_gateway_client, connection_id,
                        "tool", name=inner_event["current_tool_use"]["name"]
                    )

            # ----- NODE COMPLETION EVENTS -----
            # multiagent_node_stop fires when a graph node finishes execution.
            # We accumulate every node's result, then act on specific nodes:
            # - verification_builder → send prediction_ready (pipeline done)
            # - review → send review_ready (review done)
            # - parser/categorizer → just accumulate (needed for VB parsing)
            elif event_type == "multiagent_node_stop":
                node_id = event_data.get("node_id", "")
                node_result = event_data.get("node_result")

                # Store the result for later parsing.
                # By the time VB stops, parser and categorizer results are
                # already in accumulated.results (sequential pipeline guarantee).
                if node_result is not None:
                    accumulated.add_node_result(node_id, node_result)

                if node_id == "verification_builder":
                    # ----- FIRST PUSH: prediction_ready -----
                    # Pipeline branch complete — all 3 agents have finished.
                    # (Parser → Categorizer → VB is sequential, so VB completing
                    # means Parser and Categorizer already completed.)
                    pipeline_data = parse_pipeline_results(accumulated)
                    prediction_ready_data = build_prediction_ready(pipeline_data, state)

                    send_ws(
                        api_gateway_client, connection_id,
                        "prediction_ready", prediction_ready_data
                    )
                    logger.info(
                        f"Sent prediction_ready (round {state['round']}, "
                        f"category: {prediction_ready_data['verifiable_category']})"
                    )

                elif node_id == "review":
                    # ----- SECOND PUSH: review_ready -----
                    # Review branch complete — parse and send review_ready.
                    # If ReviewAgent failed or returned bad JSON, parse_review_results
                    # returns empty reviewable_sections (graceful degradation).
                    try:
                        review_data = parse_review_results(accumulated)
                    except Exception as e:
                        # ReviewAgent failure is non-fatal — the prediction is
                        # still valid. Send empty sections so the frontend knows
                        # review is done (just with no suggestions).
                        logger.error(
                            f"ReviewAgent result parsing failed: {str(e)}",
                            exc_info=True
                        )
                        review_data = {"reviewable_sections": []}

                    send_ws(
                        api_gateway_client, connection_id,
                        "review_ready", review_data
                    )
                    logger.info(
                        f"Sent review_ready with "
                        f"{len(review_data.get('reviewable_sections', []))} sections"
                    )

            # ----- GRAPH COMPLETION EVENT -----
            elif event_type == "multiagent_result":
                # The entire graph has finished (all nodes done).
                # Send a complete message so the frontend knows no more
                # messages are coming for this round.
                send_ws(
                    api_gateway_client, connection_id,
                    "complete", status="ready"
                )
                logger.info("Graph execution complete — sent complete message")

        # --- DEBUG: Summary of all events received (Task 1.1) ---
        logger.info(
            f"[STREAM_DEBUG] Event summary: {json.dumps(event_counts)}, "
            f"text_chunks_sent={text_chunks_sent}, "
            f"tool_events_sent={tool_events_sent}"
        )

    except Exception as e:
        # Graph execution failed — notify client and re-raise.
        # The caller (async_handler) catches this and returns 500.
        logger.error(f"Graph execution failed: {str(e)}", exc_info=True)
        send_ws(
            api_gateway_client, connection_id,
            "error", message=f"Processing failed: {str(e)}"
        )
        raise


# ---------------------------------------------------------------------------
# ASYNC HANDLER — Task 5.5
#
# The main async handler that:
# 1. Extracts WebSocket connection info (connection_id, domain_name, stage)
# 2. Creates API Gateway Management API client
# 3. Parses the request body
# 4. Routes to the correct action (makecall or clarify)
# 5. Builds the appropriate state
# 6. Sends "processing" status
# 7. Calls execute_and_deliver for two-push delivery
#
# WHY asyncio.run() IN LAMBDA:
# Lambda's Python 3.12 runtime supports asyncio.run(). The event loop is
# created fresh per invocation — no long-running process concerns. This is
# the standard pattern for async Lambda handlers in Python.
#
# WHY STATELESS ROUTING:
# The backend doesn't track sessions. Each request carries everything
# needed — makecall has the prompt, clarify has the full previous state.
# This makes the backend horizontally scalable and eliminates race conditions.
# ---------------------------------------------------------------------------


async def async_handler(event, context):
    """
    Async Lambda handler — processes WebSocket messages and delivers results.

    This is the v2 handler that supports:
    - makecall action (round 1, same as v1)
    - clarify action (round 2+, new in v2)
    - Two-push WebSocket delivery (prediction_ready + review_ready)

    Args:
        event: Lambda event from API Gateway WebSocket
        context: Lambda context

    Returns:
        Lambda response dict with statusCode and body
    """
    try:
        logger.info("WebSocket message event received")

        # ----- STEP 1: Extract WebSocket connection info -----
        # API Gateway WebSocket events carry connection metadata in requestContext.
        # We need connection_id to send messages back, and domain_name + stage
        # to construct the Management API endpoint URL.
        connection_id = event.get('requestContext', {}).get('connectionId')
        domain_name = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')

        if not connection_id or not domain_name or not stage:
            logger.error("Missing WebSocket connection information")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing WebSocket connection information'})
            }

        # ----- STEP 2: Create API Gateway Management API client -----
        # This client lets us send messages back to the WebSocket connection.
        # The endpoint URL is constructed from the WebSocket API's domain and stage.
        api_gateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f"https://{domain_name}/{stage}"
        )

        # ----- STEP 3: Parse request body -----
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON format'})
            }

        # ----- STEP 4: Action routing (Task 5.1) -----
        # Two actions supported:
        # - "makecall": round 1 initial prediction (existing v1 behavior)
        # - "clarify": round 2+ clarification (new in v2)
        # Unknown actions get a 400 error.
        action = body.get('action', 'makecall')

        if action == 'makecall':
            # Round 1 — same as v1. Need a prompt to proceed.
            prompt = body.get('prompt', '')
            if not prompt:
                logger.warning("No prompt provided in makecall request")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No prompt provided'})
                }

            # build_round1_state handles datetime fetching internally.
            state = build_round1_state(body)

        elif action == 'clarify':
            # Round 2+ — build enriched state from previous round + new clarification.
            # build_clarify_state returns (state, None) on success or (None, error) on failure.
            state, error = build_clarify_state(body)
            if state is None:
                logger.warning(f"Clarify validation failed: {error}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': error or 'Missing required fields: user_input and current_state'
                    })
                }

        else:
            # Unknown action — reject with 400.
            logger.warning(f"Unknown action: {action}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }

        # ----- STEP 5: Send processing status -----
        # Immediate feedback that the request was received and graph is starting.
        # The frontend can show a loading indicator.
        send_ws(
            api_gateway_client, connection_id,
            "status", status="processing",
            message=f"Processing your prediction (round {state['round']})..."
        )

        # ----- STEP 6: Execute graph and deliver results -----
        # This is where the magic happens — stream_async events trigger
        # prediction_ready and review_ready at the right moments.
        await execute_and_deliver(state, connection_id, api_gateway_client)

        logger.info(f"Handler completed successfully (round {state['round']})")
        return {
            'statusCode': 200,
            'body': json.dumps({'status': 'Processing completed'})
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)

        # Try to notify client of error — best effort.
        # api_gateway_client and connection_id may not be defined if the
        # error happened before they were created.
        try:
            send_ws(
                api_gateway_client, connection_id,
                "error", message=f"Processing failed: {str(e)}"
            )
        except Exception:
            # If we can't even send the error, just log and move on.
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ---------------------------------------------------------------------------
# SYNC LAMBDA ENTRY POINT — Task 5.5
#
# Lambda's Python 3.12 runtime creates a fresh event loop per invocation.
# asyncio.run() is the standard way to run async code from a sync context.
# No long-running process concerns — the graph executes and completes
# within the Lambda timeout (300s, typically finishes in 5-10s).
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """
    Sync Lambda entry point — wraps the async handler with asyncio.run().

    WHY asyncio.run():
    Lambda's Python 3.12 runtime creates a fresh event loop per invocation.
    asyncio.run() is the standard way to run async code from a sync context.
    The event loop is created, runs async_handler to completion, then closes.
    No long-running process concerns.

    Args:
        event: Lambda event from API Gateway WebSocket
        context: Lambda context

    Returns:
        Lambda response dict with statusCode and body
    """
    return asyncio.run(async_handler(event, context))
