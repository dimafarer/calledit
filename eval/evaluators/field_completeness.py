"""Tier 1: Field Completeness — checks key list fields are non-empty."""


def evaluate(bundle: dict) -> dict:
    """Check sources, criteria, steps are non-empty lists.

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    plan = bundle.get("verification_plan", {})
    empty_fields = []

    for field in ("sources", "criteria", "steps"):
        val = plan.get(field, [])
        if not isinstance(val, list) or len(val) == 0:
            empty_fields.append(field)

    if empty_fields:
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Empty fields: {', '.join(empty_fields)}",
        }
    return {"score": 1.0, "pass": True, "reason": "All list fields non-empty"}
