"""Verdict Accuracy Evaluator — deterministic exact match vs expected_output."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified


class VerdictAccuracyEvaluator(Evaluator):
    """Exact match of actual verdict against expected_output.

    Returns no-op for non-qualifying cases. Returns empty list when expected_output is None.
    """

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verdict_accuracy")
        if skip:
            return skip

        if evaluation_case.expected_output is None:
            return []

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="verdict_accuracy",
            )]

        verdict = result.get("verdict")
        expected = evaluation_case.expected_output

        if verdict == expected:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason=f"Verdict '{verdict}' matches expected",
                label="verdict_accuracy",
            )]
        return [EvaluationOutput(
            score=0.0, test_pass=False,
            reason=f"Verdict '{verdict}' != expected '{expected}'",
            label="verdict_accuracy",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
