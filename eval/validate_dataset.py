#!/usr/bin/env python3
"""
Golden Dataset V2 Validation Script

Validates all structural constraints, referential integrity, ground truth
coherence, coverage requirements, and count integrity. Collects ALL errors
rather than failing on the first one.

USAGE:
    python eval/validate_dataset.py                          # Default path
    python eval/validate_dataset.py eval/golden_dataset.json # Custom path

EXIT CODES:
    0 = valid (no errors)
    1 = errors found
"""

import json
import sys
from typing import List

# Valid enum values (mirrored from golden_dataset.py)
VALID_CATEGORIES = {"auto_verifiable", "automatable", "human_only"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_OBJECTIVITY = {"objective", "subjective", "mixed"}
VALID_STAKES = {"life-changing", "significant", "moderate", "trivial"}
VALID_TIME_HORIZONS = {"minutes-to-hours", "days", "weeks-to-months", "months-to-years"}
VALID_FUZZINESS_LEVELS = {0, 1, 2, 3}


def validate_dataset(path: str = "eval/golden_dataset.json") -> List[str]:
    """Validate all structural constraints and return list of errors.

    Checks:
    1. STRUCTURAL: required fields, types, valid enum values
    2. REFERENTIAL: fuzzy base_prediction_id references resolve
    3. UNIQUENESS: no duplicate IDs, no base/fuzzy ID collisions
    4. COHERENCE: ground truth metadata consistency
    5. COVERAGE: category/domain/stakes/horizon distribution
    6. INTEGRITY: count matches metadata
    7. VERSIONING: dataset_version present

    Returns:
        List of error strings. Empty list = valid.
    """
    errors: List[str] = []

    # Load JSON
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return [f"File not found: {path}"]
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Schema version
    version = data.get("schema_version")
    if version != "2.0":
        errors.append(f"STRUCTURAL: schema_version must be '2.0', got '{version}'")

    # Dataset version
    dv = data.get("dataset_version")
    if not dv or not isinstance(dv, str):
        errors.append("STRUCTURAL: missing or empty 'dataset_version'")

    base_preds = data.get("base_predictions", [])
    fuzzy_preds = data.get("fuzzy_predictions", [])

    # --- Validate base predictions ---
    base_ids = []
    categories = []
    domains = set()
    stakes_set = set()
    horizons_set = set()
    personas = set()
    boundary_count = 0

    for idx, bp in enumerate(base_preds):
        prefix = f"base[{idx}]"
        bp_id = bp.get("id", f"<missing-{idx}>")

        # ID
        if not bp.get("id") or not isinstance(bp.get("id"), str):
            errors.append(f"STRUCTURAL: {prefix} missing or invalid 'id'")
        base_ids.append(bp.get("id"))

        # prediction_text
        if not bp.get("prediction_text") or not isinstance(bp.get("prediction_text"), str):
            errors.append(f"STRUCTURAL: {prefix} '{bp_id}' missing 'prediction_text'")

        # difficulty
        diff = bp.get("difficulty")
        if diff not in VALID_DIFFICULTIES:
            errors.append(f"STRUCTURAL: {prefix} '{bp_id}' invalid difficulty '{diff}'")

        # ground_truth
        gt = bp.get("ground_truth")
        if not gt or not isinstance(gt, dict):
            errors.append(f"STRUCTURAL: {prefix} '{bp_id}' missing 'ground_truth'")
        else:
            errors.extend(_validate_ground_truth(gt, bp_id))

        # dimension_tags
        dt = bp.get("dimension_tags")
        if not dt or not isinstance(dt, dict):
            errors.append(f"STRUCTURAL: {prefix} '{bp_id}' missing 'dimension_tags'")
        else:
            dt_errors, domain, stakes, horizon, persona = _validate_dimension_tags(dt, bp_id)
            errors.extend(dt_errors)
            if domain:
                domains.add(domain)
            if stakes:
                stakes_set.add(stakes)
            if horizon:
                horizons_set.add(horizon)
            if persona:
                personas.add(persona)


        # expected_category
        expected = bp.get("expected_per_agent_outputs", {})
        cat_data = expected.get("categorizer", {})
        cat = cat_data.get("expected_category")
        if cat not in VALID_CATEGORIES:
            errors.append(
                f"STRUCTURAL: {prefix} '{bp_id}' invalid expected_category '{cat}'"
            )
        else:
            categories.append(cat)

        # boundary case
        if bp.get("is_boundary_case"):
            boundary_count += 1
            bd = bp.get("boundary_description")
            if not bd or not isinstance(bd, str):
                errors.append(
                    f"STRUCTURAL: {prefix} '{bp_id}' boundary_description required "
                    f"when is_boundary_case=True"
                )

    # --- Validate fuzzy predictions ---
    fuzzy_ids = []
    base_id_set = set(base_ids)
    fuzziness_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    category_unchanged_count = 0
    base_fuzzy_levels = {}  # base_id -> set of fuzziness_levels

    for idx, fp in enumerate(fuzzy_preds):
        prefix = f"fuzzy[{idx}]"
        fp_id = fp.get("id", f"<missing-{idx}>")

        # ID
        if not fp.get("id") or not isinstance(fp.get("id"), str):
            errors.append(f"STRUCTURAL: {prefix} missing or invalid 'id'")
        fuzzy_ids.append(fp.get("id"))

        # fuzzy_text
        if not fp.get("fuzzy_text") or not isinstance(fp.get("fuzzy_text"), str):
            errors.append(f"STRUCTURAL: {prefix} '{fp_id}' missing 'fuzzy_text'")

        # base_prediction_id
        base_ref = fp.get("base_prediction_id")
        if not base_ref or base_ref not in base_id_set:
            errors.append(
                f"REFERENTIAL: {prefix} '{fp_id}' base_prediction_id '{base_ref}' "
                f"not found in base predictions"
            )

        # fuzziness_level
        fl = fp.get("fuzziness_level")
        if fl not in VALID_FUZZINESS_LEVELS:
            errors.append(
                f"STRUCTURAL: {prefix} '{fp_id}' invalid fuzziness_level '{fl}'"
            )
        else:
            fuzziness_counts[fl] += 1
            # Track levels per base for distinct check
            if base_ref:
                base_fuzzy_levels.setdefault(base_ref, set()).add(fl)

        # simulated_clarifications
        sc = fp.get("simulated_clarifications")
        if not sc or not isinstance(sc, list):
            errors.append(
                f"STRUCTURAL: {prefix} '{fp_id}' missing 'simulated_clarifications'"
            )

        # expected_clarification_topics
        ect = fp.get("expected_clarification_topics")
        if not ect or not isinstance(ect, list):
            errors.append(
                f"STRUCTURAL: {prefix} '{fp_id}' missing 'expected_clarification_topics'"
            )

        # expected_category in post-clarification
        expected = fp.get("expected_post_clarification_outputs", {})
        cat_data = expected.get("categorizer", {})
        post_cat = cat_data.get("expected_category")
        if post_cat not in VALID_CATEGORIES:
            errors.append(
                f"STRUCTURAL: {prefix} '{fp_id}' invalid post-clarification "
                f"expected_category '{post_cat}'"
            )

        # Check if clarification doesn't change category
        if base_ref and base_ref in base_id_set:
            base_bp = next((b for b in base_preds if b.get("id") == base_ref), None)
            if base_bp:
                base_cat = (base_bp.get("expected_per_agent_outputs", {})
                           .get("categorizer", {}).get("expected_category"))
                if base_cat and post_cat and base_cat == post_cat:
                    category_unchanged_count += 1

    # --- UNIQUENESS checks ---
    seen_base = set()
    for bid in base_ids:
        if bid and bid in seen_base:
            errors.append(f"UNIQUENESS: duplicate base prediction ID '{bid}'")
        if bid:
            seen_base.add(bid)

    seen_fuzzy = set()
    for fid in fuzzy_ids:
        if fid and fid in seen_fuzzy:
            errors.append(f"UNIQUENESS: duplicate fuzzy prediction ID '{fid}'")
        if fid:
            seen_fuzzy.add(fid)

    collisions = seen_base & seen_fuzzy
    if collisions:
        errors.append(f"UNIQUENESS: ID collision between base and fuzzy: {collisions}")

    # --- COVERAGE checks ---
    cat_counts = {}
    for c in categories:
        cat_counts[c] = cat_counts.get(c, 0) + 1

    for cat in VALID_CATEGORIES:
        count = cat_counts.get(cat, 0)
        if count < 12:
            errors.append(
                f"COVERAGE: need at least 12 '{cat}' base predictions, got {count}"
            )

    if len(domains) < 8:
        errors.append(f"COVERAGE: need at least 8 domains, got {len(domains)}: {domains}")

    for s in VALID_STAKES:
        stakes_count = sum(
            1 for bp in base_preds
            if bp.get("dimension_tags", {}).get("stakes") == s
        )
        if stakes_count < 3:
            errors.append(f"COVERAGE: need at least 3 '{s}' stakes, got {stakes_count}")

    for h in VALID_TIME_HORIZONS:
        horizon_count = sum(
            1 for bp in base_preds
            if bp.get("dimension_tags", {}).get("time_horizon") == h
        )
        if horizon_count < 3:
            errors.append(f"COVERAGE: need at least 3 '{h}' time horizon, got {horizon_count}")

    if len(personas) < 12:
        errors.append(f"COVERAGE: need at least 12 personas, got {len(personas)}")

    if boundary_count < 5:
        errors.append(f"COVERAGE: need at least 5 boundary cases, got {boundary_count}")

    # Fuzzy coverage
    if fuzziness_counts[0] < 3:
        errors.append(
            f"COVERAGE: need at least 3 fuzziness level 0, got {fuzziness_counts[0]}"
        )
    for level in [1, 2, 3]:
        if fuzziness_counts[level] < 5:
            errors.append(
                f"COVERAGE: need at least 5 fuzziness level {level}, "
                f"got {fuzziness_counts[level]}"
            )

    if category_unchanged_count < 5:
        errors.append(
            f"COVERAGE: need at least 5 fuzzy predictions where clarification "
            f"doesn't change category, got {category_unchanged_count}"
        )

    # --- COUNT INTEGRITY ---
    meta = data.get("metadata")
    if meta and isinstance(meta, dict):
        eb = meta.get("expected_base_count")
        if eb is not None and len(base_preds) != eb:
            errors.append(
                f"INTEGRITY: expected_base_count={eb}, actual={len(base_preds)}"
            )
        ef = meta.get("expected_fuzzy_count")
        if ef is not None and len(fuzzy_preds) != ef:
            errors.append(
                f"INTEGRITY: expected_fuzzy_count={ef}, actual={len(fuzzy_preds)}"
            )

    return errors


def _validate_ground_truth(gt: dict, bp_id: str) -> List[str]:
    """Check ground truth metadata coherence."""
    errors = []

    for field_name in ["verifiability_reasoning", "date_derivation"]:
        val = gt.get(field_name)
        if not val or not isinstance(val, str):
            errors.append(
                f"COHERENCE: '{bp_id}' ground_truth.{field_name} must be non-empty string"
            )

    for field_name in ["verification_sources", "verification_criteria", "verification_steps"]:
        val = gt.get(field_name)
        if not val or not isinstance(val, list) or not all(isinstance(s, str) for s in val):
            errors.append(
                f"COHERENCE: '{bp_id}' ground_truth.{field_name} must be non-empty list of strings"
            )

    oa = gt.get("objectivity_assessment")
    if oa not in VALID_OBJECTIVITY:
        errors.append(
            f"COHERENCE: '{bp_id}' ground_truth.objectivity_assessment "
            f"must be one of {VALID_OBJECTIVITY}, got '{oa}'"
        )

    return errors


def _validate_dimension_tags(dt: dict, bp_id: str):
    """Check dimension tags validity. Returns (errors, domain, stakes, horizon, persona)."""
    errors = []
    domain = dt.get("domain")
    if not domain or not isinstance(domain, str):
        errors.append(f"STRUCTURAL: '{bp_id}' dimension_tags.domain must be non-empty string")
        domain = None

    stakes = dt.get("stakes")
    if stakes not in VALID_STAKES:
        errors.append(
            f"STRUCTURAL: '{bp_id}' dimension_tags.stakes must be one of {VALID_STAKES}"
        )
        stakes = None

    horizon = dt.get("time_horizon")
    if horizon not in VALID_TIME_HORIZONS:
        errors.append(
            f"STRUCTURAL: '{bp_id}' dimension_tags.time_horizon must be one of {VALID_TIME_HORIZONS}"
        )
        horizon = None

    persona = dt.get("persona")
    if not persona or not isinstance(persona, str):
        errors.append(f"STRUCTURAL: '{bp_id}' dimension_tags.persona must be non-empty string")
        persona = None

    return errors, domain, stakes, horizon, persona


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "eval/golden_dataset.json"
    errors = validate_dataset(path)

    if errors:
        print(f"VALIDATION FAILED: {len(errors)} error(s) found", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(f"\n{len(errors)} errors in {path}")
        sys.exit(1)
    else:
        print(f"VALID: {path} passes all checks")
        sys.exit(0)


if __name__ == "__main__":
    main()
