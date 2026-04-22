"""Verdict Validity Evaluator — checks verdict is confirmed/refuted/inconclusive."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified

VALID_VERDICTS = {"confirmed", "refuted", "inconclusive"}


class VerdictValidityEvaluator(Evaluator):
    """Check verdict is one of: confirmed, refuted, inconclusive."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verification_verdict_validity")
        if skip:
            return skip

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="verification_verdict_validity",
            )]

        verdict = result.get("verdict")
        if verdict in VALID_VERDICTS:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason=f"Valid verdict: {verdict}", label="verification_verdict_validity",
            )]
        return [EvaluationOutput(
            score=0.0, test_pass=False,
            reason=f"Invalid verdict: {verdict!r}", label="verification_verdict_validity",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
