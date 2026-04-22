"""Tests for verdict accuracy evaluator — Property 6."""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification.verdict_accuracy import VerdictAccuracyEvaluator


def _make_eval_data(verdict: str, expected: str = None) -> EvaluationData:
    return EvaluationData(
        input="test",
        actual_output={"verification_result": {"verdict": verdict}},
        expected_output=expected,
        metadata={},
    )


# Feature: strands-evals-migration, Property 6: Verdict accuracy evaluator correctness
@given(
    verdict=st.sampled_from(["confirmed", "refuted", "inconclusive"]),
    expected=st.one_of(
        st.none(),
        st.sampled_from(["confirmed", "refuted", "inconclusive"]),
    ),
)
@settings(max_examples=100)
def test_verdict_accuracy_property(verdict, expected):
    """Score=1.0 when match, 0.0 when mismatch, empty when expected is None."""
    case = _make_eval_data(verdict, expected)
    result = VerdictAccuracyEvaluator().evaluate(case)

    if expected is None:
        assert result == [], "Should return empty list for None expected"
    elif verdict == expected:
        assert result[0].score == 1.0
        assert result[0].test_pass is True
    else:
        assert result[0].score == 0.0
        assert result[0].test_pass is False


# Feature: strands-evals-migration, Property 6: None expected always empty
@given(verdict=st.sampled_from(["confirmed", "refuted", "inconclusive"]))
@settings(max_examples=50)
def test_none_expected_returns_empty(verdict):
    """When expected_output is None, always return empty list."""
    case = _make_eval_data(verdict, None)
    result = VerdictAccuracyEvaluator().evaluate(case)
    assert result == []


class TestVerdictAccuracyEdgeCases:

    def test_no_verification_result(self):
        case = EvaluationData(
            input="test", actual_output={}, expected_output="confirmed", metadata={},
        )
        result = VerdictAccuracyEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_exact_match_confirmed(self):
        result = VerdictAccuracyEvaluator().evaluate(_make_eval_data("confirmed", "confirmed"))
        assert result[0].score == 1.0

    def test_mismatch_refuted_vs_confirmed(self):
        result = VerdictAccuracyEvaluator().evaluate(_make_eval_data("refuted", "confirmed"))
        assert result[0].score == 0.0
