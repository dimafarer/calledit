"""Date Resolution Evaluator — checks verification_date is valid ISO 8601."""

from datetime import datetime

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class DateResolutionEvaluator(Evaluator):
    """Verify verification_date is a valid ISO 8601 datetime string."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="date_resolution",
            )]

        claim = bundle.get("parsed_claim", {})
        date_str = claim.get("verification_date")

        if not date_str or not isinstance(date_str, str):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"verification_date missing or not a string: {date_str!r}",
                label="date_resolution",
            )]

        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason=f"Valid ISO 8601: {date_str}", label="date_resolution",
            )]
        except (ValueError, TypeError):
            pass

        return [EvaluationOutput(
            score=0.0, test_pass=False,
            reason=f"Invalid ISO 8601 date: {date_str!r}", label="date_resolution",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
