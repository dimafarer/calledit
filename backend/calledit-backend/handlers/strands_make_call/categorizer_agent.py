"""
Categorizer Agent for Prediction Verification System

This agent classifies predictions into one of 3 verifiability categories:
- auto_verifiable: can be verified now with current tools + reasoning
- automatable: could be verified with a tool that doesn't exist yet
- human_only: requires subjective judgment, no tool can help

It's the second agent in the graph workflow.
"""

# NOTE: categorizer_node_function() was removed in v2 cleanup (Spec 1).
# It was leftover from a custom-node architecture where each agent had a
# node function that manually managed graph state. The graph now uses
# create_categorizer_agent() with the plain Agent pattern instead, where
# Strands Graph handles input propagation between nodes automatically.
# The `json` import was also removed — it was only used by the node function.
# See: .kiro/specs/v2-cleanup-foundation/design.md, Component 1

import logging
from strands import Agent

logger = logging.getLogger(__name__)


# Valid verifiability categories
VALID_CATEGORIES = {
    "auto_verifiable",
    "automatable",
    "human_only"
}


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

# Categorizer Agent System Prompt (focused, ~30 lines)
CATEGORIZER_SYSTEM_PROMPT = """You are a verifiability categorizer. Classify predictions into exactly one category:

1. auto_verifiable - Can be verified NOW using reasoning plus currently available tools.
   The agent has the tools and knowledge needed to determine truth.
   Examples: "Sun will rise tomorrow" (reasoning), "Christmas 2025 is Thursday" (reasoning),
   "Current weather in Seattle is rainy" (web search tool, if available)

2. automatable - Cannot be verified today, but an agent could plausibly find or build
   a tool to verify it. This is automatable in principle — the information exists
   somewhere accessible, we just don't have the right tool yet.
   Examples: "Bitcoin hits $100k by December" (needs price API), "My flight lands on time" (needs flight tracker)

3. human_only - Requires one or more of:
   (a) Subjective judgment that no tool can assess (e.g., "I will feel happy", "The movie will be good")
   (b) Direct physical observation of a specific person, place, or event that no remote tool can capture (e.g., "Tom will wear his blue shirt", "My soufflé won't fall")
   (c) Private personal information not accessible through any API or public data source (e.g., "I'll get the promotion", "80% of my students will pass")
   Even with unlimited tools, verification ultimately depends on a human.

AVAILABLE TOOLS:
{tool_manifest}

IMPORTANT: If an available tool's capabilities match the prediction's verification needs,
classify as auto_verifiable. If no tool matches but one could plausibly exist, classify
as automatable. Only use human_only when the prediction is fundamentally subjective or
requires personal observation no tool can provide.

Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON.

{{
    "verifiable_category": "one of 3 categories above",
    "category_reasoning": "clear explanation of why you chose this category"
}}

REFINEMENT MODE (when previous output is provided):
You are refining a prediction. Your previous output is provided below.
Review it in light of any new user clarifications — confirm it if it stands,
update it if the new information makes a more precise version possible.
Always return the complete JSON output, whether confirmed or updated.
"""


def create_categorizer_agent(tool_manifest: str = "") -> Agent:
    """
    Create the Categorizer Agent with explicit configuration.
    
    Fetches the system prompt from Bedrock Prompt Management if available,
    falls back to the bundled CATEGORIZER_SYSTEM_PROMPT constant if not.
    The tool_manifest is injected as a variable in both paths.
    
    Args:
        tool_manifest: Human-readable list of available tools and their capabilities.
                       Empty string means no tools registered (pure reasoning mode).
    
    Returns:
        Configured Categorizer Agent
    """
    manifest_text = tool_manifest if tool_manifest else "No tools currently registered. Rely on pure reasoning for auto_verifiable."

    try:
        from prompt_client import fetch_prompt
        system_prompt = fetch_prompt(
            "categorizer",
            variables={"tool_manifest": manifest_text},
        )
    except Exception as e:
        logger.warning(f"Prompt Management unavailable, using bundled prompt: {e}")
        system_prompt = CATEGORIZER_SYSTEM_PROMPT.format(tool_manifest=manifest_text)

    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt
    )
    
    logger.info(f"Categorizer Agent created with {len(tool_manifest.splitlines()) if tool_manifest else 0} tools in manifest")
    return agent


