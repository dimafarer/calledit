"""Shared utilities for verification evaluators."""

from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


def skip_if_not_verified(evaluation_case: EvaluationData, label: str) -> list[EvaluationOutput] | None:
    """Return a no-op score if the case was intentionally skipped (non-qualifying).

    Returns None if the case should be evaluated normally.
    Returns [EvaluationOutput(score=1.0, ...)] if the case should be skipped.
    """
    qualifying = (evaluation_case.metadata or {}).get("qualifying", True)
    verification_error = None

    if evaluation_case.actual_output and isinstance(evaluation_case.actual_output, dict):
        verification_error = evaluation_case.actual_output.get("verification_error")

    # Skip non-qualifying cases that were intentionally not verified
    if not qualifying and verification_error and "non-qualifying" in str(verification_error).lower():
        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason="N/A — non-qualifying case (no expected outcome)",
            label=label,
        )]

    # Also skip if there's simply no verification result and the case isn't qualifying
    if not qualifying:
        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — non-qualifying case (no expected outcome)",
                label=label,
            )]

    return None
