"""Tests for baseline comparison — Property 10."""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.compare_baselines import compare_scores, validate_migration


# Feature: strands-evals-migration, Property 10: Baseline comparison validation logic
@given(
    old_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    new_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=100)
def test_deterministic_exact_match(old_score, new_score):
    """Deterministic evaluators require exact match (tolerance=0.0)."""
    old = {"schema_validity": old_score}
    new = {"schema_validity": new_score}
    results = compare_scores(old, new)

    assert len(results) == 1
    r = results[0]
    assert r["tolerance"] == 0.0
    assert r["pass"] == (old_score == new_score)


# Feature: strands-evals-migration, Property 10: LLM judge tolerance
@given(
    old_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    new_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
@settings(max_examples=100)
def test_llm_judge_tolerance(old_score, new_score):
    """LLM judge evaluators allow ±0.05 tolerance."""
    old = {"intent_preservation": old_score}
    new = {"intent_preservation": new_score}
    results = compare_scores(old, new)

    assert len(results) == 1
    r = results[0]
    assert r["tolerance"] == 0.05
    assert r["pass"] == (abs(old_score - new_score) <= 0.05)


# Feature: strands-evals-migration, Property 10: Validation decision
@given(
    scores=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        ),
        min_size=1,
        max_size=5,
    ),
)
@settings(max_examples=100)
def test_validation_decision(scores):
    """Migration validated iff all comparisons pass."""
    old = {f"eval_{i}": s[0] for i, s in enumerate(scores)}
    new = {f"eval_{i}": s[1] for i, s in enumerate(scores)}
    results = compare_scores(old, new)
    validated = validate_migration(results)

    # All deterministic, so all must be exact match
    all_pass = all(s[0] == s[1] for s in scores)
    assert validated == all_pass


class TestComparisonEdgeCases:

    def test_missing_evaluator_fails(self):
        results = compare_scores({"a": 1.0}, {"b": 1.0})
        assert not validate_migration(results)

    def test_empty_scores(self):
        results = compare_scores({}, {})
        assert validate_migration(results)  # vacuously true

    def test_mixed_deterministic_and_llm(self):
        old = {"schema_validity": 1.0, "intent_preservation": 0.85}
        new = {"schema_validity": 1.0, "intent_preservation": 0.88}
        results = compare_scores(old, new)
        assert validate_migration(results)  # exact + within 0.05

    def test_llm_judge_just_outside_tolerance(self):
        old = {"intent_preservation": 0.80}
        new = {"intent_preservation": 0.86}
        results = compare_scores(old, new)
        assert not validate_migration(results)  # 0.06 > 0.05
