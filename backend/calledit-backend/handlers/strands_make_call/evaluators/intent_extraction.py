"""IntentExtraction Evaluator — LLM judge for the Parser agent.

Scores whether the Parser correctly extracted the factual claim from the
raw prediction, giving the Verification Builder clean intent to work with.

The Parser's job is to:
- Strip framing language: "I bet", "I think", "I predict" are framing, not intent
- Resolve temporal references: "tomorrow" → concrete date, "next week" → date range
- Preserve the factual claim without distortion or addition

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

INTENT_EXTRACTION_RUBRIC = """
Evaluate whether the Parser correctly extracted the factual claim from the
raw prediction, giving the Verification Builder clean intent to work with.

The Parser's job is to:
- Strip framing language: "I bet", "I think", "I predict" are framing, not intent
- Resolve temporal references: "tomorrow" → concrete date, "next week" → date range
- Preserve the factual claim without distortion or addition

Context: The Parser's output feeds directly into the Categorizer and
Verification Builder. If the Parser loses temporal info or keeps framing
language, the Verification Builder builds a plan for the wrong thing.

Scoring:
- 1.0: Factual claim extracted cleanly, framing stripped, temporal refs
       resolved to concrete dates
- 0.8: Claim extracted correctly but temporal resolution is approximate
       (e.g., "tomorrow" kept as relative instead of resolved to YYYY-MM-DD)
- 0.5: Claim partially extracted — some framing kept or key detail lost
- 0.3: Claim distorted — meaning changed from what user intended
- 0.0: Parser output doesn't represent the user's prediction at all
"""


def evaluate_intent_extraction(
    prediction_text: str,
    parser_output: dict,
    expected_criteria: List[str],
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether the Parser extracted the factual claim cleanly.

    Args:
        prediction_text: Original raw prediction text from the user.
        parser_output: Parser agent's structured output dict (should contain
            prediction_statement, prediction_date, date_reasoning).
        expected_criteria: Expected verification criteria from golden dataset
            ground truth — used as reference for what the claim should be.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "IntentExtraction",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=INTENT_EXTRACTION_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        eval_data = EvaluationData(
            input=f"RAW PREDICTION: {prediction_text}",
            actual_output=json.dumps(parser_output),
            expected_output=json.dumps(expected_criteria),
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "IntentExtraction",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "IntentExtraction",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(f"IntentExtraction judge failed: {type(e).__name__}: {e}")
        return {
            "score": 0.0,
            "evaluator": "IntentExtraction",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
