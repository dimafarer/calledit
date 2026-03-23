"""Unit tests for V4-2 Built-in Tools wiring.

Tests verify tool configuration, system prompt content, and tool list.
All tests exercise pure logic (importable constants, list structure) — no
external service calls.

The one property test (test_agent_exception_returns_error_json) uses a
user-approved mock (Decision 96 exception) to verify the error handling path.

Updated for V4-3a:
- AWS_REGION removed from main.py (region from AWS CLI config, not hardcoded)
- SYSTEM_PROMPT renamed to SIMPLE_PROMPT_SYSTEM
- TOOLS list now has 3 elements (added current_time)
- handler() context parameter is now RequestContext, not dict

Updated for V4-3b:
- handler() is now async and yields stream events
- Tests use asyncio to collect yielded events
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, strategies as st
from strands_tools.browser import AgentCoreBrowser
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

# Add src to path so we can import main
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import (
    MODEL_ID,
    SIMPLE_PROMPT_SYSTEM,
    TOOLS,
    browser_tool,
    code_interpreter_tool,
    handler,
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


# ---------------------------------------------------------------------------
# Unit Tests (Task 4.1)
# ---------------------------------------------------------------------------


class TestToolWiring:
    """Verify both tools are wired into the TOOLS list correctly."""

    def test_tools_list_has_three_elements(self):
        """TOOLS list must contain 3 tool callables: browser, code_interpreter, current_time."""
        assert len(TOOLS) == 3

    def test_tools_are_callable(self):
        """Each element in TOOLS must be callable."""
        for tool in TOOLS:
            assert callable(tool)

    def test_browser_tool_is_agentcore_browser(self):
        """browser_tool must be an AgentCoreBrowser instance (Req 1.2)."""
        assert isinstance(browser_tool, AgentCoreBrowser)

    def test_code_interpreter_tool_is_agentcore_code_interpreter(self):
        """code_interpreter_tool must be an AgentCoreCodeInterpreter instance (Req 1.3)."""
        assert isinstance(code_interpreter_tool, AgentCoreCodeInterpreter)


class TestSystemPrompt:
    """Verify simple prompt mode system prompt describes available tools."""

    def test_system_prompt_mentions_browser(self):
        """SIMPLE_PROMPT_SYSTEM must describe Browser capability."""
        assert "Browser" in SIMPLE_PROMPT_SYSTEM

    def test_system_prompt_mentions_code_interpreter(self):
        """SIMPLE_PROMPT_SYSTEM must describe Code Interpreter capability."""
        assert "Code Interpreter" in SIMPLE_PROMPT_SYSTEM


class TestPayloadValidation:
    """Regression check — payload validation unchanged from V4-1."""

    def test_missing_prompt_returns_error(self):
        """Missing prompt key must yield an error stream event."""
        events = _collect_events({})
        assert len(events) == 1
        parsed = json.loads(events[0])
        assert parsed["type"] == "error"
        assert "message" in parsed["data"]


# ---------------------------------------------------------------------------
# Property Test (Task 4.2) — APPROVED MOCK EXCEPTION (Decision 96)
#
# This is the ONLY approved mock in v4. Approved because:
# (a) Testing real tool exceptions requires real AWS infrastructure
# (b) The property validates the handler's catch-all error path (pure logic)
# (c) User explicitly approved this mock
# ---------------------------------------------------------------------------


# Feature: builtin-tools, Property 1: Tool exceptions produce structured error responses
class TestPropertyToolExceptions:
    @settings(max_examples=100)
    @given(
        prompt=st.text(min_size=1),
        error_msg=st.text(min_size=1),
    )
    @patch("main.Agent")
    @patch("main.BedrockModel")
    def test_agent_exception_returns_error_json(
        self, mock_model_cls, mock_agent_cls, prompt, error_msg
    ):
        """For any exception during invocation, handler yields error event with 'error' key."""
        mock_agent = MagicMock()
        mock_agent.side_effect = Exception(error_msg)
        mock_agent_cls.return_value = mock_agent

        events = _collect_events({"prompt": prompt})

        assert len(events) == 1
        parsed = json.loads(events[0])
        assert parsed["type"] == "error"
        assert error_msg in parsed["data"]["message"]
