"""StepFidelity Evaluator — Strands Evals SDK wrapper.

Scores whether the Verification Executor's execution followed the
sequence and intent of the Verification Plan's steps field.

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Judge model must differ from agent model to avoid self-evaluation bias
DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

VALID_DELTA_CLASSIFICATIONS = {"plan_error", "new_information", "tool_drift"}

STEP_FIDELITY_RUBRIC = """
Evaluate whether the Verification Executor's execution followed the
sequence and intent of the Verification Plan's steps.

You are given:
- PLANNED STEPS: The verification plan's steps (what should be done, in order)
- EXECUTION EVIDENCE: The verification outcome's evidence, reasoning, and tools used

Evaluate three dimensions:

1. **Step Completion**: Was each planned step attempted?
   - Good: All planned steps have corresponding evidence of execution
   - Bad: Some planned steps were never attempted

2. **Step Ordering**: Were steps executed in the planned order?
   - Good: Evidence shows steps were followed sequentially as planned
   - Bad: Steps were executed out of order or in a jumbled sequence

3. **No Critical Skips**: Were any critical steps skipped entirely?
   - Good: No important steps were omitted from execution
   - Bad: Key verification steps were skipped, undermining the result

Scoring:
- 1.0: All steps attempted in order, no critical steps skipped
- 0.8: Most steps followed with minor ordering differences
- 0.5: Some steps skipped or significantly reordered
- 0.3: Many steps skipped or execution diverged substantially from plan
- 0.0: Execution bears no resemblance to the planned steps

IMPORTANT — Delta Classification:
When your score is LESS THAN 1.0, you MUST include exactly one of these
classifications in your reasoning, prefixed with "DELTA_CLASSIFICATION:":
- DELTA_CLASSIFICATION: plan_error — The plan was flawed or impossible to execute as written
- DELTA_CLASSIFICATION: new_information — The executor adapted because new information emerged
- DELTA_CLASSIFICATION: tool_drift — The executor deviated from the plan for no clear reason

When your score IS 1.0, do NOT include a DELTA_CLASSIFICATION line.
"""


def _extract_delta_classification(reasoning: str, score: float) -> str | None:
    """Extract delta_classification from judge reasoning text.

    Returns None when score == 1.0 or classification not found.
    """
    if score >= 1.0:
        return None

    match = re.search(
        r"DELTA_CLASSIFICATION:\s*(plan_error|new_information|tool_drift)",
        reasoning,
        re.IGNORECASE,
    )
    if match:
        classification = match.group(1).lower()
        if classification in VALID_DELTA_CLASSIFICATIONS:
            return classification

    return None


def evaluate_step_fidelity(
    verification_plan: dict,
    verification_outcome: dict,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether execution followed planned steps.

    Args:
        verification_plan: Dict with source, criteria, and steps fields.
        verification_outcome: Dict with status, confidence, evidence,
            reasoning, and tools_used fields.
        judge_model: Model ID for the judge.

    Returns:
        {"score": float, "evaluator": "StepFidelity",
         "judge_reasoning": str, "judge_model": str,
         "delta_classification": str|None}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=STEP_FIDELITY_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        steps = verification_plan.get("steps", [])
        evidence = verification_outcome.get("evidence", [])
        reasoning = verification_outcome.get("reasoning", "")
        tools_used = verification_outcome.get("tools_used", [])

        eval_data = EvaluationData(
            input=f"PLANNED STEPS: {json.dumps(steps)}",
            actual_output=json.dumps({
                "evidence": evidence,
                "reasoning": reasoning,
                "tools_used": tools_used,
            }),
            expected_output="All planned steps should be attempted in order "
                "with no critical steps skipped.",
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "StepFidelity",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
                "delta_classification": None,
            }

        score = max(0.0, min(1.0, float(result.score)))
        judge_reasoning = result.reason or "No reasoning provided"
        delta_classification = _extract_delta_classification(judge_reasoning, score)

        return {
            "score": score,
            "evaluator": "StepFidelity",
            "judge_reasoning": judge_reasoning,
            "judge_model": judge_model,
            "delta_classification": delta_classification,
        }

    except Exception as e:
        logger.error(f"StepFidelity judge failed: {type(e).__name__}: {e}")
        return {
            "score": 0.0,
            "evaluator": "StepFidelity",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
            "delta_classification": None,
        }
