#!/usr/bin/env python3
"""
Golden Dataset v5.0 Integrity Validation Script
Task 3: Checkpoint - Validate dataset integrity

Verifies:
1. JSON is valid and parseable
2. All 18 personal/subjective cases preserved unchanged
3. base-004 and base-009 present and unchanged
4. base-046 and base-052 NOT present
5. base-056 through base-060 present with correct fields
6. Metadata counts match actual data
7. schema_version and dataset_version are "5.0"
"""

import json
import sys
import os

def load_dataset(path):
    """Load and parse the golden dataset JSON."""
    with open(path, "r") as f:
        return json.load(f)

def get_prediction_by_id(predictions, pred_id):
    """Find a prediction by its id field."""
    for p in predictions:
        if p["id"] == pred_id:
            return p
    return None

def validate_json_parseable(path):
    """1. Ensure the golden dataset JSON is valid and parseable."""
    print("=" * 60)
    print("CHECK 1: JSON is valid and parseable")
    try:
        data = load_dataset(path)
        assert isinstance(data, dict), "Root should be a dict"
        assert "base_predictions" in data, "Missing base_predictions"
        assert "metadata" in data, "Missing metadata"
        assert "schema_version" in data, "Missing schema_version"
        assert "dataset_version" in data, "Missing dataset_version"
        print("  PASS: JSON is valid and contains required top-level keys")
        return data
    except json.JSONDecodeError as e:
        print(f"  FAIL: JSON parse error: {e}")
        sys.exit(1)

def validate_personal_subjective_cases(predictions):
    """2. Verify all 18 personal/subjective cases are preserved unchanged."""
    print("=" * 60)
    print("CHECK 2: All 18 personal/subjective cases preserved")
    expected_ids = [
        "base-027", "base-028", "base-029", "base-030", "base-031",
        "base-032", "base-033", "base-034", "base-035", "base-036",
        "base-037", "base-038", "base-039", "base-041", "base-042",
        "base-043", "base-044", "base-045"
    ]
    all_ids = {p["id"] for p in predictions}
    missing = [pid for pid in expected_ids if pid not in all_ids]
    if missing:
        print(f"  FAIL: Missing personal/subjective cases: {missing}")
        return False
    else:
        print(f"  PASS: All {len(expected_ids)} personal/subjective cases present")
        return True

def validate_base_004_and_009(predictions):
    """3. Verify base-004 and base-009 are present and unchanged."""
    print("=" * 60)
    print("CHECK 3: base-004 and base-009 present and unchanged")
    ok = True

    b004 = get_prediction_by_id(predictions, "base-004")
    if b004 is None:
        print("  FAIL: base-004 not found")
        ok = False
    else:
        if "S&P 500" not in b004["prediction_text"]:
            print(f"  FAIL: base-004 prediction_text unexpected: {b004['prediction_text'][:80]}")
            ok = False
        if b004.get("smoke_test") is not True:
            print(f"  FAIL: base-004 smoke_test should be true, got {b004.get('smoke_test')}")
            ok = False
        if b004.get("verification_mode") != "at_date":
            print(f"  FAIL: base-004 verification_mode should be 'at_date', got {b004.get('verification_mode')}")
            ok = False

    b009 = get_prediction_by_id(predictions, "base-009")
    if b009 is None:
        print("  FAIL: base-009 not found")
        ok = False
    else:
        if "national debt" not in b009["prediction_text"].lower():
            print(f"  FAIL: base-009 prediction_text unexpected: {b009['prediction_text'][:80]}")
            ok = False
        if b009.get("verification_mode") != "immediate":
            print(f"  FAIL: base-009 verification_mode should be 'immediate', got {b009.get('verification_mode')}")
            ok = False

    if ok:
        print("  PASS: base-004 and base-009 present with expected fields")
    return ok

def validate_removed_cases(predictions):
    """4. Verify base-046 and base-052 are NOT present."""
    print("=" * 60)
    print("CHECK 4: base-046 and base-052 NOT present (removed)")
    all_ids = {p["id"] for p in predictions}
    ok = True
    if "base-046" in all_ids:
        print("  FAIL: base-046 should have been removed but is still present")
        ok = False
    if "base-052" in all_ids:
        print("  FAIL: base-052 should have been removed but is still present")
        ok = False
    if ok:
        print("  PASS: base-046 and base-052 correctly removed")
    return ok

def validate_new_predictions(predictions):
    """5. Verify base-056 through base-060 are present with correct fields."""
    print("=" * 60)
    print("CHECK 5: base-056 through base-060 present with correct fields")
    new_ids = ["base-056", "base-057", "base-058", "base-059", "base-060"]
    ok = True

    for pid in new_ids:
        pred = get_prediction_by_id(predictions, pid)
        if pred is None:
            print(f"  FAIL: {pid} not found")
            ok = False
            continue

        # Check verification_mode is immediate
        if pred.get("verification_mode") != "immediate":
            print(f"  FAIL: {pid} verification_mode should be 'immediate', got {pred.get('verification_mode')}")
            ok = False

        # Check expected_verification_outcome is non-null
        outcome = pred.get("expected_verification_outcome")
        if outcome is None:
            print(f"  FAIL: {pid} expected_verification_outcome should be non-null, got None")
            ok = False
        elif outcome not in ("confirmed", "refuted"):
            print(f"  FAIL: {pid} expected_verification_outcome should be 'confirmed' or 'refuted', got '{outcome}'")
            ok = False

        # Check ground_truth has required fields
        gt = pred.get("ground_truth", {})
        for field in ["verification_sources", "verification_criteria", "verification_steps", "expected_verification_method"]:
            val = gt.get(field)
            if not val:
                print(f"  FAIL: {pid} ground_truth.{field} is missing or empty")
                ok = False

        # Check has prediction_text
        if not pred.get("prediction_text"):
            print(f"  FAIL: {pid} missing prediction_text")
            ok = False

    if ok:
        print(f"  PASS: All {len(new_ids)} new predictions present with correct fields")
    return ok

def validate_metadata_counts(data):
    """6. Verify metadata counts match actual data."""
    print("=" * 60)
    print("CHECK 6: Metadata counts match actual data")
    predictions = data["base_predictions"]
    metadata = data["metadata"]
    ok = True

    # Expected base count
    actual_base = len(predictions)
    expected_base = metadata.get("expected_base_count")
    if actual_base != expected_base:
        print(f"  FAIL: expected_base_count={expected_base} but actual={actual_base}")
        ok = False
    if expected_base != 58:
        print(f"  FAIL: expected_base_count should be 58, got {expected_base}")
        ok = False

    # Expected smoke test count
    actual_smoke = sum(1 for p in predictions if p.get("smoke_test") is True)
    expected_smoke = metadata.get("expected_smoke_test_count")
    if actual_smoke != expected_smoke:
        print(f"  FAIL: expected_smoke_test_count={expected_smoke} but actual={actual_smoke}")
        ok = False
    if expected_smoke != 13:
        print(f"  FAIL: expected_smoke_test_count should be 13, got {expected_smoke}")
        ok = False

    # Expected mode counts
    mode_counts = {}
    for p in predictions:
        mode = p.get("verification_mode", "unknown")
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    expected_modes = metadata.get("expected_mode_counts", {})
    expected_mode_values = {"immediate": 15, "at_date": 30, "before_date": 11, "recurring": 2}

    for mode, expected_count in expected_mode_values.items():
        actual_count = mode_counts.get(mode, 0)
        metadata_count = expected_modes.get(mode, 0)

        if metadata_count != expected_count:
            print(f"  FAIL: metadata expected_mode_counts.{mode}={metadata_count} should be {expected_count}")
            ok = False
        if actual_count != expected_count:
            print(f"  FAIL: actual {mode} count={actual_count} should be {expected_count}")
            ok = False

    # Check total mode counts add up
    total_modes = sum(mode_counts.values())
    if total_modes != actual_base:
        print(f"  FAIL: total mode counts ({total_modes}) != base count ({actual_base})")
        ok = False

    if ok:
        print(f"  PASS: All metadata counts match actual data")
        print(f"    base_count: {actual_base}")
        print(f"    smoke_test_count: {actual_smoke}")
        print(f"    mode_counts: {dict(sorted(mode_counts.items()))}")
    return ok

def validate_versions(data):
    """7. Verify schema_version and dataset_version are '5.0'."""
    print("=" * 60)
    print("CHECK 7: schema_version and dataset_version are '5.0'")
    ok = True
    sv = data.get("schema_version")
    dv = data.get("dataset_version")
    if sv != "5.0":
        print(f"  FAIL: schema_version should be '5.0', got '{sv}'")
        ok = False
    if dv != "5.0":
        print(f"  FAIL: dataset_version should be '5.0', got '{dv}'")
        ok = False
    if ok:
        print("  PASS: Both versions are '5.0'")
    return ok

def main():
    dataset_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    print(f"Validating: {dataset_path}")
    print()

    # Check 1: Parse JSON
    data = validate_json_parseable(dataset_path)
    predictions = data["base_predictions"]

    # Run all checks
    results = []
    results.append(("Personal/subjective cases", validate_personal_subjective_cases(predictions)))
    results.append(("base-004 and base-009", validate_base_004_and_009(predictions)))
    results.append(("Removed cases", validate_removed_cases(predictions)))
    results.append(("New predictions", validate_new_predictions(predictions)))
    results.append(("Metadata counts", validate_metadata_counts(data)))
    results.append(("Versions", validate_versions(data)))

    # Summary
    print("=" * 60)
    print("SUMMARY")
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("ALL CHECKS PASSED - Dataset integrity verified!")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED - See details above")
        sys.exit(1)

if __name__ == "__main__":
    main()
