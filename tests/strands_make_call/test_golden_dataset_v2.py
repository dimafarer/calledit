"""
Unit tests for golden_dataset.py v2 schema, loader, serialization, and filtering.

Tests tasks 1.1-1.4: dataclasses, load_golden_dataset, dataset_to_dict, filter_test_cases.
"""

import json
import os
import tempfile
import pytest

import sys
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "backend", "calledit-backend", "handlers", "strands_make_call",
    ),
)

from golden_dataset import (
    SUPPORTED_SCHEMA_VERSION,
    VALID_CATEGORIES,
    VALID_OBJECTIVITY,
    VALID_STAKES,
    VALID_TIME_HORIZONS,
    VALID_FUZZINESS_LEVELS,
    GroundTruthMetadata,
    DimensionTags,
    DatasetMetadata,
    BasePrediction,
    FuzzyPrediction,
    GoldenDataset,
    load_golden_dataset,
    dataset_to_dict,
    filter_test_cases,
)


# --- Helpers ---

def _make_ground_truth_dict(**overrides):
    """Build a valid ground truth metadata dict with optional overrides."""
    gt = {
        "verifiability_reasoning": "Test reasoning",
        "date_derivation": "Explicit date in text",
        "verification_sources": ["test_api"],
        "objectivity_assessment": "objective",
        "verification_criteria": ["price > threshold"],
        "verification_steps": ["query API", "compare"],
        "verification_timing": "Immediate: data is available now via API",
    }
    gt.update(overrides)
    return gt


def _make_dimension_tags_dict(**overrides):
    """Build a valid dimension tags dict with optional overrides."""
    dt = {
        "domain": "finance",
        "stakes": "moderate",
        "time_horizon": "days",
        "persona": "investor",
    }
    dt.update(overrides)
    return dt


def _make_base_prediction_dict(id="base-001", **overrides):
    """Build a valid v2 base prediction dict."""
    bp = {
        "id": id,
        "prediction_text": "Bitcoin will exceed $150k by Dec 2026",
        "difficulty": "medium",
        "ground_truth": _make_ground_truth_dict(),
        "dimension_tags": _make_dimension_tags_dict(),
        "tool_manifest_config": {"tools": []},
        "expected_per_agent_outputs": {
            "categorizer": {"expected_category": "automatable"}
        },
        "evaluation_rubric": "Test rubric",
        "is_boundary_case": False,
        "boundary_description": None,
    }
    bp.update(overrides)
    return bp


def _make_fuzzy_prediction_dict(id="fuzzy-001", base_id="base-001", **overrides):
    """Build a valid v2 fuzzy prediction dict."""
    fp = {
        "id": id,
        "fuzzy_text": "The crypto thing will moon soon",
        "base_prediction_id": base_id,
        "fuzziness_level": 2,
        "simulated_clarifications": ["I mean Bitcoin will exceed $150k by Dec 2026"],
        "expected_clarification_topics": ["cryptocurrency", "price_target", "timeframe"],
        "expected_post_clarification_outputs": {
            "categorizer": {"expected_category": "automatable"}
        },
        "evaluation_rubric": "Test fuzzy rubric",
    }
    fp.update(overrides)
    return fp


def _make_dataset_dict(**overrides):
    """Build a valid v2 dataset dict."""
    ds = {
        "schema_version": "2.0",
        "dataset_version": "2.0",
        "base_predictions": [_make_base_prediction_dict()],
        "fuzzy_predictions": [_make_fuzzy_prediction_dict()],
    }
    ds.update(overrides)
    return ds


def _write_and_load(data: dict) -> GoldenDataset:
    """Write dataset dict to temp file and load it."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        path = f.name
    try:
        return load_golden_dataset(path)
    finally:
        os.unlink(path)


# --- Task 1.1: Dataclass and constant tests ---


class TestConstants:
    def test_schema_version(self):
        assert SUPPORTED_SCHEMA_VERSION == "2.0"

    def test_valid_objectivity(self):
        assert VALID_OBJECTIVITY == {"objective", "subjective", "mixed"}

    def test_valid_stakes(self):
        assert VALID_STAKES == {"life-changing", "significant", "moderate", "trivial"}

    def test_valid_time_horizons(self):
        assert VALID_TIME_HORIZONS == {
            "minutes-to-hours", "days", "weeks-to-months", "months-to-years"
        }

    def test_valid_fuzziness_levels(self):
        assert VALID_FUZZINESS_LEVELS == {0, 1, 2, 3}

    def test_valid_categories(self):
        assert VALID_CATEGORIES == {"auto_verifiable", "automatable", "human_only"}


class TestDataclasses:
    def test_ground_truth_metadata(self):
        gt = GroundTruthMetadata(
            verifiability_reasoning="reason",
            date_derivation="explicit",
            verification_sources=["api"],
            objectivity_assessment="objective",
            verification_criteria=["crit"],
            verification_steps=["step"],
            verification_timing="Immediate: data available now",
        )
        assert gt.verifiability_reasoning == "reason"
        assert gt.objectivity_assessment == "objective"
        assert gt.verification_timing == "Immediate: data available now"

    def test_dimension_tags(self):
        dt = DimensionTags(
            domain="finance", stakes="moderate",
            time_horizon="days", persona="investor",
        )
        assert dt.domain == "finance"
        assert dt.stakes == "moderate"

    def test_dataset_metadata_defaults(self):
        dm = DatasetMetadata()
        assert dm.expected_base_count is None
        assert dm.expected_fuzzy_count is None

    def test_base_prediction_v2_fields(self):
        gt = GroundTruthMetadata("r", "d", ["s"], "objective", ["c"], ["st"], "Immediate")
        dt = DimensionTags("finance", "moderate", "days", "investor")
        bp = BasePrediction(
            id="base-001", prediction_text="test", difficulty="medium",
            ground_truth=gt, dimension_tags=dt,
        )
        assert bp.is_boundary_case is False
        assert bp.boundary_description is None
        assert bp.expected_per_agent_outputs == {}

    def test_fuzzy_prediction_v2_fields(self):
        fp = FuzzyPrediction(
            id="fuzzy-001", fuzzy_text="test",
            base_prediction_id="base-001", fuzziness_level=3,
        )
        assert fp.fuzziness_level == 3

    def test_golden_dataset_v2_fields(self):
        ds = GoldenDataset(dataset_version="2.0")
        assert ds.schema_version == "2.0"
        assert ds.dataset_version == "2.0"
        assert ds.metadata is None


# --- Task 1.2: Loader tests ---


class TestLoadGoldenDataset:
    def test_load_valid_v2_dataset(self):
        ds = _write_and_load(_make_dataset_dict())
        assert ds.schema_version == "2.0"
        assert ds.dataset_version == "2.0"
        assert len(ds.base_predictions) == 1
        assert len(ds.fuzzy_predictions) == 1

    def test_reject_v1_schema(self):
        data = _make_dataset_dict(schema_version="1.0")
        with pytest.raises(ValueError, match="Unsupported schema version '1.0'"):
            _write_and_load(data)

    def test_reject_unknown_schema(self):
        data = _make_dataset_dict(schema_version="3.0")
        with pytest.raises(ValueError, match="3.0"):
            _write_and_load(data)

    def test_reject_missing_schema_version(self):
        data = _make_dataset_dict()
        del data["schema_version"]
        with pytest.raises(ValueError, match="Unsupported schema version"):
            _write_and_load(data)

    def test_reject_missing_dataset_version(self):
        data = _make_dataset_dict()
        del data["dataset_version"]
        with pytest.raises(ValueError, match="dataset_version"):
            _write_and_load(data)

    def test_reject_empty_dataset_version(self):
        data = _make_dataset_dict(dataset_version="")
        with pytest.raises(ValueError, match="dataset_version"):
            _write_and_load(data)

    def test_reject_missing_ground_truth(self):
        bp = _make_base_prediction_dict()
        del bp["ground_truth"]
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="ground_truth"):
            _write_and_load(data)

    def test_reject_invalid_objectivity(self):
        bp = _make_base_prediction_dict()
        bp["ground_truth"]["objectivity_assessment"] = "unknown"
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="objectivity_assessment"):
            _write_and_load(data)

    def test_reject_empty_verification_sources(self):
        bp = _make_base_prediction_dict()
        bp["ground_truth"]["verification_sources"] = []
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="verification_sources"):
            _write_and_load(data)

    def test_reject_missing_dimension_tags(self):
        bp = _make_base_prediction_dict()
        del bp["dimension_tags"]
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="dimension_tags"):
            _write_and_load(data)

    def test_reject_invalid_stakes(self):
        bp = _make_base_prediction_dict()
        bp["dimension_tags"]["stakes"] = "extreme"
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="stakes"):
            _write_and_load(data)

    def test_reject_invalid_time_horizon(self):
        bp = _make_base_prediction_dict()
        bp["dimension_tags"]["time_horizon"] = "centuries"
        data = _make_dataset_dict(base_predictions=[bp])
        with pytest.raises(ValueError, match="time_horizon"):
            _write_and_load(data)

    def test_reject_missing_expected_category(self):
        bp = _make_base_prediction_dict()
        bp["expected_per_agent_outputs"] = {"categorizer": {}}
        data = _make_dataset_dict(base_predictions=[bp], fuzzy_predictions=[])
        with pytest.raises(ValueError, match="expected_category"):
            _write_and_load(data)

    def test_reject_invalid_expected_category(self):
        bp = _make_base_prediction_dict()
        bp["expected_per_agent_outputs"]["categorizer"]["expected_category"] = "invalid"
        data = _make_dataset_dict(base_predictions=[bp], fuzzy_predictions=[])
        with pytest.raises(ValueError, match="expected_category"):
            _write_and_load(data)

    def test_reject_invalid_fuzziness_level(self):
        fp = _make_fuzzy_prediction_dict(fuzziness_level=5)
        data = _make_dataset_dict(fuzzy_predictions=[fp])
        with pytest.raises(ValueError, match="fuzziness_level"):
            _write_and_load(data)

    def test_reject_dangling_fuzzy_reference(self):
        fp = _make_fuzzy_prediction_dict(base_id="base-999")
        data = _make_dataset_dict(fuzzy_predictions=[fp])
        with pytest.raises(ValueError, match="base-999"):
            _write_and_load(data)

    def test_reject_fuzzy_missing_expected_category(self):
        fp = _make_fuzzy_prediction_dict()
        fp["expected_post_clarification_outputs"] = {"categorizer": {}}
        data = _make_dataset_dict(fuzzy_predictions=[fp])
        with pytest.raises(ValueError, match="expected_category"):
            _write_and_load(data)

    def test_count_integrity_base_mismatch(self):
        data = _make_dataset_dict(
            metadata={"expected_base_count": 5, "expected_fuzzy_count": 1}
        )
        with pytest.raises(ValueError, match="Count mismatch.*base"):
            _write_and_load(data)

    def test_count_integrity_fuzzy_mismatch(self):
        data = _make_dataset_dict(
            metadata={"expected_base_count": 1, "expected_fuzzy_count": 5}
        )
        with pytest.raises(ValueError, match="Count mismatch.*fuzzy"):
            _write_and_load(data)

    def test_count_integrity_passes_when_correct(self):
        data = _make_dataset_dict(
            metadata={"expected_base_count": 1, "expected_fuzzy_count": 1}
        )
        ds = _write_and_load(data)
        assert ds.metadata.expected_base_count == 1
        assert ds.metadata.expected_fuzzy_count == 1

    def test_duplicate_base_ids_rejected(self):
        bp1 = _make_base_prediction_dict(id="base-001")
        bp2 = _make_base_prediction_dict(id="base-001")
        bp2["prediction_text"] = "Different text"
        data = _make_dataset_dict(base_predictions=[bp1, bp2], fuzzy_predictions=[])
        with pytest.raises(ValueError, match="Duplicate base prediction IDs"):
            _write_and_load(data)

    def test_boundary_case_requires_description(self):
        bp = _make_base_prediction_dict(is_boundary_case=True, boundary_description=None)
        data = _make_dataset_dict(base_predictions=[bp], fuzzy_predictions=[])
        with pytest.raises(ValueError, match="boundary_description"):
            _write_and_load(data)

    def test_boundary_case_with_description_passes(self):
        bp = _make_base_prediction_dict(
            is_boundary_case=True,
            boundary_description="Tool availability changes category",
        )
        data = _make_dataset_dict(base_predictions=[bp], fuzzy_predictions=[])
        ds = _write_and_load(data)
        assert ds.base_predictions[0].is_boundary_case is True
        assert ds.base_predictions[0].boundary_description == "Tool availability changes category"

    def test_all_fuzziness_levels_accepted(self):
        """Levels 0, 1, 2, 3 should all load successfully."""
        for level in [0, 1, 2, 3]:
            fp = _make_fuzzy_prediction_dict(
                id=f"fuzzy-{level:03d}", fuzziness_level=level
            )
            data = _make_dataset_dict(fuzzy_predictions=[fp])
            ds = _write_and_load(data)
            assert ds.fuzzy_predictions[0].fuzziness_level == level


# --- Task 1.3: Serialization tests ---


class TestDatasetToDict:
    def test_round_trip_basic(self):
        data = _make_dataset_dict()
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        assert serialized["schema_version"] == "2.0"
        assert serialized["dataset_version"] == "2.0"
        assert len(serialized["base_predictions"]) == 1
        assert len(serialized["fuzzy_predictions"]) == 1

    def test_round_trip_preserves_ground_truth(self):
        data = _make_dataset_dict()
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        gt = serialized["base_predictions"][0]["ground_truth"]
        assert gt["verifiability_reasoning"] == "Test reasoning"
        assert gt["objectivity_assessment"] == "objective"
        assert gt["verification_sources"] == ["test_api"]

    def test_round_trip_preserves_dimension_tags(self):
        data = _make_dataset_dict()
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        dt = serialized["base_predictions"][0]["dimension_tags"]
        assert dt["domain"] == "finance"
        assert dt["stakes"] == "moderate"
        assert dt["time_horizon"] == "days"
        assert dt["persona"] == "investor"

    def test_round_trip_preserves_fuzziness_level(self):
        data = _make_dataset_dict()
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        assert serialized["fuzzy_predictions"][0]["fuzziness_level"] == 2

    def test_round_trip_preserves_boundary_case(self):
        bp = _make_base_prediction_dict(
            is_boundary_case=True,
            boundary_description="Boundary test",
        )
        data = _make_dataset_dict(base_predictions=[bp], fuzzy_predictions=[])
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        assert serialized["base_predictions"][0]["is_boundary_case"] is True
        assert serialized["base_predictions"][0]["boundary_description"] == "Boundary test"

    def test_round_trip_metadata(self):
        data = _make_dataset_dict(
            metadata={"expected_base_count": 1, "expected_fuzzy_count": 1}
        )
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        assert serialized["metadata"]["expected_base_count"] == 1
        assert serialized["metadata"]["expected_fuzzy_count"] == 1

    def test_round_trip_no_metadata(self):
        data = _make_dataset_dict()
        ds = _write_and_load(data)
        serialized = dataset_to_dict(ds)
        assert "metadata" not in serialized

    def test_full_round_trip_reload(self):
        """Serialize → JSON → reload should produce equivalent dataset."""
        data = _make_dataset_dict(
            metadata={"expected_base_count": 1, "expected_fuzzy_count": 1}
        )
        ds1 = _write_and_load(data)
        serialized = dataset_to_dict(ds1)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(serialized, f)
            path = f.name
        try:
            ds2 = load_golden_dataset(path)
        finally:
            os.unlink(path)

        assert ds2.schema_version == ds1.schema_version
        assert ds2.dataset_version == ds1.dataset_version
        assert len(ds2.base_predictions) == len(ds1.base_predictions)
        assert len(ds2.fuzzy_predictions) == len(ds1.fuzzy_predictions)
        assert ds2.base_predictions[0].id == ds1.base_predictions[0].id
        assert ds2.fuzzy_predictions[0].fuzziness_level == ds1.fuzzy_predictions[0].fuzziness_level


# --- Task 1.4: Filter tests ---


class TestFilterTestCases:
    def _make_loaded_dataset(self):
        """Create a dataset with multiple predictions for filtering."""
        bp1 = _make_base_prediction_dict(id="base-001")
        bp1["expected_per_agent_outputs"]["categorizer"]["expected_category"] = "automatable"
        bp1["difficulty"] = "easy"

        bp2 = _make_base_prediction_dict(id="base-002")
        bp2["prediction_text"] = "It will rain tomorrow"
        bp2["expected_per_agent_outputs"]["categorizer"]["expected_category"] = "auto_verifiable"
        bp2["difficulty"] = "hard"
        bp2["ground_truth"]["objectivity_assessment"] = "objective"
        bp2["dimension_tags"]["domain"] = "weather"

        fp1 = _make_fuzzy_prediction_dict(id="fuzzy-001", base_id="base-001")
        fp1["fuzziness_level"] = 1
        fp1["expected_post_clarification_outputs"]["categorizer"]["expected_category"] = "automatable"

        fp2 = _make_fuzzy_prediction_dict(id="fuzzy-002", base_id="base-002")
        fp2["fuzzy_text"] = "Will it rain?"
        fp2["fuzziness_level"] = 3
        fp2["expected_post_clarification_outputs"]["categorizer"]["expected_category"] = "auto_verifiable"

        data = _make_dataset_dict(
            base_predictions=[bp1, bp2],
            fuzzy_predictions=[fp1, fp2],
        )
        return _write_and_load(data)

    def test_no_filters_returns_all(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds)
        assert len(results) == 4

    def test_filter_by_layer_base(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, layer="base")
        assert len(results) == 2
        assert all(isinstance(r, BasePrediction) for r in results)

    def test_filter_by_layer_fuzzy(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, layer="fuzzy")
        assert len(results) == 2
        assert all(isinstance(r, FuzzyPrediction) for r in results)

    def test_filter_by_category(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, category="automatable")
        assert len(results) == 2  # base-001 + fuzzy-001

    def test_filter_by_name(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, name="base-002")
        assert len(results) == 1
        assert results[0].id == "base-002"

    def test_filter_by_difficulty(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, difficulty="hard")
        # base-002 (hard) + fuzzy-002 (base is base-002 which is hard)
        assert len(results) == 2

    def test_filter_by_fuzziness_level(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, fuzziness_level=3)
        assert len(results) == 1
        assert results[0].id == "fuzzy-002"

    def test_filter_fuzziness_level_excludes_base(self):
        """When filtering by fuzziness_level, base predictions are excluded."""
        ds = self._make_loaded_dataset()
        results = filter_test_cases(ds, fuzziness_level=1)
        assert len(results) == 1
        assert isinstance(results[0], FuzzyPrediction)

    def test_filter_combined(self):
        ds = self._make_loaded_dataset()
        results = filter_test_cases(
            ds, layer="fuzzy", category="auto_verifiable"
        )
        assert len(results) == 1
        assert results[0].id == "fuzzy-002"
