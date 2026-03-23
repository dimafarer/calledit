"""Pydantic models for the 3-turn creation flow.

Each model is used as a Strands `structured_output_model` for type-safe
extraction from a specific turn. All fields include Field(description=...)
so Strands can generate accurate tool specifications (Req 5.10).
"""

from typing import List

from pydantic import BaseModel, Field


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


class ClarificationAnswer(BaseModel):
    """A single question-answer pair from a clarification round."""

    question: str = Field(
        description="The clarification question from the reviewer"
    )
    answer: str = Field(
        description="The user's answer to the clarification question"
    )
