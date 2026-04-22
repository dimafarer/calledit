"""Schema Validity Evaluator — validates bundle against Pydantic models."""

import sys
import os

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput

# Add calleditv4/src to path for Pydantic model imports
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "calleditv4", "src")
)

from models import ParsedClaim, VerificationPlan, PlanReview  # noqa: E402

_MODEL_MAP = {
    "parsed_claim": ParsedClaim,
    "verification_plan": VerificationPlan,
    "plan_review": PlanReview,
}


class SchemaValidityEvaluator(Evaluator):
    """Validate creation bundle against ParsedClaim, VerificationPlan, PlanReview."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        bundle = (evaluation_case.actual_output or {}).get("creation_bundle")
        if not bundle or not isinstance(bundle, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No creation bundle", label="schema_validity",
            )]

        errors = []
        for key, model in _MODEL_MAP.items():
            try:
                model(**bundle.get(key, {}))
            except Exception as e:
                errors.append(f"{model.__name__}: {e}")

        if errors:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="; ".join(errors), label="schema_validity",
            )]
        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason="All models validate", label="schema_validity",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
