"""Intent Preservation Evaluator — LLM judge via OutputEvaluator.

Replaces the hand-rolled intent_preservation.py (~80 lines) with SDK OutputEvaluator.
"""

import json

from strands_evals.evaluators import OutputEvaluator

JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

RUBRIC = """Evaluate whether the AI agent faithfully preserved the user's
prediction intent when converting it into a structured verification plan.

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
- 0.0-0.3: Major drift — plan misrepresents or significantly alters the prediction"""


def create_intent_preservation_evaluator() -> OutputEvaluator:
    """Create an OutputEvaluator configured for intent preservation."""
    return OutputEvaluator(
        rubric=RUBRIC,
        model=JUDGE_MODEL,
        include_inputs=True,
    )
