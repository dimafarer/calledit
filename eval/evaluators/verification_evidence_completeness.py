"""Evidence Completeness evaluator for verification agent output (Tier 1).

Checks that the evidence list is non-empty — verdicts with no supporting
evidence are flagged immediately.
"""


def evaluate(result: dict) -> dict:
    """Check evidence list is non-empty.

    Args:
        result: Dict from VerificationBackend.invoke()

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    evidence = result.get("evidence", [])

    if isinstance(evidence, list) and len(evidence) > 0:
        return {
            "score": 1.0,
            "pass": True,
            "reason": f"Evidence list has {len(evidence)} item(s)",
        }

    return {
        "score": 0.0,
        "pass": False,
        "reason": "Evidence list is empty — no supporting evidence provided",
    }
