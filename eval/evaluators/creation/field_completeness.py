"""Field Completeness Evaluator — checks key list fields are non-empty."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class FieldCompletenessEvaluator(Evaluator):
    """Check sources, criteria, steps are non-empty lists in verification_plan."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="field_completeness",
            )]

        plan = bundle.get("verification_plan", {})
        empty_fields = []

        for field in ("sources", "criteria", "steps"):
            val = plan.get(field, [])
            if not isinstance(val, list) or len(val) == 0:
                empty_fields.append(field)

        if empty_fields:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason=f"Empty fields: {', '.join(empty_fields)}",
                label="field_completeness",
            )]
        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason="All list fields non-empty", label="field_completeness",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
