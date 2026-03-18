"""CategorizationJustification Evaluator — LLM judge for the Categorizer agent.

Scores whether the Categorizer's routing decision sets up the Verification
Builder to produce the best possible verification plan. This is NOT about
whether the category label matches a ground truth label — it's about whether
the routing decision enables the Verification Builder to build the most
automated, actionable verification plan given the available tools.

Per Decision 44: category labels are routing hints. The real question is
whether the routing led to a good Verification Builder output.

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

CATEGORIZATION_JUSTIFICATION_RUBRIC = """
Evaluate whether the Categorizer's routing decision sets up the Verification
Builder to produce the best possible verification plan.

This is NOT about whether the category label matches a ground truth label.
It's about whether the routing decision enables the Verification Builder to
build the most automated, actionable verification plan given the available tools.

Context provided:
- Parser's extracted claim (what the categorizer received as input)
- Categorizer's output (category + reasoning)
- Tool manifest (what tools are available)
- Verification Builder's actual output (to assess downstream impact)

Scoring:
- 1.0: Routing decision clearly enables the Verification Builder to build the
       best plan. The category correctly reflects what's automatable given
       available tools, and the Verification Builder produced a strong plan.
- 0.8: Routing is reasonable but a different category might have led to a
       slightly better Verification Builder plan (e.g., categorized as
       automatable when auto_verifiable was possible with available tools,
       but Verification Builder still produced a decent plan).
- 0.5: Routing is defensible but the Verification Builder's plan suffers
       because of it (e.g., categorized as human_only when tools could
       partially automate verification).
- 0.3: Routing actively misled the Verification Builder — the Verification
       Builder built a plan for the wrong verification path.
- 0.0: Routing is completely wrong and the Verification Builder's plan is
       useless as a result.
"""


def evaluate_categorization_justification(
    parser_output: dict,
    categorizer_output: dict,
    tool_manifest: str,
    final_output: dict,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score whether the Categorizer's routing enables a good Verification Builder plan.

    Args:
        parser_output: Parser agent's output (prediction_statement, dates).
        categorizer_output: Categorizer's output (category + reasoning).
        tool_manifest: Available tools string for context.
        final_output: The pipeline's final output including Verification Builder
            results — used to assess downstream impact of the routing decision.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "CategorizationJustification",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=CATEGORIZATION_JUSTIFICATION_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        # Build context showing what the categorizer had to work with
        # and what the Verification Builder produced as a result
        context = json.dumps({
            "parser_claim": parser_output.get("prediction_statement", ""),
            "parser_date": parser_output.get("prediction_date", ""),
            "tool_manifest": tool_manifest,
            "vb_criteria": final_output.get(
                "verification_method", {}
            ).get("criteria", []),
            "vb_method": final_output.get("verification_method", {}),
        })

        eval_data = EvaluationData(
            input=f"CONTEXT: {context}",
            actual_output=json.dumps(categorizer_output),
            expected_output=(
                "Routing should enable the best possible verification plan"
            ),
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "CategorizationJustification",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "CategorizationJustification",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(
            f"CategorizationJustification judge failed: "
            f"{type(e).__name__}: {e}"
        )
        return {
            "score": 0.0,
            "evaluator": "CategorizationJustification",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
