"""At-Date Verdict Evaluator — temporal logic for at_date verification mode."""

from datetime import datetime, timezone

from strands_evals.evaluators import Evaluator
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput


class AtDateVerdictEvaluator(Evaluator):
    """Evaluate verdict correctness for at_date verification mode.

    Before verification_date: inconclusive is correct.
    At/after verification_date: verdict must match expected_output.
    Returns no-op for non-at_date modes.
    """

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        mode = (evaluation_case.metadata or {}).get("verification_mode")
        if mode != "at_date":
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — not at_date mode", label="at_date_verdict",
            )]

        # Skip non-qualifying cases (no expected outcome, not verified)
        qualifying = (evaluation_case.metadata or {}).get("qualifying", True)
        if not qualifying:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="N/A — non-qualifying case", label="at_date_verdict",
            )]

        result = (evaluation_case.actual_output or {}).get("verification_result")
        if not result or not isinstance(result, dict):
            return [EvaluationOutput(
                score=0.0, test_pass=False,
                reason="No verification result", label="at_date_verdict",
            )]

        verdict = result.get("verdict")
        expected = evaluation_case.expected_output
        now = datetime.now(timezone.utc)

        # Parse verification_date from metadata or creation bundle
        vdate_str = (evaluation_case.metadata or {}).get("verification_date")
        if not vdate_str:
            bundle = (evaluation_case.actual_output or {}).get("creation_bundle", {})
            claim = bundle.get("parsed_claim", {})
            vdate_str = claim.get("verification_date")

        if vdate_str:
            try:
                vdate = datetime.fromisoformat(str(vdate_str).replace("Z", "+00:00"))
                if now < vdate:
                    # Before verification date: inconclusive is correct
                    if verdict == "inconclusive":
                        return [EvaluationOutput(
                            score=1.0, test_pass=True,
                            reason="Correctly inconclusive before verification date",
                            label="at_date_verdict",
                        )]
                    return [EvaluationOutput(
                        score=0.0, test_pass=False,
                        reason=f"Expected inconclusive before date, got {verdict}",
                        label="at_date_verdict",
                    )]
            except (ValueError, TypeError):
                pass

        # At/after verification date: exact match
        if expected is None:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason="No expected output to compare", label="at_date_verdict",
            )]

        if verdict == expected:
            return [EvaluationOutput(
                score=1.0, test_pass=True,
                reason=f"Verdict '{verdict}' matches expected", label="at_date_verdict",
            )]
        return [EvaluationOutput(
            score=0.0, test_pass=False,
            reason=f"Verdict '{verdict}' != expected '{expected}'", label="at_date_verdict",
        )]

    async def evaluate_async(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(evaluation_case)
