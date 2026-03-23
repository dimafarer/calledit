"""Property-based tests for bundle construction module (V4-3a).

Tests verify prediction ID format, bundle assembly invariants,
serialization round-trip, DDB item format, and float-to-Decimal conversion.

No mocks. Decision 96: v4 has zero mocks across all test types.
"""

import re
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from hypothesis import given, settings, strategies as st

# Add src to path so we can import bundle
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bundle import (
    _convert_floats_to_decimal,
    build_bundle,
    deserialize_bundle,
    format_ddb_item,
    generate_prediction_id,
    serialize_bundle,
)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# UUID4 pattern: 8-4-4-4-12 hex chars
_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_PRED_ID_RE = re.compile(
    r"^pred-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _make_bundle_inputs():
    """Build a strategy that produces valid build_bundle() keyword args."""
    return st.fixed_dictionaries({
        "prediction_id": st.text(min_size=1, max_size=50).map(
            lambda _: f"pred-{uuid.uuid4()}"
        ),
        "user_id": st.text(min_size=1, max_size=50),
        "raw_prediction": st.text(min_size=1, max_size=200),
        "parsed_claim": st.fixed_dictionaries({
            "statement": st.text(min_size=1, max_size=100),
            "verification_date": st.text(min_size=1, max_size=50),
            "date_reasoning": st.text(min_size=1, max_size=100),
        }),
        "verification_plan": st.fixed_dictionaries({
            "sources": st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
            "criteria": st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
            "steps": st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5),
        }),
        "verifiability_score": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        "verifiability_reasoning": st.text(min_size=1, max_size=200),
        "reviewable_sections": st.lists(
            st.fixed_dictionaries({
                "section": st.text(min_size=1, max_size=50),
                "improvable": st.booleans(),
                "questions": st.lists(st.text(min_size=1, max_size=50), max_size=3),
                "reasoning": st.text(min_size=1, max_size=100),
            }),
            max_size=3,
        ),
        "prompt_versions": st.fixed_dictionaries({
            "prediction_parser": st.text(min_size=1, max_size=10),
            "verification_planner": st.text(min_size=1, max_size=10),
            "plan_reviewer": st.text(min_size=1, max_size=10),
        }),
    })


# ---------------------------------------------------------------------------
# Property Test — Task 2.2
# Feature: creation-agent-core, Property 7: Prediction ID format
# **Validates: Requirements 5.1**
# ---------------------------------------------------------------------------


class TestPredictionIdFormat:
    """Property 7: generate_prediction_id() returns pred-{uuid4} pattern."""

    @settings(max_examples=100)
    @given(st.integers())  # dummy input — function is parameterless
    def test_prediction_id_matches_pattern(self, _dummy):
        """For any call to generate_prediction_id(), result matches pred-{uuid4}.

        Feature: creation-agent-core, Property 7: Prediction ID format
        **Validates: Requirements 5.1**
        """
        pred_id = generate_prediction_id()

        # Must start with "pred-"
        assert pred_id.startswith("pred-"), f"ID doesn't start with 'pred-': {pred_id}"

        # Full pattern match
        assert _PRED_ID_RE.match(pred_id), f"ID doesn't match pred-{{uuid4}} pattern: {pred_id}"

        # UUID portion must be valid UUID v4
        uuid_part = pred_id[5:]  # strip "pred-"
        assert len(uuid_part) == 36, f"UUID portion wrong length: {uuid_part}"
        parsed = uuid.UUID(uuid_part, version=4)
        assert str(parsed) == uuid_part


# ---------------------------------------------------------------------------
# Property Test — Task 2.3
# Feature: creation-agent-core, Property 3: Bundle assembly invariants
# **Validates: Requirements 3.5, 5.5, 5.6**
# ---------------------------------------------------------------------------


class TestBundleAssemblyInvariants:
    """Property 3: build_bundle() returns dict with all required fields."""

    REQUIRED_FIELDS = {
        "prediction_id",
        "user_id",
        "raw_prediction",
        "parsed_claim",
        "verification_plan",
        "verifiability_score",
        "verifiability_reasoning",
        "reviewable_sections",
        "clarification_rounds",
        "created_at",
        "status",
        "prompt_versions",
    }

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_bundle_has_all_required_fields(self, inputs):
        """For any valid inputs, build_bundle() contains all required fields.

        Feature: creation-agent-core, Property 3: Bundle assembly invariants
        **Validates: Requirements 3.5, 5.5, 5.6**
        """
        bundle = build_bundle(**inputs)
        assert self.REQUIRED_FIELDS == set(bundle.keys())

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_bundle_status_is_pending(self, inputs):
        """For any valid inputs, status is always 'pending'.

        Feature: creation-agent-core, Property 3: Bundle assembly invariants
        **Validates: Requirements 3.5, 5.5, 5.6**
        """
        bundle = build_bundle(**inputs)
        assert bundle["status"] == "pending"

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_bundle_clarification_rounds_is_zero(self, inputs):
        """For any valid inputs, clarification_rounds is always 0.

        Feature: creation-agent-core, Property 3: Bundle assembly invariants
        **Validates: Requirements 3.5, 5.5, 5.6**
        """
        bundle = build_bundle(**inputs)
        assert bundle["clarification_rounds"] == 0

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_bundle_created_at_is_valid_iso8601(self, inputs):
        """For any valid inputs, created_at is a valid ISO 8601 UTC timestamp.

        Feature: creation-agent-core, Property 3: Bundle assembly invariants
        **Validates: Requirements 3.5, 5.5, 5.6**
        """
        bundle = build_bundle(**inputs)
        created_at = bundle["created_at"]
        # Must parse as ISO 8601
        parsed = datetime.fromisoformat(created_at)
        # Must be UTC
        assert parsed.tzinfo is not None
        assert parsed.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# Property Test — Task 2.4
# Feature: creation-agent-core, Property 4: Bundle serialization round-trip
# **Validates: Requirements 5.8, 4.6**
# ---------------------------------------------------------------------------


class TestBundleSerializationRoundTrip:
    """Property 4: serialize then deserialize produces equivalent dict."""

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_serialize_deserialize_round_trip(self, inputs):
        """For any valid bundle, serialize→deserialize produces equivalent dict.

        Feature: creation-agent-core, Property 4: Bundle serialization round-trip
        **Validates: Requirements 5.8, 4.6**
        """
        bundle = build_bundle(**inputs)
        json_str = serialize_bundle(bundle)
        restored = deserialize_bundle(json_str)

        # All fields should be present
        assert set(bundle.keys()) == set(restored.keys())

        # String fields should be identical
        for key in ("prediction_id", "user_id", "raw_prediction",
                     "verifiability_reasoning", "status", "created_at"):
            assert bundle[key] == restored[key], f"Mismatch on {key}"

        # Nested dicts/lists should be equivalent
        assert bundle["parsed_claim"] == restored["parsed_claim"]
        assert bundle["verification_plan"] == restored["verification_plan"]
        assert bundle["reviewable_sections"] == restored["reviewable_sections"]
        assert bundle["prompt_versions"] == restored["prompt_versions"]

        # Integer fields
        assert bundle["clarification_rounds"] == restored["clarification_rounds"]

        # Float field — json.dumps(default=str) converts float to string,
        # json.loads parses numeric strings back. With default=str, the float
        # is serialized as its string repr, so we compare via string.
        assert str(bundle["verifiability_score"]) == str(restored["verifiability_score"])


# ---------------------------------------------------------------------------
# Property Test — Task 2.5
# Feature: creation-agent-core, Property 5: DDB item format
# **Validates: Requirements 4.1, 4.2**
# ---------------------------------------------------------------------------


class TestDdbItemFormat:
    """Property 5: format_ddb_item() produces correct PK/SK and preserves fields."""

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_ddb_item_has_correct_pk(self, inputs):
        """For any valid bundle, PK equals PRED#{prediction_id}.

        Feature: creation-agent-core, Property 5: DDB item format
        **Validates: Requirements 4.1, 4.2**
        """
        bundle = build_bundle(**inputs)
        item = format_ddb_item(bundle)
        assert item["PK"] == f"PRED#{bundle['prediction_id']}"

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_ddb_item_has_correct_sk(self, inputs):
        """For any valid bundle, SK equals 'BUNDLE'.

        Feature: creation-agent-core, Property 5: DDB item format
        **Validates: Requirements 4.1, 4.2**
        """
        bundle = build_bundle(**inputs)
        item = format_ddb_item(bundle)
        assert item["SK"] == "BUNDLE"

    @settings(max_examples=100)
    @given(inputs=_make_bundle_inputs())
    def test_ddb_item_preserves_all_bundle_fields(self, inputs):
        """For any valid bundle, all original fields are present in the DDB item.

        Feature: creation-agent-core, Property 5: DDB item format
        **Validates: Requirements 4.1, 4.2**
        """
        bundle = build_bundle(**inputs)
        item = format_ddb_item(bundle)

        for key in bundle:
            assert key in item, f"Missing bundle field in DDB item: {key}"


# ---------------------------------------------------------------------------
# Property Test — Task 2.6
# Feature: creation-agent-core, Property 6: Float-to-Decimal conversion
# **Validates: Requirements 4.3**
# ---------------------------------------------------------------------------


class TestFloatToDecimalConversion:
    """Property 6: _convert_floats_to_decimal() preserves values."""

    @settings(max_examples=100)
    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    def test_float_becomes_decimal(self, value):
        """For any finite float, conversion produces a Decimal.

        Feature: creation-agent-core, Property 6: Float-to-Decimal conversion preserves value
        **Validates: Requirements 4.3**
        """
        result = _convert_floats_to_decimal(value)
        assert isinstance(result, Decimal), f"Expected Decimal, got {type(result)}"

    @settings(max_examples=100)
    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    def test_decimal_round_trips_to_original_float(self, value):
        """For any finite float, Decimal(str(value)) converts back to original.

        Feature: creation-agent-core, Property 6: Float-to-Decimal conversion preserves value
        **Validates: Requirements 4.3**
        """
        result = _convert_floats_to_decimal(value)
        assert float(result) == value

    @settings(max_examples=100)
    @given(
        d=st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.one_of(
                st.floats(allow_nan=False, allow_infinity=False),
                st.integers(),
                st.text(max_size=20),
                st.booleans(),
            ),
            max_size=5,
        )
    )
    def test_nested_dict_floats_become_decimals(self, d):
        """For any dict, all floats become Decimals, non-floats unchanged.

        Feature: creation-agent-core, Property 6: Float-to-Decimal conversion preserves value
        **Validates: Requirements 4.3**
        """
        result = _convert_floats_to_decimal(d)
        for key in d:
            if isinstance(d[key], float):
                assert isinstance(result[key], Decimal)
                assert float(result[key]) == d[key]
            else:
                assert result[key] == d[key]

    @settings(max_examples=100)
    @given(
        lst=st.lists(
            st.one_of(
                st.floats(allow_nan=False, allow_infinity=False),
                st.integers(),
                st.text(max_size=20),
            ),
            max_size=5,
        )
    )
    def test_nested_list_floats_become_decimals(self, lst):
        """For any list, all floats become Decimals, non-floats unchanged.

        Feature: creation-agent-core, Property 6: Float-to-Decimal conversion preserves value
        **Validates: Requirements 4.3**
        """
        result = _convert_floats_to_decimal(lst)
        for i, val in enumerate(lst):
            if isinstance(val, float):
                assert isinstance(result[i], Decimal)
                assert float(result[i]) == val
            else:
                assert result[i] == val

    def test_non_float_types_unchanged(self):
        """Strings, ints, bools, None pass through unchanged.

        Feature: creation-agent-core, Property 6: Float-to-Decimal conversion preserves value
        **Validates: Requirements 4.3**
        """
        assert _convert_floats_to_decimal("hello") == "hello"
        assert _convert_floats_to_decimal(42) == 42
        assert _convert_floats_to_decimal(True) is True
        assert _convert_floats_to_decimal(None) is None
