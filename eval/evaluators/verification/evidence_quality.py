"""Evidence Quality Evaluator — LLM judge via OutputEvaluator.

Replaces the hand-rolled verification_evidence_quality.py (~90 lines) with SDK OutputEvaluator.
"""

import json

from strands_evals.evaluators import OutputEvaluator

JUDGE_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

RUBRIC = """Evaluate the quality of evidence gathered by a verification agent.

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
- 0.0-0.3: Poor quality — fabricated sources, vague findings, no criteria linkage"""


def create_evidence_quality_evaluator() -> OutputEvaluator:
    """Create an OutputEvaluator configured for evidence quality."""
    return OutputEvaluator(
        rubric=RUBRIC,
        model=JUDGE_MODEL,
        include_inputs=True,
    )
