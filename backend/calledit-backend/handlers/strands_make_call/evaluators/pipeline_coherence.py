"""PipelineCoherence Evaluator — LLM judge for cross-agent coherence.

Scores whether agents in the pipeline built on each other's work to
produce a coherent verification plan, or whether they worked in silos
re-interpreting the prediction from scratch (the "silo problem").

Adapts to any number of agents — for a single-agent backend it scores
internal coherence of the response sections; for a 4-agent backend it
scores inter-agent coherence.

Critical for architecture comparison: the serial graph may score low
(silo problem) while the single agent scores high (one context).

Uses Strands Evals SDK OutputEvaluator for judge invocation.
"""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "us.anthropic.claude-opus-4-6-v1"

PIPELINE_COHERENCE_RUBRIC = """
Evaluate whether the agents in this pipeline built on each other's work
to produce a coherent verification plan, or whether they worked in silos
re-interpreting the prediction from scratch.

For multi-agent pipelines: check that each agent's output references or
builds on the previous agent's output. The chain should be:
- Parser extracts claim + resolves dates
- Categorizer uses parser's claim and dates to determine verification path
- Verification Builder uses categorizer's reasoning and parser's dates
  to build the plan
- ReviewAgent targets gaps in the Verification Builder's specific plan,
  not the original prediction

For single-agent pipelines: check that the response sections are
internally coherent (dates in parsing section match dates in verification
plan, category reasoning aligns with verification method chosen, etc.)

Scoring:
- 1.0: Clear chain of reasoning — each step builds on the previous.
       Dates, claims, and reasoning flow coherently through the pipeline.
- 0.8: Mostly coherent but one agent slightly re-interprets instead of
       building on predecessor (e.g., Verification Builder uses a slightly
       different date than parser extracted).
- 0.5: Some agents build on predecessors, others re-interpret from
       scratch. Mixed.
- 0.3: Agents mostly work in silos — each re-analyzes the original
       prediction independently, leading to inconsistencies.
- 0.0: Agents contradict each other (e.g., parser says date is March 18,
       Verification Builder says verify on March 20 with no explanation).
"""


def evaluate_pipeline_coherence(
    prediction_text: str,
    agent_outputs: Dict[str, Any],
    final_output: dict,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Score cross-agent coherence — does each agent build on the previous?

    Args:
        prediction_text: Original raw prediction text.
        agent_outputs: Dict of per-agent outputs. Keys vary by backend
            (e.g., parser/categorizer/verification_builder/review for serial,
            just "agent" for single-agent).
        final_output: The pipeline's final merged output.
        judge_model: Model ID for the judge.

    Returns:
        {"score": 0.0-1.0, "evaluator": "PipelineCoherence",
         "judge_reasoning": str, "judge_model": str}
    """
    try:
        from strands_evals.evaluators import OutputEvaluator
        from strands_evals.types import EvaluationData

        evaluator = OutputEvaluator(
            rubric=PIPELINE_COHERENCE_RUBRIC,
            model=judge_model,
            include_inputs=True,
        )

        eval_data = EvaluationData(
            input=(
                f"PREDICTION: {prediction_text}\n"
                f"ARCHITECTURE AGENTS: {list(agent_outputs.keys())}"
            ),
            actual_output=json.dumps({
                "agent_outputs": agent_outputs,
                "final_output": final_output,
            }),
            expected_output=(
                "Coherent chain of reasoning from first agent to last"
            ),
        )

        results = evaluator.evaluate(eval_data)
        result = results[0] if results else None

        if result is None:
            return {
                "score": 0.0,
                "evaluator": "PipelineCoherence",
                "judge_reasoning": "SDK returned no evaluation results",
                "judge_model": judge_model,
            }

        score = max(0.0, min(1.0, float(result.score)))
        return {
            "score": score,
            "evaluator": "PipelineCoherence",
            "judge_reasoning": result.reason or "No reasoning provided",
            "judge_model": judge_model,
        }

    except Exception as e:
        logger.error(
            f"PipelineCoherence judge failed: {type(e).__name__}: {e}"
        )
        return {
            "score": 0.0,
            "evaluator": "PipelineCoherence",
            "judge_reasoning": f"SDK invocation failed: {e}",
            "judge_model": judge_model,
        }
