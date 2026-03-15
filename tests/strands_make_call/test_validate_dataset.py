"""
Tests for eval/validate_dataset.py — Golden Dataset V2 validation script.

Tests structural, referential, uniqueness, coherence, and coverage checks.
"""

import json
import os
import tempfile
import pytest

# Add eval/ to path so we can import validate_dataset
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "eval"))

from validate_dataset import validate_dataset


def _make_ground_truth(**overrides):
    gt = {
        "verifiability_reasoning": "Test reasoning",
        "date_derivation": "Explicit date in text",
        "verification_sources": ["test_source"],
        "objectivity_assessment": "objective",
        "verification_criteria": ["criterion_1"],
        "verification_steps": ["step_1"],
    }
    gt.update(overrides)
    return gt


def _make_base(id="base-001", **overrides):
    bp = {
        "id": id,
        "prediction_text": f"Test prediction {id}",
        "difficulty": "medium",
        "ground_truth": _make_ground_truth(),
        "dimension_tags": {
            "domain": "finance",
            "stakes": "moderate",
            "time_horizon": "days",
            "persona": "investor",
        },
        "tool_manifest_config": {"tools": []},
        "expected_per_agent_outputs": {
            "categorizer": {"expected_category": "automatable"}
        },
    }
    bp.update(overrides)
    return bp


def _make_fuzzy(id="fuzzy-001", base_id="base-001", **overrides):
    fp = {
        "id": id,
        "fuzzy_text": f"Fuzzy text {id}",
        "base_prediction_id": base_id,
        "fuzziness_level": 1,
        "simulated_clarifications": ["clarification"],
        "expected_clarification_topics": ["topic"],
        "expected_post_clarification_outputs": {
            "categorizer": {"expected_category": "automatable"}
        },
    }
    fp.update(overrides)
    return fp


def _make_dataset(**overrides):
    d = {
        "schema_version": "2.0",
        "dataset_version": "2.0",
        "base_predictions": [_make_base()],
        "fuzzy_predictions": [_make_fuzzy()],
    }
    d.update(overrides)
    return d


def _validate(data: dict) -> list:
    """Write data to temp file and validate."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        return validate_dataset(path)
    finally:
        os.unlink(path)


class TestStructural:
    def test_valid_minimal_dataset(self):
        errors = _validate(_make_dataset())
        structural = [e for e in errors if e.startswith("STRUCTURAL")]
        assert len(structural) == 0

    def test_wrong_schema_version(self):
        errors = _validate(_make_dataset(schema_version="1.0"))
        assert any("schema_version" in e for e in errors)

    def test_missing_dataset_version(self):
        d = _make_dataset()
        del d["dataset_version"]
        errors = _validate(d)
        assert any("dataset_version" in e for e in errors)

    def test_missing_ground_truth(self):
        bp = _make_base()
        del bp["ground_truth"]
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("ground_truth" in e for e in errors)

    def test_invalid_objectivity(self):
        bp = _make_base()
        bp["ground_truth"]["objectivity_assessment"] = "invalid"
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("objectivity_assessment" in e for e in errors)

    def test_missing_dimension_tags(self):
        bp = _make_base()
        del bp["dimension_tags"]
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("dimension_tags" in e for e in errors)

    def test_invalid_stakes(self):
        bp = _make_base()
        bp["dimension_tags"]["stakes"] = "invalid"
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("stakes" in e for e in errors)

    def test_invalid_expected_category(self):
        bp = _make_base()
        bp["expected_per_agent_outputs"]["categorizer"]["expected_category"] = "bad"
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("expected_category" in e for e in errors)

    def test_invalid_fuzziness_level(self):
        fp = _make_fuzzy(fuzziness_level=5)
        errors = _validate(_make_dataset(fuzzy_predictions=[fp]))
        assert any("fuzziness_level" in e for e in errors)

    def test_boundary_case_missing_description(self):
        bp = _make_base(is_boundary_case=True)
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("boundary_description" in e for e in errors)


class TestReferential:
    def test_dangling_fuzzy_reference(self):
        fp = _make_fuzzy(base_id="nonexistent")
        errors = _validate(_make_dataset(fuzzy_predictions=[fp]))
        assert any("REFERENTIAL" in e and "nonexistent" in e for e in errors)


class TestUniqueness:
    def test_duplicate_base_ids(self):
        bp1 = _make_base(id="base-001")
        bp2 = _make_base(id="base-001")
        bp2["prediction_text"] = "Different text"
        errors = _validate(_make_dataset(
            base_predictions=[bp1, bp2], fuzzy_predictions=[]
        ))
        assert any("UNIQUENESS" in e and "base-001" in e for e in errors)

    def test_duplicate_fuzzy_ids(self):
        fp1 = _make_fuzzy(id="fuzzy-001")
        fp2 = _make_fuzzy(id="fuzzy-001")
        fp2["fuzzy_text"] = "Different text"
        errors = _validate(_make_dataset(fuzzy_predictions=[fp1, fp2]))
        assert any("UNIQUENESS" in e and "fuzzy-001" in e for e in errors)

    def test_base_fuzzy_id_collision(self):
        bp = _make_base(id="shared-id")
        fp = _make_fuzzy(id="shared-id", base_id="shared-id")
        errors = _validate(_make_dataset(
            base_predictions=[bp], fuzzy_predictions=[fp]
        ))
        assert any("collision" in e.lower() for e in errors)


class TestIntegrity:
    def test_base_count_mismatch(self):
        d = _make_dataset()
        d["metadata"] = {"expected_base_count": 5}
        errors = _validate(d)
        assert any("INTEGRITY" in e and "expected_base_count" in e for e in errors)

    def test_fuzzy_count_mismatch(self):
        d = _make_dataset()
        d["metadata"] = {"expected_fuzzy_count": 10}
        errors = _validate(d)
        assert any("INTEGRITY" in e and "expected_fuzzy_count" in e for e in errors)

    def test_correct_counts_no_error(self):
        d = _make_dataset()
        d["metadata"] = {"expected_base_count": 1, "expected_fuzzy_count": 1}
        errors = _validate(d)
        integrity_errors = [e for e in errors if e.startswith("INTEGRITY")]
        assert len(integrity_errors) == 0


class TestCoherence:
    def test_empty_verification_sources(self):
        bp = _make_base()
        bp["ground_truth"]["verification_sources"] = []
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("verification_sources" in e for e in errors)

    def test_empty_verification_steps(self):
        bp = _make_base()
        bp["ground_truth"]["verification_steps"] = []
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("verification_steps" in e for e in errors)

    def test_missing_verifiability_reasoning(self):
        bp = _make_base()
        bp["ground_truth"]["verifiability_reasoning"] = ""
        errors = _validate(_make_dataset(base_predictions=[bp], fuzzy_predictions=[]))
        assert any("verifiability_reasoning" in e for e in errors)


class TestCollectsAllErrors:
    def test_multiple_errors_collected(self):
        """Validation should collect ALL errors, not stop at first."""
        d = _make_dataset(schema_version="1.0")
        d["dataset_version"] = ""
        bp = _make_base()
        bp["ground_truth"]["objectivity_assessment"] = "bad"
        d["base_predictions"] = [bp]
        d["fuzzy_predictions"] = []
        errors = _validate(d)
        assert len(errors) >= 2  # At least schema + objectivity errors
