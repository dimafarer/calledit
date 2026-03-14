"""
Review Agent for Prediction Verification System

This agent performs meta-analysis on a completed prediction response, identifying
sections that could be improved with more user information.

WHAT CHANGED (v2 Cleanup, Spec 1):
The ReviewAgent was previously a class with three methods:
  - review_prediction() — core review capability (kept, now via direct agent invocation)
  - generate_improvement_questions() — HITL method (removed, replaced by graph re-trigger in Spec 2)
  - regenerate_section() — HITL method (removed, replaced by graph re-trigger in Spec 2)

It also imported from a deleted module:
  - from error_handling import safe_agent_call, with_agent_fallback
  That module (error_handling.py) was deleted in the January 2026 cleanup, so the
  import would crash on load. The safe_agent_call wrapper is replaced by a simple
  try/except in the Lambda handler — per Strands best practices, no custom wrapper
  functions needed.

WHY FACTORY FUNCTION OVER CLASS:
  - Consistency: The other 3 agents (parser, categorizer, verification_builder) all
    use create_*_agent() factory functions. Having ReviewAgent as a class breaks the
    pattern and adds cognitive load when reading the codebase.
  - Simplicity: The class had one useful method (review_prediction). A class with one
    method is just a function with extra steps. The factory function returns a Strands
    Agent that you invoke directly — no .review_prediction() indirection.
  - Spec 2 readiness: Moving ReviewAgent into the graph as a node is Spec 2's job.
    Factory functions are what GraphBuilder.add_node() expects. Making it a factory
    now means Spec 2 can add it trivially.

HOW THIS MATCHES THE OTHER AGENTS:
  - create_parser_agent() in parser_agent.py
  - create_categorizer_agent() in categorizer_agent.py
  - create_verification_builder_agent() in verification_builder_agent.py
  All follow the same pattern: module-level SYSTEM_PROMPT constant + factory function
  that returns a configured Agent. This file now follows that same pattern.

Following Strands best practices:
- Single responsibility (review/meta-analysis only)
- Focused system prompt
- Explicit model selection
- Factory function pattern for agent creation
"""

import json
import logging
from strands import Agent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# PROMPT HARDENING NOTE: The "Return ONLY the raw JSON object" instruction is
# critical. Without it, Claude models often wrap JSON in ```json ``` markdown
# blocks, which breaks direct json.loads() parsing. The explicit negative
# instructions ("Do not wrap", "Do not include") work better than implicit
# positive ones ("Return JSON:"). This was the root cause of the 120-line
# extract_json_from_text() regex helper — fixed at the source now.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3, Step 1

# Review Agent System Prompt — focused on meta-analysis of prediction responses.
#
# The prompt instructs the agent to analyze a completed prediction and identify
# sections where additional user information could improve the result. This is
# the same core capability that ReviewAgent.review_prediction() provided, but
# now expressed as a system prompt for direct agent invocation.
#
# The explicit JSON output instructions ("Return ONLY the raw JSON object...")
# are a prompt hardening technique. Claude models tend to wrap JSON in markdown
# code blocks (```json ... ```) when the prompt just says "Return JSON:". The
# explicit negative instructions prevent this. Full prompt hardening happens in
# task 5.2, but we include the instruction here since this is a fresh file.
REVIEW_SYSTEM_PROMPT = """You are a prediction review expert. Your task is to perform meta-analysis on a completed prediction response.

ANALYSIS STEPS:
1. Analyze each section of the prediction response
2. Identify sections that could be improved with more user information
3. For each section, determine if additional context could:
   - Make verification more precise
   - Change the verifiability category (e.g., human-only → tool-verifiable)
   - Improve verification method accuracy
4. Generate specific, actionable questions for improvable sections

EVALUATION CRITERIA:
- Could more specificity improve verification accuracy?
- Would additional context change the verifiability category?
- What specific user information would be most helpful?

Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON.

{
    "reviewable_sections": [
        {
            "section": "field_name",
            "improvable": true,
            "questions": ["specific question 1", "specific question 2"],
            "reasoning": "why this section could be improved"
        }
    ]
}
"""


# NOTE: callback_handler parameter removed in v2 (Spec 2).
# In v1, ReviewAgent was invoked standalone and needed its own callback for
# WebSocket streaming. In v2, ReviewAgent is a graph node — the graph's
# stream_async handles event delivery. No per-agent callback needed.
#
# WHY NO REFINEMENT MODE FOR ReviewAgent:
# ReviewAgent's job is to analyze the CURRENT pipeline output and identify
# improvable sections. It doesn't have "previous output" to refine — it
# always analyzes fresh. Each round produces a new set of reviewable sections
# based on the current pipeline output.
def create_review_agent() -> Agent:
    """
    Create the Review Agent with explicit configuration.

    Fetches the system prompt from Bedrock Prompt Management if available,
    falls back to the bundled REVIEW_SYSTEM_PROMPT constant if not.

    Returns:
        Configured Review Agent (strands.Agent instance)
    """
    try:
        from prompt_client import fetch_prompt
        system_prompt = fetch_prompt("review")
    except Exception as e:
        logger.warning(f"Prompt Management unavailable, using bundled prompt: {e}")
        system_prompt = REVIEW_SYSTEM_PROMPT

    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt
    )

    logger.info("Review Agent created with explicit model configuration")
    return agent
