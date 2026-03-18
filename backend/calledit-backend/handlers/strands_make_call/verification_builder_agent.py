"""
Verification Builder Agent for Prediction Verification System

This agent constructs detailed verification methods with source, criteria, and steps.
It's the third agent in the graph workflow.

Following Strands best practices:
- Single responsibility (verification method building only)
- Focused system prompt (~25 lines)
- Explicit model specification
- No tools needed (pure reasoning)
"""

# NOTE: verification_builder_node_function() was removed in v2 cleanup (Spec 1).
# It was leftover from a custom-node architecture where each agent had a
# node function that manually managed graph state. The graph now uses
# create_verification_builder_agent() with the plain Agent pattern instead,
# where Strands Graph handles input propagation between nodes automatically.
# The `json` import was also removed — it was only used by the node function.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 1

import logging
from strands import Agent

logger = logging.getLogger(__name__)


# PROMPT HARDENING NOTE: The "Return ONLY the raw JSON object" instruction is
# critical. Without it, Claude models often wrap JSON in ```json ``` markdown
# blocks, which breaks direct json.loads() parsing. The explicit negative
# instructions ("Do not wrap", "Do not include") work better than implicit
# positive ones ("Return JSON:"). This was the root cause of the 120-line
# extract_json_from_text() regex helper — fixed at the source now.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3, Step 1

# REFINEMENT MODE NOTE: The refinement block at the end of this prompt is always
# present but only activates when the user prompt includes previous output and
# clarifications (round > 1). In round 1, agents ignore it because no previous
# output is provided. This is a "static prompt with conditional activation" pattern.
#
# WHY NOT DYNAMIC PROMPT CONSTRUCTION:
# Strands agents are created once as module-level singletons (for graph reuse
# across warm Lambda invocations). Dynamic prompt construction would require
# creating new agents per invocation, losing the singleton benefit. The refinement
# block is ~4 lines and doesn't bloat the prompt for round 1.
#
# HOW PREVIOUS OUTPUT REACHES AGENTS:
# Via the user prompt (initial_prompt), not the system prompt. The Lambda handler
# builds the prompt differently for round 1 vs round 2+:
# - Round 1: "PREDICTION: {prompt}\nCURRENT DATE: ...\nTIMEZONE: ..."
# - Round 2+: Same + "\n\nPREVIOUS OUTPUT:\n{json}\n\nUSER CLARIFICATIONS:\n- ..."

# Verification Builder Agent System Prompt (focused, ~25 lines)
VERIFICATION_BUILDER_SYSTEM_PROMPT = """You are a verification method builder. Create detailed verification plans.

For the given prediction and category, specify:
- source: List of reliable sources to check (e.g., APIs, databases, tools)
- criteria: List of measurable criteria for determining truth
- steps: List of detailed verification steps to execute

Make verification methods:
- Specific and actionable
- Appropriate for the verifiability category
- Measurable and objective
- Realistic and achievable

IMPORTANT: All three fields (source, criteria, steps) must be lists, not single strings.

Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON.

{
    "verification_method": {
        "source": ["source1", "source2"],
        "criteria": ["criterion1", "criterion2"],
        "steps": ["step1", "step2", "step3"]
    }
}

REFINEMENT MODE (when previous output is provided):
You are refining a prediction. Your previous output is provided below.
Review it in light of any new user clarifications — confirm it if it stands,
update it if the new information makes a more precise version possible.
Always return the complete JSON output, whether confirmed or updated.
"""


def create_verification_builder_agent(model_id: str = None) -> Agent:
    """
    Create the Verification Builder Agent with explicit configuration.
    
    Args:
        model_id: Optional model override. If None, uses default Sonnet 4.
    
    Returns:
        Configured Verification Builder Agent
    """
    try:
        from prompt_client import fetch_prompt
        system_prompt = fetch_prompt("vb")
    except Exception as e:
        logger.warning(f"Prompt Management unavailable, using bundled prompt: {e}")
        system_prompt = VERIFICATION_BUILDER_SYSTEM_PROMPT

    agent = Agent(
        model=model_id or "us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt
    )
    
    logger.info("Verification Builder Agent created with explicit model configuration")
    return agent


