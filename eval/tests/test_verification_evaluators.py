"""Tests for verification evaluators — Property 4 + edge cases."""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from eval.evaluators.verification import (
    VerificationSchemaEvaluator,
    VerdictValidityEvaluator,
    ConfidenceRangeEvaluator,
    EvidenceCompletenessEvaluator,
    EvidenceStructureEvaluator,
)


def _make_eval_data(vresult: dict) -> EvaluationData:
    return EvaluationData(
        input="test", actual_output={"verification_result": vresult},
        expected_output="confirmed", metadata={},
    )


# --- Property 4: Deterministic verification evaluator equivalence ---


# Feature: strands-evals-migration, Property 4: Verdict validity evaluator
@given(verdict=st.text(min_size=0, max_size=20))
@settings(max_examples=100)
def test_verdict_validity_property(verdict):
    """Score=1.0 iff verdict is in {confirmed, refuted, inconclusive}."""
    vresult = {"verdict": verdict, "confidence": 0.9, "evidence": [], "reasoning": "test"}
    result = VerdictValidityEvaluator().evaluate(_make_eval_data(vresult))
    valid = verdict in {"confirmed", "refuted", "inconclusive"}
    assert result[0].score == (1.0 if valid else 0.0)


# Feature: strands-evals-migration, Property 4: Confidence range evaluator
@given(conf=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_confidence_range_property(conf):
    """Score=1.0 iff confidence is in [0.0, 1.0]."""
    vresult = {"verdict": "confirmed", "confidence": conf, "evidence": [], "reasoning": "test"}
    result = ConfidenceRangeEvaluator().evaluate(_make_eval_data(vresult))
    in_range = 0.0 <= conf <= 1.0
    assert result[0].score == (1.0 if in_range else 0.0)


# Feature: strands-evals-migration, Property 4: Evidence completeness evaluator
@given(count=st.integers(min_value=0, max_value=5))
@settings(max_examples=100)
def test_evidence_completeness_property(count):
    """Score=1.0 iff at least 1 evidence item."""
    evidence = [{"source": f"s{i}", "finding": f"f{i}", "relevant_to_criteria": True} for i in range(count)]
    vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": evidence, "reasoning": "test"}
    result = EvidenceCompletenessEvaluator().evaluate(_make_eval_data(vresult))
    assert result[0].score == (1.0 if count >= 1 else 0.0)


# Feature: strands-evals-migration, Property 4: Evidence structure evaluator
@given(
    has_source=st.booleans(),
    has_finding=st.booleans(),
    has_relevant=st.booleans(),
)
@settings(max_examples=100)
def test_evidence_structure_property(has_source, has_finding, has_relevant):
    """Score=1.0 iff all evidence items have source, finding, relevant_to_criteria."""
    item = {}
    if has_source:
        item["source"] = "espn.com"
    if has_finding:
        item["finding"] = "score was 100-90"
    if has_relevant:
        item["relevant_to_criteria"] = True

    vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": [item], "reasoning": "test"}
    result = EvidenceStructureEvaluator().evaluate(_make_eval_data(vresult))
    all_present = has_source and has_finding and has_relevant
    assert result[0].score == (1.0 if all_present else 0.0)


# Feature: strands-evals-migration, Property 4: Schema validity evaluator
@given(
    has_verdict=st.booleans(),
    has_confidence=st.booleans(),
    has_evidence=st.booleans(),
    has_reasoning=st.booleans(),
)
@settings(max_examples=100)
def test_schema_validity_property(has_verdict, has_confidence, has_evidence, has_reasoning):
    """Score=1.0 iff all required fields present with correct types."""
    vresult = {}
    if has_verdict:
        vresult["verdict"] = "confirmed"
    if has_confidence:
        vresult["confidence"] = 0.9
    if has_evidence:
        vresult["evidence"] = []
    if has_reasoning:
        vresult["reasoning"] = "test"

    result = VerificationSchemaEvaluator().evaluate(_make_eval_data(vresult))
    all_present = has_verdict and has_confidence and has_evidence and has_reasoning
    assert result[0].score == (1.0 if all_present else 0.0)


# --- Unit tests for edge cases ---


class TestVerificationEvaluatorEdgeCases:

    def test_no_verification_result(self):
        """All evaluators return 0.0 when no verification_result."""
        case = EvaluationData(input="test", actual_output={}, expected_output=None, metadata={})
        for cls in [
            VerificationSchemaEvaluator, VerdictValidityEvaluator,
            ConfidenceRangeEvaluator, EvidenceCompletenessEvaluator,
            EvidenceStructureEvaluator,
        ]:
            result = cls().evaluate(case)
            assert result[0].score == 0.0, f"{cls.__name__} should return 0.0"

    def test_none_actual_output(self):
        case = EvaluationData(input="test", actual_output=None, expected_output=None, metadata={})
        for cls in [
            VerificationSchemaEvaluator, VerdictValidityEvaluator,
            ConfidenceRangeEvaluator, EvidenceCompletenessEvaluator,
            EvidenceStructureEvaluator,
        ]:
            result = cls().evaluate(case)
            assert result[0].score == 0.0

    def test_confidence_non_numeric(self):
        vresult = {"verdict": "confirmed", "confidence": "high", "evidence": [], "reasoning": "test"}
        result = ConfidenceRangeEvaluator().evaluate(_make_eval_data(vresult))
        assert result[0].score == 0.0

    def test_evidence_not_list(self):
        vresult = {"verdict": "confirmed", "confidence": 0.9, "evidence": "not a list", "reasoning": "test"}
        result = EvidenceStructureEvaluator().evaluate(_make_eval_data(vresult))
        assert result[0].score == 0.0
