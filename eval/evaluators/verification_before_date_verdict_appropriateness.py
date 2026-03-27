"""before_date Verdict Appropriateness evaluator for verification agent output.

Mode-specific evaluator for before_date predictions:
- Before verification_date: 'confirmed' and 'inconclusive' both score 1.0,
  'refuted' scores 0.0 (can't refute before deadline)
- At/after verification_date: exact match against expected verdict

Requirements: 7.5, 7.6
"""

from datetime import datetime
from typing import Optional


def evaluate(
    result: dict,
    expected_verdict: Optional[str],
    verification_date: str = "",
    simulated_time: Optional[str] = None,
) -> Optional[dict]:
    """Check verdict appropriateness for before_date mode predictions.

    Args:
        result: Dict from VerificationBackend.invoke()
        expected_verdict: Ground truth verdict, or None to skip.
        verification_date: ISO date string for the deadline.
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
        # Before deadline: confirmed and inconclusive are acceptable
        if actual in ("confirmed", "inconclusive"):
            return {
                "score": 1.0,
                "pass": True,
                "reason": (
                    f"before_date: '{actual}' is acceptable before deadline "
                    f"({verification_date})"
                ),
            }
        # refuted before deadline is wrong
        return {
            "score": 0.0,
            "pass": False,
            "reason": (
                f"before_date: '{actual}' is not appropriate before deadline "
                f"({verification_date}) — only 'confirmed' or 'inconclusive' "
                f"are acceptable"
            ),
        }

    # At/after deadline: standard exact match
    if actual == expected_verdict:
        return {
            "score": 1.0,
            "pass": True,
            "reason": (
                f"before_date: verdict '{actual}' matches expected "
                f"'{expected_verdict}' (at/after deadline)"
            ),
        }

    return {
        "score": 0.0,
        "pass": False,
        "reason": (
            f"before_date: verdict mismatch — actual: '{actual}', "
            f"expected: '{expected_verdict}' (at/after deadline)"
        ),
    }
