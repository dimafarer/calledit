"""Pydantic models for the 3-turn creation flow.

Each model is used as a Strands `structured_output_model` for type-safe
extraction from a specific turn. All fields include Field(description=...)
so Strands can generate accurate tool specifications (Req 5.10).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

VERIFICATION_MODES = Literal["immediate", "at_date", "before_date", "recurring"]


class ParsedClaim(BaseModel):
    """Turn 1 output: extracted prediction statement with resolved dates."""

    statement: str = Field(
        description="The user's exact prediction statement"
    )
    verification_date: str = Field(
        description="ISO 8601 datetime for when to verify the prediction"
    )
    date_reasoning: str = Field(
        description="Explanation of how the date was resolved from the input"
    )


class VerificationPlan(BaseModel):
    """Turn 2 output: verification plan with sources, criteria, steps."""

    sources: List[str] = Field(
        description="Reliable sources to check for verification"
    )
    criteria: List[str] = Field(
        description="Measurable criteria for determining truth"
    )
    steps: List[str] = Field(
        description="Ordered verification steps to execute"
    )
    verification_mode: VERIFICATION_MODES = Field(
        default="immediate",
        description="Verification timing mode: immediate, at_date, before_date, or recurring",
    )
    recurring_interval: Optional[str] = Field(
        default=None,
        description="Minimum time between recurring checks: 'every_scan', 'daily', or 'weekly'. Only set when verification_mode is 'recurring'.",
    )


class ReviewableSection(BaseModel):
    """A section of the verification plan that could be improved."""

    section: str = Field(
        description="The field name being reviewed"
    )
    improvable: bool = Field(
        description="Whether this section has questionable assumptions"
    )
    questions: List[str] = Field(
        description="Targeted clarification questions referencing specific plan elements"
    )
    reasoning: str = Field(
        description="What assumption in the verification plan this question validates"
    )


class DimensionAssessment(BaseModel):
    """One dimension's assessment from the plan reviewer."""

    dimension: str = Field(
        description="Dimension name: criteria_specificity, source_availability, "
        "temporal_clarity, outcome_objectivity, or tool_coverage"
    )
    assessment: str = Field(
        description="Rating: strong, moderate, or weak"
    )
    explanation: str = Field(
        description="One-line explanation of the rating"
    )


class PlanReview(BaseModel):
    """Turn 3 output: combined verifiability scoring and plan review."""

    verifiability_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Likelihood (0.0-1.0) that the verification agent will "
        "successfully determine the prediction's truth value",
    )
    verifiability_reasoning: str = Field(
        description="Explanation of the score across 5 dimensions"
    )
    reviewable_sections: List[ReviewableSection] = Field(
        description="Sections with assumptions that could be validated "
        "via clarification questions"
    )
    score_tier: str = Field(
        description="Tier: high (>=0.7), moderate (>=0.4), or low (<0.4)"
    )
    score_label: str = Field(
        description="Human-readable label, e.g. 'High Confidence'"
    )
    score_guidance: str = Field(
        description="Actionable guidance text based on the assessment"
    )
    dimension_assessments: List[DimensionAssessment] = Field(
        description="Exactly 5 entries, one per scoring dimension"
    )
    verification_mode: VERIFICATION_MODES = Field(
        default="immediate",
        description="Reviewer's independent assessment of the correct verification mode",
    )


class ClarificationAnswer(BaseModel):
    """A single question-answer pair from a clarification round."""

    question: str = Field(
        description="The clarification question from the reviewer"
    )
    answer: str = Field(
        description="The user's answer to the clarification question"
    )


def score_to_tier(score: float) -> dict:
    """Map a verifiability score to deterministic display constants.

    Clamps score to [0.0, 1.0] before computing tier.
    Returns dict with keys: tier, label, color, icon.
    """
    score = max(0.0, min(1.0, score))
    if score >= 0.7:
        return {"tier": "high", "label": "High Confidence",
                "color": "#166534", "icon": "🟢"}
    if score >= 0.4:
        return {"tier": "moderate", "label": "Moderate Confidence",
                "color": "#854d0e", "icon": "🟡"}
    return {"tier": "low", "label": "Low Confidence",
            "color": "#991b1b", "icon": "🔴"}
