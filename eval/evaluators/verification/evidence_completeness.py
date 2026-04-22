"""Evidence Completeness Evaluator — checks at least 1 evidence item."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified


class EvidenceCompletenessEvaluator(Evaluator):
    """Verify evidence list contains at least 1 item."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verification_evidence_completeness")
        if skip:
            return skip

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result",
                label="verification_evidence_completeness",
            )]

        evidence = result.get("evidence", [])
        if not isinstance(evidence, list) or len(evidence) == 0:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No evidence items",
                label="verification_evidence_completeness",
            )]

        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"{len(evidence)} evidence items",
            label="verification_evidence_completeness",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
