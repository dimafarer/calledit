"""Convergence Evaluator — weighted score (0.0-1.0).

Compares round 2 per-agent outputs against the base prediction's expected outputs.
Weights: category match 0.5, prediction statement similarity 0.2,
         verification method overlap 0.2, date accuracy 0.1.
When round2 equals base exactly → 1.0. This is Tier 1 (deterministic).
"""


def _text_similarity(a: str, b: str) -> float:
    """Simple word overlap similarity (Jaccard). Good enough for convergence."""
    if not a or not b:
        return 0.0
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _list_overlap(a: list, b: list) -> float:
    """Proportion of items in b that appear in a (case-insensitive)."""
    if not b:
        return 1.0  # nothing expected, nothing to miss
    if not a:
        return 0.0
    a_lower = {str(x).lower() for x in a}
    found = sum(1 for x in b if str(x).lower() in a_lower)
    return found / len(b)


def evaluate_convergence(round2_outputs: dict, base_expected: dict, span_id: str = "") -> dict:
    """Score how well round 2 outputs converge to the base prediction's expected outputs.

    Args:
        round2_outputs: Parsed pipeline results from round 2 execution.
        base_expected: Expected per-agent outputs from the base prediction.
            Should have keys: parser, categorizer, verification_builder.
        span_id: Trace span ID for traceability.

    Returns:
        {"score": 0.0-1.0, "evaluator": "Convergence", "span_id": str}
    """
    # Category match (weight 0.5) — most important signal
    actual_cat = round2_outputs.get("verifiable_category", "")
    # V2 uses expected_category, V1 used verifiable_category
    expected_cat = base_expected.get("categorizer", {}).get("expected_category", "") or \
                   base_expected.get("categorizer", {}).get("verifiable_category", "")
    cat_score = 1.0 if actual_cat == expected_cat else 0.0

    # Prediction statement similarity (weight 0.2)
    actual_stmt = round2_outputs.get("prediction_statement", "")
    expected_stmt = base_expected.get("parser", {}).get("prediction_statement", "")
    stmt_score = _text_similarity(actual_stmt, expected_stmt)

    # Verification method overlap (weight 0.2)
    actual_vm = round2_outputs.get("verification_method", {})
    expected_vm = base_expected.get("verification_builder", {}).get("verification_method", {})
    vm_scores = []
    for field in ["source", "criteria", "steps"]:
        actual_list = actual_vm.get(field, [])
        expected_list = expected_vm.get(field, [])
        if expected_list:
            vm_scores.append(_list_overlap(actual_list, expected_list))
    vm_score = sum(vm_scores) / len(vm_scores) if vm_scores else 0.0

    # Date accuracy (weight 0.1) — simple string prefix match on date portion
    actual_date = round2_outputs.get("verification_date", "")[:10]
    expected_date = base_expected.get("parser", {}).get("verification_date", "")[:10]
    date_score = 1.0 if actual_date and actual_date == expected_date else 0.0

    # Weighted combination
    score = (cat_score * 0.5) + (stmt_score * 0.2) + (vm_score * 0.2) + (date_score * 0.1)
    score = round(max(0.0, min(1.0, score)), 10)

    return {"score": score, "evaluator": "Convergence", "span_id": span_id}
