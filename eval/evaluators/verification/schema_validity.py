"""Verification Schema Evaluator — checks verdict/confidence/evidence/reasoning types."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified


class VerificationSchemaEvaluator(Evaluator):
    """Check verification result has required fields with correct types."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verification_schema_validity")
        if skip:
            return skip

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="verification_schema_validity",
            )]

        errors = []
        if not isinstance(result.get("verdict"), str):
            errors.append("verdict must be str")
        if not isinstance(result.get("confidence"), (int, float)):
            errors.append("confidence must be float")
        if not isinstance(result.get("evidence"), list):
            errors.append("evidence must be list")
        if not isinstance(result.get("reasoning"), str):
            errors.append("reasoning must be str")

        if errors:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="; ".join(errors), label="verification_schema_validity",
            )]
        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason="All fields valid", label="verification_schema_validity",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
