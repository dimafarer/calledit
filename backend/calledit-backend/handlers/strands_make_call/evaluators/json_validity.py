"""JSONValidity Evaluator — structural score (0.0-1.0).

Checks field presence and type correctness per agent:
- Parser: prediction_statement (str), verification_date (str), date_reasoning (str)
- Categorizer: verifiable_category (str in VALID_CATEGORIES), category_reasoning (str)
- VB: verification_method with source, criteria, steps as non-empty lists

Score = fields_present_and_correct / total_expected_fields.
Malformed JSON (non-parseable string input) → 0.0 with error message.
This is Tier 1 (deterministic).
"""

import json

VALID_CATEGORIES = {"auto_verifiable", "automatable", "human_only"}

AGENT_SCHEMAS = {
    "parser": [
        ("prediction_statement", str),
        ("verification_date", str),
        ("date_reasoning", str),
    ],
    "categorizer": [
        ("verifiable_category", str),
        ("category_reasoning", str),
    ],
    "verification_builder": [
        ("verification_method", dict),
    ],
}

VB_SUBFIELDS = ["source", "criteria", "steps"]


def evaluate_json_validity(span_output, agent_name: str, span_id: str = "") -> dict:
    """Score field presence and type correctness for an agent's output.

    Args:
        span_output: Either a dict (already parsed) or a string (raw JSON).
        agent_name: One of "parser", "categorizer", "verification_builder".
        span_id: Trace span ID for traceability.

    Returns:
        {"score": 0.0-1.0, "evaluator": "JSONValidity", "span_id": str, "error": str|None}
    """
    # Parse string input if needed
    if isinstance(span_output, str):
        try:
            span_output = json.loads(span_output)
        except (json.JSONDecodeError, TypeError) as e:
            return {"score": 0.0, "evaluator": "JSONValidity", "span_id": span_id,
                    "error": f"JSON parse error: {e}"}

    if not isinstance(span_output, dict):
        return {"score": 0.0, "evaluator": "JSONValidity", "span_id": span_id,
                "error": f"Expected dict, got {type(span_output).__name__}"}

    schema = AGENT_SCHEMAS.get(agent_name)
    if not schema:
        return {"score": 0.0, "evaluator": "JSONValidity", "span_id": span_id,
                "error": f"Unknown agent: {agent_name}"}

    # Count correct fields
    if agent_name == "verification_builder":
        # VB has nested structure: verification_method.{source, criteria, steps}
        total = 1 + len(VB_SUBFIELDS)  # verification_method + 3 subfields
        correct = 0
        vm = span_output.get("verification_method")
        if isinstance(vm, dict):
            correct += 1  # verification_method exists and is dict
            for subfield in VB_SUBFIELDS:
                val = vm.get(subfield)
                if isinstance(val, list) and len(val) > 0:
                    correct += 1
        score = correct / total if total > 0 else 0.0
    else:
        total = len(schema)
        correct = 0
        for field_name, field_type in schema:
            val = span_output.get(field_name)
            if val is not None and isinstance(val, field_type):
                if field_name == "verifiable_category":
                    if val in VALID_CATEGORIES:
                        correct += 1
                elif isinstance(val, str) and len(val) > 0:
                    correct += 1
                elif not isinstance(val, str):
                    correct += 1
        score = correct / total if total > 0 else 0.0

    return {"score": score, "evaluator": "JSONValidity", "span_id": span_id, "error": None}
