"""Before-Date Verdict Evaluator — deadline logic for before_date mode."""

from datetime import datetime, timezone

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class BeforeDateVerdictEvaluator(Evaluator):
    """Evaluate verdict correctness for before_date verification mode.

    Before deadline: confirmed and inconclusive are valid, refuted is wrong.
    At/after deadline: verdict must match expected_output.
    Returns no-op for non-before_date modes.
    """

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        mode = (evaluation_case.metadata or {}).get("verification_mode")
        if mode != "before_date":
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — not before_date mode", label="before_date_verdict",
            )]

        qualifying = (evaluation_case.metadata or {}).get("qualifying", True)
        if not qualifying:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — non-qualifying case", label="before_date_verdict",
            )]

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="before_date_verdict",
            )]

        verdict = result.get("verdict")
        expected = evaluation_case.expected_output
        now = datetime.now(timezone.utc)

        vdate_str = (evaluation_case.metadata or {}).get("verification_date")
        if not vdate_str:
            bundle = (evaluation_case.actual_output or {}).get("creation_bundle", {})
            claim = bundle.get("parsed_claim", {})
            vdate_str = claim.get("verification_date")

        if vdate_str:
            try:
                vdate = datetime.fromisoformat(str(vdate_str).replace("Z", "+00:00"))
                if now < vdate:
                    # Before deadline: confirmed and inconclusive are OK
                    if verdict in ("confirmed", "inconclusive"):
                        return [EvaluationOutput(
                            score=1.0, test_pass=True,
                            reason=f"'{verdict}' is valid before deadline",
                            label="before_date_verdict",
                        )]
                    return [EvaluationOutput(
                        score=0.0, test_pass=False,
                        reason=f"'{verdict}' is invalid before deadline",
                        label="before_date_verdict",
                    )]
            except (ValueError, TypeError):
                pass

        # At/after deadline: exact match
        if expected is None:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="No expected output to compare", label="before_date_verdict",
            )]

        if verdict == expected:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason=f"Verdict '{verdict}' matches expected", label="before_date_verdict",
            )]
        return [EvaluationOutput(
            score=0.0, test_pass=False,
            reason=f"Verdict '{verdict}' != expected '{expected}'",
            label="before_date_verdict",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
