"""Tier 2: Intent Preservation — LLM judge for prediction intent fidelity.

Decision 126: Priority #1 metric. Does the parsed claim + verification plan
faithfully represent what the user actually predicted?
"""

import json
import logging

import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)

RUBRIC = """You are evaluating whether an AI agent faithfully preserved the user's
prediction intent when converting it into a structured verification plan.

ORIGINAL PREDICTION: {prediction_text}

PARSED CLAIM: {parsed_claim}

VERIFICATION PLAN: {verification_plan}

Evaluate on these dimensions:
1. FIDELITY: Does the parsed statement capture the user's actual prediction
   without reinterpretation, softening, or narrowing?
2. TEMPORAL INTENT: Is the verification date consistent with what the user meant?
3. SCOPE: Does the plan test exactly what the user predicted — not more, not less?
4. ASSUMPTIONS: Does the plan add assumptions not present in the original text?

Score on a 0.0 to 1.0 scale:
- 1.0: Perfect intent preservation — the plan tests exactly what the user meant
- 0.7-0.9: Minor drift — small reinterpretation but core intent preserved
- 0.4-0.6: Moderate drift — plan tests something related but not quite right
- 0.0-0.3: Major drift — plan misrepresents or significantly alters the prediction

Return ONLY valid JSON: {{"score": <float>, "reasoning": "<explanation>"}}"""


JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def evaluate(bundle: dict, prediction_text: str) -> dict:
    """Assess intent preservation using LLM judge.

    Args:
        bundle: The prediction bundle from the creation agent.
        prediction_text: The original user prediction text.

    Returns: {"score": float, "pass": bool, "reason": str}
    """
    prompt = RUBRIC.format(
        prediction_text=prediction_text,
        parsed_claim=json.dumps(bundle.get("parsed_claim", {}), indent=2),
        verification_plan=json.dumps(
            bundle.get("verification_plan", {}), indent=2
        ),
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
        logger.error(f"Intent preservation judge failed: {e}", exc_info=True)
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Judge invocation failed: {e}",
        }
