"""Tests for eval/continuous_metrics.py — property-based (P4-P6) and unit tests."""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, strategies as st

from eval.continuous_state import CaseState, ContinuousState, VerdictEntry
from eval.continuous_metrics import (
    compute_resolution_rate,
    compute_resolution_speed_by_tier,
    compute_stale_inconclusive_rate,
    compute_continuous_calibration,
)


# --- Helpers ---

def _make_case(
    case_id: str,
    status: str = "pending",
    verdict: str | None = None,
    verdict_history: list | None = None,
    verification_date: str | None = None,
    resolved_on_pass: int | None = None,
    verifiability_score: float | None = None,
    prediction_id: str | None = "pid-1",
) -> CaseState:
    return CaseState(
        case_id=case_id,
        prediction_id=prediction_id,
        status=status,
        verdict=verdict,
        verdict_history=verdict_history or [],
        verification_date=verification_date,
        resolved_on_pass=resolved_on_pass,
        verifiability_score=verifiability_score,
    )


def _make_state(cases: list[CaseState]) -> ContinuousState:
    state = ContinuousState.fresh()
    for c in cases:
        state.cases[c.case_id] = c
    return state


# --- Property 4: Resolution rate computation ---

# Feature: continuous-verification-eval, Property 4: Resolution rate computation
@given(
    n_resolved=st.integers(min_value=0, max_value=10),
    n_inconclusive=st.integers(min_value=0, max_value=10),
    n_unverified=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_p4_resolution_rate(n_resolved, n_inconclusive, n_unverified):
    """Resolution rate = resolved / verified-at-least-once."""
    cases = []
    for i in range(n_resolved):
        cases.append(_make_case(
            f"r-{i}", status="resolved", verdict="confirmed",
            verdict_history=[VerdictEntry(1, "ts", "confirmed", 0.9)],
        ))
    for i in range(n_inconclusive):
        cases.append(_make_case(
            f"i-{i}", status="inconclusive", verdict="inconclusive",
            verdict_history=[VerdictEntry(1, "ts", "inconclusive", 0.3)],
        ))
    for i in range(n_unverified):
        cases.append(_make_case(f"u-{i}", status="pending"))

    state = _make_state(cases)
    rate = compute_resolution_rate(state)

    verified_count = n_resolved + n_inconclusive
    if verified_count == 0:
        assert rate == 0.0
    else:
        expected = n_resolved / verified_count
        assert abs(rate - expected) < 1e-9

    assert 0.0 <= rate <= 1.0


# --- Property 5: Stale inconclusive rate computation ---

# Feature: continuous-verification-eval, Property 5: Stale inconclusive rate computation
@given(
    n_stale=st.integers(min_value=0, max_value=5),
    n_resolved_past=st.integers(min_value=0, max_value=5),
    n_future=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100, deadline=None)
def test_p5_stale_inconclusive_rate(n_stale, n_resolved_past, n_future):
    """Stale rate = (inconclusive AND past) / (past). Future dates excluded."""
    now = datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc)
    past_date = (now - timedelta(days=7)).isoformat()
    future_date = (now + timedelta(days=7)).isoformat()

    cases = []
    for i in range(n_stale):
        cases.append(_make_case(
            f"s-{i}", status="inconclusive", verdict="inconclusive",
            verification_date=past_date,
        ))
    for i in range(n_resolved_past):
        cases.append(_make_case(
            f"rp-{i}", status="resolved", verdict="confirmed",
            verification_date=past_date,
        ))
    for i in range(n_future):
        cases.append(_make_case(
            f"f-{i}", status="inconclusive", verdict="inconclusive",
            verification_date=future_date,
        ))

    state = _make_state(cases)
    rate = compute_stale_inconclusive_rate(state, now)

    past_count = n_stale + n_resolved_past
    if past_count == 0:
        assert rate == 0.0
    else:
        expected = n_stale / past_count
        assert abs(rate - expected) < 1e-9

    assert 0.0 <= rate <= 1.0


# --- Property 6: Resolution speed by tier ---

# Feature: continuous-verification-eval, Property 6: Resolution speed by tier
@given(
    high_passes=st.lists(st.integers(min_value=1, max_value=20), max_size=6),
    mod_passes=st.lists(st.integers(min_value=1, max_value=20), max_size=6),
    low_passes=st.lists(st.integers(min_value=1, max_value=20), max_size=6),
)
@settings(max_examples=100, deadline=None)
def test_p6_resolution_speed_by_tier(high_passes, mod_passes, low_passes):
    """Median resolution pass per tier, null when < 2 cases."""
    import statistics

    cases = []
    for i, p in enumerate(high_passes):
        cases.append(_make_case(
            f"h-{i}", status="resolved", resolved_on_pass=p,
            verifiability_score=0.8,
        ))
    for i, p in enumerate(mod_passes):
        cases.append(_make_case(
            f"m-{i}", status="resolved", resolved_on_pass=p,
            verifiability_score=0.5,
        ))
    for i, p in enumerate(low_passes):
        cases.append(_make_case(
            f"l-{i}", status="resolved", resolved_on_pass=p,
            verifiability_score=0.2,
        ))

    state = _make_state(cases)
    result = compute_resolution_speed_by_tier(state)

    for tier_name, passes in [("high", high_passes), ("moderate", mod_passes), ("low", low_passes)]:
        if len(passes) < 2:
            assert result[tier_name] is None
        else:
            assert result[tier_name] == statistics.median(passes)


# --- Unit tests ---

def test_resolution_rate_zero_cases():
    """Empty state → 0.0."""
    state = ContinuousState.fresh()
    assert compute_resolution_rate(state) == 0.0


def test_resolution_rate_all_resolved():
    """All verified cases resolved → 1.0."""
    cases = [
        _make_case("c1", status="resolved", verdict="confirmed",
                    verdict_history=[VerdictEntry(1, "ts", "confirmed", 0.9)]),
        _make_case("c2", status="resolved", verdict="refuted",
                    verdict_history=[VerdictEntry(1, "ts", "refuted", 0.8)]),
    ]
    assert compute_resolution_rate(_make_state(cases)) == 1.0


def test_stale_rate_all_future():
    """All verification dates in future → 0.0."""
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    cases = [
        _make_case("c1", status="inconclusive", verdict="inconclusive",
                    verification_date=future),
    ]
    assert compute_stale_inconclusive_rate(_make_state(cases)) == 0.0


def test_stale_rate_null_dates():
    """Cases with null verification_date excluded."""
    cases = [
        _make_case("c1", status="inconclusive", verdict="inconclusive",
                    verification_date=None),
    ]
    assert compute_stale_inconclusive_rate(_make_state(cases)) == 0.0


def test_resolution_speed_one_per_tier():
    """Exactly 1 resolved case per tier → all null."""
    cases = [
        _make_case("h1", status="resolved", resolved_on_pass=2, verifiability_score=0.8),
        _make_case("m1", status="resolved", resolved_on_pass=4, verifiability_score=0.5),
        _make_case("l1", status="resolved", resolved_on_pass=6, verifiability_score=0.2),
    ]
    result = compute_resolution_speed_by_tier(_make_state(cases))
    assert result == {"high": None, "moderate": None, "low": None}


def test_resolution_speed_two_per_tier():
    """Exactly 2 resolved cases → correct median."""
    cases = [
        _make_case("h1", status="resolved", resolved_on_pass=2, verifiability_score=0.8),
        _make_case("h2", status="resolved", resolved_on_pass=4, verifiability_score=0.9),
    ]
    result = compute_resolution_speed_by_tier(_make_state(cases))
    assert result["high"] == 3.0  # median of [2, 4]


def test_continuous_calibration_structure():
    """compute_continuous_calibration returns expected keys."""
    state = ContinuousState.fresh()
    cal = compute_continuous_calibration(state)
    assert "resolution_rate" in cal
    assert "stale_inconclusive_rate" in cal
    assert "resolution_speed_by_tier" in cal
    assert "verdict_distribution" in cal
