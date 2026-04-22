"""Tests for creation evaluators — Property 3 + edge cases.

Property tests verify that each evaluator returns score=1.0 iff the
corresponding validation condition holds, and score=0.0 otherwise.
"""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.creation import (
    FieldCompletenessEvaluator,
    ScoreRangeEvaluator,
    DateResolutionEvaluator,
    DimensionCountEvaluator,
    TierConsistencyEvaluator,
)
from eval.evaluators.creation.tier_consistency import expected_tier
from strands_evals.evaluators import OutputEvaluator


def _make_eval_data(bundle: dict) -> EvaluationData:
    """Helper to wrap a creation bundle in EvaluationData."""
    return EvaluationData(
        input="test prediction",
        actual_output={"creation_bundle": bundle},
        expected_output="confirmed",
        metadata={},
    )


# --- Property 3: Deterministic creation evaluator equivalence ---


# Feature: strands-evals-migration, Property 3: Field completeness evaluator
@given(
    sources=st.lists(st.text(min_size=1), min_size=0, max_size=3),
    criteria=st.lists(st.text(min_size=1), min_size=0, max_size=3),
    steps=st.lists(st.text(min_size=1), min_size=0, max_size=3),
)
@settings(max_examples=100)
def test_field_completeness_property(sources, criteria, steps):
    """Score=1.0 iff all three list fields are non-empty."""
    bundle = {"verification_plan": {"sources": sources, "criteria": criteria, "steps": steps}}
    result = FieldCompletenessEvaluator().evaluate(_make_eval_data(bundle))

    all_non_empty = len(sources) > 0 and len(criteria) > 0 and len(steps) > 0
    assert result[0].score == (1.0 if all_non_empty else 0.0)
    assert result[0].test_pass == all_non_empty


# Feature: strands-evals-migration, Property 3: Score range evaluator
@given(score=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_score_range_property(score):
    """Score=1.0 iff verifiability_score is in [0.0, 1.0]."""
    bundle = {"plan_review": {"verifiability_score": score}}
    result = ScoreRangeEvaluator().evaluate(_make_eval_data(bundle))

    in_range = 0.0 <= score <= 1.0
    assert result[0].score == (1.0 if in_range else 0.0)
    assert result[0].test_pass == in_range


# Feature: strands-evals-migration, Property 3: Date resolution evaluator
@given(
    date_str=st.one_of(
        # Valid ISO dates
        st.from_regex(r"20\d{2}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\dZ", fullmatch=True),
        # Invalid strings
        st.text(min_size=1, max_size=20),
    )
)
@settings(max_examples=100)
def test_date_resolution_property(date_str):
    """Score=1.0 iff verification_date is valid ISO 8601."""
    from datetime import datetime

    bundle = {"parsed_claim": {"verification_date": date_str}}
    result = DateResolutionEvaluator().evaluate(_make_eval_data(bundle))

    # Check if it's actually valid
    try:
        datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        is_valid = True
    except (ValueError, TypeError):
        is_valid = False

    assert result[0].score == (1.0 if is_valid else 0.0)


# Feature: strands-evals-migration, Property 3: Dimension count evaluator
@given(count=st.integers(min_value=0, max_value=10))
@settings(max_examples=100)
def test_dimension_count_property(count):
    """Score=1.0 iff at least 1 dimension assessment exists."""
    dims = [{"name": f"dim-{i}", "score": 0.5} for i in range(count)]
    bundle = {"plan_review": {"dimension_assessments": dims}}
    result = DimensionCountEvaluator().evaluate(_make_eval_data(bundle))

    has_dims = count >= 1
    assert result[0].score == (1.0 if has_dims else 0.0)
    assert result[0].test_pass == has_dims


# Feature: strands-evals-migration, Property 3: Tier consistency evaluator
@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@settings(max_examples=100)
def test_tier_consistency_correct_tier(score):
    """Score=1.0 when tier label matches the score thresholds."""
    tier = expected_tier(score)
    bundle = {"plan_review": {"verifiability_score": score, "score_tier": tier}}
    result = TierConsistencyEvaluator().evaluate(_make_eval_data(bundle))
    assert result[0].score == 1.0
    assert result[0].test_pass is True


# Feature: strands-evals-migration, Property 3: Tier consistency wrong tier
@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
@settings(max_examples=100)
def test_tier_consistency_wrong_tier(score):
    """Score=0.0 when tier label doesn't match the score thresholds."""
    correct = expected_tier(score)
    wrong = {"high": "low", "moderate": "high", "low": "moderate"}[correct]
    bundle = {"plan_review": {"verifiability_score": score, "score_tier": wrong}}
    result = TierConsistencyEvaluator().evaluate(_make_eval_data(bundle))
    assert result[0].score == 0.0
    assert result[0].test_pass is False


# --- Unit tests for edge cases (Task 4.9) ---


class TestCreationEvaluatorEdgeCases:
    """Edge case tests for all 6 creation evaluators."""

    def test_no_bundle_returns_zero(self):
        """All evaluators return 0.0 when no creation_bundle."""
        case = EvaluationData(
            input="test", actual_output={}, expected_output=None, metadata={}
        )
        for cls in [
            FieldCompletenessEvaluator,
            ScoreRangeEvaluator,
            DateResolutionEvaluator,
            DimensionCountEvaluator,
            TierConsistencyEvaluator,
        ]:
            result = cls().evaluate(case)
            assert result[0].score == 0.0, f"{cls.__name__} should return 0.0"

    def test_none_actual_output(self):
        """All evaluators handle None actual_output."""
        case = EvaluationData(
            input="test", actual_output=None, expected_output=None, metadata={}
        )
        for cls in [
            FieldCompletenessEvaluator,
            ScoreRangeEvaluator,
            DateResolutionEvaluator,
            DimensionCountEvaluator,
            TierConsistencyEvaluator,
        ]:
            result = cls().evaluate(case)
            assert result[0].score == 0.0

    def test_score_range_non_numeric(self):
        """ScoreRangeEvaluator returns 0.0 for non-numeric score."""
        bundle = {"plan_review": {"verifiability_score": "not a number"}}
        result = ScoreRangeEvaluator().evaluate(_make_eval_data(bundle))
        assert result[0].score == 0.0

    def test_dimension_count_not_list(self):
        """DimensionCountEvaluator returns 0.0 when dimension_assessments is not a list."""
        bundle = {"plan_review": {"dimension_assessments": "not a list"}}
        result = DimensionCountEvaluator().evaluate(_make_eval_data(bundle))
        assert result[0].score == 0.0

    def test_date_resolution_none_date(self):
        """DateResolutionEvaluator returns 0.0 for None date."""
        bundle = {"parsed_claim": {"verification_date": None}}
        result = DateResolutionEvaluator().evaluate(_make_eval_data(bundle))
        assert result[0].score == 0.0

    def test_field_completeness_non_list_fields(self):
        """FieldCompletenessEvaluator returns 0.0 for non-list fields."""
        bundle = {"verification_plan": {"sources": "not a list", "criteria": [], "steps": []}}
        result = FieldCompletenessEvaluator().evaluate(_make_eval_data(bundle))
        assert result[0].score == 0.0

    def test_tier_consistency_non_numeric_score(self):
        """TierConsistencyEvaluator returns 0.0 for non-numeric score."""
        bundle = {"plan_review": {"verifiability_score": None, "score_tier": "high"}}
        result = TierConsistencyEvaluator().evaluate(_make_eval_data(bundle))
        assert result[0].score == 0.0


# --- LLM judge configuration tests (Task 8.7) ---


class TestLLMJudgeConfiguration:
    """Verify LLM judge evaluators are correctly configured (no LLM invocation)."""

    def test_intent_preservation_config(self):
        from eval.evaluators.creation.intent_preservation import (
            create_intent_preservation_evaluator,
            RUBRIC,
            JUDGE_MODEL,
        )
        evaluator = create_intent_preservation_evaluator()
        assert isinstance(evaluator, OutputEvaluator)
        assert "FIDELITY" in RUBRIC
        assert "TEMPORAL INTENT" in RUBRIC
        assert JUDGE_MODEL == "us.anthropic.claude-sonnet-4-20250514-v1:0"

    def test_plan_quality_config(self):
        from eval.evaluators.creation.plan_quality import (
            create_plan_quality_evaluator,
            RUBRIC,
            JUDGE_MODEL,
        )
        evaluator = create_plan_quality_evaluator()
        assert isinstance(evaluator, OutputEvaluator)
        assert "CRITERIA SPECIFICITY" in RUBRIC
        assert "SOURCE ACCESSIBILITY" in RUBRIC
        assert JUDGE_MODEL == "us.anthropic.claude-sonnet-4-20250514-v1:0"

    def test_evidence_quality_config(self):
        from eval.evaluators.verification.evidence_quality import (
            create_evidence_quality_evaluator,
            RUBRIC,
            JUDGE_MODEL,
        )
        evaluator = create_evidence_quality_evaluator()
        assert isinstance(evaluator, OutputEvaluator)
        assert "SOURCE AUTHENTICITY" in RUBRIC
        assert "FINDING SPECIFICITY" in RUBRIC
        assert JUDGE_MODEL == "us.anthropic.claude-sonnet-4-20250514-v1:0"
