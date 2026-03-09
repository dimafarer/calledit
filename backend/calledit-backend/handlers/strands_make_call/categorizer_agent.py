"""
Categorizer Agent for Prediction Verification System

This agent classifies predictions into one of 5 verifiability categories.
It's the second agent in the graph workflow.

Following Strands best practices:
- Single responsibility (categorization only)
- Focused system prompt (~30 lines)
- Explicit model specification
- No tools needed (pure reasoning)
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
    "agent_verifiable",
    "current_tool_verifiable",
    "strands_tool_verifiable",
    "api_tool_verifiable",
    "human_verifiable_only"
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

1. agent_verifiable - Pure reasoning/knowledge, no external tools needed
   Examples: "Sun will rise tomorrow", "2+2=4", "Christmas 2025 is Thursday"
   
2. current_tool_verifiable - Only needs current_time tool
   Examples: "It's after 3pm", "Today is a weekday", "We're in January 2025"
   
3. strands_tool_verifiable - Needs Strands library tools (calculator, python_repl)
   Examples: "Calculate compound interest", "Parse complex data", "Math computation"
   
4. api_tool_verifiable - Needs external APIs or MCP integrations
   Examples: "Bitcoin hits $100k", "Weather is sunny", "Stock prices", "Sports scores"
   
5. human_verifiable_only - Needs human observation/judgment
   Examples: "Movie will be good", "I will feel happy", "Meeting goes well"

IMPORTANT: Choose the MOST SPECIFIC category. If it can be verified with simpler tools, use that category.

Return ONLY the raw JSON object. Do not wrap in markdown code blocks. Do not include any text before or after the JSON.

{
    "verifiable_category": "one of 5 categories above",
    "category_reasoning": "clear explanation of why you chose this category"
}

REFINEMENT MODE (when previous output is provided):
You are refining a prediction. Your previous output is provided below.
Review it in light of any new user clarifications — confirm it if it stands,
update it if the new information makes a more precise version possible.
Always return the complete JSON output, whether confirmed or updated.
"""


def create_categorizer_agent() -> Agent:
    """
    Create the Categorizer Agent with explicit configuration.
    
    Following Strands best practices:
    - Explicit model selection (Bedrock model ID)
    - Focused system prompt
    - No tools (pure reasoning task)
    
    Returns:
        Configured Categorizer Agent
    """
    # Model: Claude Sonnet 4 (upgraded from 3.5 Sonnet v2 in Spec 1)
    # Why Sonnet 4: Better instruction following (critical for clean JSON output),
    # same Sonnet tier cost/latency, current Strands SDK default.
    # Why us. prefix: Cross-region inference — works in all US regions.
    # See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3, Step 0
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=CATEGORIZER_SYSTEM_PROMPT
    )
    
    logger.info("Categorizer Agent created with explicit model configuration")
    return agent


