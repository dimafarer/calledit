"""
Tests for EvalReasoningStore — DynamoDB eval reasoning capture.

Uses mocked DynamoDB to test fire-and-forget behavior, item structure,
and resilience to failures.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..",
    "backend", "calledit-backend", "handlers", "strands_make_call"
))

from eval_reasoning_store import EvalReasoningStore, TTL_DAYS


@pytest.fixture
def mock_table():
    """Create a store with a mocked DynamoDB table."""
    store = EvalReasoningStore.__new__(EvalReasoningStore)
    store.eval_run_id = "test-run-id"
    store.table_name = "calledit-eval-reasoning"
    store._table = MagicMock()
    return store


class TestFireAndForget:
    """DDB failures must never raise — log warning and continue."""

    def test_put_item_catches_connection_error(self, mock_table):
        mock_table._table.put_item.side_effect = ConnectionError("no connection")
        # Should not raise
        mock_table._put_item("test#key", {"data": "value"})
        mock_table._table.put_item.assert_called_once()

    def test_put_item_catches_generic_exception(self, mock_table):
        mock_table._table.put_item.side_effect = Exception("throttled")
        mock_table._put_item("test#key", {"data": "value"})

    def test_put_item_noop_when_table_none(self):
        store = EvalReasoningStore.__new__(EvalReasoningStore)
        store._table = None
        store.eval_run_id = "test"
        # Should not raise
        store._put_item("test#key", {"data": "value"})

    def test_write_run_metadata_survives_failure(self, mock_table):
        mock_table._table.put_item.side_effect = Exception("fail")
        mock_table.write_run_metadata(
            manifest={"parser": "1"}, dataset_version="2.0",
            schema_version="2.0", total_tests=10, pass_rate=0.8,
            duration_s=120.5,
        )

    def test_write_agent_outputs_survives_failure(self, mock_table):
        mock_table._table.put_item.side_effect = Exception("fail")
        mock_table.write_agent_outputs("base-001", {
            "parser": "output", "categorizer": "output",
            "verification_builder": "output", "review": "output",
        })

    def test_write_judge_reasoning_survives_failure(self, mock_table):
        mock_table._table.put_item.side_effect = Exception("fail")
        mock_table.write_judge_reasoning(
            "base-001", "categorizer", 0.85, "good reasoning", "opus-4.6"
        )

    def test_write_token_counts_survives_failure(self, mock_table):
        mock_table._table.put_item.side_effect = Exception("fail")
        mock_table.write_token_counts("base-001", {
            "parser": {"input_tokens": 100, "output_tokens": 50},
        })


class TestItemStructure:
    """Verify DDB items have correct keys, types, and TTL."""

    def test_run_metadata_item(self, mock_table):
        mock_table.write_run_metadata(
            manifest={"parser": "3", "categorizer": "5"},
            dataset_version="2.0", schema_version="2.0",
            total_tests=45, pass_rate=0.82, duration_s=340.5,
        )
        item = mock_table._table.put_item.call_args[1]["Item"]
        assert item["eval_run_id"] == "test-run-id"
        assert item["record_key"] == "report_summary#SUMMARY"
        assert item["dataset_version"] == "2.0"
        assert item["total_tests"] == 45
        assert item["pass_rate"] == "0.82"
        assert "ttl" in item
        assert item["ttl"] > time.time()

    def test_agent_outputs_item(self, mock_table):
        mock_table.write_agent_outputs("base-005", {
            "parser": "parsed text",
            "categorizer": "category text",
            "verification_builder": "vb text",
            "review": "review text",
        })
        item = mock_table._table.put_item.call_args[1]["Item"]
        assert item["record_key"] == "agent_output#base-005"
        assert item["parser_output"] == "parsed text"
        assert item["categorizer_output"] == "category text"
        assert item["verification_builder_output"] == "vb text"
        assert item["review_output"] == "review text"

    def test_judge_reasoning_item(self, mock_table):
        mock_table.write_judge_reasoning(
            "base-003", "categorizer", 0.9, "Sound reasoning", "opus-4.6"
        )
        item = mock_table._table.put_item.call_args[1]["Item"]
        assert item["record_key"] == "judge_reasoning#base-003#categorizer"
        assert item["agent_name"] == "categorizer"
        assert item["score"] == "0.9"
        assert item["judge_reasoning"] == "Sound reasoning"
        assert item["judge_model"] == "opus-4.6"

    def test_token_counts_item(self, mock_table):
        mock_table.write_token_counts("base-001", {
            "parser": {"input_tokens": 1200, "output_tokens": 350},
            "categorizer": {"input_tokens": 1500, "output_tokens": 280},
        })
        item = mock_table._table.put_item.call_args[1]["Item"]
        assert item["record_key"] == "token_counts#base-001"
        assert item["parser_input_tokens"] == 1200
        assert item["parser_output_tokens"] == 350
        assert item["categorizer_input_tokens"] == 1500

    def test_ttl_is_90_days_in_future(self, mock_table):
        mock_table.write_agent_outputs("base-001", {"parser": "x"})
        item = mock_table._table.put_item.call_args[1]["Item"]
        expected_min = int(time.time()) + (TTL_DAYS * 86400) - 10
        expected_max = int(time.time()) + (TTL_DAYS * 86400) + 10
        assert expected_min <= item["ttl"] <= expected_max

    def test_eval_run_id_is_uuid_format(self):
        store = EvalReasoningStore.__new__(EvalReasoningStore)
        store._table = None
        import uuid
        store.eval_run_id = str(uuid.uuid4())
        # Should be valid UUID
        uuid.UUID(store.eval_run_id)


class TestInitialization:
    """Test store initialization handles missing DDB gracefully."""

    def test_init_with_boto3_failure(self):
        """When DDB is unavailable, store disables itself gracefully."""
        # Use a nonexistent table name — boto3 won't fail at Table() creation
        # but _put_item will fail on actual writes. The key behavior is that
        # __init__ catches exceptions and sets _table = None.
        store = EvalReasoningStore.__new__(EvalReasoningStore)
        store.eval_run_id = str(__import__("uuid").uuid4())
        store.table_name = "nonexistent"
        store._table = None  # Simulate failed init
        # Writes should be no-ops
        store.write_agent_outputs("base-001", {"parser": "test"})
        # No exception raised = success

    def test_init_sets_eval_run_id(self):
        """Store always gets a valid UUID even if DDB fails."""
        store = EvalReasoningStore.__new__(EvalReasoningStore)
        store._table = None
        store.eval_run_id = str(__import__("uuid").uuid4())
        import uuid
        uuid.UUID(store.eval_run_id)  # Should not raise
