"""Dimension Count Evaluator — checks at least 1 dimension assessment exists."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class DimensionCountEvaluator(Evaluator):
    """Verify at least 1 dimension assessment exists in plan_review."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="dimension_count",
            )]

        review = bundle.get("plan_review", {})
        dims = review.get("dimension_assessments", [])

        if not isinstance(dims, list):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"dimension_assessments is {type(dims).__name__}, not list",
                label="dimension_count",
            )]

        if len(dims) < 1:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No dimension assessments", label="dimension_count",
            )]

        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"{len(dims)} dimension assessments", label="dimension_count",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
