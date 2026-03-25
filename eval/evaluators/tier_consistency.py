"""Tier 1: Tier Consistency — checks score_tier matches verifiability_score."""


def _expected_tier(score: float) -> str:
    """Deterministic tier mapping matching calleditv4/src/models.py score_to_tier."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    return "low"


def evaluate(bundle: dict) -> dict:
    """Check score_tier matches the verifiability_score thresholds.

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    review = bundle.get("plan_review", {})
    v_score = review.get("verifiability_score")
    actual_tier = review.get("score_tier")

    if not isinstance(v_score, (int, float)):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Cannot check tier: verifiability_score is {v_score!r}",
        }

    expected = _expected_tier(float(v_score))
    if actual_tier != expected:
        return {
            "score": 0.0,
            "pass": False,
            "reason": (
                f"Tier mismatch: score={v_score}, "
                f"actual_tier='{actual_tier}', expected='{expected}'"
            ),
        }

    return {
        "score": 1.0,
        "pass": True,
        "reason": f"Tier '{actual_tier}' matches score {v_score}",
    }
