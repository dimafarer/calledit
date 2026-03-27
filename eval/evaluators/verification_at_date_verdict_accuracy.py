"""at_date Verdict Accuracy evaluator for verification agent output.

Mode-specific evaluator for at_date predictions:
- Before verification_date: only 'inconclusive' is correct (score 1.0)
- At/after verification_date: exact match against expected verdict (standard logic)

Requirements: 7.3, 7.4
"""

from datetime import datetime
from typing import Optional


def evaluate(
    result: dict,
    expected_verdict: Optional[str],
    verification_date: str = "",
    simulated_time: Optional[str] = None,
) -> Optional[dict]:
    """Check verdict correctness for at_date mode predictions.

    Args:
        result: Dict from VerificationBackend.invoke()
        expected_verdict: Ground truth verdict, or None to skip.
        verification_date: ISO date string for when verification becomes meaningful.
        simulated_time: ISO datetime string for the simulated current time.

    Returns:
        {"score": float, "pass": bool, "reason": str} or None if skipped.
    """
    if expected_verdict is None:
        return None

    actual = result.get("verdict")

    # Determine time relationship
    before_date = False
    if simulated_time and verification_date:
        try:
            sim = datetime.fromisoformat(simulated_time.replace("Z", "+00:00"))
            vdate = datetime.fromisoformat(verification_date.replace("Z", "+00:00"))
            before_date = sim < vdate
        except (ValueError, TypeError):
            pass

    if before_date:
        # Before verification_date: only inconclusive is correct
        if actual == "inconclusive":
            return {
                "score": 1.0,
                "pass": True,
                "reason": (
                    f"at_date: correctly returned 'inconclusive' before "
                    f"verification_date ({verification_date})"
                ),
            }
        return {
            "score": 0.0,
            "pass": False,
            "reason": (
                f"at_date: returned '{actual}' before verification_date "
                f"({verification_date}) — should be 'inconclusive'"
            ),
        }

    # At/after verification_date: standard exact match
    if actual == expected_verdict:
        return {
            "score": 1.0,
            "pass": True,
            "reason": f"at_date: verdict '{actual}' matches expected '{expected_verdict}'",
        }

    return {
        "score": 0.0,
        "pass": False,
        "reason": (
            f"at_date: verdict mismatch — actual: '{actual}', "
            f"expected: '{expected_verdict}'"
        ),
    }
