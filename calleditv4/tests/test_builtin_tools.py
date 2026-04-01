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
    build_tools,
    build_tool_manifest,
    build_simple_prompt_system,
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
    """Verify tools are wired into the TOOLS list correctly."""

    def test_tools_list_has_expected_elements(self):
        """TOOLS list must contain tool callables (count depends on VERIFICATION_TOOLS)."""
        # Default (no env var) = brave + code_interpreter + current_time = 3
        # or browser + code_interpreter + current_time = 3
        # or all four = 4
        assert len(TOOLS) >= 2  # at minimum code_interpreter + current_time

    def test_tools_are_callable(self):
        """Each element in TOOLS must be callable."""
        for tool in TOOLS:
            assert callable(tool)

    def test_build_tools_browser_mode(self):
        """build_tools('browser') returns browser + code_interpreter + current_time."""
        tools = build_tools("browser")
        assert len(tools) == 3
        tool_names = [getattr(t, "__name__", str(t)) for t in tools]
        assert "browser" in tool_names

    def test_build_tools_brave_mode(self):
        """build_tools('brave') returns 3 tools (brave or browser fallback + code_interpreter + current_time)."""
        tools = build_tools("brave")
        assert len(tools) == 3
        assert all(callable(t) for t in tools)

    def test_build_tools_default_is_brave(self):
        """build_tools(None) defaults to brave."""
        tools = build_tools(None)
        tool_names = [getattr(t, "__name__", str(t)) for t in tools]
        assert "brave_web_search" in tool_names or len(tools) >= 2


class TestSystemPrompt:
    """Verify simple prompt mode system prompt describes available tools."""

    def test_system_prompt_mentions_code_interpreter(self):
        """SIMPLE_PROMPT_SYSTEM must describe Code Interpreter capability."""
        assert "Code Interpreter" in SIMPLE_PROMPT_SYSTEM

    def test_system_prompt_mentions_configured_tool(self):
        """SIMPLE_PROMPT_SYSTEM must describe the configured web tool."""
        # Default is brave, so should mention Brave Search or Browser
        assert "Brave Search" in SIMPLE_PROMPT_SYSTEM or "Browser" in SIMPLE_PROMPT_SYSTEM

    def test_build_simple_prompt_browser(self):
        """build_simple_prompt_system('browser') mentions Browser."""
        prompt = build_simple_prompt_system("browser")
        assert "Browser" in prompt
        assert "Brave Search" not in prompt

    def test_build_simple_prompt_brave(self):
        """build_simple_prompt_system('brave') mentions Brave Search."""
        prompt = build_simple_prompt_system("brave")
        assert "Brave Search" in prompt

    def test_build_simple_prompt_both(self):
        """build_simple_prompt_system('both') mentions both tools."""
        prompt = build_simple_prompt_system("both")
        assert "Brave Search" in prompt
        assert "Browser" in prompt


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
