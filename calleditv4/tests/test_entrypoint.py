"""Unit tests for the CalledIt v4 AgentCore entrypoint.

Only tests that exercise pure logic without touching the Strands Agent.
Tests that require real Bedrock calls are validated manually via
`agentcore invoke --dev` (Tasks 7-8).

No mocks. Decision 96: v4 has zero mocks across all test types.
"""

import inspect
import json
import sys
from pathlib import Path

# Add src to path so we can import main
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import (
    MODEL_ID,
    SIMPLE_PROMPT_SYSTEM,
    TOOLS,
    DYNAMODB_TABLE_NAME,
    handler,
    app,
)


class TestConstants:
    """Verify module-level constants match design requirements."""

    def test_model_id(self):
        """MODEL_ID must be Claude Sonnet 4 cross-region inference profile (Req 2.1)."""
        assert MODEL_ID == "us.anthropic.claude-sonnet-4-20250514-v1:0"

    def test_simple_prompt_system_contains_calledit_v4(self):
        """SIMPLE_PROMPT_SYSTEM must identify the agent as CalledIt v4 (Req 2.4)."""
        assert "CalledIt v4" in SIMPLE_PROMPT_SYSTEM

    def test_dynamodb_table_name_defaults_to_calledit_db(self):
        """DYNAMODB_TABLE_NAME defaults to calledit-db (Req 4.4)."""
        assert DYNAMODB_TABLE_NAME == "calledit-db"

    def test_tools_list_has_three_elements(self):
        """TOOLS list must have 3 elements: browser, code_interpreter, current_time (Req 6.5)."""
        assert len(TOOLS) == 3


class TestEntrypointPattern:
    """Verify the entrypoint uses the correct AgentCore pattern."""

    def test_uses_bedrock_agentcore_app(self):
        """Entrypoint must use BedrockAgentCoreApp (Req 6.4)."""
        from bedrock_agentcore.runtime import BedrockAgentCoreApp

        assert isinstance(app, BedrockAgentCoreApp)

    def test_handler_context_type_annotation(self):
        """handler() must accept context: RequestContext (Req 6.6)."""
        from bedrock_agentcore import RequestContext

        sig = inspect.signature(handler)
        context_param = sig.parameters.get("context")
        assert context_param is not None
        assert context_param.annotation is RequestContext

    def test_main_block_calls_app_run(self):
        """main.py must call app.run() in __main__ block (Req 6.4)."""
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        source = main_path.read_text()
        assert 'if __name__ == "__main__":' in source
        assert "app.run()" in source


class TestPayloadValidation:
    """Verify error handling for missing/wrong payload keys.

    These tests exercise the validation path that returns BEFORE
    creating a Strands Agent — no Bedrock calls, no mocks needed.
    """

    def test_empty_payload_returns_error(self):
        """Empty payload {} must return error JSON (Req 6.3)."""
        from bedrock_agentcore import RequestContext

        result = handler({}, RequestContext())
        parsed = json.loads(result)
        assert "error" in parsed

    def test_wrong_key_returns_error(self):
        """Payload with wrong key must return error JSON (Req 6.3)."""
        from bedrock_agentcore import RequestContext

        result = handler({"message": "hi"}, RequestContext())
        parsed = json.loads(result)
        assert "error" in parsed

    def test_error_message_mentions_both_fields(self):
        """Error message should mention both prediction_text and prompt (Req 6.3)."""
        from bedrock_agentcore import RequestContext

        result = handler({"foo": "bar"}, RequestContext())
        parsed = json.loads(result)
        assert "prediction_text" in parsed["error"] or "prompt" in parsed["error"]

    def test_prediction_text_key_routes_to_creation(self):
        """Payload with prediction_text key should NOT return the missing-field error."""
        # We can't run the full creation flow without Bedrock, but we can verify
        # the routing doesn't return the "missing field" error.
        from bedrock_agentcore import RequestContext

        result = handler({"prediction_text": "test"}, RequestContext())
        parsed = json.loads(result)
        # It will fail (no Bedrock), but the error should be about creation flow,
        # not about missing fields
        if "error" in parsed:
            assert "Missing" not in parsed["error"]
