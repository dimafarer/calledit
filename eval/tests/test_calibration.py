"""Tests for calibration — Property 8 + edge cases."""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.calibration import (
    compute_calibration,
    classify_score_tier,
    is_calibration_correct,
)


def _make_case_result(score: float, verdict: str) -> dict:
    """Helper to create a task function output dict for calibration."""
    return {
        "creation_bundle": {
            "plan_review": {"verifiability_score": score},
        },
        "verification_result": {"verdict": verdict},
        "creation_error": None,
        "verification_error": None,
    }


# --- Property 8: Calibration metrics correctness ---


# Feature: strands-evals-migration, Property 8: Calibration metrics correctness
@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=20,
    ),
    verdicts=st.lists(
        st.sampled_from(["confirmed", "refuted", "inconclusive"]),
        min_size=1,
        max_size=20,
    ),
)
@settings(max_examples=100)
def test_calibration_metrics_correctness(scores, verdicts):
    """All 5 calibration metrics are mathematically correct."""
    n = min(len(scores), len(verdicts))
    case_results = [_make_case_result(scores[i], verdicts[i]) for i in range(n)]

    result = compute_calibration(case_results)

    # Manually compute expected values
    correct = 0
    mae_sum = 0.0
    high_resolved = 0
    high_total = 0
    low_inconclusive = 0
    low_total = 0
    vdist = {"confirmed": 0, "refuted": 0, "inconclusive": 0, "error": 0}

    for i in range(n):
        s, v = scores[i], verdicts[i]
        tier = classify_score_tier(s)
        vdist[v] += 1

        if is_calibration_correct(tier, v):
            correct += 1

        binary = 1.0 if v in ("confirmed", "refuted") else 0.0
        mae_sum += abs(s - binary)

        if tier == "high":
            high_total += 1
            if v in ("confirmed", "refuted"):
                high_resolved += 1
        if tier == "low":
            low_total += 1
            if v == "inconclusive":
                low_inconclusive += 1

    assert result["calibration_accuracy"] == pytest.approx(correct / n, abs=0.001)
    assert result["mean_absolute_error"] == pytest.approx(mae_sum / n, abs=0.001)

    if high_total > 0:
        assert result["high_score_confirmation_rate"] == pytest.approx(
            high_resolved / high_total, abs=0.001
        )
    if low_total > 0:
        assert result["low_score_failure_rate"] == pytest.approx(
            low_inconclusive / low_total, abs=0.001
        )

    assert result["verdict_distribution"] == vdist


# Feature: strands-evals-migration, Property 8: Verdict distribution counts
@given(
    verdicts=st.lists(
        st.sampled_from(["confirmed", "refuted", "inconclusive"]),
        min_size=1,
        max_size=30,
    ),
)
@settings(max_examples=50)
def test_verdict_distribution_exact_counts(verdicts):
    """Verdict distribution counts match exact occurrences."""
    case_results = [_make_case_result(0.8, v) for v in verdicts]
    result = compute_calibration(case_results)

    for v in ["confirmed", "refuted", "inconclusive"]:
        assert result["verdict_distribution"][v] == verdicts.count(v)


# --- Unit tests for edge cases ---


class TestCalibrationEdgeCases:

    def test_empty_list(self):
        result = compute_calibration([])
        assert result["calibration_accuracy"] == 0.0
        assert result["mean_absolute_error"] == 0.0

    def test_all_errors(self):
        cases = [
            {"creation_error": "fail", "creation_bundle": None,
             "verification_result": None, "verification_error": None},
        ]
        result = compute_calibration(cases)
        assert result["calibration_accuracy"] == 0.0
        assert result["verdict_distribution"]["error"] == 1

    def test_single_case_confirmed(self):
        result = compute_calibration([_make_case_result(0.9, "confirmed")])
        assert result["calibration_accuracy"] == 1.0
        assert result["high_score_confirmation_rate"] == 1.0

    def test_high_score_inconclusive_is_wrong(self):
        result = compute_calibration([_make_case_result(0.9, "inconclusive")])
        assert result["calibration_accuracy"] == 0.0

    def test_low_score_inconclusive_is_correct(self):
        result = compute_calibration([_make_case_result(0.2, "inconclusive")])
        assert result["calibration_accuracy"] == 1.0
        assert result["low_score_failure_rate"] == 1.0

    def test_moderate_always_correct(self):
        result = compute_calibration([_make_case_result(0.5, "inconclusive")])
        assert result["calibration_accuracy"] == 1.0

    def test_verification_error_counted(self):
        cases = [
            {"creation_bundle": {"plan_review": {"verifiability_score": 0.8}},
             "verification_result": None, "verification_error": "timeout",
             "creation_error": None},
        ]
        result = compute_calibration(cases)
        assert result["verdict_distribution"]["error"] == 1
