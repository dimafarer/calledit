"""Tier 1: Score Range — checks verifiability_score is in [0.0, 1.0]."""


def evaluate(bundle: dict) -> dict:
    """Check verifiability_score is a float in [0.0, 1.0].

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    review = bundle.get("plan_review", {})
    val = review.get("verifiability_score")

    if not isinstance(val, (int, float)):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"verifiability_score is {type(val).__name__}, not float",
        }

    if not (0.0 <= float(val) <= 1.0):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"verifiability_score {val} outside [0.0, 1.0]",
        }

    return {"score": 1.0, "pass": True, "reason": f"Score {val} in valid range"}
