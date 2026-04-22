"""Tier Consistency Evaluator — checks score_tier matches verifiability_score."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


def expected_tier(score: float) -> str:
    """Deterministic tier mapping matching calleditv4/src/models.py score_to_tier."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    return "low"


class TierConsistencyEvaluator(Evaluator):
    """Verify score_tier label matches the verifiability_score thresholds."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="tier_consistency",
            )]

        review = bundle.get("plan_review", {})
        v_score = review.get("verifiability_score")
        actual_tier = review.get("score_tier")

        if not isinstance(v_score, (int, float)):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"Cannot check tier: verifiability_score is {v_score!r}",
                label="tier_consistency",
            )]

        exp = expected_tier(float(v_score))
        if actual_tier != exp:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"Tier mismatch: score={v_score}, actual='{actual_tier}', expected='{exp}'",
                label="tier_consistency",
            )]

        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"Tier '{actual_tier}' matches score {v_score}",
            label="tier_consistency",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
