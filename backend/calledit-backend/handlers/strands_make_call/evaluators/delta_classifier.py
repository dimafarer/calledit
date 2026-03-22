"""Delta Classification — lightweight Bedrock converse call.

Classifies WHY a plan-execution delta occurred for deterministic evaluators
(ToolAlignment, SourceAccuracy) when score < 1.0.

Uses direct boto3 bedrock-runtime converse call (not Strands Evals SDK)
to keep it lightweight — just a classification prompt, not a full rubric.

Returns one of: "plan_error", "new_information", "tool_drift", or None on failure.
"""

import json
import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

VALID_CLASSIFICATIONS = {"plan_error", "new_information", "tool_drift"}

DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

CLASSIFICATION_PROMPT = """You are classifying WHY a verification plan diverged from actual execution.

The Verification Builder planned certain {plan_field}, but the Verification Executor used different ones.

PLANNED: {planned_items}
ACTUAL: {actual_items}

EXECUTOR REASONING: {reasoning}

Classify the root cause as exactly ONE of:
- plan_error: The plan specified something that couldn't be executed as written (wrong name, unavailable resource)
- new_information: The executor found better or different information than planned (adaptive behavior)
- tool_drift: The executor used different items than planned for no clear reason

Return ONLY valid JSON: {{"classification": "plan_error"|"new_information"|"tool_drift"}}"""


def classify_delta(
    plan_field: str,
    planned_items: list,
    actual_items: list,
    reasoning: str,
    model: str = DEFAULT_MODEL,
) -> Optional[str]:
    """Classify WHY a plan-execution delta occurred.

    Args:
        plan_field: What diverged (e.g., "tools", "sources").
        planned_items: Items from the verification plan.
        actual_items: Items from the verification outcome.
        reasoning: The executor's reasoning for its choices.
        model: Bedrock model ID for classification.

    Returns:
        One of "plan_error", "new_information", "tool_drift", or None on failure.
    """
    try:
        prompt = CLASSIFICATION_PROMPT.format(
            plan_field=plan_field,
            planned_items=json.dumps(planned_items),
            actual_items=json.dumps(actual_items),
            reasoning=reasoning or "No reasoning provided",
        )

        client = boto3.client("bedrock-runtime", region_name="us-west-2")
        response = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 100},
        )

        result_text = response["output"]["message"]["content"][0]["text"]
        result = json.loads(result_text)
        classification = result.get("classification", "")

        if classification in VALID_CLASSIFICATIONS:
            return classification

        logger.warning(
            "Delta classification returned invalid value: %s", classification
        )
        return None

    except Exception as e:
        logger.warning("Delta classification failed: %s: %s", type(e).__name__, e)
        return None
