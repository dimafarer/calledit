"""Confidence Range Evaluator — checks confidence is in [0.0, 1.0]."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified


class ConfidenceRangeEvaluator(Evaluator):
    """Verify confidence is a float in [0.0, 1.0]."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verification_confidence_range")
        if skip:
            return skip

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="verification_confidence_range",
            )]

        val = result.get("confidence")
        if not isinstance(val, (int, float)):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"confidence is {type(val).__name__}, not float",
                label="verification_confidence_range",
            )]

        if not (0.0 <= float(val) <= 1.0):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"confidence {val} outside [0.0, 1.0]",
                label="verification_confidence_range",
            )]

        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"Confidence {val} in valid range",
            label="verification_confidence_range",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
