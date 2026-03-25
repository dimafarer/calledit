#!/usr/bin/env python3
"""Reshape the v3 golden dataset to v4-native format.

Removes v3 technical debt (3-category system, tool_manifest_config),
adds v4 fields (verifiability score ranges, verification outcomes,
smoke test flags), updates evaluation rubric text to v4 concepts.

Idempotent — running twice produces identical output.

Decisions: 122 (tiered evaluators), 124 (dataset reshape),
           125 (smoke test subset), 126 (priority metrics)
"""

import json
import logging
import sys

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Lookup Tables ---

# Score ranges: [low, high] based on ground truth analysis.
# auto_verifiable (objective, public data, accessible tools) → [0.7, 1.0]
# automatable (data exists but needs specific tools/timing) → [0.4, 0.7]
# human_only (subjective, physical observation, private data) → [0.0, 0.4]
# Individual overrides where the default doesn't fit.
SCORE_RANGES: dict[str, list[float]] = {
    # auto_verifiable — high confidence
    "base-001": [0.8, 1.0],   # sunrise — astronomical certainty
    "base-002": [0.8, 1.0],   # Christmas Friday — calendar arithmetic
    "base-003": [0.7, 0.9],   # Central Park temp — weather forecast via Browser
    "base-004": [0.7, 0.9],   # S&P 500 higher — financial data via Browser
    "base-005": [0.7, 0.9],   # London rain — weather forecast via Browser
    "base-006": [0.6, 0.9],   # USGS earthquake 5.0+ — 30-day window adds complexity
    "base-007": [0.7, 0.9],   # Yankees game after 6pm — schedule data via Browser
    "base-008": [0.8, 1.0],   # Tokyo temp >10°C — real-time weather via Browser
    "base-009": [0.7, 0.9],   # US national debt >$35T — Treasury data via Browser
    "base-010": [0.8, 1.0],   # next full moon before April 1 — astronomical calc
    "base-011": [0.7, 0.9],   # Python 3.13 released — python.org via Browser
    "base-012": [0.7, 0.9],   # EUR/USD >1.05 — financial data via Browser
    "base-013": [0.6, 0.9],   # Wikipedia AI >500 refs — page parsing via Browser
    # automatable — moderate confidence
    "base-014": [0.4, 0.7],   # Bitcoin >$100k by Dec 2026 — future event
    "base-015": [0.4, 0.7],   # Flight AA1234 on time — airline data, timing dependent
    "base-016": [0.4, 0.7],   # iPhone Sept 2026 — future Apple announcement
    "base-017": [0.4, 0.7],   # Atlantic hurricane Cat 4+ — seasonal, monitoring needed
    "base-018": [0.4, 0.7],   # World Cup 2026 team — future sports event
    "base-019": [0.4, 0.7],   # Fed rate cut — future monetary policy
    "base-020": [0.4, 0.7],   # Tesla deliveries >500k — future quarterly report
    "base-021": [0.4, 0.7],   # Yellowstone geyser — geological monitoring
    "base-022": [0.3, 0.5],   # Amazon package by Friday — private tracking data
    "base-023": [0.3, 0.5],   # DMV wait <30 min — no public real-time data
    "base-024": [0.4, 0.7],   # Airbnb <$150/night — search-dependent, timing
    "base-025": [0.4, 0.7],   # cherry blossoms peak — NPS monitoring
    "base-026": [0.4, 0.7],   # SpaceX Starship before May 1 — volatile schedule
    # human_only — low confidence
    "base-027": [0.05, 0.25],  # enjoy movie — subjective emotional state
    "base-028": [0.05, 0.25],  # meeting go well — subjective quality judgment
    "base-029": [0.05, 0.2],   # Tom blue shirt — physical observation required
    "base-030": [0.05, 0.2],   # feel happy tomorrow — subjective emotional state
    "base-031": [0.1, 0.3],    # soufflé won't fall — physical observation
    "base-032": [0.05, 0.2],   # dream about flying — private mental state
    "base-033": [0.1, 0.3],    # get promotion — private workplace decision
    "base-034": [0.05, 0.25],  # dinner taste good — subjective taste
    "base-035": [0.1, 0.3],    # relationship improve — mixed subjective/objective
    "base-036": [0.15, 0.35],  # concert sell out — objective but private sales data
    "base-037": [0.1, 0.3],    # coworker quit — private personal decision
    "base-038": [0.15, 0.35],  # book bestseller — objective but future list data
    "base-039": [0.1, 0.3],    # neighbor move — private personal decision
    # boundary cases
    "base-040": [0.8, 1.0],   # boundary: auto_verifiable, easy, nature, immediate
    "base-041": [0.15, 0.35],  # boundary: human_only, medium, tech, objective
    "base-042": [0.1, 0.3],    # boundary: human_only, medium, weather, subjective
    "base-043": [0.1, 0.3],    # boundary: human_only, hard, food, objective
    "base-044": [0.3, 0.5],    # boundary: automatable, hard, health, private but objective
    "base-045": [0.15, 0.35],  # boundary: human_only, hard, travel, objective
}

# Verification outcomes: what the verification agent would conclude.
# "confirmed"/"refuted" for deterministic/immediate, null for future/subjective.
VERIFICATION_OUTCOMES: dict[str, str | None] = {
    "base-001": "confirmed",     # sunrise — always true
    "base-002": "confirmed",     # Christmas 2026 is Friday — true
    "base-003": None,            # weather tomorrow — future
    "base-004": None,            # S&P 500 today — depends on market
    "base-005": None,            # London rain tomorrow — future
    "base-006": None,            # earthquake 30 days — future window
    "base-007": None,            # Yankees next game — schedule may change
    "base-008": None,            # Tokyo temp now — depends on current weather
    "base-009": "confirmed",     # US debt >$35T — currently true (as of 2026)
    "base-010": "confirmed",     # full moon before April 1 — astronomical certainty
    "base-011": "confirmed",     # Python 3.13 released — yes, released Oct 2024
    "base-012": None,            # EUR/USD >1.05 — depends on current rate
    "base-013": "confirmed",     # Wikipedia AI >500 refs — currently true
    "base-014": None,            # Bitcoin >$100k by Dec 2026 — future
    "base-015": None,            # flight on time — future
    "base-016": None,            # iPhone Sept 2026 — future
    "base-017": None,            # hurricane Cat 4+ — future season
    "base-018": None,            # World Cup team — future
    "base-019": None,            # Fed rate cut — future
    "base-020": None,            # Tesla deliveries — future quarter
    "base-021": None,            # Yellowstone geyser — geological
    "base-022": None,            # Amazon package — private tracking
    "base-023": None,            # DMV wait — no data
    "base-024": None,            # Airbnb price — search-dependent
    "base-025": None,            # cherry blossoms — future season
    "base-026": None,            # SpaceX launch — future
    "base-027": None,            # enjoy movie — subjective
    "base-028": None,            # meeting go well — subjective
    "base-029": None,            # Tom blue shirt — physical observation
    "base-030": None,            # feel happy — subjective
    "base-031": None,            # soufflé — physical observation
    "base-032": None,            # dream — private mental state
    "base-033": None,            # promotion — private decision
    "base-034": None,            # dinner taste — subjective
    "base-035": None,            # relationship — mixed
    "base-036": None,            # concert sell out — future
    "base-037": None,            # coworker quit — private
    "base-038": None,            # book bestseller — future
    "base-039": None,            # neighbor move — private
    "base-040": "confirmed",     # boundary: astronomical certainty
    "base-041": None,            # boundary: tech, objective but human-only
    "base-042": None,            # boundary: weather, subjective framing
    "base-043": None,            # boundary: food, objective but needs context
    "base-044": None,            # boundary: health, private data
    "base-045": None,            # boundary: travel, objective but human-only
}

# Smoke test subset: 12 cases (4 easy + 5 medium + 3 hard), all 12 domains.
# Includes boundary, immediate, subjective, and objective cases.
SMOKE_TEST_IDS: set[str] = {
    # Easy (4): personal, weather, entertainment, food
    "base-002",  # easy, personal, objective, immediate
    "base-008",  # easy, weather, objective, immediate
    "base-027",  # easy, entertainment, subjective
    "base-034",  # easy, food, subjective
    # Medium (5): finance, sports, tech, travel, work
    "base-004",  # medium, finance, objective
    "base-007",  # medium, sports, objective, immediate
    "base-011",  # medium, tech, objective, immediate
    "base-015",  # medium, travel, objective
    "base-033",  # medium, work, objective (human_only — promotion)
    # Hard (3): nature, social, health
    "base-006",  # hard, nature, objective
    "base-023",  # hard, social, objective
    "base-044",  # hard, health, objective, boundary case
}

CATEGORY_TO_TIER: dict[str, str] = {
    "auto_verifiable": "high",
    "automatable": "moderate",
    "human_only": "low",
}

# V3 rubric text replacements → v4 concepts
RUBRIC_REPLACEMENTS: list[tuple[str, str]] = [
    ("auto_verifiable", "high verifiability (score ≥0.7)"),
    ("automatable", "moderate verifiability (score 0.4–0.7)"),
    ("human_only", "low verifiability (score <0.4)"),
    ("Categorizer should", "The creation agent's verifiability scoring should"),
    ("Categorizer must", "The creation agent's verifiability scoring must"),
    ("categorizer should", "the creation agent's verifiability scoring should"),
    ("categorizer must", "the creation agent's verifiability scoring must"),
    ("Categorizer reasoning", "Verifiability score reasoning"),
    ("categorizer reasoning", "verifiability score reasoning"),
    (" VB ", " VerificationPlan "),
    ("VB should", "VerificationPlan should"),
    ("VB steps", "VerificationPlan steps"),
]


# --- Transformation Functions ---


def update_rubric(text: str) -> str:
    """Replace v3 terms in evaluation rubric text with v4 concepts."""
    for old, new in RUBRIC_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def transform_base_prediction(pred: dict) -> dict:
    """Apply all v3→v4 transformations to a base prediction.

    Idempotent: safe to run on already-transformed predictions.
    """
    result = dict(pred)

    # Remove v3 dead fields (silent skip for idempotency)
    result.pop("expected_per_agent_outputs", None)
    result.pop("tool_manifest_config", None)

    # Add v4 fields from lookup tables
    pred_id = result.get("id", "")

    if pred_id in SCORE_RANGES:
        result["expected_verifiability_score_range"] = SCORE_RANGES[pred_id]
    elif "expected_verifiability_score_range" not in result:
        logger.warning(f"No score range for {pred_id} — skipping")

    if pred_id in VERIFICATION_OUTCOMES:
        result["expected_verification_outcome"] = VERIFICATION_OUTCOMES[pred_id]
    elif "expected_verification_outcome" not in result:
        logger.warning(f"No verification outcome for {pred_id} — skipping")

    result["smoke_test"] = pred_id in SMOKE_TEST_IDS

    # Update rubric text
    if "evaluation_rubric" in result:
        result["evaluation_rubric"] = update_rubric(result["evaluation_rubric"])

    return result


def transform_fuzzy_prediction(pred: dict) -> dict:
    """Apply v3→v4 transformations to a fuzzy prediction.

    Replaces expected_post_clarification_outputs (v3 category)
    with expected_post_clarification_verifiability (v4 tier).
    Idempotent.
    """
    result = dict(pred)

    # Extract category from v3 field and map to v4 tier
    post_clar = result.pop("expected_post_clarification_outputs", None)
    if post_clar is not None:
        # Extract category — could be nested in various ways
        category = None
        if isinstance(post_clar, dict):
            cat_data = post_clar.get("categorizer", {})
            if isinstance(cat_data, dict):
                category = cat_data.get("expected_category")
            elif isinstance(cat_data, str):
                category = cat_data
        elif isinstance(post_clar, str):
            category = post_clar

        if category and category in CATEGORY_TO_TIER:
            result["expected_post_clarification_verifiability"] = (
                CATEGORY_TO_TIER[category]
            )
        else:
            logger.warning(
                f"Could not extract category from "
                f"expected_post_clarification_outputs for {result.get('id')}"
            )
            # Default to moderate if we can't determine
            result.setdefault(
                "expected_post_clarification_verifiability", "moderate"
            )
    else:
        # Already transformed or field never existed — ensure v4 field exists
        result.setdefault(
            "expected_post_clarification_verifiability", "moderate"
        )

    # Update rubric text if present
    if "evaluation_rubric" in result:
        result["evaluation_rubric"] = update_rubric(result["evaluation_rubric"])

    return result


def reshape() -> None:
    """Main reshape pipeline. Reads v3, writes v4 to same file."""
    dataset_path = "eval/golden_dataset.json"

    logger.info(f"Loading {dataset_path}")
    with open(dataset_path) as f:
        data = json.load(f)

    # Track transformation counts
    fields_removed = 0
    fields_added = 0
    rubrics_updated = 0
    smoke_count = 0

    # Transform base predictions
    transformed_base = []
    for bp in data.get("base_predictions", []):
        had_v3_fields = (
            "expected_per_agent_outputs" in bp
            or "tool_manifest_config" in bp
        )
        old_rubric = bp.get("evaluation_rubric", "")

        result = transform_base_prediction(bp)
        transformed_base.append(result)

        if had_v3_fields:
            fields_removed += 1
        if "expected_verifiability_score_range" in result:
            fields_added += 1
        if result.get("evaluation_rubric", "") != old_rubric:
            rubrics_updated += 1
        if result.get("smoke_test"):
            smoke_count += 1

    # Transform fuzzy predictions
    transformed_fuzzy = []
    for fp in data.get("fuzzy_predictions", []):
        result = transform_fuzzy_prediction(fp)
        transformed_fuzzy.append(result)

    # Update top-level fields
    data["schema_version"] = "4.0"
    data["dataset_version"] = "4.0"
    data["base_predictions"] = transformed_base
    data["fuzzy_predictions"] = transformed_fuzzy
    data["metadata"] = {
        "expected_base_count": len(transformed_base),
        "expected_fuzzy_count": len(transformed_fuzzy),
        "expected_smoke_test_count": smoke_count,
    }

    # Write back
    logger.info(f"Writing {dataset_path}")
    with open(dataset_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Print summary
    print(f"\n=== Reshape Summary ===")
    print(f"Base predictions: {len(transformed_base)}")
    print(f"Fuzzy predictions: {len(transformed_fuzzy)}")
    print(f"V3 fields removed from: {fields_removed} predictions")
    print(f"V4 fields added to: {fields_added} predictions")
    print(f"Rubrics updated: {rubrics_updated}")
    print(f"Smoke test cases flagged: {smoke_count}")
    print(f"Schema version: 4.0")
    print(f"Dataset version: 4.0")


if __name__ == "__main__":
    reshape()
