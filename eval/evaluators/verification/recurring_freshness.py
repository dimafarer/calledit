"""Recurring Freshness Evaluator — evidence source field coverage."""

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class RecurringFreshnessEvaluator(Evaluator):
    """Evaluate evidence freshness for recurring verification mode.

    Score = fraction of evidence items with non-empty source fields.
    Returns no-op for non-recurring modes.
    """

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        mode = (evaluation_case.metadata or {}).get("verification_mode")
        if mode != "recurring":
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — not recurring mode", label="recurring_freshness",
            )]

        qualifying = (evaluation_case.metadata or {}).get("qualifying", True)
        if not qualifying:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — non-qualifying case", label="recurring_freshness",
            )]

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="recurring_freshness",
            )]

        evidence = result.get("evidence", [])
        if not isinstance(evidence, list) or len(evidence) == 0:
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No evidence items", label="recurring_freshness",
            )]

        with_source = sum(
            1 for item in evidence
            if isinstance(item, dict) and item.get("source")
        )
        score = with_source / len(evidence)

        return [EvaluationOutput(
            score=score,
            test_pass=score > 0.0,
            reason=f"{with_source}/{len(evidence)} evidence items have source",
            label="recurring_freshness",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
