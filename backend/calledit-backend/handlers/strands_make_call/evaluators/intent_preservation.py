"""IntentPreservation Evaluator — Strands Evals SDK wrapper.

Scores whether the Verification Builder's criteria faithfully capture
the user's original prediction intent, stripping framing language
("I bet", "I think") to assess semantic equivalence.

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging
from typing import List

logger = logging.getLogger(__name__)

# Judge model must differ from agent model to avoid self-evaluation bias
DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

INTENT_RUBRIC = """
Evaluate whether the Verification Builder's criteria faithfully captures
the user's original prediction intent.

Key principles:
- Framing language ("I bet", "I think", "I predict") is NOT intent.
  "I bet the sun rises tomorrow" → intent is "the sun will rise tomorrow"
- The criteria should be checkable true/false conditions, not opinions
- The criteria must preserve the factual claim without losing meaning
- IMPORTANT: When a prediction uses vague or subjective language ("nice weather",
  "taste good", "go well"), the criteria SHOULD operationalize it into measurable
  conditions (e.g., temperature ranges, specific observable outcomes). This is
  intent preservation through clarification, not intent distortion. The VB's job
  is to make vague predictions verifiable.
- Compare the actual criteria against the expected criteria for semantic equivalence

Scoring:
- 1.0: Criteria captures the claim accurately, strips framing, operationalizes vague terms into measurable conditions
- 0.8: Criteria captures the core claim with minor differences from expected
- 0.5: Criteria partially captures intent but misses key nuance or is too literal
- 0.3: Criteria captures a related but different claim than what the user predicted
- 0.0: Criteria misrepresents the prediction or is completely wrong
"""


def evaluate_intent_preservation(
    prediction_text: str,
    vb_criteria: list,
    expected_criteria: List[str],
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether VB criteria captures the prediction's intent.

    Args:
        prediction_text: Original user prediction text.
        vb_criteria: Verification Builder's output criteria (list of strings or dicts).
        expected_criteria: Expected verification criteria from golden dataset.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "IntentPreservation",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=INTENT_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        eval_data = EvaluationData(
            input=f"PREDICTION: {prediction_text}",
            actual_output=json.dumps(vb_criteria) if isinstance(vb_criteria, list) else str(vb_criteria),
            expected_output=json.dumps(expected_criteria),
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "IntentPreservation",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "IntentPreservation",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(f"IntentPreservation judge failed: {type(e).__name__}: {e}")
        return {
            "score": 0.0,
            "evaluator": "IntentPreservation",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
