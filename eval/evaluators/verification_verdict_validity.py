"""Verdict Validity evaluator for verification agent output (Tier 1).

Checks that verdict is one of the three allowed values:
"confirmed", "refuted", or "inconclusive".
"""

ALLOWED_VERDICTS = {"confirmed", "refuted", "inconclusive"}


def evaluate(result: dict) -> dict:
    """Check verdict is one of the three allowed values.

    Args:
        result: Dict from VerificationBackend.invoke()

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    verdict = result.get("verdict")

    if verdict in ALLOWED_VERDICTS:
        return {"score": 1.0, "pass": True, "reason": f"Verdict '{verdict}' is valid"}

    return {
        "score": 0.0,
        "pass": False,
        "reason": f"Verdict '{verdict}' is not one of {sorted(ALLOWED_VERDICTS)}",
    }
