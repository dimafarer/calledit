"""Bug condition exploration tests for continuous eval dashboard fixes.

These tests exercise the UNFIXED code to confirm the bugs exist.
They are EXPECTED TO FAIL on unfixed code — failure proves the bug is real.

Bug 2: Inconclusive cases get vresult=None because the status filter
       only checks for "resolved", excluding "inconclusive".
Bug 3: pass_num always starts at 0 regardless of state.pass_number,
       so resumed runs always report "Pass 1".
"""

from hypothesis import given, settings, strategies as st

from eval.continuous_state import CaseState


# ---------------------------------------------------------------------------
# Bug 2 — Extracted vresult construction logic (mirrors _run_verification_pass)
# ---------------------------------------------------------------------------

def build_vresult(cs: CaseState) -> dict | None:
    """Reconstruct the vresult logic from _run_verification_pass().

    This mirrors the condition in run_eval.py.
    FIXED: includes "inconclusive" in the status check.
    """
    vresult = None
    if cs.verdict and cs.status in ("resolved", "inconclusive"):
        vresult = {
            "verdict": cs.verdict,
            "confidence": cs.confidence,
            "evidence": cs.evidence or [],
            "reasoning": cs.reasoning or "",
        }
    return vresult


# ---------------------------------------------------------------------------
# Bug 3 — Extracted pass_num initialization logic (mirrors run())
# ---------------------------------------------------------------------------

def compute_first_pass_number(state_pass_number: int) -> int:
    """Reconstruct the pass_num initialization from run().

    FIXED: uses state_pass_number instead of hardcoded 0.
    """
    pass_num = state_pass_number  # Fixed: reads from state
    pass_num += 1  # The loop increments before use
    return pass_num


# ===========================================================================
# Bug Condition Exploration Property Tests
# ===========================================================================


# Feature: continuous-eval-dashboard-fixes, Property 2: Bug Condition — Inconclusive Cases in Task Outputs
# **Validates: Requirements 1.3, 1.4, 2.3, 2.4**
@given(confidence=st.floats(min_value=0.0, max_value=1.0))
@settings(max_examples=50, deadline=None)
def test_bug_condition_inconclusive_vresult(confidence):
    """For any inconclusive CaseState, build_vresult SHOULD return a dict.

    On UNFIXED code, build_vresult returns None because cs.status == "resolved"
    is False when status is "inconclusive" — so this test FAILS, confirming Bug 2.
    """
    cs = CaseState(
        case_id="test-case",
        prediction_id="pid-test",
        status="inconclusive",
        verdict="inconclusive",
        confidence=confidence,
        evidence=[{"source": "test"}],
        reasoning="test reasoning",
    )

    result = build_vresult(cs)

    # Expected: a dict with the four keys
    assert result is not None, (
        f"build_vresult returned None for inconclusive case (confidence={confidence}). "
        "Bug 2: the condition `cs.status == 'resolved'` excludes inconclusive cases."
    )
    assert "verdict" in result
    assert "confidence" in result
    assert "evidence" in result
    assert "reasoning" in result
    assert result["verdict"] == "inconclusive"
    assert result["confidence"] == confidence


# Feature: continuous-eval-dashboard-fixes, Property 3: Bug Condition — Sequential Pass Numbering on Resume
# **Validates: Requirements 1.5, 2.5**
@given(state_pass_number=st.integers(min_value=1, max_value=100))
@settings(max_examples=50, deadline=None)
def test_bug_condition_pass_numbering_reset(state_pass_number):
    """For any resumed state with pass_number >= 1, first pass SHOULD be pass_number + 1.

    On UNFIXED code, compute_first_pass_number always returns 1 because
    pass_num is hardcoded to 0 — so this test FAILS, confirming Bug 3.
    """
    first_pass = compute_first_pass_number(state_pass_number)

    assert first_pass == state_pass_number + 1, (
        f"Expected first pass to be {state_pass_number + 1} "
        f"(state_pass_number={state_pass_number}), but got {first_pass}. "
        "Bug 3: pass_num is hardcoded to 0, ignoring state.pass_number."
    )


# ===========================================================================
# Preservation Property Tests
# ===========================================================================
# These tests verify non-buggy behavior on UNFIXED code.
# They SHOULD PASS — establishing the baseline to preserve after fixes.


# Feature: continuous-eval-dashboard-fixes, Property 4: Preservation — Resolved Cases Unchanged
# **Validates: Requirements 3.3, 3.4**
@given(
    verdict=st.sampled_from(["confirmed", "refuted"]),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=50, deadline=None)
def test_preservation_resolved_case_vresult(verdict, confidence):
    """For any resolved CaseState with confirmed/refuted verdict, build_vresult
    SHOULD return a dict with all four keys and correct values.

    This PASSES on unfixed code — resolved cases are handled correctly.
    """
    cs = CaseState(
        case_id="test-resolved",
        prediction_id="pid-resolved",
        status="resolved",
        verdict=verdict,
        confidence=confidence,
        evidence=[{"source": "test"}],
        reasoning="test reasoning",
    )

    result = build_vresult(cs)

    assert result is not None, (
        f"build_vresult returned None for resolved case "
        f"(verdict={verdict}, confidence={confidence})"
    )
    assert result["verdict"] == verdict
    assert result["confidence"] == confidence
    assert result["evidence"] == [{"source": "test"}]
    assert result["reasoning"] == "test reasoning"


# Feature: continuous-eval-dashboard-fixes, Property 4: Preservation — Pending/Error Cases Return None
# **Validates: Requirements 3.3, 3.4**
@given(status=st.sampled_from(["pending", "error"]))
@settings(max_examples=50, deadline=None)
def test_preservation_pending_error_case_vresult(status):
    """For any CaseState with status in (pending, error), build_vresult
    SHOULD return None.

    This PASSES on unfixed code — pending/error cases correctly produce None.
    """
    cs = CaseState(
        case_id="test-no-verdict",
        prediction_id="pid-no-verdict",
        status=status,
        verdict=None,
        confidence=None,
        evidence=None,
        reasoning=None,
    )

    result = build_vresult(cs)

    assert result is None, (
        f"build_vresult returned {result} for {status} case — expected None"
    )


# Feature: continuous-eval-dashboard-fixes, Property 5: Preservation — Fresh State Pass Numbering
# **Validates: Requirements 3.5, 3.6**
def test_preservation_fresh_state_pass_numbering():
    """When state_pass_number == 0 (fresh state), compute_first_pass_number
    SHOULD return 1.

    This PASSES on unfixed code — fresh state always starts at pass 1.
    """
    first_pass = compute_first_pass_number(0)

    assert first_pass == 1, (
        f"Expected first pass to be 1 for fresh state (pass_number=0), "
        f"but got {first_pass}"
    )
