"""Tier 2: Plan Quality — LLM judge for verification plan actionability.

Decision 126: Priority #2 metric. Are criteria measurable, sources real,
steps executable?
"""

import json
import logging

import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)

RUBRIC = """You are evaluating the quality of a verification plan created by an AI agent.
The plan should be actionable — a verification agent with web browser and code
interpreter tools should be able to execute it.

ORIGINAL PREDICTION: {prediction_text}

VERIFICATION PLAN:
  Sources: {sources}
  Criteria: {criteria}
  Steps: {steps}

VERIFIABILITY SCORE: {score} ({tier})

Evaluate on these dimensions:
1. CRITERIA SPECIFICITY: Are criteria measurable and unambiguous? Could you
   determine true/false from them without interpretation?
2. SOURCE ACCESSIBILITY: Are the sources real and accessible via web browser
   or code interpreter? Not hypothetical or paywalled?
3. STEP EXECUTABILITY: Are steps ordered logically? Could a verification agent
   follow them sequentially to reach a verdict?
4. LANGUAGE PRECISION: Is the plan free of vague terms like "check if it seems",
   "roughly", "approximately" without defined thresholds?

Score on a 0.0 to 1.0 scale:
- 1.0: Excellent plan — specific criteria, real sources, executable steps
- 0.7-0.9: Good plan — minor vagueness but fundamentally actionable
- 0.4-0.6: Weak plan — some criteria vague, sources questionable, steps unclear
- 0.0-0.3: Poor plan — criteria unmeasurable, sources fictional, steps unexecutable

Return ONLY valid JSON: {{"score": <float>, "reasoning": "<explanation>"}}"""


JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def evaluate(bundle: dict, prediction_text: str) -> dict:
    """Assess plan quality using LLM judge.

    Args:
        bundle: The prediction bundle from the creation agent.
        prediction_text: The original user prediction text.

    Returns: {"score": float, "pass": bool, "reason": str}
    """
    plan = bundle.get("verification_plan", {})
    review = bundle.get("plan_review", {})

    prompt = RUBRIC.format(
        prediction_text=prediction_text,
        sources=json.dumps(plan.get("sources", []), indent=2),
        criteria=json.dumps(plan.get("criteria", []), indent=2),
        steps=json.dumps(plan.get("steps", []), indent=2),
        score=review.get("verifiability_score", "N/A"),
        tier=review.get("score_tier", "N/A"),
    )

    try:
        model = BedrockModel(model_id=JUDGE_MODEL)
        agent = Agent(
            model=model,
            system_prompt="You are an evaluation judge. Return only valid JSON.",
            callback_handler=None,
        )
        response = agent(prompt)
        result = json.loads(str(response))
        score = float(result.get("score", 0.0))
        reasoning = result.get("reasoning", "No reasoning provided")
        return {
            "score": max(0.0, min(1.0, score)),
            "pass": score >= 0.5,
            "reason": reasoning,
        }
    except Exception as e:
        logger.error(f"Plan quality judge failed: {e}", exc_info=True)
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Judge invocation failed: {e}",
        }
