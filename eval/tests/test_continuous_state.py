"""Tests for eval/continuous_state.py — property-based (P1-P3) and unit tests."""

import json
import os
import tempfile

import pytest
from hypothesis import given, settings, strategies as st

from eval.continuous_state import CaseState, ContinuousState, VerdictEntry


# --- Hypothesis strategies ---

verdict_st = st.sampled_from(["confirmed", "refuted", "inconclusive"])
status_st = st.sampled_from(["pending", "inconclusive", "resolved", "error"])
iso_ts_st = st.just("2026-04-21T12:00:00+00:00")
optional_float = st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
optional_str = st.one_of(st.none(), st.text(min_size=1, max_size=20))
optional_int = st.one_of(st.none(), st.integers(min_value=1, max_value=100))


@st.composite
def verdict_entry_st(draw):
    return VerdictEntry(
        pass_number=draw(st.integers(min_value=1, max_value=50)),
        timestamp=draw(iso_ts_st),
        verdict=draw(verdict_st),
        confidence=draw(optional_float),
    )


@st.composite
def case_state_st(draw):
    status = draw(status_st)
    has_pid = status != "error" or draw(st.booleans())
    return CaseState(
        case_id=draw(st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnop0123456789-")),
        prediction_id=f"pid-{draw(st.integers(min_value=1, max_value=999))}" if has_pid else None,
        status=status,
        verdict=draw(st.one_of(st.none(), verdict_st)),
        confidence=draw(optional_float),
        evidence=None,
        reasoning=draw(optional_str),
        creation_error=draw(optional_str) if status == "error" else None,
        verification_error=None,
        creation_duration=draw(st.floats(min_value=0.0, max_value=300.0, allow_nan=False)),
        verification_date=draw(st.one_of(st.none(), iso_ts_st)),
        resolved_on_pass=draw(optional_int) if status == "resolved" else None,
        verifiability_score=draw(optional_float),
        score_tier=draw(st.one_of(st.none(), st.sampled_from(["high", "moderate", "low"]))),
        verdict_history=draw(st.lists(verdict_entry_st(), max_size=5)),
    )


@st.composite
def continuous_state_st(draw):
    cases = {}
    for _ in range(draw(st.integers(min_value=0, max_value=8))):
        case = draw(case_state_st())
        cases[case.case_id] = case
    return ContinuousState(
        pass_number=draw(st.integers(min_value=0, max_value=50)),
        cases=cases,
        pass_timestamps=draw(st.lists(iso_ts_st, max_size=5)),
        created_at=draw(iso_ts_st),
        eval_table="calledit-v4-eval",
    )


# --- Property 1: State serialization round-trip ---

# Feature: continuous-verification-eval, Property 1: State serialization round-trip
@given(state=continuous_state_st())
@settings(max_examples=100, deadline=None)
def test_p1_state_round_trip(state):
    """For any valid ContinuousState, save→load produces equivalent state."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        state.save(path)
        loaded = ContinuousState.load(path)

        assert loaded.pass_number == state.pass_number
        assert loaded.created_at == state.created_at
        assert loaded.eval_table == state.eval_table
        assert loaded.pass_timestamps == state.pass_timestamps
        assert set(loaded.cases.keys()) == set(state.cases.keys())

        for case_id in state.cases:
            orig = state.cases[case_id]
            load = loaded.cases[case_id]
            assert load.case_id == orig.case_id
            assert load.prediction_id == orig.prediction_id
            assert load.status == orig.status
            assert load.verdict == orig.verdict
            assert load.resolved_on_pass == orig.resolved_on_pass
            assert len(load.verdict_history) == len(orig.verdict_history)
            for vh_orig, vh_load in zip(orig.verdict_history, load.verdict_history):
                assert vh_load.pass_number == vh_orig.pass_number
                assert vh_load.verdict == vh_orig.verdict
    finally:
        os.unlink(path)


# --- Property 2: Case eligibility for verification ---

# Feature: continuous-verification-eval, Property 2: Case eligibility for verification
@given(state=continuous_state_st(), reverify=st.booleans())
@settings(max_examples=100, deadline=None)
def test_p2_case_eligibility(state, reverify):
    """Eligible cases follow status + reverify_resolved rules."""
    eligible = state.get_eligible_for_verification(reverify_resolved=reverify)
    eligible_ids = {c.case_id for c in eligible}

    for case in state.cases.values():
        if case.prediction_id is None:
            assert case.case_id not in eligible_ids, "No prediction_id → never eligible"
        elif case.status in ("pending", "inconclusive"):
            assert case.case_id in eligible_ids, f"{case.status} with pid → eligible"
        elif case.status == "resolved":
            if reverify:
                assert case.case_id in eligible_ids, "resolved + reverify → eligible"
            else:
                assert case.case_id not in eligible_ids, "resolved + no reverify → excluded"
        elif case.status == "error" and case.prediction_id is not None:
            # Error cases with prediction_id are not eligible (they failed verification)
            # The design says error cases with no prediction_id are excluded
            # Error cases with prediction_id: not in pending/inconclusive, so excluded
            assert case.case_id not in eligible_ids


# --- Property 3: State transition correctness ---

# Feature: continuous-verification-eval, Property 3: State transition correctness
@given(
    state=continuous_state_st(),
    verdict=st.one_of(st.none(), verdict_st),
    confidence=optional_float,
    pass_num=st.integers(min_value=1, max_value=50),
)
@settings(max_examples=100, deadline=None)
def test_p3_state_transitions(state, verdict, confidence, pass_num):
    """update_case_verdict transitions status correctly."""
    if not state.cases:
        return  # Nothing to test

    case_id = list(state.cases.keys())[0]
    case = state.cases[case_id]
    prev_status = case.status
    prev_verdict = case.verdict
    prev_resolved_on = case.resolved_on_pass
    prev_history_len = len(case.verdict_history)

    state.update_case_verdict(case_id, verdict, confidence, pass_num)

    if verdict is None:
        # Error — preserve previous state
        assert case.status == prev_status
        assert case.verdict == prev_verdict
        assert len(case.verdict_history) == prev_history_len
    elif verdict in ("confirmed", "refuted"):
        assert case.status == "resolved"
        assert case.verdict == verdict
        assert case.confidence == confidence
        assert len(case.verdict_history) == prev_history_len + 1
        if prev_resolved_on is None:
            assert case.resolved_on_pass == pass_num
        else:
            assert case.resolved_on_pass == prev_resolved_on  # First resolution preserved
    elif verdict == "inconclusive":
        assert case.status == "inconclusive"
        assert case.verdict == "inconclusive"
        assert len(case.verdict_history) == prev_history_len + 1


# --- Unit tests ---

def test_load_missing_file():
    """Loading from non-existent path returns fresh state."""
    state = ContinuousState.load("/tmp/nonexistent_state_12345.json")
    assert state.pass_number == 0
    assert state.cases == {}


def test_load_corrupt_json():
    """Loading corrupt JSON returns fresh state with warning."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json!!!")
        path = f.name
    try:
        state = ContinuousState.load(path)
        assert state.pass_number == 0
        assert state.cases == {}
    finally:
        os.unlink(path)


def test_fresh_defaults():
    """fresh() creates state with pass_number=0 and empty cases."""
    state = ContinuousState.fresh("my-table")
    assert state.pass_number == 0
    assert state.cases == {}
    assert state.eval_table == "my-table"
    assert state.created_at != ""


def test_update_unknown_case_id():
    """Updating unknown case_id is a no-op."""
    state = ContinuousState.fresh()
    state.update_case_verdict("nonexistent", "confirmed", 0.9, 1)
    assert "nonexistent" not in state.cases


def test_resolved_on_pass_preserved_on_re_resolution():
    """resolved_on_pass is set on first resolution and preserved on subsequent ones."""
    state = ContinuousState.fresh()
    state.cases["c1"] = CaseState(case_id="c1", prediction_id="p1", status="pending")

    state.update_case_verdict("c1", "confirmed", 0.9, 3)
    assert state.cases["c1"].resolved_on_pass == 3

    state.update_case_verdict("c1", "refuted", 0.8, 5)
    assert state.cases["c1"].resolved_on_pass == 3  # Still 3, not 5
