"""Tests for continuous mode CLI flags and runner orchestration."""

import sys
from unittest.mock import patch

import pytest


def _parse_with_args(args: list[str]):
    """Helper to call parse_args with specific CLI args."""
    with patch("sys.argv", ["run_eval.py"] + args):
        from eval.run_eval import parse_args
        return parse_args()


def test_continuous_implies_skip_cleanup():
    """--continuous sets skip_cleanup=True."""
    args = _parse_with_args(["--continuous"])
    assert args.continuous is True
    assert args.skip_cleanup is True


def test_continuous_default_interval():
    """--continuous without --interval defaults to 15."""
    args = _parse_with_args(["--continuous"])
    assert args.interval == 15


def test_continuous_custom_interval():
    """--continuous --interval 30 sets interval to 30."""
    args = _parse_with_args(["--continuous", "--interval", "30"])
    assert args.interval == 30


def test_continuous_max_passes():
    """--continuous --max-passes 5 sets max_passes to 5."""
    args = _parse_with_args(["--continuous", "--max-passes", "5"])
    assert args.max_passes == 5


def test_continuous_once():
    """--continuous --once sets once=True."""
    args = _parse_with_args(["--continuous", "--once"])
    assert args.once is True


def test_continuous_verify_only():
    """--continuous --verify-only skips creation."""
    args = _parse_with_args(["--continuous", "--verify-only"])
    assert args.verify_only is True
    assert args.continuous is True


def test_continuous_resume():
    """--continuous --resume loads state."""
    args = _parse_with_args(["--continuous", "--resume"])
    assert args.resume is True
    assert args.continuous is True


def test_once_without_continuous_fails():
    """--once without --continuous raises error."""
    with pytest.raises(SystemExit):
        _parse_with_args(["--once"])


def test_interval_without_continuous_fails():
    """--interval without --continuous raises error."""
    with pytest.raises(SystemExit):
        _parse_with_args(["--interval", "30"])


def test_max_passes_without_continuous_fails():
    """--max-passes without --continuous raises error."""
    with pytest.raises(SystemExit):
        _parse_with_args(["--max-passes", "5"])


def test_reverify_resolved_without_continuous_fails():
    """--reverify-resolved without --continuous raises error."""
    with pytest.raises(SystemExit):
        _parse_with_args(["--reverify-resolved"])


def test_non_continuous_mode_unchanged():
    """Normal (non-continuous) mode still works."""
    args = _parse_with_args(["--tier", "smoke", "--dry-run"])
    assert args.continuous is False
    assert args.tier == "smoke"
    assert args.dry_run is True



# --- Property 7: Creation phase resilience ---

from unittest.mock import MagicMock
from hypothesis import given, settings, strategies as st
from eval.continuous_state import CaseState, ContinuousState
from strands_evals import Case


def _make_mock_runner(cases, fail_indices):
    """Create a ContinuousEvalRunner with a mock creation backend that fails at specified indices."""
    from eval.run_eval import ContinuousEvalRunner

    args = MagicMock()
    args.verify_only = False
    args.once = False
    args.continuous = True
    args.skip_cleanup = True
    args.resume = False
    args.reverify_resolved = False
    args.interval = 15
    args.max_passes = 1
    args.tier = "smoke"
    args.description = None
    args.dataset = "eval/golden_dataset.json"
    args.dynamic_dataset = None

    creation_backend = MagicMock()
    call_count = {"n": 0}

    def mock_invoke(**kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx in fail_indices:
            raise Exception(f"Simulated failure at index {idx}")
        return {
            "prediction_id": f"pid-{idx}",
            "parsed_claim": {"verification_date": "2026-05-01T00:00:00Z"},
            "plan_review": {"verifiability_score": 0.8, "score_tier": "high"},
        }

    creation_backend.invoke = mock_invoke

    state = ContinuousState.fresh()
    runner = ContinuousEvalRunner(
        args=args,
        cases=cases,
        creation_backend=creation_backend,
        verification_backend=MagicMock(),
        evaluators=[],
        state=state,
    )
    return runner


# Feature: continuous-verification-eval, Property 7: Creation phase resilience
@given(
    n_cases=st.integers(min_value=1, max_value=10),
    fail_fraction=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=50, deadline=None)
def test_p7_creation_resilience(n_cases, fail_fraction):
    """For any set of cases with random failures, all cases get state entries."""
    cases = [
        Case(input=f"Prediction {i}", expected_output=None, name=f"case-{i}")
        for i in range(n_cases)
    ]
    n_fail = int(n_cases * fail_fraction)
    fail_indices = set(range(n_fail))

    runner = _make_mock_runner(cases, fail_indices)
    runner._run_creation_phase()

    # All cases should have entries
    assert len(runner.state.cases) == n_cases

    for i in range(n_cases):
        case_id = f"case-{i}"
        cs = runner.state.cases[case_id]
        if i in fail_indices:
            assert cs.status == "error"
            assert cs.creation_error is not None
            assert cs.prediction_id is None
        else:
            assert cs.status == "pending"
            assert cs.prediction_id is not None
            assert cs.creation_error is None
