"""Tests for report format — Property 9 + report store adaptation."""

import sys
import os
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.run_eval import build_report


class _FakeArgs:
    """Minimal args object for build_report."""
    def __init__(self, **kwargs):
        self.dataset = kwargs.get("dataset", "eval/golden_dataset.json")
        self.dynamic_dataset = kwargs.get("dynamic_dataset", None)
        self.tier = kwargs.get("tier", "smoke")
        self.description = kwargs.get("description", "test run")


# --- Property 9: Report format completeness and aggregate correctness ---


# Feature: strands-evals-migration, Property 9: Report format completeness
@given(
    case_count=st.integers(min_value=1, max_value=10),
    duration=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
)
@settings(max_examples=100)
def test_report_format_completeness(case_count, duration):
    """Report contains all required run_metadata keys."""
    case_results = [{"creation_bundle": {}, "verification_result": {}} for _ in range(case_count)]
    evaluator_results = {"creation": {"schema_validity": 1.0}, "verification": {"verdict_validity": 1.0}}

    args = _FakeArgs(tier="full", description="property test")
    report = build_report(args, case_results, evaluator_results, {}, duration)

    # Required run_metadata keys
    meta = report["run_metadata"]
    required_keys = {
        "description", "run_tier", "timestamp", "duration_seconds",
        "case_count", "dataset_sources", "git_commit", "prompt_versions",
    }
    assert required_keys.issubset(set(meta.keys()))
    assert meta["case_count"] == case_count
    assert meta["run_tier"] == "full"
    assert meta["description"] == "property test"

    # Top-level report keys
    assert "creation_scores" in report
    assert "verification_scores" in report
    assert "calibration_scores" in report
    assert "case_results" in report
    assert len(report["case_results"]) == case_count


# Feature: strands-evals-migration, Property 9: Dataset sources
@given(has_dynamic=st.booleans())
@settings(max_examples=50)
def test_report_dataset_sources(has_dynamic):
    """Dataset sources reflect static + optional dynamic."""
    dynamic = "eval/dynamic_golden_dataset.json" if has_dynamic else None
    args = _FakeArgs(dynamic_dataset=dynamic)
    report = build_report(args, [], {"creation": {}, "verification": {}}, {}, 0.0)

    sources = report["run_metadata"]["dataset_sources"]
    assert "eval/golden_dataset.json" in sources
    if has_dynamic:
        assert len(sources) == 2
    else:
        assert len(sources) == 1


class TestReportEdgeCases:

    def test_empty_case_results(self):
        args = _FakeArgs()
        report = build_report(args, [], {"creation": {}, "verification": {}}, {}, 0.0)
        assert report["run_metadata"]["case_count"] == 0
        assert report["case_results"] == []

    def test_calibration_scores_included(self):
        cal = {"calibration_accuracy": 0.95, "mean_absolute_error": 0.1}
        args = _FakeArgs(tier="full")
        report = build_report(args, [], {"creation": {}, "verification": {}}, cal, 100.0)
        assert report["calibration_scores"]["calibration_accuracy"] == 0.95
