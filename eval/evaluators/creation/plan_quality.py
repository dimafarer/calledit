"""Plan Quality Evaluator — LLM judge via OutputEvaluator.

Replaces the hand-rolled plan_quality.py (~80 lines) with SDK OutputEvaluator.
"""

import json

from strands_evals.evaluators import OutputEvaluator

JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

RUBRIC = """Evaluate the quality of a verification plan created by an AI agent.
The plan should be actionable — a verification agent with web browser and code
interpreter tools should be able to execute it.

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
- 0.0-0.3: Poor plan — criteria unmeasurable, sources fictional, steps unexecutable"""


def create_plan_quality_evaluator() -> OutputEvaluator:
    """Create an OutputEvaluator configured for plan quality."""
    return OutputEvaluator(
        rubric=RUBRIC,
        model=JUDGE_MODEL,
        include_inputs=True,
    )
