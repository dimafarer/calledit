"""Evidence Structure Evaluator — checks each evidence item has required fields."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.utils import skip_if_not_verified

REQUIRED_FIELDS = ("source", "finding", "relevant_to_criteria")


class EvidenceStructureEvaluator(Evaluator):
    """Verify each evidence item has source, finding, relevant_to_criteria."""

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        skip = skip_if_not_verified(evaluation_case, "verification_evidence_structure")
        if skip:
            return skip

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result",
                label="verification_evidence_structure",
            )]

        evidence = result.get("evidence", [])
        if not isinstance(evidence, list):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="evidence is not a list",
                label="verification_evidence_structure",
            )]

        errors = []
        for i, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"evidence[{i}] is not a dict")
                continue
            for field in REQUIRED_FIELDS:
                if field not in item:
                    errors.append(f"evidence[{i}] missing '{field}'")

        if errors:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="; ".join(errors),
                label="verification_evidence_structure",
            )]
        return [EvaluationOutput(
            score=1.0, test_pass=True,
            reason=f"All {len(evidence)} evidence items valid",
            label="verification_evidence_structure",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
