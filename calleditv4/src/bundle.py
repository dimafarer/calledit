"""Prediction bundle construction, serialization, and DDB formatting."""

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict


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
) -> Dict[str, Any]:
    """Assemble the prediction bundle from all 3 turn outputs."""
    return {
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
