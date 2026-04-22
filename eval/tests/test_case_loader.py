"""Tests for eval.case_loader — Property 1, 2 + unit tests.

Property tests use hypothesis to verify correctness properties across
randomly generated inputs. Unit tests verify specific examples and edge cases.
"""

import sys
import os

import pytest
from hypothesis import given, settings, strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from eval.case_loader import _prediction_to_case, _filter_cases, load_cases


# --- Hypothesis strategies ---

def prediction_strategy():
    """Generate random prediction dicts matching golden dataset schema."""
    return st.fixed_dictionaries({
        "id": st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=20,
        ),
        "prediction_text": st.text(min_size=1, max_size=200),
        "difficulty": st.sampled_from(["easy", "medium", "hard"]),
        "verification_mode": st.sampled_from(
            ["immediate", "at_date", "before_date", "recurring"]
        ),
        "smoke_test": st.booleans(),
        "expected_verification_outcome": st.one_of(
            st.none(),
            st.sampled_from(["confirmed", "refuted", "inconclusive"]),
        ),
        "expected_verifiability_score_range": st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            min_size=2,
            max_size=2,
        ),
        "ground_truth": st.just({}),
    })


# --- Property 1: Case construction preserves prediction data ---

# Feature: strands-evals-migration, Property 1: Case construction preserves prediction data
@given(prediction=prediction_strategy())
@settings(max_examples=100)
def test_case_construction_preserves_data(prediction):
    """For any prediction dict, the constructed Case preserves all fields."""
    case = _prediction_to_case(prediction)

    assert case.input == prediction["prediction_text"]
    assert case.expected_output == prediction["expected_verification_outcome"]
    assert case.name == prediction["id"]
    assert case.session_id == prediction["id"]

    # Metadata mappings
    assert case.metadata["id"] == prediction["id"]
    assert case.metadata["difficulty"] == prediction["difficulty"]
    assert case.metadata["verification_mode"] == prediction["verification_mode"]
    assert case.metadata["smoke_test"] == prediction["smoke_test"]
    assert case.metadata["ground_truth"] == prediction.get("ground_truth", {})
    assert (
        case.metadata["expected_verifiability_score_range"]
        == prediction["expected_verifiability_score_range"]
    )

    # Qualifying flag
    expected_qualifying = prediction["expected_verification_outcome"] is not None
    assert case.metadata["qualifying"] == expected_qualifying


# Feature: strands-evals-migration, Property 1: None expected_output → qualifying=False
@given(prediction=prediction_strategy().filter(
    lambda p: p["expected_verification_outcome"] is None
))
@settings(max_examples=50)
def test_none_expected_output_means_not_qualifying(prediction):
    """When expected_verification_outcome is None, qualifying must be False."""
    case = _prediction_to_case(prediction)
    assert case.metadata["qualifying"] is False
    assert case.expected_output is None


# Feature: strands-evals-migration, Property 1: non-None expected_output → qualifying=True
@given(prediction=prediction_strategy().filter(
    lambda p: p["expected_verification_outcome"] is not None
))
@settings(max_examples=50)
def test_non_none_expected_output_means_qualifying(prediction):
    """When expected_verification_outcome is not None, qualifying must be True."""
    case = _prediction_to_case(prediction)
    assert case.metadata["qualifying"] is True
    assert case.expected_output is not None


# --- Property 2: Case filtering correctness ---

def _make_case(name: str, smoke_test: bool = False) -> object:
    """Helper to create a Case with minimal fields for filtering tests."""
    from strands_evals import Case

    return Case(
        name=name,
        input=f"prediction for {name}",
        expected_output="confirmed",
        session_id=name,
        metadata={"smoke_test": smoke_test, "qualifying": True},
    )


# Feature: strands-evals-migration, Property 2: Case filtering correctness
@given(
    names=st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=10,
        ),
        min_size=1,
        max_size=20,
        unique=True,
    ),
    smoke_flags=st.lists(st.booleans(), min_size=1, max_size=20),
)
@settings(max_examples=100)
def test_filter_by_smoke_is_subset(names, smoke_flags):
    """Smoke-filtered cases are always a subset of the full set."""
    # Align lengths
    n = min(len(names), len(smoke_flags))
    cases = [_make_case(names[i], smoke_flags[i]) for i in range(n)]

    filtered = _filter_cases(cases, tier="smoke")

    # Subset check
    filtered_names = {c.name for c in filtered}
    all_names = {c.name for c in cases}
    assert filtered_names.issubset(all_names)

    # All filtered cases have smoke_test=True
    for c in filtered:
        assert c.metadata["smoke_test"] is True

    # Count matches
    expected_count = sum(1 for c in cases if c.metadata["smoke_test"])
    assert len(filtered) == expected_count


# Feature: strands-evals-migration, Property 2: Case filtering by id
@given(
    names=st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=10,
        ),
        min_size=1,
        max_size=20,
        unique=True,
    ),
)
@settings(max_examples=100)
def test_filter_by_case_id_returns_exactly_one(names):
    """Filtering by case_id returns exactly one matching case."""
    cases = [_make_case(n) for n in names]
    target = names[0]

    filtered = _filter_cases(cases, case_id=target)

    assert len(filtered) == 1
    assert filtered[0].name == target


# Feature: strands-evals-migration, Property 2: Missing case_id returns empty
@given(
    names=st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=10,
        ),
        min_size=1,
        max_size=10,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_filter_by_missing_case_id_returns_empty(names):
    """Filtering by a non-existent case_id returns empty list."""
    cases = [_make_case(n) for n in names]
    filtered = _filter_cases(cases, case_id="nonexistent-id-xyz")
    assert len(filtered) == 0


# Feature: strands-evals-migration, Property 2: No filter returns all
@given(
    names=st.lists(
        st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
            min_size=1,
            max_size=10,
        ),
        min_size=1,
        max_size=20,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_no_filter_returns_all(names):
    """No filter criteria returns all cases."""
    cases = [_make_case(n) for n in names]
    filtered = _filter_cases(cases)
    assert len(filtered) == len(cases)


# --- Unit tests ---


class TestLoadCasesWithRealDataset:
    """Unit tests using the actual golden_dataset.json."""

    def test_load_static_dataset_count(self):
        """Static dataset has 55 predictions."""
        cases = load_cases("eval/golden_dataset.json")
        assert len(cases) == 55

    def test_load_merged_dataset_count(self):
        """Merged dataset has 70 predictions (55 static - replacements + 16 dynamic)."""
        cases = load_cases(
            "eval/golden_dataset.json", "eval/dynamic_golden_dataset.json"
        )
        assert len(cases) == 70

    def test_smoke_filter_count(self):
        """Smoke filter returns exactly 12 cases."""
        cases = load_cases("eval/golden_dataset.json", tier="smoke")
        assert len(cases) == 12

    def test_base_001_fields(self):
        """base-001 has correct field values."""
        cases = load_cases("eval/golden_dataset.json", case_id="base-001")
        assert len(cases) == 1
        c = cases[0]
        assert c.name == "base-001"
        assert c.input == "The sun will rise tomorrow in New York City"
        assert c.expected_output == "confirmed"
        assert c.session_id == "base-001"
        assert c.metadata["difficulty"] == "easy"
        assert c.metadata["verification_mode"] == "immediate"
        assert c.metadata["qualifying"] is True

    def test_base_002_fields(self):
        """base-002 (Christmas day) has correct field values."""
        cases = load_cases("eval/golden_dataset.json", case_id="base-002")
        c = cases[0]
        assert c.name == "base-002"
        assert c.metadata["qualifying"] is True
        assert c.expected_output == "confirmed"

    def test_qualifying_count_static(self):
        """Static dataset has 7 qualifying cases (non-null expected outcome)."""
        cases = load_cases("eval/golden_dataset.json")
        qualifying = [c for c in cases if c.metadata["qualifying"]]
        assert len(qualifying) == 7

    def test_qualifying_count_merged(self):
        """Merged dataset has 22 qualifying cases."""
        cases = load_cases(
            "eval/golden_dataset.json", "eval/dynamic_golden_dataset.json"
        )
        qualifying = [c for c in cases if c.metadata["qualifying"]]
        assert len(qualifying) == 22

    def test_non_qualifying_has_none_expected(self):
        """Non-qualifying cases have expected_output=None."""
        cases = load_cases("eval/golden_dataset.json")
        non_qualifying = [c for c in cases if not c.metadata["qualifying"]]
        for c in non_qualifying:
            assert c.expected_output is None


class TestEdgeCases:
    """Edge case unit tests."""

    def test_prediction_missing_optional_fields(self):
        """Prediction with minimal fields still constructs a Case."""
        pred = {
            "id": "test-minimal",
            "prediction_text": "Something will happen",
        }
        case = _prediction_to_case(pred)
        assert case.name == "test-minimal"
        assert case.input == "Something will happen"
        assert case.expected_output is None
        assert case.metadata["qualifying"] is False
        assert case.metadata["smoke_test"] is False

    def test_empty_case_list_filter(self):
        """Filtering an empty list returns empty."""
        assert _filter_cases([], tier="smoke") == []
        assert _filter_cases([], case_id="anything") == []
        assert _filter_cases([]) == []
