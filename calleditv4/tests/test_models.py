"""Unit and property tests for Pydantic models (V4-3a).

Tests verify model structure, field types, Field descriptions (Req 5.10),
and PlanReview score validation via property-based testing.

No mocks. Decision 96: v4 has zero mocks across all test types.
"""

import sys
from pathlib import Path
from typing import List, get_type_hints

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import Field, ValidationError

# Add src to path so we can import models
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models import (
    DimensionAssessment,
    ParsedClaim,
    PlanReview,
    ReviewableSection,
    VerificationPlan,
    score_to_tier,
)


# Default V4-4 fields for PlanReview construction in tests
_DEFAULT_DIMS = [
    DimensionAssessment(dimension="criteria_specificity", assessment="strong", explanation="test"),
    DimensionAssessment(dimension="source_availability", assessment="strong", explanation="test"),
    DimensionAssessment(dimension="temporal_clarity", assessment="moderate", explanation="test"),
    DimensionAssessment(dimension="outcome_objectivity", assessment="strong", explanation="test"),
    DimensionAssessment(dimension="tool_coverage", assessment="strong", explanation="test"),
]

_V44_FIELDS = {
    "score_tier": "high",
    "score_label": "High Confidence",
    "score_guidance": "Good to go.",
    "dimension_assessments": _DEFAULT_DIMS,
}


# ---------------------------------------------------------------------------
# Unit Tests — Task 1.2
# ---------------------------------------------------------------------------


class TestParsedClaimStructure:
    """Verify ParsedClaim has the correct fields (Req 5.2)."""

    def test_has_statement_field(self):
        claim = ParsedClaim(
            statement="Lakers win tonight",
            verification_date="2025-01-15T23:00:00Z",
            date_reasoning="Tonight resolved to end of day",
        )
        assert claim.statement == "Lakers win tonight"

    def test_has_verification_date_field(self):
        claim = ParsedClaim(
            statement="test",
            verification_date="2025-06-01T00:00:00Z",
            date_reasoning="test",
        )
        assert claim.verification_date == "2025-06-01T00:00:00Z"

    def test_has_date_reasoning_field(self):
        claim = ParsedClaim(
            statement="test",
            verification_date="2025-06-01T00:00:00Z",
            date_reasoning="Resolved from relative date",
        )
        assert claim.date_reasoning == "Resolved from relative date"

    def test_all_fields_are_str(self):
        hints = get_type_hints(ParsedClaim)
        assert hints["statement"] is str
        assert hints["verification_date"] is str
        assert hints["date_reasoning"] is str


class TestVerificationPlanStructure:
    """Verify VerificationPlan has the correct fields (Req 5.3)."""

    def test_has_sources_field(self):
        plan = VerificationPlan(
            sources=["ESPN", "NBA.com"],
            criteria=["Final score"],
            steps=["Check score"],
        )
        assert plan.sources == ["ESPN", "NBA.com"]

    def test_has_criteria_field(self):
        plan = VerificationPlan(
            sources=["src"], criteria=["c1", "c2"], steps=["s1"]
        )
        assert plan.criteria == ["c1", "c2"]

    def test_has_steps_field(self):
        plan = VerificationPlan(
            sources=["src"], criteria=["c1"], steps=["step1", "step2"]
        )
        assert plan.steps == ["step1", "step2"]

    def test_all_fields_are_list_str(self):
        hints = get_type_hints(VerificationPlan)
        assert hints["sources"] == List[str]
        assert hints["criteria"] == List[str]
        assert hints["steps"] == List[str]


class TestReviewableSectionStructure:
    """Verify ReviewableSection has the correct fields (Req 5.4)."""

    def test_has_section_field(self):
        rs = ReviewableSection(
            section="sources",
            improvable=True,
            questions=["Why ESPN?"],
            reasoning="ESPN may not cover this",
        )
        assert rs.section == "sources"

    def test_has_improvable_field(self):
        rs = ReviewableSection(
            section="criteria",
            improvable=False,
            questions=[],
            reasoning="Criteria are clear",
        )
        assert rs.improvable is False

    def test_has_questions_field(self):
        rs = ReviewableSection(
            section="steps",
            improvable=True,
            questions=["Q1", "Q2"],
            reasoning="Steps need clarification",
        )
        assert rs.questions == ["Q1", "Q2"]

    def test_has_reasoning_field(self):
        rs = ReviewableSection(
            section="steps",
            improvable=True,
            questions=["Q1"],
            reasoning="Assumption about timing",
        )
        assert rs.reasoning == "Assumption about timing"


class TestPlanReviewStructure:
    """Verify PlanReview has the correct fields (Req 5.4)."""

    def test_has_verifiability_score_field(self):
        review = PlanReview(
            verifiability_score=0.85,
            verifiability_reasoning="Good plan",
            reviewable_sections=[],
            **_V44_FIELDS,
        )
        assert review.verifiability_score == 0.85

    def test_has_verifiability_reasoning_field(self):
        review = PlanReview(
            verifiability_score=0.5,
            verifiability_reasoning="Moderate confidence",
            reviewable_sections=[],
            **_V44_FIELDS,
        )
        assert review.verifiability_reasoning == "Moderate confidence"

    def test_has_reviewable_sections_field(self):
        section = ReviewableSection(
            section="sources",
            improvable=True,
            questions=["Why?"],
            reasoning="Unclear source",
        )
        review = PlanReview(
            verifiability_score=0.7,
            verifiability_reasoning="OK",
            reviewable_sections=[section],
            **_V44_FIELDS,
        )
        assert len(review.reviewable_sections) == 1
        assert review.reviewable_sections[0].section == "sources"

    def test_has_v44_score_tier_fields(self):
        review = PlanReview(
            verifiability_score=0.8,
            verifiability_reasoning="test",
            reviewable_sections=[],
            **_V44_FIELDS,
        )
        assert review.score_tier == "high"
        assert review.score_label == "High Confidence"
        assert review.score_guidance == "Good to go."
        assert len(review.dimension_assessments) == 5


class TestFieldDescriptions:
    """Verify all Pydantic model fields have Field(description=...) (Req 5.10)."""

    def _get_field_descriptions(self, model_cls):
        """Extract field name → description mapping from a Pydantic model."""
        return {
            name: info.description
            for name, info in model_cls.model_fields.items()
        }

    def test_parsed_claim_fields_have_descriptions(self):
        descs = self._get_field_descriptions(ParsedClaim)
        for field_name in ("statement", "verification_date", "date_reasoning"):
            assert descs[field_name] is not None, (
                f"ParsedClaim.{field_name} missing Field(description=...)"
            )
            assert len(descs[field_name]) > 0

    def test_verification_plan_fields_have_descriptions(self):
        descs = self._get_field_descriptions(VerificationPlan)
        for field_name in ("sources", "criteria", "steps"):
            assert descs[field_name] is not None, (
                f"VerificationPlan.{field_name} missing Field(description=...)"
            )
            assert len(descs[field_name]) > 0

    def test_reviewable_section_fields_have_descriptions(self):
        descs = self._get_field_descriptions(ReviewableSection)
        for field_name in ("section", "improvable", "questions", "reasoning"):
            assert descs[field_name] is not None, (
                f"ReviewableSection.{field_name} missing Field(description=...)"
            )
            assert len(descs[field_name]) > 0

    def test_plan_review_fields_have_descriptions(self):
        descs = self._get_field_descriptions(PlanReview)
        for field_name in (
            "verifiability_score",
            "verifiability_reasoning",
            "reviewable_sections",
            "score_tier",
            "score_label",
            "score_guidance",
            "dimension_assessments",
        ):
            assert descs[field_name] is not None, (
                f"PlanReview.{field_name} missing Field(description=...)"
            )
            assert len(descs[field_name]) > 0

    def test_dimension_assessment_fields_have_descriptions(self):
        descs = self._get_field_descriptions(DimensionAssessment)
        for field_name in ("dimension", "assessment", "explanation"):
            assert descs[field_name] is not None, (
                f"DimensionAssessment.{field_name} missing Field(description=...)"
            )
            assert len(descs[field_name]) > 0


# ---------------------------------------------------------------------------
# Property Test — Task 1.3
# Feature: creation-agent-core, Property 8: PlanReview score validation
# **Validates: Requirements 5.4**
# ---------------------------------------------------------------------------


class TestPlanReviewScoreValidation:
    """Property 8: PlanReview verifiability_score must be in [0.0, 1.0]."""

    @settings(max_examples=100)
    @given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    def test_valid_scores_accepted(self, score):
        """For any float within [0.0, 1.0], PlanReview construction succeeds."""
        review = PlanReview(
            verifiability_score=score,
            verifiability_reasoning="test",
            reviewable_sections=[],
            **_V44_FIELDS,
        )
        assert review.verifiability_score == score

    @settings(max_examples=100)
    @given(score=st.floats(min_value=1.0001, allow_nan=False, allow_infinity=False))
    def test_scores_above_one_rejected(self, score):
        """For any float > 1.0, PlanReview construction raises ValidationError."""
        with pytest.raises(ValidationError):
            PlanReview(
                verifiability_score=score,
                verifiability_reasoning="test",
                reviewable_sections=[],
                **_V44_FIELDS,
            )

    @settings(max_examples=100)
    @given(score=st.floats(max_value=-0.0001, allow_nan=False, allow_infinity=False))
    def test_scores_below_zero_rejected(self, score):
        """For any float < 0.0, PlanReview construction raises ValidationError."""
        with pytest.raises(ValidationError):
            PlanReview(
                verifiability_score=score,
                verifiability_reasoning="test",
                reviewable_sections=[],
                **_V44_FIELDS,
            )

    def test_nan_rejected(self):
        with pytest.raises(ValidationError):
            PlanReview(
                verifiability_score=float("nan"),
                verifiability_reasoning="test",
                reviewable_sections=[],
                **_V44_FIELDS,
            )

    def test_positive_infinity_rejected(self):
        with pytest.raises(ValidationError):
            PlanReview(
                verifiability_score=float("inf"),
                verifiability_reasoning="test",
                reviewable_sections=[],
                **_V44_FIELDS,
            )

    def test_negative_infinity_rejected(self):
        with pytest.raises(ValidationError):
            PlanReview(
                verifiability_score=float("-inf"),
                verifiability_reasoning="test",
                reviewable_sections=[],
                **_V44_FIELDS,
            )


# ---------------------------------------------------------------------------
# V4-4: score_to_tier tests
# ---------------------------------------------------------------------------


class TestScoreToTier:
    """Verify score_to_tier() boundary behavior and output structure."""

    def test_high_tier_at_0_7(self):
        result = score_to_tier(0.7)
        assert result["tier"] == "high"
        assert result["label"] == "High Confidence"
        assert result["color"] == "#166534"
        assert result["icon"] == "🟢"

    def test_high_tier_at_1_0(self):
        result = score_to_tier(1.0)
        assert result["tier"] == "high"

    def test_moderate_tier_at_0_4(self):
        result = score_to_tier(0.4)
        assert result["tier"] == "moderate"
        assert result["label"] == "Moderate Confidence"
        assert result["color"] == "#854d0e"
        assert result["icon"] == "🟡"

    def test_moderate_tier_at_0_69(self):
        result = score_to_tier(0.69)
        assert result["tier"] == "moderate"

    def test_low_tier_at_0_0(self):
        result = score_to_tier(0.0)
        assert result["tier"] == "low"
        assert result["label"] == "Low Confidence"
        assert result["color"] == "#991b1b"
        assert result["icon"] == "🔴"

    def test_low_tier_at_0_39(self):
        result = score_to_tier(0.39)
        assert result["tier"] == "low"

    def test_clamps_negative(self):
        result = score_to_tier(-0.5)
        assert result["tier"] == "low"

    def test_clamps_above_one(self):
        result = score_to_tier(1.5)
        assert result["tier"] == "high"

    def test_output_has_four_keys(self):
        result = score_to_tier(0.5)
        assert set(result.keys()) == {"tier", "label", "color", "icon"}

    def test_no_legacy_category_in_plan_review(self):
        """Verify PlanReview schema does NOT include legacy_category (Decision 103)."""
        assert "legacy_category" not in PlanReview.model_fields
