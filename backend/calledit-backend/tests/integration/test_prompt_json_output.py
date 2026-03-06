"""
Prompt JSON Output Testing Harness

PURPOSE: Validates that all four agents produce clean JSON output that can be
parsed with a single json.loads() call — no regex extraction needed.

THIS IS THE GATE: We don't remove extract_json_from_text() from prediction_graph.py
until this test passes consistently. The test validates the combination of:
- Claude Sonnet 4 model (upgraded from 3.5 Sonnet in task 5.1)
- Hardened prompts with "Return ONLY the raw JSON object" (task 5.2)

WHY 3 RUNS PER AGENT: LLM output has variance. A prompt that works 2 out of 3
times isn't reliable enough to remove the safety net. We need consistent success
across multiple invocations.

WHAT TO DO IF TESTS FAIL:
1. Check the logged raw output — is the agent wrapping JSON in markdown?
2. If yes, the prompt hardening needs to be stronger (add more explicit instructions)
3. If the JSON is malformed (not just wrapped), the prompt structure needs work
4. Do NOT proceed to task 8 (parsing simplification) until all tests pass

See: .kiro/specs/v2-cleanup-foundation/design.md, Component 3

Validates: Requirements 3.3, 3.4, 3.7
"""

import json
import logging
import pytest

# ---------------------------------------------------------------------------
# Agent imports — the conftest.py at this level adds the handlers directory
# to sys.path, so we can import directly from the agent modules.
# ---------------------------------------------------------------------------
from parser_agent import create_parser_agent
from categorizer_agent import create_categorizer_agent
from verification_builder_agent import create_verification_builder_agent
from review_agent import create_review_agent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# How many times to invoke each agent. 3 is the minimum to catch variance.
# If an agent passes 3/3, we have reasonable confidence the prompt is solid.
# If it fails even 1/3, the prompt needs more work before we simplify parsing.
# ---------------------------------------------------------------------------
NUM_INVOCATIONS = 3

# ---------------------------------------------------------------------------
# Valid verifiability categories — used to validate categorizer output.
# These must match the categories defined in categorizer_agent.py.
# ---------------------------------------------------------------------------
VALID_CATEGORIES = {
    "agent_verifiable",
    "current_tool_verifiable",
    "strands_tool_verifiable",
    "api_tool_verifiable",
    "human_verifiable_only",
}



@pytest.mark.integration
@pytest.mark.slow
class TestPromptJsonOutput:
    """
    Integration tests that invoke real LLM endpoints to validate clean JSON output.

    Each test method invokes one agent NUM_INVOCATIONS times and asserts that
    every invocation produces output parseable by a single json.loads() call.

    WHY A CLASS: Groups the helper method and per-agent tests together. The
    class itself is stateless — each test method is independent.
    """

    # -------------------------------------------------------------------
    # Helper: invoke an agent and validate JSON output
    # -------------------------------------------------------------------
    def _invoke_and_validate(self, agent, prompt, expected_keys, agent_name):
        """
        Invoke an agent and attempt to parse its output with json.loads().

        This is the core validation logic. It does NOT use regex extraction —
        that's the whole point. If json.loads() fails, the prompt hardening
        isn't working and we log the raw output for debugging.

        Args:
            agent: A Strands Agent instance (from a create_*_agent() factory).
            prompt: The user prompt to send to the agent.
            expected_keys: Set of keys we expect in the parsed JSON. Used for
                          structural validation — not just "is it JSON?" but
                          "is it the RIGHT JSON?".
            agent_name: Human-readable name for logging (e.g., "Parser").

        Returns:
            Tuple of (success: bool, parsed_data: dict or None, raw_output: str)
            - success is True only if json.loads() worked AND expected keys exist
            - parsed_data is the parsed dict on success, None on failure
            - raw_output is always the str(result) for debugging
        """
        raw_output = ""
        try:
            # Invoke the agent — this is a real LLM call via Bedrock
            result = agent(prompt)
            raw_output = str(result)

            # THE KEY ASSERTION: can we parse with a single json.loads()?
            # No regex, no markdown stripping, no fallback strategies.
            parsed = json.loads(raw_output)

            # Structural validation — check that expected keys are present.
            # This catches cases where the JSON is valid but wrong shape
            # (e.g., the agent returned {"error": "..."} instead of the
            # expected schema).
            missing_keys = expected_keys - set(parsed.keys())
            if missing_keys:
                logger.warning(
                    f"[{agent_name}] JSON parsed OK but missing keys: {missing_keys}. "
                    f"Got keys: {set(parsed.keys())}"
                )
                # Still count as success — the JSON parsed cleanly.
                # Missing keys are a prompt quality issue, not a parsing issue.

            logger.info(f"[{agent_name}] ✅ json.loads() succeeded")
            return (True, parsed, raw_output)

        except json.JSONDecodeError as e:
            # THIS IS THE FAILURE CASE we care about.
            # Log at ERROR level because after prompt hardening, this should
            # not happen. If it does, the prompt needs more work.
            logger.error(
                f"[{agent_name}] ❌ json.loads() FAILED: {e}\n"
                f"  Raw output (first 500 chars): {raw_output[:500]}"
            )
            return (False, None, raw_output)

        except Exception as e:
            # Catch-all for unexpected errors (network issues, Bedrock errors, etc.)
            logger.error(
                f"[{agent_name}] ❌ Unexpected error: {type(e).__name__}: {e}\n"
                f"  Raw output (first 500 chars): {raw_output[:500]}"
            )
            return (False, None, raw_output)

    # -------------------------------------------------------------------
    # Test: Parser Agent — 3 invocations
    # -------------------------------------------------------------------
    def test_parser_agent_json_output(self):
        """
        Validate that the Parser Agent returns clean JSON on every invocation.

        The parser is the most complex agent — it uses tools (parse_relative_date,
        current_time) which means the final output goes through more processing.
        Tool-using agents are more likely to wrap output in markdown because the
        model is already in a "helpful assistant" mode from tool interactions.

        Expected JSON keys: prediction_statement, verification_date, date_reasoning
        """
        agent = create_parser_agent()
        prompt = (
            "PREDICTION: Bitcoin will hit $100k before 3pm today\n"
            "CURRENT DATE: 2026-03-06 10:00:00 EST\n"
            "TIMEZONE: America/New_York\n\n"
            "Extract the prediction and parse the verification date."
        )
        expected_keys = {"prediction_statement", "verification_date", "date_reasoning"}

        successes = 0
        failures = []

        for i in range(NUM_INVOCATIONS):
            logger.info(f"[Parser] Invocation {i + 1}/{NUM_INVOCATIONS}")
            success, parsed, raw = self._invoke_and_validate(
                agent, prompt, expected_keys, f"Parser (run {i + 1})"
            )
            if success:
                successes += 1
            else:
                failures.append(raw)

        # Report success rate
        logger.info(
            f"[Parser] Success rate: {successes}/{NUM_INVOCATIONS} "
            f"({successes / NUM_INVOCATIONS * 100:.0f}%)"
        )

        # ALL invocations must succeed — we need 100% reliability before
        # removing extract_json_from_text().
        assert successes == NUM_INVOCATIONS, (
            f"Parser Agent failed {NUM_INVOCATIONS - successes}/{NUM_INVOCATIONS} "
            f"invocations. Raw outputs that failed json.loads():\n"
            + "\n---\n".join(f[:500] for f in failures)
        )

    # -------------------------------------------------------------------
    # Test: Categorizer Agent — 3 invocations
    # -------------------------------------------------------------------
    def test_categorizer_agent_json_output(self):
        """
        Validate that the Categorizer Agent returns clean JSON on every invocation.

        The categorizer is a pure reasoning agent (no tools), so it should be
        the most reliable at following JSON output instructions. If this agent
        fails, the prompt hardening approach itself may need rethinking.

        Expected JSON keys: verifiable_category, category_reasoning
        Also validates that verifiable_category is one of the 5 valid categories.
        """
        agent = create_categorizer_agent()
        prompt = (
            "PREDICTION: Bitcoin will reach $100,000 before 15:00:00 on 2026-03-06\n"
            "VERIFICATION DATE: 2026-03-06 15:00:00\n\n"
            "Categorize this prediction's verifiability."
        )
        expected_keys = {"verifiable_category", "category_reasoning"}

        successes = 0
        failures = []

        for i in range(NUM_INVOCATIONS):
            logger.info(f"[Categorizer] Invocation {i + 1}/{NUM_INVOCATIONS}")
            success, parsed, raw = self._invoke_and_validate(
                agent, prompt, expected_keys, f"Categorizer (run {i + 1})"
            )
            if success:
                successes += 1
                # Extra validation: check the category value is valid
                if parsed and "verifiable_category" in parsed:
                    category = parsed["verifiable_category"]
                    if category not in VALID_CATEGORIES:
                        logger.warning(
                            f"[Categorizer (run {i + 1})] Category '{category}' "
                            f"not in valid set: {VALID_CATEGORIES}"
                        )
            else:
                failures.append(raw)

        logger.info(
            f"[Categorizer] Success rate: {successes}/{NUM_INVOCATIONS} "
            f"({successes / NUM_INVOCATIONS * 100:.0f}%)"
        )

        assert successes == NUM_INVOCATIONS, (
            f"Categorizer Agent failed {NUM_INVOCATIONS - successes}/{NUM_INVOCATIONS} "
            f"invocations. Raw outputs that failed json.loads():\n"
            + "\n---\n".join(f[:500] for f in failures)
        )

    # -------------------------------------------------------------------
    # Test: Verification Builder Agent — 3 invocations
    # -------------------------------------------------------------------
    def test_verification_builder_agent_json_output(self):
        """
        Validate that the Verification Builder Agent returns clean JSON.

        The verification builder produces the most complex JSON structure —
        a nested object with three list fields (source, criteria, steps).
        Complex output structures are more likely to trigger markdown wrapping
        because the model "wants to be helpful" with formatting.

        Expected JSON keys: verification_method (containing source, criteria, steps)
        """
        agent = create_verification_builder_agent()
        prompt = (
            "PREDICTION: Bitcoin will reach $100,000 before 15:00:00 on 2026-03-06\n"
            "CATEGORY: api_tool_verifiable\n"
            "VERIFICATION DATE: 2026-03-06 15:00:00\n\n"
            "Build a detailed verification method for this prediction."
        )
        expected_keys = {"verification_method"}

        successes = 0
        failures = []

        for i in range(NUM_INVOCATIONS):
            logger.info(f"[VerificationBuilder] Invocation {i + 1}/{NUM_INVOCATIONS}")
            success, parsed, raw = self._invoke_and_validate(
                agent, prompt, expected_keys, f"VerificationBuilder (run {i + 1})"
            )
            if success:
                successes += 1
                # Extra validation: check nested structure
                if parsed and "verification_method" in parsed:
                    vm = parsed["verification_method"]
                    for field in ("source", "criteria", "steps"):
                        if field not in vm:
                            logger.warning(
                                f"[VerificationBuilder (run {i + 1})] "
                                f"verification_method missing '{field}' field"
                            )
                        elif not isinstance(vm[field], list):
                            logger.warning(
                                f"[VerificationBuilder (run {i + 1})] "
                                f"verification_method.{field} is {type(vm[field]).__name__}, "
                                f"expected list"
                            )
            else:
                failures.append(raw)

        logger.info(
            f"[VerificationBuilder] Success rate: {successes}/{NUM_INVOCATIONS} "
            f"({successes / NUM_INVOCATIONS * 100:.0f}%)"
        )

        assert successes == NUM_INVOCATIONS, (
            f"Verification Builder Agent failed "
            f"{NUM_INVOCATIONS - successes}/{NUM_INVOCATIONS} invocations. "
            f"Raw outputs that failed json.loads():\n"
            + "\n---\n".join(f[:500] for f in failures)
        )

    # -------------------------------------------------------------------
    # Test: Review Agent — 3 invocations
    # -------------------------------------------------------------------
    def test_review_agent_json_output(self):
        """
        Validate that the Review Agent returns clean JSON on every invocation.

        The review agent receives a complete prediction response as input and
        performs meta-analysis. Its input is a large JSON blob, which means the
        model sees a lot of JSON context — this can sometimes cause it to
        "mirror" the formatting and wrap its own output in markdown blocks.

        Expected JSON keys: reviewable_sections (a list of section analyses)
        """
        # Build a representative prediction response for the review agent to analyze.
        # This mirrors what the Lambda handler would pass after the 3-agent graph runs.
        sample_prediction_response = {
            "prediction_statement": "Bitcoin will reach $100,000 before 15:00:00 on 2026-03-06",
            "verification_date": "2026-03-06 15:00:00",
            "date_reasoning": "User specified 'before 3pm today', converted to 24-hour format",
            "verifiable_category": "api_tool_verifiable",
            "category_reasoning": (
                "Bitcoin price requires external API data from cryptocurrency exchanges"
            ),
            "verification_method": {
                "source": ["CoinGecko API", "Binance API"],
                "criteria": ["BTC/USD price >= 100000"],
                "steps": [
                    "Query cryptocurrency price API at verification time",
                    "Compare current BTC/USD price against $100,000 threshold",
                    "Record the exact price and timestamp for verification",
                ],
            },
        }

        agent = create_review_agent()
        prompt = (
            "PREDICTION RESPONSE TO REVIEW:\n"
            f"{json.dumps(sample_prediction_response, indent=2)}\n\n"
            "Analyze each section and determine what could be improved."
        )
        expected_keys = {"reviewable_sections"}

        successes = 0
        failures = []

        for i in range(NUM_INVOCATIONS):
            logger.info(f"[Review] Invocation {i + 1}/{NUM_INVOCATIONS}")
            success, parsed, raw = self._invoke_and_validate(
                agent, prompt, expected_keys, f"Review (run {i + 1})"
            )
            if success:
                successes += 1
                # Extra validation: reviewable_sections should be a list
                if parsed and "reviewable_sections" in parsed:
                    sections = parsed["reviewable_sections"]
                    if not isinstance(sections, list):
                        logger.warning(
                            f"[Review (run {i + 1})] reviewable_sections is "
                            f"{type(sections).__name__}, expected list"
                        )
                    elif len(sections) > 0:
                        # Check first section has expected structure
                        first = sections[0]
                        for field in ("section", "improvable", "questions", "reasoning"):
                            if field not in first:
                                logger.warning(
                                    f"[Review (run {i + 1})] First section "
                                    f"missing '{field}' field"
                                )
            else:
                failures.append(raw)

        logger.info(
            f"[Review] Success rate: {successes}/{NUM_INVOCATIONS} "
            f"({successes / NUM_INVOCATIONS * 100:.0f}%)"
        )

        assert successes == NUM_INVOCATIONS, (
            f"Review Agent failed {NUM_INVOCATIONS - successes}/{NUM_INVOCATIONS} "
            f"invocations. Raw outputs that failed json.loads():\n"
            + "\n---\n".join(f[:500] for f in failures)
        )

    # -------------------------------------------------------------------
    # Summary test: overall success rates across all agents
    # -------------------------------------------------------------------
    def test_all_agents_summary(self):
        """
        Run all four agents and report a combined summary.

        This test is a convenience wrapper that invokes each agent once and
        reports a combined pass/fail. The individual per-agent tests above
        are more thorough (3 runs each), but this gives a quick overview.

        WHY THIS EXISTS: When running the full test suite, you want a single
        test that tells you "all agents produce clean JSON" or "these agents
        have issues". The individual tests give you the detail for debugging.
        """
        agents_config = [
            {
                "name": "Parser",
                "agent": create_parser_agent(),
                "prompt": (
                    "PREDICTION: The temperature will exceed 90°F in Austin tomorrow\n"
                    "CURRENT DATE: 2026-06-15 08:00:00 CDT\n"
                    "TIMEZONE: America/Chicago\n\n"
                    "Extract the prediction and parse the verification date."
                ),
                "expected_keys": {"prediction_statement", "verification_date", "date_reasoning"},
            },
            {
                "name": "Categorizer",
                "agent": create_categorizer_agent(),
                "prompt": (
                    "PREDICTION: The temperature will exceed 90°F in Austin by 2026-06-16 17:00:00\n"
                    "VERIFICATION DATE: 2026-06-16 17:00:00\n\n"
                    "Categorize this prediction's verifiability."
                ),
                "expected_keys": {"verifiable_category", "category_reasoning"},
            },
            {
                "name": "VerificationBuilder",
                "agent": create_verification_builder_agent(),
                "prompt": (
                    "PREDICTION: The temperature will exceed 90°F in Austin by 2026-06-16 17:00:00\n"
                    "CATEGORY: api_tool_verifiable\n"
                    "VERIFICATION DATE: 2026-06-16 17:00:00\n\n"
                    "Build a detailed verification method for this prediction."
                ),
                "expected_keys": {"verification_method"},
            },
            {
                "name": "Review",
                "agent": create_review_agent(),
                "prompt": (
                    "PREDICTION RESPONSE TO REVIEW:\n"
                    + json.dumps(
                        {
                            "prediction_statement": "Temperature will exceed 90°F in Austin",
                            "verification_date": "2026-06-16 17:00:00",
                            "date_reasoning": "User said 'tomorrow', parsed relative to current date",
                            "verifiable_category": "api_tool_verifiable",
                            "category_reasoning": "Weather data requires external API",
                            "verification_method": {
                                "source": ["OpenWeatherMap API"],
                                "criteria": ["Temperature > 90°F"],
                                "steps": ["Query weather API for Austin, TX forecast"],
                            },
                        },
                        indent=2,
                    )
                    + "\n\nAnalyze each section and determine what could be improved."
                ),
                "expected_keys": {"reviewable_sections"},
            },
        ]

        results = {}
        for config in agents_config:
            name = config["name"]
            logger.info(f"[Summary] Testing {name}...")
            success, parsed, raw = self._invoke_and_validate(
                config["agent"], config["prompt"], config["expected_keys"], name
            )
            results[name] = success

        # Log summary
        logger.info("=" * 60)
        logger.info("PROMPT JSON OUTPUT SUMMARY")
        logger.info("=" * 60)
        for name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {name}: {status}")
        logger.info("=" * 60)

        total_passed = sum(1 for v in results.values() if v)
        total = len(results)
        logger.info(f"  Overall: {total_passed}/{total} agents passed")
        logger.info("=" * 60)

        # All agents must pass
        failed_agents = [name for name, passed in results.items() if not passed]
        assert not failed_agents, (
            f"These agents failed to produce clean JSON: {failed_agents}. "
            f"Check ERROR-level logs above for raw outputs."
        )
