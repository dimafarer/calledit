"""ToolAlignment Evaluator — deterministic Jaccard similarity score.

Measures set overlap between tools referenced in the Verification_Plan's
steps field and tools listed in the Verification_Outcome's tools_used field.

Score = |intersection| / |union|, or 1.0 when both sets are empty.
When score < 1.0, a lightweight LLM call classifies the delta root cause.

This is a deterministic evaluator following the category_match.py pattern.
"""

import logging
from typing import Optional

try:
    from evaluators.delta_classifier import classify_delta
except ImportError:
    from .delta_classifier import classify_delta

logger = logging.getLogger(__name__)

KNOWN_TOOLS = [
    "brave_web_search",
    "fetch",
    "fetch_txt",
    "playwright_navigate",
    "playwright_screenshot",
    "playwright_click",
    "playwright_fill",
    "playwright_evaluate",
]


def _extract_planned_tools(steps: list) -> set:
    """Extract tool names from plan step descriptions via keyword matching.

    Scans each step string for known MCP tool names (case-insensitive).
    """
    found = set()
    for step in steps:
        step_lower = step.lower() if isinstance(step, str) else ""
        for tool_name in KNOWN_TOOLS:
            if tool_name.lower() in step_lower:
                found.add(tool_name)
    return found


def evaluate_tool_alignment(
    verification_plan: dict,
    verification_outcome: dict,
) -> dict:
    """Score tool overlap between plan and execution.

    Args:
        verification_plan: Dict with at least a 'steps' field (list of strings).
        verification_outcome: Dict with at least a 'tools_used' field (list of strings).

    Returns:
        {"score": float, "evaluator": "ToolAlignment",
         "planned_tools": list, "used_tools": list,
         "overlap": list, "plan_only": list, "execution_only": list,
         "delta_classification": str|None}
    """
    steps = verification_plan.get("steps", [])
    planned = _extract_planned_tools(steps)

    used = set(verification_outcome.get("tools_used", []))

    overlap = planned & used
    plan_only = planned - used
    execution_only = used - planned
    union = planned | used

    if len(union) == 0:
        score = 1.0
    else:
        score = len(overlap) / len(union)

    delta_classification: Optional[str] = None
    if score < 1.0:
        reasoning = verification_outcome.get("reasoning", "")
        delta_classification = classify_delta(
            plan_field="tools",
            planned_items=sorted(planned),
            actual_items=sorted(used),
            reasoning=reasoning,
        )

    return {
        "score": score,
        "evaluator": "ToolAlignment",
        "planned_tools": sorted(planned),
        "used_tools": sorted(used),
        "overlap": sorted(overlap),
        "plan_only": sorted(plan_only),
        "execution_only": sorted(execution_only),
        "delta_classification": delta_classification,
    }
