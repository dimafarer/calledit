"""Prediction bundle construction, serialization, and DDB formatting."""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


def generate_prediction_id() -> str:
    """Generate a prediction ID in the format pred-{uuid4}."""
    return f"pred-{uuid.uuid4()}"


def build_bundle(
    prediction_id: str,
    user_id: str,
    raw_prediction: str,
    parsed_claim: Dict[str, Any],
    verification_plan: Dict[str, Any],
    verifiability_score: float,
    verifiability_reasoning: str,
    reviewable_sections: list,
    prompt_versions: Dict[str, str],
    user_timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the prediction bundle from all 3 turn outputs."""
    bundle = {
        "prediction_id": prediction_id,
        "user_id": user_id,
        "raw_prediction": raw_prediction,
        "parsed_claim": parsed_claim,
        "verification_plan": verification_plan,
        "verifiability_score": verifiability_score,
        "verifiability_reasoning": verifiability_reasoning,
        "reviewable_sections": reviewable_sections,
        "clarification_rounds": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "prompt_versions": prompt_versions,
    }
    if user_timezone is not None:
        bundle["user_timezone"] = user_timezone
    return bundle


def serialize_bundle(bundle: Dict[str, Any]) -> str:
    """Serialize a prediction bundle to a JSON string."""
    return json.dumps(bundle, default=str)


def deserialize_bundle(json_str: str) -> Dict[str, Any]:
    """Deserialize a JSON string back to a prediction bundle dict."""
    return json.loads(json_str)


def _convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    return obj


def format_ddb_item(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Format a prediction bundle as a DynamoDB item with PK/SK."""
    item = _convert_floats_to_decimal(bundle)
    item["PK"] = f"PRED#{bundle['prediction_id']}"
    item["SK"] = "BUNDLE"
    return item


def load_bundle_from_ddb(table, prediction_id: str) -> Optional[Dict[str, Any]]:
    """Load an existing prediction bundle from DynamoDB.

    Args:
        table: boto3 DynamoDB Table resource
        prediction_id: The prediction ID (e.g., "pred-abc123...")

    Returns:
        The bundle dict if found, None otherwise.
    """
    response = table.get_item(
        Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"}
    )
    item = response.get("Item")
    if item is None:
        return None
    # Remove DDB keys, return clean bundle
    item.pop("PK", None)
    item.pop("SK", None)
    return item


def build_clarification_context(
    existing_bundle: Dict[str, Any],
    clarification_answers: List[Dict[str, str]],
) -> str:
    """Build the enriched context string for a clarification round.

    Combines the original prediction, the previous round's reviewable
    sections (the questions), and the user's answers into a single
    text block that replaces prediction_text in Turn 1.

    Args:
        existing_bundle: The loaded bundle from DDB
        clarification_answers: List of {question, answer} dicts

    Returns:
        A formatted string for the parser prompt input.
    """
    raw_prediction = existing_bundle["raw_prediction"]
    reviewable_sections = existing_bundle.get("reviewable_sections", [])

    parts = [f"Original prediction: {raw_prediction}"]

    if reviewable_sections:
        parts.append("\nPrevious review identified these areas for improvement:")
        for section in reviewable_sections:
            if section.get("improvable"):
                parts.append(
                    f"- {section['section']}: {section.get('reasoning', '')}"
                )
                for q in section.get("questions", []):
                    parts.append(f"  Question: {q}")

    parts.append("\nUser's clarification answers:")
    for qa in clarification_answers:
        parts.append(f"Q: {qa['question']}")
        parts.append(f"A: {qa['answer']}")

    parts.append(
        "\nPlease re-analyze this prediction incorporating the "
        "clarification answers above."
    )
    return "\n".join(parts)


def format_ddb_update(
    prediction_id: str,
    parsed_claim: Dict[str, Any],
    verification_plan: Dict[str, Any],
    verifiability_score: float,
    verifiability_reasoning: str,
    reviewable_sections: list,
    prompt_versions: Dict[str, str],
    clarification_answers: List[Dict[str, str]],
    user_timezone: Optional[str] = None,
    score_tier: Optional[str] = None,
    score_label: Optional[str] = None,
    score_guidance: Optional[str] = None,
    dimension_assessments: Optional[list] = None,
    tier_display: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the kwargs for a DynamoDB update_item call.

    Returns a dict suitable for table.update_item(**result).
    Uses ConditionExpression to prevent phantom updates (Req 7.3).
    Uses ADD for atomic clarification_rounds increment (Req 7.2).
    Converts floats to Decimal (Req 7.6).
    """
    now = datetime.now(timezone.utc).isoformat()

    update_parts = [
        "SET parsed_claim = :pc",
        "verification_plan = :vp",
        "verifiability_score = :vs",
        "verifiability_reasoning = :vr",
        "reviewable_sections = :rs",
        "prompt_versions = :pv",
        "updated_at = :ua",
        "clarification_history = list_append("
        "if_not_exists(clarification_history, :empty_list), :ch)",
    ]
    if user_timezone:
        update_parts.append("user_timezone = :tz")
    # V4-4: Score tier fields
    if score_tier is not None:
        update_parts.append("score_tier = :st")
        update_parts.append("score_label = :sl")
        update_parts.append("score_guidance = :sg")
        update_parts.append("dimension_assessments = :da")
        update_parts.append("tier_display = :td")

    update_expr = ", ".join(update_parts) + " ADD clarification_rounds :one"

    attr_values = {
        ":pc": _convert_floats_to_decimal(parsed_claim),
        ":vp": _convert_floats_to_decimal(verification_plan),
        ":vs": _convert_floats_to_decimal(verifiability_score),
        ":vr": verifiability_reasoning,
        ":rs": _convert_floats_to_decimal(reviewable_sections),
        ":pv": prompt_versions,
        ":ua": now,
        ":ch": [{"answers": clarification_answers, "timestamp": now}],
        ":empty_list": [],
        ":one": 1,
    }
    if user_timezone:
        attr_values[":tz"] = user_timezone
    if score_tier is not None:
        attr_values[":st"] = score_tier
        attr_values[":sl"] = score_label
        attr_values[":sg"] = score_guidance
        attr_values[":da"] = _convert_floats_to_decimal(dimension_assessments)
        attr_values[":td"] = _convert_floats_to_decimal(tier_display)

    return {
        "Key": {"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"},
        "UpdateExpression": update_expr,
        "ExpressionAttributeValues": attr_values,
        "ConditionExpression": "attribute_exists(PK)",
    }
