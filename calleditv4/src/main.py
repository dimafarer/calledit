"""
CalledIt v4 — Prediction Creation Agent on AgentCore

V4-3b: Async streaming entrypoint with clarification round support.

Supports three modes:
1. Creation flow: prediction_text → 3-turn streaming → bundle → DDB save → stream events
2. Clarification: prediction_id + answers → load bundle → 3-turn streaming → DDB update → stream events
3. Simple prompt: prompt → agent response (V4-1/V4-2 backward compatibility)

Changes from V4-3a:
- handler() is now async def, yields JSON stream events
- New clarification routing: prediction_id + clarification_answers
- stream_async() replaces synchronous agent() calls
- User timezone from payload (Decision 101)
- Session ID logged for observability (Req 8)

Decisions:
  94  — Single agent, multi-turn prompts
  98  — No fallbacks in dev, graceful fallback in production
  99  — 3 turns not 4 (merged score + review into plan-reviewer)
  100 — LLM-native date resolution (current_time tool + Code Interpreter)
  101 — User timezone from payload takes priority
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Ensure AWS region is set for all boto3 calls in AgentCore Runtime
if not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

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

from models import ClarificationAnswer, ParsedClaim, PlanReview, VerificationPlan, score_to_tier
from prompt_client import fetch_prompt, get_prompt_version_manifest
from bundle import (
    build_bundle,
    build_clarification_context,
    format_ddb_item,
    format_ddb_update,
    generate_prediction_id,
    load_bundle_from_ddb,
    serialize_bundle,
)

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "calledit-v4")
MAX_CLARIFICATION_ROUNDS = int(
    os.environ.get("MAX_CLARIFICATION_ROUNDS", "5")
)

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


def _make_event(event_type: str, prediction_id: str, data: dict) -> str:
    """Build a stream event JSON string. (Req 5.1-5.8)"""
    return json.dumps({
        "type": event_type,
        "prediction_id": prediction_id,
        "data": data,
    }, default=str)


def _sanitize_for_json(obj):
    """Recursively convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(i) for i in obj]
    return obj


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


async def _run_streaming_turn(agent, prompt, model_cls, turn_number,
                              turn_name, prediction_id):
    """Run one turn via stream_async with structured output.

    Yields text events token-by-token for real-time reasoning display,
    then returns the structured output from the final result event.
    Returns (structured_output, turn_complete_event_json, text_events_list).
    """
    text_events = []
    structured = None

    async for event in agent.stream_async(
        prompt, structured_output_model=model_cls
    ):
        if "data" in event:
            # Token-by-token text — yield to frontend for reasoning display
            text_events.append(_make_event("text", prediction_id, {
                "turn_number": turn_number,
                "turn_name": turn_name,
                "content": event["data"],
            }))
        elif "result" in event:
            # Final event — extract structured output
            structured = event["result"].structured_output

    turn_event = _make_event("turn_complete", prediction_id, {
        "turn_number": turn_number,
        "turn_name": turn_name,
        "output": structured.model_dump(),
    })
    return structured, turn_event, text_events


async def _run_streaming_turn_ws(agent, prompt, model_cls, turn_number,
                                  turn_name, prediction_id, websocket):
    """WebSocket variant — sends each token immediately for real-time UX.

    Same logic as _run_streaming_turn but sends events via websocket.send_json()
    as they arrive instead of collecting into a list.
    """
    structured = None

    async for event in agent.stream_async(
        prompt, structured_output_model=model_cls
    ):
        if "data" in event:
            await websocket.send_json({
                "type": "text",
                "prediction_id": prediction_id,
                "data": {
                    "turn_number": turn_number,
                    "turn_name": turn_name,
                    "content": event["data"],
                },
            })
        elif "result" in event:
            structured = event["result"].structured_output

    turn_event = {
        "type": "turn_complete",
        "prediction_id": prediction_id,
        "data": {
            "turn_number": turn_number,
            "turn_name": turn_name,
            "output": structured.model_dump() if structured else {},
        },
    }
    await websocket.send_json(turn_event)
    return structured


@app.entrypoint
async def handler(payload: dict, context: RequestContext):
    """Async streaming entrypoint — routes to creation, clarification, or simple mode.

    V4-3b: yields JSON stream events instead of returning a single string.

    Routing logic:
    - payload has prediction_id + clarification_answers → clarification round
    - payload has prediction_text → initial creation flow
    - payload has prompt → V4-1/V4-2 simple mode (backward compat)
    - none of the above → error event
    """
    # Extract session_id for observability (Req 8)
    session_id = getattr(context, "session_id", None)
    user_timezone = payload.get("timezone")  # Decision 101

    # --- Clarification route ---
    if "prediction_id" in payload and "clarification_answers" in payload:
        prediction_id = payload["prediction_id"]
        if session_id:
            logger.info(
                f"Clarification request: prediction_id={prediction_id}, "
                f"session_id={session_id}"
            )

        # Validate payload (Req 1.4-1.6)
        answers_raw = payload["clarification_answers"]
        if not prediction_id or not isinstance(prediction_id, str):
            yield _make_event("error", prediction_id or "", {
                "message": "prediction_id must be a non-empty string"
            })
            return
        if not answers_raw or not isinstance(answers_raw, list) or len(answers_raw) == 0:
            yield _make_event("error", prediction_id, {
                "message": "clarification_answers must be a non-empty list"
            })
            return
        for item in answers_raw:
            if (not isinstance(item, dict)
                    or not item.get("question") or not item.get("answer")):
                yield _make_event("error", prediction_id, {
                    "message": "Each clarification answer must have "
                    "non-empty 'question' and 'answer' strings"
                })
                return

        # Load existing bundle (Req 1.2-1.3)
        ddb = boto3.resource("dynamodb")
        table = ddb.Table(DYNAMODB_TABLE_NAME)
        existing_bundle = load_bundle_from_ddb(table, prediction_id)
        if existing_bundle is None:
            yield _make_event("error", prediction_id, {
                "message": f"Prediction {prediction_id} not found"
            })
            return

        # Check cap (Req 3.1-3.3)
        current_rounds = existing_bundle.get("clarification_rounds", 0)
        if current_rounds >= MAX_CLARIFICATION_ROUNDS:
            yield _make_event("error", prediction_id, {
                "message": f"Maximum clarification rounds "
                f"({MAX_CLARIFICATION_ROUNDS}) reached"
            })
            return

        # Build clarification context (Req 2.1-2.2)
        clarification_context = build_clarification_context(
            existing_bundle, answers_raw
        )

        # yield flow_started (Req 4.2)
        flow_started_data = {
            "flow_type": "clarification",
            "clarification_round": current_rounds + 1,
        }
        if session_id:
            flow_started_data["session_id"] = session_id
        yield _make_event("flow_started", prediction_id, flow_started_data)

        try:
            # 3-turn streaming flow with clarification context (Req 2.3)
            current_date = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            tool_manifest = _get_tool_manifest()

            model = BedrockModel(model_id=MODEL_ID)
            agent = Agent(model=model, tools=TOOLS)

            # Turn 1: Parse with clarification context
            parse_variables = {"current_date": current_date}
            if user_timezone:
                parse_variables["user_timezone"] = user_timezone
            parse_prompt = fetch_prompt(
                "prediction_parser", variables=parse_variables
            )
            parse_input = (
                f"{parse_prompt}\n\nPrediction (with clarification):\n"
                f"{clarification_context}"
            )
            parsed_claim, turn_event, text_events = await _run_streaming_turn(
                agent, parse_input, ParsedClaim, 1, "parse", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Turn 2: Plan
            plan_prompt = fetch_prompt(
                "verification_planner",
                variables={"tool_manifest": tool_manifest},
            )
            verification_plan, turn_event, text_events = await _run_streaming_turn(
                agent, plan_prompt, VerificationPlan, 2, "plan", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Turn 3: Review
            review_prompt = fetch_prompt("plan_reviewer")
            plan_review, turn_event, text_events = await _run_streaming_turn(
                agent, review_prompt, PlanReview, 3, "review", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Update DDB (Req 7.1-7.6)
            review_dump = plan_review.model_dump()
            update_params = format_ddb_update(
                prediction_id=prediction_id,
                parsed_claim=parsed_claim.model_dump(),
                verification_plan=verification_plan.model_dump(),
                verifiability_score=plan_review.verifiability_score,
                verifiability_reasoning=plan_review.verifiability_reasoning,
                reviewable_sections=[
                    s.model_dump() for s in plan_review.reviewable_sections
                ],
                prompt_versions=get_prompt_version_manifest(),
                clarification_answers=answers_raw,
                user_timezone=user_timezone,
                score_tier=review_dump["score_tier"],
                score_label=review_dump["score_label"],
                score_guidance=review_dump["score_guidance"],
                dimension_assessments=review_dump["dimension_assessments"],
                tier_display=score_to_tier(plan_review.verifiability_score),
            )

            # Build the updated bundle for the response
            updated_bundle = {
                **existing_bundle,
                "parsed_claim": parsed_claim.model_dump(),
                "verification_plan": verification_plan.model_dump(),
                "verifiability_score": plan_review.verifiability_score,
                "verifiability_reasoning": plan_review.verifiability_reasoning,
                "reviewable_sections": [
                    s.model_dump() for s in plan_review.reviewable_sections
                ],
                "prompt_versions": get_prompt_version_manifest(),
                "clarification_rounds": current_rounds + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # V4-4: Score tier fields from PlanReview structured output
                "score_tier": review_dump["score_tier"],
                "score_label": review_dump["score_label"],
                "score_guidance": review_dump["score_guidance"],
                "dimension_assessments": review_dump["dimension_assessments"],
                "tier_display": score_to_tier(plan_review.verifiability_score),
            }
            if user_timezone:
                updated_bundle["user_timezone"] = user_timezone

            try:
                table.update_item(**update_params)
            except table.meta.client.exceptions.ConditionalCheckFailedException:
                # Req 7.4: item deleted between load and update
                yield _make_event("error", prediction_id, {
                    "message": "Prediction was deleted between load and update"
                })
                return
            except Exception as save_err:
                # Req 7.5: other DDB failure — return bundle with save_error
                logger.error(
                    f"DDB update failed for {prediction_id}: {save_err}",
                    exc_info=True,
                )
                updated_bundle["save_error"] = str(save_err)

            yield _make_event("flow_complete", prediction_id, updated_bundle)

        except Exception as e:
            logger.error(
                f"Clarification flow failed for {prediction_id}: {e}",
                exc_info=True,
            )
            yield _make_event("error", prediction_id, {
                "message": str(e),
            })
            return

    # --- Creation route ---
    elif "prediction_text" in payload:
        prediction_id = generate_prediction_id()
        user_id = payload.get("user_id", "anonymous")
        if session_id:
            logger.info(
                f"Creation request: prediction_id={prediction_id}, "
                f"session_id={session_id}"
            )

        # yield flow_started
        flow_started_data = {
            "flow_type": "creation",
            "clarification_round": 0,
        }
        if session_id:
            flow_started_data["session_id"] = session_id
        yield _make_event("flow_started", prediction_id, flow_started_data)

        try:
            current_date = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            tool_manifest = _get_tool_manifest()

            model = BedrockModel(model_id=MODEL_ID)
            agent = Agent(model=model, tools=TOOLS)

            # Turn 1: Parse (Req 9.1-9.2 — timezone from payload)
            parse_variables = {"current_date": current_date}
            if user_timezone:
                parse_variables["user_timezone"] = user_timezone
            parse_prompt = fetch_prompt(
                "prediction_parser", variables=parse_variables
            )
            parse_input = (
                f"{parse_prompt}\n\nPrediction: {payload['prediction_text']}"
            )
            parsed_claim, turn_event, text_events = await _run_streaming_turn(
                agent, parse_input, ParsedClaim, 1, "parse", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Turn 2: Plan
            plan_prompt = fetch_prompt(
                "verification_planner",
                variables={"tool_manifest": tool_manifest},
            )
            verification_plan, turn_event, text_events = await _run_streaming_turn(
                agent, plan_prompt, VerificationPlan, 2, "plan", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Turn 3: Review
            review_prompt = fetch_prompt("plan_reviewer")
            plan_review, turn_event, text_events = await _run_streaming_turn(
                agent, review_prompt, PlanReview, 3, "review", prediction_id
            )
            for te in text_events:
                yield te
            yield turn_event

            # Assemble bundle (Req 9.4 — user_timezone in bundle)
            bundle = build_bundle(
                prediction_id=prediction_id,
                user_id=user_id,
                raw_prediction=payload["prediction_text"],
                parsed_claim=parsed_claim.model_dump(),
                verification_plan=verification_plan.model_dump(),
                verifiability_score=plan_review.verifiability_score,
                verifiability_reasoning=plan_review.verifiability_reasoning,
                reviewable_sections=[
                    s.model_dump() for s in plan_review.reviewable_sections
                ],
                prompt_versions=get_prompt_version_manifest(),
                user_timezone=user_timezone,
            )

            # V4-4: Inject score tier fields from PlanReview structured output
            review_dump = plan_review.model_dump()
            bundle["score_tier"] = review_dump["score_tier"]
            bundle["score_label"] = review_dump["score_label"]
            bundle["score_guidance"] = review_dump["score_guidance"]
            bundle["dimension_assessments"] = review_dump["dimension_assessments"]
            bundle["tier_display"] = score_to_tier(plan_review.verifiability_score)

            # Save to DDB — failure doesn't block response
            try:
                ddb = boto3.resource("dynamodb")
                table = ddb.Table(DYNAMODB_TABLE_NAME)
                table.put_item(Item=format_ddb_item(bundle))
            except Exception as save_err:
                logger.error(
                    f"DDB save failed for {prediction_id}: {save_err}",
                    exc_info=True,
                )
                bundle["save_error"] = str(save_err)

            yield _make_event("flow_complete", prediction_id, bundle)

        except Exception as e:
            logger.error(
                f"Creation flow failed for {prediction_id}: {e}",
                exc_info=True,
            )
            yield _make_event("error", prediction_id, {
                "message": str(e),
            })
            return

    # --- Simple prompt mode (backward compat, Req 6.4) ---
    elif "prompt" in payload:
        try:
            model = BedrockModel(model_id=MODEL_ID)
            agent = Agent(
                model=model, system_prompt=SIMPLE_PROMPT_SYSTEM, tools=TOOLS
            )
            response = agent(payload["prompt"])
            yield _make_event("flow_complete", "", {
                "response": str(response),
            })
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}", exc_info=True)
            yield _make_event("error", "", {
                "message": f"Agent invocation failed: {str(e)}",
            })

    # --- Missing fields (Req 6.5) ---
    else:
        yield _make_event("error", "", {
            "message": "Missing 'prediction_text', 'prediction_id', "
            "or 'prompt' field in payload"
        })


@app.websocket
async def websocket_handler(websocket, context):
    """WebSocket entrypoint — token-by-token streaming directly to browser.

    Decision 119: @app.websocket for browser WebSocket connections.
    Decision 121: JWT auth via Sec-WebSocket-Protocol header.

    Unlike the HTTP handler which batches text events per turn, this handler
    sends each token immediately via websocket.send_json() for real-time UX.
    """
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        logger.info(f"WebSocket received payload: {list(payload.keys())}")
        user_timezone = payload.get("timezone")

        # Extract user_id from JWT (AgentCore already validated the token)
        user_id = "anonymous"
        try:
            headers = getattr(context, "request_headers", None) or {}
            auth_header = headers.get("authorization", headers.get("Authorization", ""))
            if auth_header.startswith("Bearer "):
                import base64
                token_parts = auth_header[7:].split(".")
                if len(token_parts) >= 2:
                    # Decode JWT payload (no signature verification needed — AgentCore validated)
                    padded = token_parts[1] + "=" * (4 - len(token_parts[1]) % 4)
                    claims = json.loads(base64.urlsafe_b64decode(padded))
                    user_id = claims.get("sub", "anonymous")
                    logger.info(f"Extracted user_id from JWT: {user_id}")
        except Exception as e:
            logger.warning(f"Could not extract user_id from JWT: {e}")

        # --- Creation route (most common from browser) ---
        if "prediction_text" in payload:
            prediction_id = generate_prediction_id()

            await websocket.send_json({
                "type": "flow_started",
                "prediction_id": prediction_id,
                "data": {
                    "flow_type": "creation",
                    "clarification_round": 0,
                    "session_id": getattr(context, "session_id", None),
                },
            })

            try:
                current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                tool_manifest = _get_tool_manifest()
                model = BedrockModel(model_id=MODEL_ID)
                agent = Agent(model=model, tools=TOOLS)

                # Turn 1: Parse
                parse_variables = {"current_date": current_date}
                if user_timezone:
                    parse_variables["user_timezone"] = user_timezone
                parse_prompt = fetch_prompt("prediction_parser", variables=parse_variables)
                parse_input = f"{parse_prompt}\n\nPrediction: {payload['prediction_text']}"
                parsed_claim = await _run_streaming_turn_ws(
                    agent, parse_input, ParsedClaim, 1, "parse", prediction_id, websocket
                )

                # Turn 2: Plan
                plan_prompt = fetch_prompt("verification_planner", variables={"tool_manifest": tool_manifest})
                verification_plan = await _run_streaming_turn_ws(
                    agent, plan_prompt, VerificationPlan, 2, "plan", prediction_id, websocket
                )

                # Turn 3: Review
                review_prompt = fetch_prompt("plan_reviewer")
                plan_review = await _run_streaming_turn_ws(
                    agent, review_prompt, PlanReview, 3, "review", prediction_id, websocket
                )

                # Assemble and save bundle
                bundle = build_bundle(
                    prediction_id=prediction_id, user_id=user_id,
                    raw_prediction=payload["prediction_text"],
                    parsed_claim=parsed_claim.model_dump(),
                    verification_plan=verification_plan.model_dump(),
                    verifiability_score=plan_review.verifiability_score,
                    verifiability_reasoning=plan_review.verifiability_reasoning,
                    reviewable_sections=[s.model_dump() for s in plan_review.reviewable_sections],
                    prompt_versions=get_prompt_version_manifest(),
                    user_timezone=user_timezone,
                )
                review_dump = plan_review.model_dump()
                bundle["score_tier"] = review_dump["score_tier"]
                bundle["score_label"] = review_dump["score_label"]
                bundle["score_guidance"] = review_dump["score_guidance"]
                bundle["dimension_assessments"] = review_dump["dimension_assessments"]
                bundle["tier_display"] = score_to_tier(plan_review.verifiability_score)

                try:
                    ddb = boto3.resource("dynamodb")
                    table = ddb.Table(DYNAMODB_TABLE_NAME)
                    table.put_item(Item=format_ddb_item(bundle))
                except Exception as save_err:
                    logger.error(f"DDB save failed for {prediction_id}: {save_err}", exc_info=True)
                    bundle["save_error"] = str(save_err)

                await websocket.send_json({
                    "type": "flow_complete",
                    "prediction_id": prediction_id,
                    "data": bundle,
                })

            except Exception as e:
                logger.error(f"Creation flow failed for {prediction_id}: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error", "prediction_id": prediction_id,
                    "data": {"message": str(e)},
                })

        # --- Clarification route ---
        elif "prediction_id" in payload and "clarification_answers" in payload:
            prediction_id = payload["prediction_id"]
            answers_raw = payload["clarification_answers"]

            # Load existing bundle
            ddb = boto3.resource("dynamodb")
            table = ddb.Table(DYNAMODB_TABLE_NAME)
            existing_bundle = load_bundle_from_ddb(table, prediction_id)
            if existing_bundle is None:
                await websocket.send_json({"type": "error", "prediction_id": prediction_id, "data": {"message": f"Prediction {prediction_id} not found"}})
                return
            existing_bundle = _sanitize_for_json(existing_bundle)

            current_rounds = existing_bundle.get("clarification_rounds", 0)
            if current_rounds >= MAX_CLARIFICATION_ROUNDS:
                await websocket.send_json({"type": "error", "prediction_id": prediction_id, "data": {"message": f"Maximum clarification rounds ({MAX_CLARIFICATION_ROUNDS}) reached"}})
                return

            clarification_context = build_clarification_context(existing_bundle, answers_raw)

            await websocket.send_json({
                "type": "flow_started", "prediction_id": prediction_id,
                "data": {"flow_type": "clarification", "clarification_round": current_rounds + 1},
            })

            try:
                current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                tool_manifest = _get_tool_manifest()
                model = BedrockModel(model_id=MODEL_ID)
                agent = Agent(model=model, tools=TOOLS)

                parse_variables = {"current_date": current_date}
                if user_timezone:
                    parse_variables["user_timezone"] = user_timezone
                parse_prompt = fetch_prompt("prediction_parser", variables=parse_variables)
                parse_input = f"{parse_prompt}\n\nPrediction (with clarification):\n{clarification_context}"
                parsed_claim = await _run_streaming_turn_ws(agent, parse_input, ParsedClaim, 1, "parse", prediction_id, websocket)

                plan_prompt = fetch_prompt("verification_planner", variables={"tool_manifest": tool_manifest})
                verification_plan = await _run_streaming_turn_ws(agent, plan_prompt, VerificationPlan, 2, "plan", prediction_id, websocket)

                review_prompt = fetch_prompt("plan_reviewer")
                plan_review = await _run_streaming_turn_ws(agent, review_prompt, PlanReview, 3, "review", prediction_id, websocket)

                review_dump = plan_review.model_dump()
                update_params = format_ddb_update(
                    prediction_id=prediction_id,
                    parsed_claim=parsed_claim.model_dump(),
                    verification_plan=verification_plan.model_dump(),
                    verifiability_score=plan_review.verifiability_score,
                    verifiability_reasoning=plan_review.verifiability_reasoning,
                    reviewable_sections=[s.model_dump() for s in plan_review.reviewable_sections],
                    prompt_versions=get_prompt_version_manifest(),
                    clarification_answers=answers_raw,
                    user_timezone=user_timezone,
                    score_tier=review_dump["score_tier"],
                    score_label=review_dump["score_label"],
                    score_guidance=review_dump["score_guidance"],
                    dimension_assessments=review_dump["dimension_assessments"],
                    tier_display=score_to_tier(plan_review.verifiability_score),
                )

                updated_bundle = {
                    **existing_bundle,
                    "parsed_claim": parsed_claim.model_dump(),
                    "verification_plan": verification_plan.model_dump(),
                    "verifiability_score": plan_review.verifiability_score,
                    "verifiability_reasoning": plan_review.verifiability_reasoning,
                    "reviewable_sections": [s.model_dump() for s in plan_review.reviewable_sections],
                    "clarification_rounds": current_rounds + 1,
                    "score_tier": review_dump["score_tier"],
                    "score_label": review_dump["score_label"],
                    "score_guidance": review_dump["score_guidance"],
                    "dimension_assessments": review_dump["dimension_assessments"],
                    "tier_display": score_to_tier(plan_review.verifiability_score),
                }

                try:
                    table.update_item(**update_params)
                except Exception as save_err:
                    logger.error(f"DDB update failed for {prediction_id}: {save_err}", exc_info=True)
                    updated_bundle["save_error"] = str(save_err)

                await websocket.send_json({"type": "flow_complete", "prediction_id": prediction_id, "data": _sanitize_for_json(updated_bundle)})

            except Exception as e:
                logger.error(f"Clarification flow failed for {prediction_id}: {e}", exc_info=True)
                await websocket.send_json({"type": "error", "prediction_id": prediction_id, "data": {"message": str(e)}})

        # --- Simple prompt mode ---
        elif "prompt" in payload:
            try:
                model = BedrockModel(model_id=MODEL_ID)
                agent = Agent(model=model, system_prompt=SIMPLE_PROMPT_SYSTEM, tools=TOOLS)
                response = agent(payload["prompt"])
                await websocket.send_json({
                    "type": "flow_complete", "prediction_id": "",
                    "data": {"response": str(response)},
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error", "prediction_id": "",
                    "data": {"message": str(e)},
                })

        # --- Missing fields ---
        else:
            await websocket.send_json({
                "type": "error", "prediction_id": "",
                "data": {"message": "Missing 'prediction_text' or 'prompt' field in payload"},
            })

    except Exception as e:
        logger.error(f"WebSocket handler error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error", "prediction_id": "",
                "data": {"message": str(e)},
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    app.run()
