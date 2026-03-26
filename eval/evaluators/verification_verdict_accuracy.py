"""Verdict Accuracy evaluator for verification agent output (Tier 2, golden mode only).

Deterministic exact-match check of verdict against expected ground truth.
Only runs when expected_verdict is non-null (golden mode).
In ddb mode, expected_verdict is None and this evaluator is skipped entirely.

All 7 qualifying golden cases have 'confirmed' expected outcomes.
See backlog item 0 for adding 'refuted'/'inconclusive' ground truth cases.
"""

from typing import Optional


def evaluate(result: dict, expected_verdict: Optional[str]) -> Optional[dict]:
    """Check verdict matches expected ground truth.

    Args:
        result: Dict from VerificationBackend.invoke()
        expected_verdict: Ground truth verdict, or None to skip this evaluator.

    Returns:
        {"score": float, "pass": bool, "reason": str} when expected_verdict is non-null.
        None when expected_verdict is None (evaluator skipped in ddb mode).
    """
    if expected_verdict is None:
        return None

    actual = result.get("verdict")

    if actual == expected_verdict:
        return {
            "score": 1.0,
            "pass": True,
            "reason": f"Verdict '{actual}' matches expected '{expected_verdict}'",
        }

    return {
        "score": 0.0,
        "pass": False,
        "reason": (
            f"Verdict mismatch — actual: '{actual}', expected: '{expected_verdict}'"
        ),
    }
