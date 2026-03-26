"""Confidence Range evaluator for verification agent output (Tier 1).

Checks that confidence is a float in [0.0, 1.0] inclusive.
"""


def evaluate(result: dict) -> dict:
    """Check confidence is a float in [0.0, 1.0].

    Args:
        result: Dict from VerificationBackend.invoke()

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    confidence = result.get("confidence")

    if not isinstance(confidence, (int, float)):
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Confidence is not a float: {confidence!r} ({type(confidence).__name__})",
        }

    if 0.0 <= float(confidence) <= 1.0:
        return {"score": 1.0, "pass": True, "reason": f"Confidence {confidence} in valid range"}

    return {
        "score": 0.0,
        "pass": False,
        "reason": f"Confidence {confidence} is outside [0.0, 1.0]",
    }
