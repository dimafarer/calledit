"""Tier 1: Schema Validity — validates output against Pydantic models."""

import sys
import os

# Add calleditv4/src to path for Pydantic model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "calleditv4", "src"))

from models import ParsedClaim, VerificationPlan, PlanReview  # noqa: E402


def evaluate(bundle: dict) -> dict:
    """Validate bundle against ParsedClaim, VerificationPlan, PlanReview.

    Returns: {"score": 1.0|0.0, "pass": bool, "reason": str}
    """
    errors = []

    try:
        ParsedClaim(**bundle.get("parsed_claim", {}))
    except Exception as e:
        errors.append(f"ParsedClaim: {e}")

    try:
        VerificationPlan(**bundle.get("verification_plan", {}))
    except Exception as e:
        errors.append(f"VerificationPlan: {e}")

    try:
        PlanReview(**bundle.get("plan_review", {}))
    except Exception as e:
        errors.append(f"PlanReview: {e}")

    if errors:
        return {"score": 0.0, "pass": False, "reason": "; ".join(errors)}
    return {"score": 1.0, "pass": True, "reason": "All models validate"}
