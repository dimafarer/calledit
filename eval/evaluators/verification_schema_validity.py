"""Schema Validity evaluator for verification agent output (Tier 1).

Checks that the verdict response contains all required VerificationResult
fields with correct types: verdict (str), confidence (float),
evidence (list), reasoning (str).
"""


def evaluate(result: dict) -> dict:
    """Check VerificationResult schema validity.

    Args:
        result: Dict from VerificationBackend.invoke()

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    if not isinstance(result, dict):
        return {"score": 0.0, "pass": False, "reason": f"Result is not a dict: {type(result)}"}

    failed = []

    if "verdict" not in result:
        failed.append("verdict (missing)")
    elif not isinstance(result["verdict"], str):
        failed.append(f"verdict (expected str, got {type(result['verdict']).__name__})")

    if "confidence" not in result:
        failed.append("confidence (missing)")
    elif not isinstance(result["confidence"], (int, float)):
        failed.append(f"confidence (expected float, got {type(result['confidence']).__name__})")

    if "evidence" not in result:
        failed.append("evidence (missing)")
    elif not isinstance(result["evidence"], list):
        failed.append(f"evidence (expected list, got {type(result['evidence']).__name__})")

    if "reasoning" not in result:
        failed.append("reasoning (missing)")
    elif not isinstance(result["reasoning"], str):
        failed.append(f"reasoning (expected str, got {type(result['reasoning']).__name__})")

    if failed:
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Schema invalid — failed fields: {', '.join(failed)}",
        }

    return {"score": 1.0, "pass": True, "reason": "All required fields present with correct types"}
