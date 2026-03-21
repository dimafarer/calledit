"""
Integration Tests for Verification Executor Agent (Spec B1)

These tests call real Bedrock models and real MCP servers.
They cost money and take time (~30s+ for MCP cold start, ~5-15s per Bedrock call).

Run from the strands_make_call directory:
    cd backend/calledit-backend/handlers/strands_make_call
    /home/wsluser/projects/calledit/venv/bin/python -m pytest \
        ../../../../backend/calledit-backend/tests/test_verification_executor.py -v

Or from project root with PYTHONPATH:
    PYTHONPATH=backend/calledit-backend/handlers/strands_make_call \
    /home/wsluser/projects/calledit/venv/bin/python -m pytest \
        backend/calledit-backend/tests/test_verification_executor.py -v

NO MOCKS. All tests hit real services.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import pytest

# Add handler directory to sys.path for imports
_handler_dir = str(
    Path(__file__).resolve().parent.parent / "handlers" / "strands_make_call"
)
if _handler_dir not in sys.path:
    sys.path.insert(0, _handler_dir)

from verification_executor_agent import (
    VERIFICATION_EXECUTOR_SYSTEM_PROMPT,
    _make_inconclusive,
    _validate_outcome,
    run_verification,
    create_verification_executor_agent,
    _get_executor_agent,
)


# ---------------------------------------------------------------------------
# Test data — real predictions that can be verified right now
# ---------------------------------------------------------------------------

# A fact that is always true — good for confirming the agent works
ALWAYS_TRUE_RECORD = {
    "prediction_statement": "Christmas Day 2025 falls on a Thursday",
    "verifiable_category": "auto_verifiable",
    "verification_method": {
        "source": ["brave_web_search", "calendar lookup"],
        "criteria": ["December 25, 2025 is a Thursday"],
        "steps": [
            "Use brave_web_search to search for 'what day of the week is December 25 2025'",
            "Verify the result confirms Thursday",
        ],
    },
}

# A fact that is always false — good for confirming refutation works
ALWAYS_FALSE_RECORD = {
    "prediction_statement": "Christmas Day 2025 falls on a Monday",
    "verifiable_category": "auto_verifiable",
    "verification_method": {
        "source": ["brave_web_search", "calendar lookup"],
        "criteria": ["December 25, 2025 is a Monday"],
        "steps": [
            "Use brave_web_search to search for 'what day of the week is December 25 2025'",
            "Verify the result confirms Monday",
        ],
    },
}


# ---------------------------------------------------------------------------
# Pure function tests — no Bedrock calls, instant
# ---------------------------------------------------------------------------

class TestMakeInconclusive:
    """Tests for _make_inconclusive helper."""

    def test_returns_inconclusive_status(self):
        result = _make_inconclusive("test reason")
        assert result["status"] == "inconclusive"
        assert result["confidence"] == 0.0
        assert result["evidence"] == []
        assert result["reasoning"] == "test reason"
        assert result["tools_used"] == []

    def test_has_valid_verified_at_timestamp(self):
        result = _make_inconclusive("test")
        datetime.fromisoformat(result["verified_at"])


class TestValidateOutcome:
    """Tests for _validate_outcome — the defensive output normalizer."""

    def test_valid_input_passes_through(self):
        raw = {
            "status": "confirmed",
            "confidence": 0.9,
            "evidence": [{"source": "web", "content": "data", "relevance": "direct"}],
            "reasoning": "clear evidence",
            "tools_used": ["brave_web_search"],
        }
        result = _validate_outcome(raw)
        assert result["status"] == "confirmed"
        assert result["confidence"] == 0.9
        assert len(result["evidence"]) == 1
        assert result["reasoning"] == "clear evidence"
        assert result["tools_used"] == ["brave_web_search"]
        datetime.fromisoformat(result["verified_at"])

    def test_invalid_status_defaults_to_inconclusive(self):
        raw = {"status": "maybe", "confidence": 0.5, "reasoning": "unsure"}
        result = _validate_outcome(raw)
        assert result["status"] == "inconclusive"

    def test_confidence_clamped_to_range(self):
        raw = {"status": "confirmed", "confidence": 1.5, "reasoning": "test"}
        result = _validate_outcome(raw)
        assert result["confidence"] == 1.0

        raw2 = {"status": "confirmed", "confidence": -0.3, "reasoning": "test"}
        result2 = _validate_outcome(raw2)
        assert result2["confidence"] == 0.0

    def test_non_numeric_confidence_defaults_to_zero(self):
        raw = {"status": "confirmed", "confidence": "high", "reasoning": "test"}
        result = _validate_outcome(raw)
        assert result["confidence"] == 0.0

    def test_missing_evidence_defaults_to_empty_list(self):
        raw = {"status": "confirmed", "confidence": 0.8, "reasoning": "test"}
        result = _validate_outcome(raw)
        assert result["evidence"] == []

    def test_non_list_evidence_defaults_to_empty_list(self):
        raw = {"status": "confirmed", "confidence": 0.8, "reasoning": "test", "evidence": "not a list"}
        result = _validate_outcome(raw)
        assert result["evidence"] == []

    def test_evidence_items_normalized_to_strings(self):
        raw = {
            "status": "confirmed",
            "confidence": 0.8,
            "reasoning": "test",
            "evidence": [{"source": 123, "content": None, "relevance": True}],
        }
        result = _validate_outcome(raw)
        assert result["evidence"][0]["source"] == "123"
        assert result["evidence"][0]["content"] == "None"
        assert result["evidence"][0]["relevance"] == "True"

    def test_empty_reasoning_gets_default(self):
        raw = {"status": "confirmed", "confidence": 0.8, "reasoning": ""}
        result = _validate_outcome(raw)
        assert len(result["reasoning"]) > 0

    def test_missing_tools_used_defaults_to_empty_list(self):
        raw = {"status": "confirmed", "confidence": 0.8, "reasoning": "test"}
        result = _validate_outcome(raw)
        assert result["tools_used"] == []

    def test_completely_empty_dict(self):
        result = _validate_outcome({})
        assert result["status"] == "inconclusive"
        assert result["confidence"] == 0.0
        assert result["evidence"] == []
        assert result["tools_used"] == []
        assert len(result["reasoning"]) > 0


class TestSystemPrompt:
    """Tests for VERIFICATION_EXECUTOR_SYSTEM_PROMPT content."""

    def test_contains_verdict_rules(self):
        assert "VERDICT RULES:" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert "confirmed" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert "refuted" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert "inconclusive" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT

    def test_contains_json_format(self):
        assert '"status"' in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert '"confidence"' in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert '"evidence"' in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert '"reasoning"' in VERIFICATION_EXECUTOR_SYSTEM_PROMPT
        assert '"tools_used"' in VERIFICATION_EXECUTOR_SYSTEM_PROMPT

    def test_contains_tool_invocation_instructions(self):
        assert "Execute each step by invoking" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT

    def test_contains_raw_json_instruction(self):
        assert "Return ONLY the raw JSON object" in VERIFICATION_EXECUTOR_SYSTEM_PROMPT

    def test_line_count_is_reasonable(self):
        lines = VERIFICATION_EXECUTOR_SYSTEM_PROMPT.strip().splitlines()
        assert 20 <= len(lines) <= 40, f"System prompt has {len(lines)} lines, expected 20-40"


class TestRunVerificationPurePaths:
    """Tests for run_verification error paths that don't need Bedrock."""

    def test_missing_verification_method_returns_inconclusive(self):
        record = {"prediction_statement": "test", "verifiable_category": "auto_verifiable"}
        result = run_verification(record)
        assert result["status"] == "inconclusive"
        assert "plan" in result["reasoning"].lower() or "no verification" in result["reasoning"].lower()

    def test_none_verification_method_returns_inconclusive(self):
        record = {"prediction_statement": "test", "verification_method": None}
        result = run_verification(record)
        assert result["status"] == "inconclusive"

    def test_empty_dict_verification_method_returns_inconclusive(self):
        record = {"prediction_statement": "test", "verification_method": {}}
        result = run_verification(record)
        assert result["status"] == "inconclusive"

    def test_empty_plan_fields_returns_inconclusive(self):
        record = {
            "prediction_statement": "test",
            "verification_method": {"source": [], "criteria": [], "steps": []},
        }
        result = run_verification(record)
        assert result["status"] == "inconclusive"

    def test_completely_empty_dict_returns_inconclusive(self):
        result = run_verification({})
        assert result["status"] == "inconclusive"

    def test_non_dict_input_returns_inconclusive(self):
        # run_verification should never raise
        result = run_verification("not a dict")
        assert result["status"] == "inconclusive"

    def test_none_input_returns_inconclusive(self):
        result = run_verification(None)
        assert result["status"] == "inconclusive"


# ---------------------------------------------------------------------------
# Integration tests — real Bedrock + real MCP servers
# These are slow (~30s MCP cold start + ~5-15s per Bedrock call)
# Mark with @pytest.mark.integration so they can be run selectively
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRunVerificationIntegration:
    """Real integration tests — calls Bedrock and MCP servers."""

    def test_always_true_prediction_returns_confirmed(self):
        """Christmas 2025 is a Thursday — agent should confirm this."""
        result = run_verification(ALWAYS_TRUE_RECORD)

        # Structural validity
        assert result["status"] in {"confirmed", "refuted", "inconclusive"}
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["evidence"], list)
        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0
        datetime.fromisoformat(result["verified_at"])
        assert isinstance(result["tools_used"], list)

        # The agent should confirm this — it's a verifiable fact
        # Allow inconclusive if tools fail, but it should NOT be refuted
        assert result["status"] != "refuted", (
            f"Agent incorrectly refuted a true fact. Reasoning: {result['reasoning']}"
        )

    def test_always_false_prediction_returns_refuted(self):
        """Christmas 2025 is NOT a Monday — agent should refute this."""
        result = run_verification(ALWAYS_FALSE_RECORD)

        # Structural validity
        assert result["status"] in {"confirmed", "refuted", "inconclusive"}
        assert 0.0 <= result["confidence"] <= 1.0
        assert isinstance(result["evidence"], list)
        assert isinstance(result["reasoning"], str)
        datetime.fromisoformat(result["verified_at"])

        # The agent should refute this — it's a verifiably false claim
        # Allow inconclusive if tools fail, but it should NOT be confirmed
        assert result["status"] != "confirmed", (
            f"Agent incorrectly confirmed a false fact. Reasoning: {result['reasoning']}"
        )

    def test_output_has_all_required_fields(self):
        """Verify the output structure matches the Verification_Outcome data model."""
        result = run_verification(ALWAYS_TRUE_RECORD)

        required_fields = {"status", "confidence", "evidence", "reasoning", "verified_at", "tools_used"}
        assert required_fields.issubset(result.keys()), (
            f"Missing fields: {required_fields - result.keys()}"
        )

    def test_evidence_items_have_required_fields(self):
        """Each evidence item should have source, content, relevance."""
        result = run_verification(ALWAYS_TRUE_RECORD)

        for item in result["evidence"]:
            assert "source" in item, f"Evidence item missing 'source': {item}"
            assert "content" in item, f"Evidence item missing 'content': {item}"
            assert "relevance" in item, f"Evidence item missing 'relevance': {item}"

    def test_tools_used_is_populated(self):
        """For auto_verifiable predictions, the agent should use at least one tool."""
        result = run_verification(ALWAYS_TRUE_RECORD)

        # If status is confirmed or refuted, tools should have been used
        if result["status"] in {"confirmed", "refuted"}:
            assert len(result["tools_used"]) > 0, (
                f"Agent reached verdict '{result['status']}' without using any tools"
            )


@pytest.mark.integration
class TestFactoryIntegration:
    """Real factory tests — creates agent with real MCP tools."""

    def test_factory_creates_agent(self):
        """Factory should create an agent without raising."""
        agent = create_verification_executor_agent()
        assert agent is not None

    def test_lazy_singleton_returns_agent(self):
        """The lazy getter should return a real agent."""
        agent = _get_executor_agent()
        assert agent is not None
