"""Evidence Quality evaluator for verification agent output (Tier 2).

LLM judge assessing whether evidence items are high quality:
- Source authenticity: real, accessible URLs or named data sources
- Finding specificity: concrete observations, not vague summaries
- Criteria linkage: clear link to a specific verification criterion
"""

import json
import logging
from typing import Optional

from strands import Agent
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)

EVIDENCE_QUALITY_RUBRIC = """You are evaluating the quality of evidence gathered by a verification agent.

PREDICTION: {prediction_text}

VERDICT: {verdict} (confidence: {confidence})

EVIDENCE GATHERED:
{evidence}

REASONING: {reasoning}

Evaluate the evidence on these dimensions:

1. SOURCE AUTHENTICITY: Are the source fields real, accessible URLs or named
   data sources (e.g., "python.org", "https://...", "USGS earthquake database")?
   Not fabricated, not vague ("the internet", "various sources").

2. FINDING SPECIFICITY: Are the finding fields concrete, specific observations?
   (e.g., "Python 3.13.0 listed on python.org/downloads as of March 25, 2026")
   Not vague summaries ("found relevant information", "confirmed the prediction").

3. CRITERIA LINKAGE: Does each relevant_to_criteria field clearly identify
   which specific verification criterion the evidence addresses?
   Not generic ("supports the verdict", "relevant evidence").

Score on a 0.0 to 1.0 scale:
- 1.0: All evidence items have real sources, specific findings, clear criteria links
- 0.7-0.9: Most evidence is high quality with minor vagueness
- 0.4-0.6: Mixed quality — some items are specific, others are vague
- 0.0-0.3: Poor quality — fabricated sources, vague findings, no criteria linkage

Return ONLY valid JSON: {{"score": <float>, "reasoning": "<explanation>"}}"""

JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"


def evaluate(result: dict, prediction_text: str = "") -> dict:
    """Assess evidence quality using LLM judge.

    Args:
        result: Dict from VerificationBackend.invoke() containing verdict,
                confidence, evidence, reasoning.
        prediction_text: Original prediction text for context.

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    evidence = result.get("evidence", [])
    evidence_formatted = json.dumps(evidence, indent=2) if evidence else "[]"

    prompt = EVIDENCE_QUALITY_RUBRIC.format(
        prediction_text=prediction_text or "(not provided)",
        verdict=result.get("verdict", "unknown"),
        confidence=result.get("confidence", "unknown"),
        evidence=evidence_formatted,
        reasoning=result.get("reasoning", "(not provided)"),
    )

    try:
        model = BedrockModel(model_id=JUDGE_MODEL)
        agent = Agent(
            model=model,
            system_prompt="You are an evaluation judge. Return only valid JSON.",
            callback_handler=None,
        )
        response = agent(prompt)
        parsed = json.loads(str(response))
        score = float(parsed.get("score", 0.0))
        reasoning = parsed.get("reasoning", "No reasoning provided")
        return {
            "score": max(0.0, min(1.0, score)),
            "pass": score >= 0.5,
            "reason": reasoning,
        }
    except Exception as e:
        logger.error(f"Evidence quality judge failed: {e}", exc_info=True)
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Judge invocation failed: {e}",
        }
