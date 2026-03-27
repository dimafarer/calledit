"""Recurring Evidence Freshness evaluator for verification agent output.

Simple deterministic check that evidence items exist and have source fields.
This is a Tier 1 evaluator — can be upgraded to LLM judge later.

Requirements: 7.7
"""


def evaluate(result: dict, prediction_text: str = "") -> dict:
    """Check that evidence items exist and have source fields.

    Args:
        result: Dict from VerificationBackend.invoke() containing evidence.
        prediction_text: Original prediction text (unused for now, kept for
            future LLM-judge upgrade).

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    evidence = result.get("evidence", [])

    if not evidence:
        return {
            "score": 0.0,
            "pass": False,
            "reason": "recurring: no evidence items found",
        }

    items_with_source = 0
    total_items = len(evidence)

    for item in evidence:
        if isinstance(item, dict) and item.get("source"):
            items_with_source += 1

    if total_items == 0:
        score = 0.0
    else:
        score = round(items_with_source / total_items, 4)

    return {
        "score": score,
        "pass": score >= 0.5,
        "reason": (
            f"recurring: {items_with_source}/{total_items} evidence items "
            f"have source fields"
        ),
    }
