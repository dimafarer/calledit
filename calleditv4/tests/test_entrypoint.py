"""Unit tests for the CalledIt v4 AgentCore entrypoint.

Only tests that exercise pure logic without touching the Strands Agent.
Tests that require real Bedrock calls are validated manually via
`agentcore invoke --dev`.

No mocks. Decision 96: v4 has zero mocks across all test types.

V4-3b: Updated for async handler that yields stream events.
"""

import asyncio
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
    MAX_CLARIFICATION_ROUNDS,
    handler,
    app,
    _make_event,
)


def _collect_events(payload, context=None):
    """Run the async handler and collect all yielded events."""
    from bedrock_agentcore import RequestContext

    ctx = context or RequestContext()

    async def _gather():
        events = []
        async for event in handler(payload, ctx):
            events.append(event)
        return events

    return asyncio.get_event_loop().run_until_complete(_gather())


class TestConstants:
    """Verify module-level constants match design requirements."""

    def test_model_id(self):
        """MODEL_ID must be Claude Sonnet 4 cross-region inference profile."""
        assert MODEL_ID == "us.anthropic.claude-sonnet-4-20250514-v1:0"

    def test_simple_prompt_system_contains_calledit_v4(self):
        """SIMPLE_PROMPT_SYSTEM must identify the agent as CalledIt v4."""
        assert "CalledIt v4" in SIMPLE_PROMPT_SYSTEM

    def test_dynamodb_table_name_defaults_to_calledit_v4(self):
        """DYNAMODB_TABLE_NAME defaults to calledit-v4."""
        assert DYNAMODB_TABLE_NAME == "calledit-v4"

    def test_tools_list_has_three_elements(self):
        """TOOLS list must have 3 elements: browser, code_interpreter, current_time."""
        assert len(TOOLS) == 3

    def test_max_clarification_rounds_defaults_to_five(self):
        """MAX_CLARIFICATION_ROUNDS defaults to 5 (Req 3.1, 3.4)."""
        assert MAX_CLARIFICATION_ROUNDS == 5


class TestEntrypointPattern:
    """Verify the entrypoint uses the correct AgentCore pattern."""

    def test_uses_bedrock_agentcore_app(self):
        """Entrypoint must use BedrockAgentCoreApp."""
        from bedrock_agentcore.runtime import BedrockAgentCoreApp

        assert isinstance(app, BedrockAgentCoreApp)

    def test_handler_is_async(self):
        """handler() must be async def (Req 4.1, 6.1)."""
        assert inspect.isasyncgenfunction(handler) or inspect.iscoroutinefunction(handler)

    def test_handler_context_type_annotation(self):
        """handler() must accept context: RequestContext."""
        from bedrock_agentcore import RequestContext

        sig = inspect.signature(handler)
        context_param = sig.parameters.get("context")
        assert context_param is not None
        assert context_param.annotation is RequestContext

    def test_main_block_calls_app_run(self):
        """main.py must call app.run() in __main__ block."""
        main_path = Path(__file__).parent.parent / "src" / "main.py"
        source = main_path.read_text()
        assert 'if __name__ == "__main__":' in source
        assert "app.run()" in source


class TestMakeEvent:
    """Verify _make_event() produces correct stream event format."""

    def test_returns_valid_json(self):
        result = _make_event("test_type", "pred-123", {"key": "value"})
        parsed = json.loads(result)
        assert parsed["type"] == "test_type"
        assert parsed["prediction_id"] == "pred-123"
        assert parsed["data"] == {"key": "value"}

    def test_has_exactly_three_keys(self):
        result = _make_event("error", "", {"message": "oops"})
        parsed = json.loads(result)
        assert set(parsed.keys()) == {"type", "prediction_id", "data"}


class TestPayloadValidation:
    """Verify error handling for missing/wrong payload keys.

    V4-3b: handler yields error stream events instead of returning JSON strings.
    """

    def test_empty_payload_yields_error_event(self):
        """Empty payload {} must yield an error stream event (Req 6.5)."""
        events = _collect_events({})
        assert len(events) == 1
        parsed = json.loads(events[0])
        assert parsed["type"] == "error"
        assert "message" in parsed["data"]

    def test_wrong_key_yields_error_event(self):
        """Payload with wrong key must yield an error stream event (Req 6.5)."""
        events = _collect_events({"message": "hi"})
        assert len(events) == 1
        parsed = json.loads(events[0])
        assert parsed["type"] == "error"

    def test_error_message_mentions_required_fields(self):
        """Error message should mention the expected fields (Req 6.5)."""
        events = _collect_events({"foo": "bar"})
        parsed = json.loads(events[0])
        msg = parsed["data"]["message"]
        assert "prediction_text" in msg or "prediction_id" in msg or "prompt" in msg
