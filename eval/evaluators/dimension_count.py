"""Tier 1: Dimension Count — checks exactly 5 dimension_assessments."""


def evaluate(bundle: dict) -> dict:
    """Check dimension_assessments has exactly 5 entries.

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    review = bundle.get("plan_review", {})
    dims = review.get("dimension_assessments", [])

    if not isinstance(dims, list):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"dimension_assessments is {type(dims).__name__}, not list",
        }

    count = len(dims)
    if count != 5:
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"dimension_assessments has {count} entries, expected 5",
        }

    return {"score": 1.0, "pass": True, "reason": "Exactly 5 dimensions"}
