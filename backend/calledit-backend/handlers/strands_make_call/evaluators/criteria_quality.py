"""CriteriaQuality Evaluator — Strands Evals SDK wrapper.

Scores whether each criterion in the Verification_Plan's criteria field
contributed to a clear verdict in the Verification_Outcome, flagging
criteria that were too vague, unmeasurable, or ignored during execution.

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging

logger = logging.getLogger(__name__)

# Judge model must differ from agent model to avoid self-evaluation bias
DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

CRITERIA_QUALITY_RUBRIC = """
Evaluate whether the Verification Builder's criteria led to clear,
actionable verdicts during verification execution.

You are given:
- CRITERIA: The verification plan's criteria (what should be checked)
- EVIDENCE: The verification outcome's evidence and reasoning (what was actually found)

Evaluate three dimensions:

1. **Specificity**: Is each criterion specific enough to be checkable?
   - Good: "Temperature in NYC exceeds 80°F on July 4th"
   - Bad: "Weather is nice" (too vague to verify)

2. **Evidence Mapping**: Does the evidence map clearly to the criteria?
   - Good: Each criterion has corresponding evidence that addresses it
   - Bad: Evidence is generic and doesn't address specific criteria

3. **Completeness**: Were any criteria ignored or unmeasurable?
   - Good: All criteria were addressed in the outcome
   - Bad: Some criteria have no corresponding evidence or reasoning

Scoring:
- 1.0: All criteria are specific, each has clear evidence, none were ignored
- 0.8: Most criteria are well-formed with minor gaps in evidence mapping
- 0.5: Some criteria are vague or lack corresponding evidence
- 0.3: Many criteria are unmeasurable or ignored in the outcome
- 0.0: Criteria are entirely vague or completely disconnected from evidence
"""


def evaluate_criteria_quality(
    verification_plan: dict,
    verification_outcome: dict,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether VB criteria led to clear verdicts.

    Args:
        verification_plan: Dict with source, criteria, and steps fields.
        verification_outcome: Dict with status, confidence, evidence,
            reasoning, and tools_used fields.
        judge_model: Model ID for the judge.

    Returns:
        {"score": float, "evaluator": "CriteriaQuality",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=CRITERIA_QUALITY_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        criteria = verification_plan.get("criteria", [])
        evidence = verification_outcome.get("evidence", [])
        reasoning = verification_outcome.get("reasoning", "")
        status = verification_outcome.get("status", "")
        confidence = verification_outcome.get("confidence", "")

        eval_data = EvaluationData(
            input=f"CRITERIA: {json.dumps(criteria)}",
            actual_output=json.dumps({
                "status": status,
                "confidence": confidence,
                "evidence": evidence,
                "reasoning": reasoning,
            }),
            expected_output="All criteria should be specific, measurable, "
                "and clearly addressed by the evidence with no criteria ignored.",
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "CriteriaQuality",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "CriteriaQuality",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(f"CriteriaQuality judge failed: {type(e).__name__}: {e}")
        return {
            "score": 0.0,
            "evaluator": "CriteriaQuality",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
