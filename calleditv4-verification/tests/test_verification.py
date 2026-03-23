"""Pure function tests for the verification agent.

Tests _make_inconclusive, _build_user_message, model validation,
and bundle_loader utilities. No mocks (Decision 96).
"""

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import get_type_hints

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import EvidenceItem, VerificationResult
from main import _make_inconclusive, _build_user_message
from bundle_loader import _convert_floats_to_decimal


class TestMakeInconclusive:
    def test_verdict_is_inconclusive(self):
        result = _make_inconclusive("test reason")
        assert result.verdict == "inconclusive"

    def test_confidence_is_zero(self):
        result = _make_inconclusive("test reason")
        assert result.confidence == 0.0

    def test_evidence_is_empty(self):
        result = _make_inconclusive("test reason")
        assert result.evidence == []

    def test_reasoning_matches_input(self):
        result = _make_inconclusive("Agent crashed")
        assert result.reasoning == "Agent crashed"


class TestBuildUserMessage:
    SAMPLE_BUNDLE = {
        "parsed_claim": {
            "statement": "Lakers win tonight",
            "verification_date": "2026-03-24T07:00:00Z",
        },
        "verification_plan": {
            "sources": ["ESPN", "NBA.com"],
            "criteria": ["Lakers final score > opponent"],
            "steps": ["Check ESPN for score"],
        },
    }

    def test_contains_statement(self):
        msg = _build_user_message(self.SAMPLE_BUNDLE)
        assert "Lakers win tonight" in msg

    def test_contains_verification_date(self):
        msg = _build_user_message(self.SAMPLE_BUNDLE)
        assert "2026-03-24T07:00:00Z" in msg

    def test_contains_sources(self):
        msg = _build_user_message(self.SAMPLE_BUNDLE)
        assert "ESPN" in msg
        assert "NBA.com" in msg

    def test_contains_criteria(self):
        msg = _build_user_message(self.SAMPLE_BUNDLE)
        assert "Lakers final score > opponent" in msg

    def test_contains_steps(self):
        msg = _build_user_message(self.SAMPLE_BUNDLE)
        assert "Check ESPN for score" in msg

    def test_handles_empty_bundle(self):
        msg = _build_user_message({})
        assert "PREDICTION:" in msg
        assert "VERIFICATION PLAN:" in msg


class TestVerificationResultModel:
    def test_valid_confirmed(self):
        r = VerificationResult(
            verdict="confirmed", confidence=0.9,
            evidence=[], reasoning="Clear evidence",
        )
        assert r.verdict == "confirmed"

    def test_valid_refuted(self):
        r = VerificationResult(
            verdict="refuted", confidence=0.85,
            evidence=[], reasoning="Contradicted",
        )
        assert r.verdict == "refuted"

    def test_valid_inconclusive(self):
        r = VerificationResult(
            verdict="inconclusive", confidence=0.0,
            evidence=[], reasoning="No data",
        )
        assert r.confidence == 0.0

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            VerificationResult(
                verdict="confirmed", confidence=1.5,
                evidence=[], reasoning="test",
            )

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            VerificationResult(
                verdict="confirmed", confidence=-0.1,
                evidence=[], reasoning="test",
            )

    def test_with_evidence_items(self):
        e = EvidenceItem(
            source="https://espn.com",
            finding="Lakers won 110-105",
            relevant_to_criteria="Final score comparison",
        )
        r = VerificationResult(
            verdict="confirmed", confidence=0.95,
            evidence=[e], reasoning="ESPN confirms",
        )
        assert len(r.evidence) == 1
        assert r.evidence[0].source == "https://espn.com"


class TestFieldDescriptions:
    def _get_descriptions(self, model_cls):
        return {
            name: info.description
            for name, info in model_cls.model_fields.items()
        }

    def test_evidence_item_fields_have_descriptions(self):
        descs = self._get_descriptions(EvidenceItem)
        for field in ("source", "finding", "relevant_to_criteria"):
            assert descs[field] is not None
            assert len(descs[field]) > 0

    def test_verification_result_fields_have_descriptions(self):
        descs = self._get_descriptions(VerificationResult)
        for field in ("verdict", "confidence", "evidence", "reasoning"):
            assert descs[field] is not None
            assert len(descs[field]) > 0


class TestConvertFloatsToDecimal:
    def test_float_becomes_decimal(self):
        assert _convert_floats_to_decimal(0.85) == Decimal("0.85")

    def test_nested_dict(self):
        result = _convert_floats_to_decimal({"score": 0.9, "name": "test"})
        assert result["score"] == Decimal("0.9")
        assert result["name"] == "test"

    def test_nested_list(self):
        result = _convert_floats_to_decimal([0.1, 0.2])
        assert result == [Decimal("0.1"), Decimal("0.2")]

    def test_non_float_unchanged(self):
        assert _convert_floats_to_decimal("hello") == "hello"
        assert _convert_floats_to_decimal(42) == 42
