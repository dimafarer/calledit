"""CriteriaMethodAlignment Evaluator — Strands Evals SDK wrapper.

Scores whether the Verification Builder's method provides a realistic,
actionable plan to determine true/false given the stated criteria.

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

ALIGNMENT_RUBRIC = """
Evaluate whether the Verification Builder's method provides a realistic,
actionable plan to verify the stated criteria as true or false.

Key principles:
- The method should reference specific, accessible data sources appropriate for the criteria
- "Ask the user" should be a fallback, not the primary approach when public data sources exist
- The method should include WHEN to verify (timing matters)
- The method should gracefully degrade: if the ideal tool isn't available, describe alternatives
- Compare the actual method against the expected method for approach alignment

Scoring:
- 1.0: Method identifies specific data sources, timing, and a concrete verification plan matching expected approach
- 0.8: Method has the right approach but is less specific than expected (e.g., "check a weather service" vs "query OpenWeatherMap API")
- 0.5: Method is partially correct but missing key elements (wrong data source, no timing, or overly generic)
- 0.3: Method defaults to "ask the user" when automated verification is clearly possible
- 0.0: Method would fail to verify the criteria or is completely irrelevant
"""


def evaluate_criteria_method_alignment(
    vb_criteria: list,
    vb_method: dict,
    expected_method: str,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether VB method provides a realistic verification plan.

    Args:
        vb_criteria: Verification Builder's output criteria.
        vb_method: Verification Builder's output method (dict with source, steps, etc.).
        expected_method: Expected verification method from golden dataset.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "CriteriaMethodAlignment",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=ALIGNMENT_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        # Format the actual output as criteria + method together
        actual = json.dumps({
            "criteria": vb_criteria if isinstance(vb_criteria, list) else [str(vb_criteria)],
            "method": vb_method if isinstance(vb_method, dict) else {"description": str(vb_method)},
        })

        eval_data = EvaluationData(
            input=f"VERIFICATION CRITERIA: {json.dumps(vb_criteria)}",
            actual_output=actual,
            expected_output=expected_method,
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "CriteriaMethodAlignment",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "CriteriaMethodAlignment",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(f"CriteriaMethodAlignment judge failed: {type(e).__name__}: {e}")
        return {
            "score": 0.0,
            "evaluator": "CriteriaMethodAlignment",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
