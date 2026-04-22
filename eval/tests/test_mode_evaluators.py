"""Tests for mode-specific evaluators — Property 5 + edge cases."""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification import (
    AtDateVerdictEvaluator,
    BeforeDateVerdictEvaluator,
    RecurringFreshnessEvaluator,
)


def _make_eval_data(vresult: dict, mode: str, expected: str = None, **extra_meta) -> EvaluationData:
    meta = {"verification_mode": mode, **extra_meta}
    return EvaluationData(
        input="test", actual_output={"verification_result": vresult},
        expected_output=expected, metadata=meta,
    )


# --- Property 5: Mode-specific evaluator routing and temporal logic ---


# Feature: strands-evals-migration, Property 5: Non-matching modes return no-op
@given(mode=st.sampled_from(["immediate", "at_date", "before_date", "recurring"]))
@settings(max_examples=100)
def test_mode_routing_noop(mode):
    """Each evaluator returns no-op (score=1.0) for non-matching modes."""
    vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": [], "reasoning": "test"}

    evaluators_and_modes = [
        (AtDateVerdictEvaluator(), "at_date"),
        (BeforeDateVerdictEvaluator(), "before_date"),
        (RecurringFreshnessEvaluator(), "recurring"),
    ]

    for evaluator, target_mode in evaluators_and_modes:
        case = _make_eval_data(vresult, mode)
        result = evaluator.evaluate(case)
        if mode != target_mode:
            assert result[0].score == 1.0, (
                f"{evaluator.__class__.__name__} should return 1.0 for mode={mode}"
            )
            assert "N/A" in result[0].reason


# Feature: strands-evals-migration, Property 5: Recurring freshness scoring
@given(
    source_count=st.integers(min_value=0, max_value=5),
    total_count=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=100)
def test_recurring_freshness_scoring(source_count, total_count):
    """Score = fraction of evidence items with non-empty source."""
    source_count = min(source_count, total_count)
    evidence = []
    for i in range(total_count):
        if i < source_count:
            evidence.append({"source": f"src-{i}", "finding": "f", "relevant_to_criteria": True})
        else:
            evidence.append({"source": "", "finding": "f", "relevant_to_criteria": True})

    vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": evidence, "reasoning": "test"}
    case = _make_eval_data(vresult, "recurring")
    result = RecurringFreshnessEvaluator().evaluate(case)

    expected_score = source_count / total_count
    assert abs(result[0].score - expected_score) < 1e-9


# --- Unit tests for edge cases ---


class TestModeEvaluatorEdgeCases:

    def test_at_date_no_verification_result(self):
        case = _make_eval_data({}, "at_date")
        # Override to have no verification_result
        case = EvaluationData(
            input="test", actual_output={}, expected_output=None,
            metadata={"verification_mode": "at_date"},
        )
        result = AtDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_before_date_no_verification_result(self):
        case = EvaluationData(
            input="test", actual_output={}, expected_output=None,
            metadata={"verification_mode": "before_date"},
        )
        result = BeforeDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_recurring_no_evidence(self):
        vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": [], "reasoning": "test"}
        case = _make_eval_data(vresult, "recurring")
        result = RecurringFreshnessEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_at_date_verdict_matches_expected(self):
        """At/after date: verdict matching expected returns 1.0."""
        vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": [], "reasoning": "test"}
        case = _make_eval_data(vresult, "at_date", expected="confirmed")
        result = AtDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 1.0

    def test_at_date_verdict_mismatch(self):
        """At/after date: verdict not matching expected returns 0.0."""
        vresult = {"verdict": "refuted", "confidence": 0.9, "evidence": [], "reasoning": "test"}
        case = _make_eval_data(vresult, "at_date", expected="confirmed")
        result = AtDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_before_date_refuted_before_deadline_is_wrong(self):
        """Before deadline: refuted returns 0.0."""
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        vresult = {"verdict": "refuted", "confidence": 0.9, "evidence": [], "reasoning": "test"}
        case = _make_eval_data(vresult, "before_date", verification_date=future)
        result = BeforeDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 0.0

    def test_before_date_inconclusive_before_deadline_is_ok(self):
        """Before deadline: inconclusive returns 1.0."""
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        vresult = {"verdict": "inconclusive", "confidence": 0.5, "evidence": [], "reasoning": "test"}
        case = _make_eval_data(vresult, "before_date", verification_date=future)
        result = BeforeDateVerdictEvaluator().evaluate(case)
        assert result[0].score == 1.0
