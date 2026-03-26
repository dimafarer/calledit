"""Evidence Structure evaluator for verification agent output (Tier 1).

Checks that each EvidenceItem has all three required fields:
source, finding, relevant_to_criteria.

Vacuously true for empty evidence list (evidence_completeness catches that).
"""

REQUIRED_FIELDS = {"source", "finding", "relevant_to_criteria"}


def evaluate(result: dict) -> dict:
    """Check each evidence item has all required fields.

    Args:
        result: Dict from VerificationBackend.invoke()

    Returns:
        {"score": float, "pass": bool, "reason": str}
    """
    evidence = result.get("evidence", [])

    if not isinstance(evidence, list) or len(evidence) == 0:
        # Vacuously true — evidence_completeness handles the empty case
        return {"score": 1.0, "pass": True, "reason": "No evidence items to validate"}

    failed_items = []
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            failed_items.append(f"item[{i}] is not a dict")
            continue
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            failed_items.append(f"item[{i}] missing: {', '.join(sorted(missing))}")

    if failed_items:
        return {
            "score": 0.0,
            "pass": False,
            "reason": f"Evidence structure invalid — {'; '.join(failed_items)}",
        }

    return {
        "score": 1.0,
        "pass": True,
        "reason": f"All {len(evidence)} evidence item(s) have required fields",
    }
