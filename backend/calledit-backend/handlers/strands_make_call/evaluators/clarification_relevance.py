"""ClarificationRelevance Evaluator — LLM judge for the ReviewAgent.

Scores whether the ReviewAgent's clarification questions target the
Verification Builder's specific operationalization assumptions rather
than being generic. Replaces ClarificationQuality (keyword-based) as
the primary review evaluation.

Good questions: "Do you consider 60°F a nice day?" (targets specific
Verification Builder assumption about temperature threshold)
Bad questions: "What location?" (generic, could apply to any prediction)

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

CLARIFICATION_RELEVANCE_RUBRIC = """
Evaluate whether the ReviewAgent's clarification questions target the
Verification Builder's specific operationalization assumptions, rather
than being generic.

The ReviewAgent's job is to catch when the Verification Builder made
assumptions that need user validation. Good questions target specific
Verification Builder assumptions. Bad questions are generic
("what location?", "what time?") that could apply to any prediction.

Context provided:
- The prediction text
- The Verification Builder's verification criteria (with operationalized
  assumptions)
- The ReviewAgent's clarification questions

Scoring:
- 1.0: Questions directly target specific Verification Builder assumptions.
       E.g., if Verification Builder operationalized "nice weather" as
       "60-80°F, sunny", the question asks "Do you consider 60°F nice?"
- 0.8: Questions are relevant to the Verification Builder's plan but not
       laser-focused on specific assumptions (e.g., "What weather
       conditions matter to you?")
- 0.5: Mix of targeted and generic questions
- 0.3: Mostly generic questions that don't reference the Verification
       Builder's specific plan
- 0.0: Questions are irrelevant or would not improve the verification
       plan if answered
"""


def evaluate_clarification_relevance(
    prediction_text: str,
    vb_criteria: List,
    review_output: dict,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether ReviewAgent questions target Verification Builder assumptions.

    Args:
        prediction_text: Original raw prediction text.
        vb_criteria: Verification Builder's criteria list (the assumptions
            the ReviewAgent should be questioning).
        review_output: ReviewAgent's output dict containing
            reviewable_sections with questions.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "ClarificationRelevance",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        # Collect all questions from reviewable sections
        questions = []
        for section in review_output.get("reviewable_sections", []):
            questions.extend(section.get("questions", []))

        evaluator = OutputEvaluator(
            rubric=CLARIFICATION_RELEVANCE_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        eval_data = EvaluationData(
            input=(
                f"PREDICTION: {prediction_text}\n"
                f"VERIFICATION BUILDER CRITERIA: {json.dumps(vb_criteria)}"
            ),
            actual_output=json.dumps(questions),
            expected_output=(
                "Questions should target specific Verification Builder "
                "operationalization assumptions"
            ),
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "ClarificationRelevance",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "ClarificationRelevance",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(
            f"ClarificationRelevance judge failed: "
            f"{type(e).__name__}: {e}"
        )
        return {
            "score": 0.0,
            "evaluator": "ClarificationRelevance",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
