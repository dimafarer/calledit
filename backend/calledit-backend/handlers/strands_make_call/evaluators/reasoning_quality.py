"""ReasoningQuality Evaluator — LLM-as-Judge (Tier 2).

Uses a judge model to score reasoning quality, specificity, and soundness.
The judge model must differ from the agents being evaluated to avoid
self-evaluation bias.

Scores:
- Categorizer: Is category_reasoning sound and specific to the prediction?
- VB: Are verification steps actionable and prediction-specific (not boilerplate)?
- Review: Do clarification questions target actual ambiguity (not generic)?

The judge returns a JSON response with score (0.0-1.0) and reasoning.
"""

import json
import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# Default judge model — different from agent model (Sonnet 4) to avoid self-eval bias
# Using Opus for highest quality reasoning assessment. This is a dev-time eval tool,
# not a production hot path — latency and cost are not constraints.
DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-20250514-v1:0"
AGENT_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

JUDGE_PROMPTS = {
    "categorizer": """You are evaluating the reasoning quality of a prediction categorizer agent.

The agent classified a prediction into a verifiability category and provided reasoning.

PREDICTION: {prediction_text}
AGENT OUTPUT:
  Category: {category}
  Reasoning: {reasoning}

{rubric_section}

Score the reasoning on a scale of 0.0 to 1.0:
- 1.0: Reasoning is sound, specific to this prediction, and clearly explains why this category was chosen
- 0.7: Reasoning is correct but somewhat generic (could apply to many predictions)
- 0.4: Reasoning has logical gaps or is mostly boilerplate
- 0.0: Reasoning is wrong, contradictory, or completely generic

Return ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "your explanation"}}""",

    "verification_builder": """You are evaluating the quality of verification steps for a prediction.

PREDICTION: {prediction_text}
VERIFICATION METHOD:
  Sources: {sources}
  Criteria: {criteria}
  Steps: {steps}

{rubric_section}

Score the verification method on a scale of 0.0 to 1.0:
- 1.0: Steps are specific, actionable, and tailored to this exact prediction
- 0.7: Steps are reasonable but could be more specific to the prediction
- 0.4: Steps are generic boilerplate (e.g., "manual review needed")
- 0.0: Steps are irrelevant or nonsensical for this prediction

Return ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "your explanation"}}""",

    "review": """You are evaluating the quality of clarification questions for a prediction.

PREDICTION: {prediction_text}
CLARIFICATION QUESTIONS:
{questions}

{rubric_section}

Score the questions on a scale of 0.0 to 1.0:
- 1.0: Questions target the actual ambiguity in THIS prediction and would meaningfully improve it
- 0.7: Questions are relevant but somewhat generic (could apply to many predictions)
- 0.4: Questions are mostly generic ("what location?", "what time?") without targeting specific ambiguity
- 0.0: Questions are irrelevant or unhelpful

Return ONLY valid JSON: {{"score": 0.0-1.0, "reasoning": "your explanation"}}""",
}


def _invoke_judge(prompt: str, judge_model: str) -> dict:
    """Invoke the judge model and parse the JSON response."""
    client = boto3.client("bedrock-runtime", region_name="us-west-2")
    response = client.converse(
        modelId=judge_model,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"temperature": 0.0, "maxTokens": 500},
    )
    result_text = response["output"]["message"]["content"][0]["text"]
    return json.loads(result_text)


def _build_judge_prompt(agent_name: str, span_output: dict,
                        prediction_text: str, rubric: Optional[str]) -> str:
    """Build the judge prompt for a specific agent."""
    template = JUDGE_PROMPTS.get(agent_name)
    if not template:
        raise ValueError(f"No judge prompt for agent: {agent_name}")

    rubric_section = f"EVALUATION RUBRIC: {rubric}" if rubric else ""

    if agent_name == "categorizer":
        return template.format(
            prediction_text=prediction_text,
            category=span_output.get("verifiable_category", ""),
            reasoning=span_output.get("category_reasoning", ""),
            rubric_section=rubric_section,
        )
    elif agent_name == "verification_builder":
        vm = span_output.get("verification_method", {})
        return template.format(
            prediction_text=prediction_text,
            sources=vm.get("source", []),
            criteria=vm.get("criteria", []),
            steps=vm.get("steps", []),
            rubric_section=rubric_section,
        )
    elif agent_name == "review":
        questions = []
        for section in span_output.get("reviewable_sections", []):
            questions.extend(section.get("questions", []))
        questions_text = "\n".join(f"- {q}" for q in questions) or "No questions generated"
        return template.format(
            prediction_text=prediction_text,
            questions=questions_text,
            rubric_section=rubric_section,
        )


def evaluate_reasoning_quality(
    span_output: dict,
    agent_name: str,
    prediction_text: str,
    evaluation_rubric: Optional[str] = None,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    span_id: str = "",
) -> dict:
    """LLM-as-Judge evaluation of reasoning quality.

    Args:
        span_output: Parsed agent output dict.
        agent_name: "categorizer", "verification_builder", or "review".
        prediction_text: The original prediction text.
        evaluation_rubric: Optional rubric from golden dataset.
        judge_model: Model ID for the judge (must differ from agent model).
        span_id: Trace span ID for traceability.

    Returns:
        {"score": 0.0-1.0, "evaluator": "ReasoningQuality", "span_id": str,
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        prompt = _build_judge_prompt(agent_name, span_output, prediction_text, evaluation_rubric)
        judge_result = _invoke_judge(prompt, judge_model)

        score = float(judge_result.get("score", 0.0))
        score = max(0.0, min(1.0, score))
        reasoning = judge_result.get("reasoning", "No reasoning provided")

        return {
            "score": score,
            "evaluator": "ReasoningQuality",
            "span_id": span_id,
            "judge_reasoning": reasoning,
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(f"ReasoningQuality judge failed for {agent_name}: {e}", exc_info=True)
        return {
            "score": 0.0,
            "evaluator": "ReasoningQuality",
            "span_id": span_id,
            "judge_reasoning": f"Judge invocation failed: {e}",
            "judge_model": judge_model,
        }
