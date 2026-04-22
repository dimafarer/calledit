"""Baseline comparison — old pipeline vs new SDK pipeline.

Compares per-evaluator scores between two eval reports to validate
the SDK migration produces equivalent results.

Tolerance: exact match for deterministic evaluators, ±0.05 for LLM judges.
"""

import json
import logging

logger = logging.getLogger(__name__)

# LLM judge evaluator names (non-deterministic, allow ±0.05 tolerance)
LLM_JUDGE_EVALUATORS = {
    "intent_preservation",
    "plan_quality",
    "evidence_quality",
    "verdict_accuracy",  # deterministic but included in judges tier
}

TOLERANCE_DETERMINISTIC = 0.0
TOLERANCE_LLM_JUDGE = 0.05


def compare_scores(
    old_scores: dict,
    new_scores: dict,
    section: str = "",
) -> list[dict]:
    """Compare per-evaluator scores between old and new pipelines.

    Args:
        old_scores: Dict of evaluator_name -> score from old pipeline.
        new_scores: Dict of evaluator_name -> score from new pipeline.
        section: Label for the section (e.g., "creation", "verification").

    Returns:
        List of comparison dicts with evaluator, old, new, diff, tolerance, pass.
    """
    results = []
    all_keys = set(old_scores.keys()) | set(new_scores.keys())

    for key in sorted(all_keys):
        old_val = old_scores.get(key)
        new_val = new_scores.get(key)

        if old_val is None or new_val is None:
            results.append({
                "evaluator": f"{section}.{key}" if section else key,
                "old": old_val,
                "new": new_val,
                "diff": None,
                "tolerance": None,
                "pass": False,
                "reason": "Missing in one pipeline",
            })
            continue

        if not isinstance(old_val, (int, float)) or not isinstance(new_val, (int, float)):
            continue

        diff = abs(float(new_val) - float(old_val))
        is_llm = key in LLM_JUDGE_EVALUATORS
        tolerance = TOLERANCE_LLM_JUDGE if is_llm else TOLERANCE_DETERMINISTIC
        passed = diff <= tolerance

        results.append({
            "evaluator": f"{section}.{key}" if section else key,
            "old": float(old_val),
            "new": float(new_val),
            "diff": round(diff, 4),
            "tolerance": tolerance,
            "pass": passed,
            "reason": "LLM judge" if is_llm else "deterministic",
        })

    return results


def validate_migration(comparisons: list[dict]) -> bool:
    """Check if all comparisons pass within tolerance.

    Returns True if migration is validated (all within tolerance).
    """
    return all(c["pass"] for c in comparisons)


def print_comparison(comparisons: list[dict]) -> None:
    """Print comparison report to stdout."""
    print(f"\n{'Evaluator':<40} {'Old':>8} {'New':>8} {'Diff':>8} {'Tol':>6} {'Pass':>6}")
    print("-" * 78)
    for c in comparisons:
        old = f"{c['old']:.4f}" if isinstance(c["old"], float) else str(c["old"])
        new = f"{c['new']:.4f}" if isinstance(c["new"], float) else str(c["new"])
        diff = f"{c['diff']:.4f}" if isinstance(c["diff"], float) else str(c["diff"])
        tol = f"±{c['tolerance']:.2f}" if isinstance(c["tolerance"], float) else str(c["tolerance"])
        status = "✓" if c["pass"] else "✗"
        print(f"  {c['evaluator']:<38} {old:>8} {new:>8} {diff:>8} {tol:>6} {status:>6}")

    validated = validate_migration(comparisons)
    print(f"\nMigration validated: {'YES ✓' if validated else 'NO ✗'}")
