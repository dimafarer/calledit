#!/usr/bin/env python3
"""Validate the v4 golden dataset structural correctness.

Checks all required fields, v3 dead field absence, score range validity,
smoke test constraints, fuzzy prediction referential integrity, and
metadata counts. Exits 0 if all pass, 1 if any fail.

Runnable independently of reshape_v4.py.
"""

import json
import sys
from datetime import datetime

DATASET_PATH = "eval/golden_dataset.json"

# Required fields on every base prediction
BASE_REQUIRED_FIELDS = [
    "id", "prediction_text", "difficulty", "ground_truth",
    "dimension_tags", "evaluation_rubric", "is_boundary_case",
    "boundary_description", "expected_verifiability_score_range",
    "expected_verification_outcome", "smoke_test",
]

# Required ground_truth sub-fields
GROUND_TRUTH_REQUIRED = [
    "verifiability_reasoning", "date_derivation", "verification_sources",
    "objectivity_assessment", "verification_criteria", "verification_steps",
    "verification_timing", "expected_verification_criteria",
    "expected_verification_method",
]

# V3 dead fields that must not exist
V3_DEAD_FIELDS = ["expected_per_agent_outputs", "tool_manifest_config"]

# V3 terms that must not appear in rubrics
V3_RUBRIC_TERMS = ["auto_verifiable", "automatable", "human_only"]

# Valid verification outcomes
VALID_OUTCOMES = {"confirmed", "refuted", "inconclusive", None}

# Required fuzzy prediction fields
FUZZY_REQUIRED_FIELDS = [
    "id", "fuzzy_text", "base_prediction_id", "fuzziness_level",
    "simulated_clarifications", "expected_clarification_topics",
    "evaluation_rubric", "expected_post_clarification_verifiability",
]

VALID_TIERS = {"high", "moderate", "low"}

ALL_DOMAINS = {
    "weather", "finance", "sports", "nature", "tech", "personal",
    "entertainment", "work", "food", "health", "travel", "social",
}


def check_base_prediction(pred: dict) -> list[str]:
    """Validate one base prediction. Returns list of violation strings."""
    violations = []
    pred_id = pred.get("id", "<unknown>")

    # Required fields
    for field in BASE_REQUIRED_FIELDS:
        if field not in pred:
            violations.append(f"{pred_id}: missing required field '{field}'")

    # Ground truth sub-fields
    gt = pred.get("ground_truth", {})
    if not isinstance(gt, dict):
        violations.append(f"{pred_id}: 'ground_truth' is not a dict")
    else:
        for field in GROUND_TRUTH_REQUIRED:
            if field not in gt:
                violations.append(
                    f"{pred_id}: missing ground_truth field '{field}'"
                )

    # V3 dead fields must not exist
    for field in V3_DEAD_FIELDS:
        if field in pred:
            violations.append(f"{pred_id}: contains v3 dead field '{field}'")

    # Score range validation
    score_range = pred.get("expected_verifiability_score_range")
    if score_range is not None:
        if not isinstance(score_range, list) or len(score_range) != 2:
            violations.append(
                f"{pred_id}: expected_verifiability_score_range must be "
                f"a 2-element list, got {type(score_range).__name__} "
                f"len={len(score_range) if isinstance(score_range, list) else 'N/A'}"
            )
        else:
            low, high = score_range
            if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
                violations.append(
                    f"{pred_id}: score range values must be numeric, "
                    f"got [{type(low).__name__}, {type(high).__name__}]"
                )
            elif not (0.0 <= low <= 1.0 and 0.0 <= high <= 1.0):
                violations.append(
                    f"{pred_id}: score range values must be in [0.0, 1.0], "
                    f"got [{low}, {high}]"
                )
            elif low > high:
                violations.append(
                    f"{pred_id}: score range low ({low}) > high ({high})"
                )

    # Verification outcome validation
    outcome = pred.get("expected_verification_outcome")
    if outcome is not None and outcome not in VALID_OUTCOMES:
        violations.append(
            f"{pred_id}: expected_verification_outcome must be one of "
            f"{VALID_OUTCOMES}, got '{outcome}'"
        )

    # Rubric v3 term check
    rubric = pred.get("evaluation_rubric", "")
    for term in V3_RUBRIC_TERMS:
        if term in rubric:
            violations.append(
                f"{pred_id}: evaluation_rubric contains v3 term '{term}'"
            )

    return violations


def check_fuzzy_prediction(
    pred: dict, valid_base_ids: set[str]
) -> list[str]:
    """Validate one fuzzy prediction. Returns list of violation strings."""
    violations = []
    pred_id = pred.get("id", "<unknown>")

    # Required fields
    for field in FUZZY_REQUIRED_FIELDS:
        if field not in pred:
            violations.append(f"{pred_id}: missing required field '{field}'")

    # Referential integrity
    base_id = pred.get("base_prediction_id")
    if base_id and base_id not in valid_base_ids:
        violations.append(
            f"{pred_id}: base_prediction_id '{base_id}' not found "
            f"in base predictions"
        )

    # V3 dead field
    if "expected_post_clarification_outputs" in pred:
        violations.append(
            f"{pred_id}: contains v3 field "
            f"'expected_post_clarification_outputs'"
        )

    # Tier validation
    tier = pred.get("expected_post_clarification_verifiability")
    if tier is not None and tier not in VALID_TIERS:
        violations.append(
            f"{pred_id}: expected_post_clarification_verifiability must be "
            f"one of {VALID_TIERS}, got '{tier}'"
        )

    return violations


def check_metadata(data: dict) -> list[str]:
    """Validate metadata counts and versions."""
    violations = []
    meta = data.get("metadata", {})
    base_preds = data.get("base_predictions", [])
    fuzzy_preds = data.get("fuzzy_predictions", [])

    # Version checks
    if data.get("schema_version") != "4.0":
        violations.append(
            f"schema_version must be '4.0', "
            f"got '{data.get('schema_version')}'"
        )
    if data.get("dataset_version") != "4.0":
        violations.append(
            f"dataset_version must be '4.0', "
            f"got '{data.get('dataset_version')}'"
        )

    # Count checks
    actual_base = len(base_preds)
    expected_base = meta.get("expected_base_count")
    if expected_base != actual_base:
        violations.append(
            f"metadata.expected_base_count ({expected_base}) != "
            f"actual base count ({actual_base})"
        )

    actual_fuzzy = len(fuzzy_preds)
    expected_fuzzy = meta.get("expected_fuzzy_count")
    if expected_fuzzy != actual_fuzzy:
        violations.append(
            f"metadata.expected_fuzzy_count ({expected_fuzzy}) != "
            f"actual fuzzy count ({actual_fuzzy})"
        )

    actual_smoke = sum(
        1 for bp in base_preds if bp.get("smoke_test") is True
    )
    expected_smoke = meta.get("expected_smoke_test_count")
    if expected_smoke != actual_smoke:
        violations.append(
            f"metadata.expected_smoke_test_count ({expected_smoke}) != "
            f"actual smoke test count ({actual_smoke})"
        )

    return violations


def check_smoke_test_constraints(preds: list[dict]) -> list[str]:
    """Validate smoke test subset constraints per Decision 125."""
    violations = []
    smoke = [p for p in preds if p.get("smoke_test") is True]
    count = len(smoke)

    # Count range
    if not (10 <= count <= 14):
        violations.append(
            f"Smoke test count ({count}) not in range [10, 14]"
        )

    # Difficulty distribution
    easy = sum(1 for p in smoke if p.get("difficulty") == "easy")
    medium = sum(1 for p in smoke if p.get("difficulty") == "medium")
    hard = sum(1 for p in smoke if p.get("difficulty") == "hard")
    if easy != 4:
        violations.append(f"Smoke test easy count ({easy}) != 4")
    if medium != 5:
        violations.append(f"Smoke test medium count ({medium}) != 5")
    if hard != 3:
        violations.append(f"Smoke test hard count ({hard}) != 3")

    # Domain coverage
    domains = {
        p.get("dimension_tags", {}).get("domain") for p in smoke
    }
    missing = ALL_DOMAINS - domains
    if missing:
        violations.append(
            f"Smoke test missing domains: {sorted(missing)}"
        )

    # Boundary case
    has_boundary = any(p.get("is_boundary_case") for p in smoke)
    if not has_boundary:
        violations.append("Smoke test has no boundary case")

    # Immediate verification readiness
    has_immediate = any(
        p.get("verification_readiness") == "immediate" for p in smoke
    )
    if not has_immediate:
        violations.append(
            "Smoke test has no case with verification_readiness='immediate'"
        )

    # Subjective + objective
    objectivities = {
        p.get("ground_truth", {}).get("objectivity_assessment")
        for p in smoke
    }
    if "subjective" not in objectivities:
        violations.append("Smoke test has no subjective prediction")
    if "objective" not in objectivities:
        violations.append("Smoke test has no objective prediction")

    return violations


def validate(path: str = DATASET_PATH) -> list[str]:
    """Main validation. Returns list of all violations."""
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return [f"File not found: {path}"]

    all_violations = []
    checks = {}

    # Base predictions
    base_preds = data.get("base_predictions", [])
    valid_base_ids = {bp.get("id") for bp in base_preds}
    base_violations = []
    for bp in base_preds:
        base_violations.extend(check_base_prediction(bp))
    checks["Base predictions"] = base_violations
    all_violations.extend(base_violations)

    # Fuzzy predictions
    fuzzy_preds = data.get("fuzzy_predictions", [])
    fuzzy_violations = []
    for fp in fuzzy_preds:
        fuzzy_violations.extend(
            check_fuzzy_prediction(fp, valid_base_ids)
        )
    checks["Fuzzy predictions"] = fuzzy_violations
    all_violations.extend(fuzzy_violations)

    # Metadata
    meta_violations = check_metadata(data)
    checks["Metadata & versions"] = meta_violations
    all_violations.extend(meta_violations)

    # Smoke test constraints
    smoke_violations = check_smoke_test_constraints(base_preds)
    checks["Smoke test constraints"] = smoke_violations
    all_violations.extend(smoke_violations)

    # Print summary
    print("\n=== Validation Summary ===")
    for check_name, violations in checks.items():
        status = "PASS" if not violations else "FAIL"
        print(f"  {check_name}: {status}")
        for v in violations:
            print(f"    - {v}")

    total = len(all_violations)
    if total == 0:
        print(f"\nResult: ALL CHECKS PASSED")
    else:
        print(f"\nResult: {total} violation(s) found")

    return all_violations


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DATASET_PATH
    violations = validate(path)
    sys.exit(1 if violations else 0)
