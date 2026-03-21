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
REVIEW_SYSTEM_PROMPT = """You are a verification plan reviewer. Your PRIMARY job is to find specific assumptions
in the Verification Builder's output that could be wrong, and ask targeted questions
to validate or correct them.

You receive the full pipeline output: parser extraction, category routing, and the
verification plan (criteria, sources, steps). Focus on the verification plan.

REVIEW PROCESS:

1. Read the Verification Builder's criteria and method carefully.
2. For each criterion, ask: "What specific assumption did the Verification Builder make
   that could be wrong?" Examples:
   - It assumed "nice weather" means 60-80°F — but the user might mean something different
   - It assumed the prediction is about today — but the user might mean tomorrow
   - It assumed "the game" refers to a specific sport — but it could be another
   - It assumed a location — but the user didn't specify one
3. For each assumption found, generate a question that would confirm or correct it.

QUESTION QUALITY RULES:

DO generate questions like:
- "The verification plan assumes 'nice weather' means 60-80°F and sunny. Is that what you mean, or do you have different thresholds?"
- "The plan will check NBA scores for tonight. Is this an NBA game, or a different league?"
- "The verification is set for today at 3pm. Did you mean today or a different day?"

DO NOT generate questions like:
- "Can you be more specific?" (too vague — specific about WHAT?)
- "What do you mean by that?" (doesn't reference the verification plan)
- "Is there anything else you'd like to add?" (generic filler)

Every question MUST reference a specific element from the Verification Builder's output.
If the verification plan has no questionable assumptions, return an empty reviewable_sections list.

SECTIONS TO REVIEW:
- prediction_statement: Did the parser capture the intent correctly?
- verifiable_category: Does the routing make sense given available tools?
- verification_method.source: Are the data sources appropriate and accessible?
- verification_method.criteria: Do the criteria match the prediction's intent exactly?
- verification_method.steps: Are the steps actionable and correctly ordered?

AVAILABLE TOOLS:
{tool_manifest}

When reviewing the verification plan, also consider:
- Are the chosen tools the best match from the available tool list for this prediction?
- Could a different available tool provide better or more direct verification?
- If the plan references tools that aren't in the available list, flag this
- If a better tool exists but wasn't chosen, ask why

Return ONLY the raw JSON object. No markdown code blocks, no backticks, no explanation text before or after the JSON. The first character of your response must be { and the last must be }.

{
    "reviewable_sections": [
        {
            "section": "field_name",
            "improvable": true,
            "questions": ["specific question referencing the verification plan"],
            "reasoning": "what assumption in the verification plan this question validates"
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
def create_review_agent(tool_manifest: str = "", model_id: str = None) -> Agent:
    """
    Create the Review Agent with explicit configuration.

    Args:
        tool_manifest: Available MCP tools manifest string. Injected into the
            system prompt so the reviewer can assess whether the VB chose the
            best tools for the verification plan.
        model_id: Optional model override. If None, uses default Sonnet 4.

    Returns:
        Configured Review Agent (strands.Agent instance)
    """
    manifest_text = (
        tool_manifest
        if tool_manifest
        else "No tools currently registered."
    )

    try:
        from prompt_client import fetch_prompt
        system_prompt = fetch_prompt("review", variables={"tool_manifest": manifest_text})
    except Exception as e:
        logger.warning(f"Prompt Management unavailable, using bundled prompt: {e}")
        system_prompt = REVIEW_SYSTEM_PROMPT.replace(
            "{tool_manifest}", manifest_text
        )

    agent = Agent(
        model=model_id or "us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt
    )

    logger.info("Review Agent created with tool manifest")
    return agent
