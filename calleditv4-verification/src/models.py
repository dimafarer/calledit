"""Pydantic models for the verification agent verdict output.

Each model is used as a Strands `structured_output_model` for type-safe
extraction. All fields include Field(description=...) so Strands can
generate accurate tool specifications.
"""

from typing import List

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single piece of evidence gathered during verification."""

    source: str = Field(
        description="URL or source name where evidence was found"
    )
    finding: str = Field(
        description="What was found at this source"
    )
    relevant_to_criteria: str = Field(
        description="Which verification criterion this evidence addresses"
    )


class VerificationResult(BaseModel):
    """Complete verification verdict — used as structured_output_model."""

    verdict: str = Field(
        description="Verification outcome: confirmed, refuted, or inconclusive"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the verdict (0.0 to 1.0)",
    )
    evidence: List[EvidenceItem] = Field(
        description="Evidence items gathered during verification"
    )
    reasoning: str = Field(
        description="Explanation of how evidence maps to criteria "
        "and why this verdict was chosen"
    )
