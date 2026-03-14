"""CategoryMatch Evaluator — deterministic binary score.

Compares actual verifiable_category against expected. Score is 1.0 (match) or 0.0 (mismatch).
This is Tier 1 (deterministic) — fast, cheap, no API calls.
"""

VALID_CATEGORIES = {"auto_verifiable", "automatable", "human_only"}


def evaluate_category_match(span_output: dict, expected: dict, span_id: str = "") -> dict:
    """Score: 1.0 if actual category equals expected, 0.0 otherwise."""
    actual = span_output.get("verifiable_category", "")
    expected_cat = expected.get("verifiable_category", "")
    score = 1.0 if actual == expected_cat else 0.0
    return {"score": score, "evaluator": "CategoryMatch", "span_id": span_id,
            "actual": actual, "expected": expected_cat}
