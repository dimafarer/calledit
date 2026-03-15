"""
Tests for score_history.py v2 updates — dataset_version tracking and
cross-version comparison warnings.
"""

import json
import os
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..",
    "backend", "calledit-backend", "handlers", "strands_make_call"
))

from score_history import append_score, compare_latest


@pytest.fixture
def history_file(tmp_path):
    path = str(tmp_path / "score_history.json")
    return path


def _make_report(dataset_version="2.0", pass_rate=0.8, timestamp="2026-03-15T10:00:00Z"):
    return {
        "timestamp": timestamp,
        "dataset_version": dataset_version,
        "prompt_version_manifest": {"parser": "1", "categorizer": "1"},
        "per_agent_aggregates": {"parser": {"json_validity_avg": 0.9}},
        "per_category_accuracy": {"auto_verifiable": 0.85},
        "overall_pass_rate": pass_rate,
        "total_tests": 10,
        "passed": 8,
    }


class TestDatasetVersionTracking:
    def test_append_includes_dataset_version(self, history_file):
        append_score(_make_report(dataset_version="2.0"), path=history_file)
        with open(history_file) as f:
            data = json.load(f)
        entry = data["evaluations"][0]
        assert entry["dataset_version"] == "2.0"

    def test_append_missing_dataset_version_defaults_empty(self, history_file):
        report = _make_report()
        del report["dataset_version"]
        append_score(report, path=history_file)
        with open(history_file) as f:
            data = json.load(f)
        assert data["evaluations"][0]["dataset_version"] == ""


class TestCrossVersionComparison:
    def test_same_version_no_mismatch(self, history_file):
        append_score(_make_report("2.0", 0.7, "2026-03-15T09:00:00Z"), path=history_file)
        append_score(_make_report("2.0", 0.8, "2026-03-15T10:00:00Z"), path=history_file)
        result = compare_latest(path=history_file)
        assert result["dataset_version_mismatch"] is False
        assert result["dataset_version_warning"] is None

    def test_different_version_flags_mismatch(self, history_file):
        append_score(_make_report("1.0", 0.7, "2026-03-15T09:00:00Z"), path=history_file)
        append_score(_make_report("2.0", 0.8, "2026-03-15T10:00:00Z"), path=history_file)
        result = compare_latest(path=history_file)
        assert result["dataset_version_mismatch"] is True
        assert "1.0" in result["dataset_version_warning"]
        assert "2.0" in result["dataset_version_warning"]

    def test_mismatch_warning_contains_both_versions(self, history_file):
        append_score(_make_report("1.5", 0.6, "2026-03-15T09:00:00Z"), path=history_file)
        append_score(_make_report("2.1", 0.9, "2026-03-15T10:00:00Z"), path=history_file)
        result = compare_latest(path=history_file)
        assert result["dataset_version_mismatch"] is True
        assert "1.5" in result["dataset_version_warning"]
        assert "2.1" in result["dataset_version_warning"]
