"""Score Range Evaluator — checks verifiability_score is in [0.0, 1.0]."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class ScoreRangeEvaluator(Evaluator):
    """Verify verifiability_score is a float in [0.0, 1.0]."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="score_range",
            )]

        review = bundle.get("plan_review", {})
        val = review.get("verifiability_score")

        if not isinstance(val, (int, float)):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"verifiability_score is {type(val).__name__}, not float",
                label="score_range",
            )]

        if not (0.0 <= float(val) <= 1.0):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"verifiability_score {val} outside [0.0, 1.0]",
                label="score_range",
            )]

        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"Score {val} in valid range", label="score_range",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
