"""Tests for task function — Property 7 + error path unit tests."""

import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.task_function import compute_wait_seconds, TaskFunctionFactory


# --- Property 7: Verification wait computation ---


# Feature: strands-evals-migration, Property 7: Verification wait computation
@given(
    offset_seconds=st.integers(min_value=-86400, max_value=86400),
    mode=st.sampled_from(["immediate", "at_date", "before_date", "recurring"]),
)
@settings(max_examples=100)
def test_wait_computation_property(offset_seconds, mode):
    """Wait = max(0, (vdate - now) + 30) capped at 300s. 0 for immediate/recurring."""
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    vdate = now + timedelta(seconds=offset_seconds)
    vdate_str = vdate.isoformat()

    bundle = {"parsed_claim": {"verification_date": vdate_str}}
    wait = compute_wait_seconds(bundle, mode, now=now)

    if mode in ("immediate", "recurring"):
        assert wait == 0.0
    elif vdate <= now:
        assert wait == 0.0
    else:
        expected = min((vdate - now).total_seconds() + 30, 300.0)
        assert abs(wait - expected) < 0.01


# Feature: strands-evals-migration, Property 7: Cap at 300s
@given(offset_hours=st.integers(min_value=1, max_value=720))
@settings(max_examples=50)
def test_wait_capped_at_300(offset_hours):
    """Wait is always capped at 300 seconds."""
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    vdate = now + timedelta(hours=offset_hours)
    bundle = {"parsed_claim": {"verification_date": vdate.isoformat()}}
    wait = compute_wait_seconds(bundle, "at_date", now=now)
    assert wait <= 300.0


# Feature: strands-evals-migration, Property 7: Past dates return 0
@given(offset_seconds=st.integers(min_value=1, max_value=86400))
@settings(max_examples=50)
def test_past_dates_return_zero(offset_seconds):
    """Past verification dates return 0 wait."""
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    vdate = now - timedelta(seconds=offset_seconds)
    bundle = {"parsed_claim": {"verification_date": vdate.isoformat()}}
    wait = compute_wait_seconds(bundle, "at_date", now=now)
    assert wait == 0.0


class TestWaitEdgeCases:

    def test_no_verification_date(self):
        assert compute_wait_seconds({}, "at_date") == 0.0

    def test_invalid_date_string(self):
        bundle = {"parsed_claim": {"verification_date": "not-a-date"}}
        assert compute_wait_seconds(bundle, "at_date") == 0.0

    def test_z_suffix_date(self):
        now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
        vdate = now + timedelta(seconds=60)
        bundle = {"parsed_claim": {"verification_date": vdate.strftime("%Y-%m-%dT%H:%M:%SZ")}}
        wait = compute_wait_seconds(bundle, "at_date", now=now)
        assert wait == pytest.approx(90.0, abs=1.0)  # 60 + 30 buffer


# --- Unit tests for task function error paths (Task 10.3) ---


class TestTaskFunctionErrors:

    def _make_case(self, name="test-001"):
        from strands_evals import Case
        return Case(
            name=name, input="Test prediction",
            expected_output="confirmed",
            metadata={"verification_mode": "immediate"},
        )

    def test_creation_failure_skips_verification(self):
        """When creation fails, verification is skipped."""
        creation = MagicMock()
        creation.invoke.side_effect = RuntimeError("Creation failed")
        verification = MagicMock()

        tf = TaskFunctionFactory(creation, verification, "eval-table")
        raw = tf(self._make_case())
        result = raw["output"]

        assert result["creation_bundle"] is None
        assert result["creation_error"] == "Creation failed"
        assert result["verification_result"] is None
        verification.invoke.assert_not_called()

    def test_verification_failure_preserves_bundle(self):
        """When verification fails, creation bundle is preserved."""
        creation = MagicMock()
        creation.invoke.return_value = {
            "prediction_id": "pred-123",
            "parsed_claim": {},
            "verification_plan": {},
            "plan_review": {},
        }
        verification = MagicMock()
        verification.invoke.side_effect = RuntimeError("Verification failed")

        tf = TaskFunctionFactory(creation, verification, "eval-table")
        raw = tf(self._make_case())
        result = raw["output"]

        assert result["creation_bundle"] is not None
        assert result["prediction_id"] == "pred-123"
        assert result["verification_result"] is None
        assert result["verification_error"] == "Verification failed"

    def test_no_prediction_id_skips_verification(self):
        """When creation returns no prediction_id, verification is skipped."""
        creation = MagicMock()
        creation.invoke.return_value = {"parsed_claim": {}}
        verification = MagicMock()

        tf = TaskFunctionFactory(creation, verification, "eval-table")
        raw = tf(self._make_case())
        result = raw["output"]

        assert result["prediction_id"] is None
        assert result["verification_error"] == "No prediction_id from creation"
        verification.invoke.assert_not_called()

    def test_successful_pipeline(self):
        """Full pipeline returns both bundle and verification result."""
        creation = MagicMock()
        creation.invoke.return_value = {
            "prediction_id": "pred-456",
            "parsed_claim": {"verification_date": "2026-01-01T00:00:00Z"},
            "verification_plan": {},
            "plan_review": {"verifiability_score": 0.85},
        }
        verification = MagicMock()
        verification.invoke.return_value = {
            "verdict": "confirmed",
            "confidence": 0.9,
            "evidence": [{"source": "test"}],
            "reasoning": "Found it",
        }

        tf = TaskFunctionFactory(creation, verification, "eval-table")
        raw = tf(self._make_case())
        result = raw["output"]

        assert result["creation_bundle"] is not None
        assert result["verification_result"]["verdict"] == "confirmed"
        assert result["creation_error"] is None
        assert result["verification_error"] is None
        assert result["prediction_id"] == "pred-456"
