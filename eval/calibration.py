"""Calibration — post-experiment analysis for Strands Evals SDK.

Computes cross-agent calibration metrics: does the creation agent's
verifiability score predict the verification agent's success?

This is a post-experiment step, not an SDK Evaluator, because calibration
is an aggregate metric across all cases (not per-case).
"""

import logging

logger = logging.getLogger(__name__)


def classify_score_tier(score: float) -> str:
    """Map verifiability_score to tier: high (>=0.7), moderate (>=0.4), low (<0.4)."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    return "low"


def is_calibration_correct(score_tier: str, verdict: str) -> bool:
    """Check if score tier prediction aligned with verdict outcome.

    high → confirmed or refuted = correct (agent resolved it)
    high → inconclusive = wrong (agent couldn't resolve an easy one)
    moderate → always correct (indeterminate zone)
    low → always correct (any outcome acceptable for hard predictions)
    """
    if score_tier == "high":
        return verdict in ("confirmed", "refuted")
    return True  # moderate and low are always "correct"


def compute_calibration(case_results: list[dict]) -> dict:
    """Compute calibration metrics from task function outputs.

    Reads verifiability_score from creation_bundle and verdict from
    verification_result for each case.

    Args:
        case_results: List of task function output dicts, each containing
            creation_bundle and verification_result.

    Returns:
        Dict with calibration_accuracy, mean_absolute_error,
        high_score_confirmation_rate, low_score_failure_rate,
        verdict_distribution.
    """
    verdict_dist = {
        "confirmed": 0, "refuted": 0, "inconclusive": 0, "error": 0,
    }

    correct_count = 0
    total_scored = 0
    mae_sum = 0.0
    mae_count = 0
    high_resolved = 0
    high_total = 0
    low_inconclusive = 0
    low_total = 0

    for case in case_results:
        bundle = case.get("creation_bundle")
        vresult = case.get("verification_result")

        # Skip cases with errors
        if case.get("creation_error") or not bundle:
            verdict_dist["error"] += 1
            continue
        if case.get("verification_error") or not vresult:
            verdict_dist["error"] += 1
            continue

        verdict = vresult.get("verdict", "")
        if verdict in verdict_dist:
            verdict_dist[verdict] += 1
        else:
            verdict_dist["error"] += 1
            continue

        # Extract score and tier
        review = bundle.get("plan_review", {})
        v_score = review.get("verifiability_score", 0.0)
        if not isinstance(v_score, (int, float)):
            v_score = 0.0
        score_tier = classify_score_tier(float(v_score))

        # Calibration accuracy
        if is_calibration_correct(score_tier, verdict):
            correct_count += 1
        total_scored += 1

        # MAE: |verifiability_score - binary_outcome|
        # Decision 148: resolved (confirmed OR refuted) = 1.0, inconclusive = 0.0
        binary = 1.0 if verdict in ("confirmed", "refuted") else 0.0
        mae_sum += abs(float(v_score) - binary)
        mae_count += 1

        # High score resolution rate
        if score_tier == "high":
            high_total += 1
            if verdict in ("confirmed", "refuted"):
                high_resolved += 1

        # Low score inconclusive rate
        if score_tier == "low":
            low_total += 1
            if verdict == "inconclusive":
                low_inconclusive += 1

    return {
        "calibration_accuracy": round(correct_count / total_scored, 4) if total_scored else 0.0,
        "mean_absolute_error": round(mae_sum / mae_count, 4) if mae_count else 0.0,
        "high_score_confirmation_rate": round(high_resolved / high_total, 4) if high_total else 0.0,
        "low_score_failure_rate": round(low_inconclusive / low_total, 4) if low_total else 0.0,
        "verdict_distribution": verdict_dist,
    }
