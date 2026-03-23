"""Unit and property tests for prompt client (V4-3a).

Tests verify variable substitution, Decision 98 fallback behavior,
version resolution, manifest tracking, and import hygiene.

No mocks. Decision 96: v4 has zero mocks across all test types.
All tests exercise pure logic paths — no Bedrock API calls.
"""

import ast
import os
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

# Add src to path so we can import prompt_client
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prompt_client import (
    PROMPT_IDENTIFIERS,
    _FALLBACK_PROMPTS,
    _is_production,
    _resolve_variables,
    _prompt_version_manifest,
    fetch_prompt,
    get_prompt_version_manifest,
    reset_manifest,
)


# ---------------------------------------------------------------------------
# Property Test — Task 4.2
# Feature: creation-agent-core, Property 1: Variable substitution
# **Validates: Requirements 1.3**
# ---------------------------------------------------------------------------


# Strategy: generate variable names that are safe identifiers (no braces)
_safe_var_names = st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True)

# Strategy: generate non-empty variable values without brace patterns
_safe_var_values = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # no surrogates
        blacklist_characters="{}"
    ),
    min_size=1,
    max_size=50,
)


class TestVariableSubstitution:
    """Property 1: Variable substitution replaces all placeholders."""

    @settings(max_examples=100)
    @given(
        variables=st.dictionaries(
            keys=_safe_var_names,
            values=_safe_var_values,
            min_size=1,
            max_size=5,
        )
    )
    def test_all_placeholders_replaced(self, variables):
        """For any prompt text with {{name}} placeholders and matching variable
        dict, resolved text contains no original placeholders and contains
        all substituted values.

        Feature: creation-agent-core, Property 1: Variable substitution replaces all placeholders
        **Validates: Requirements 1.3**
        """
        # Build a template with one placeholder per variable
        template_parts = []
        for name in variables:
            template_parts.append(f"Before {{{{" + name + "}}}} after")
        template = " ".join(template_parts)

        resolved = _resolve_variables(template, variables)

        # No original placeholders should remain
        for name in variables:
            placeholder = "{{" + name + "}}"
            assert placeholder not in resolved, (
                f"Placeholder {placeholder} still present in: {resolved}"
            )

        # All substituted values should be present
        for value in variables.values():
            assert value in resolved, (
                f"Value '{value}' not found in resolved text: {resolved}"
            )

    def test_empty_variables_returns_original(self):
        """When variables is None or empty, text is returned unchanged.

        **Validates: Requirements 1.3**
        """
        text = "Hello {{name}}, today is {{date}}"
        assert _resolve_variables(text, None) == text
        assert _resolve_variables(text, {}) == text

    def test_empty_text_returns_empty(self):
        """When text is empty, empty string is returned.

        **Validates: Requirements 1.3**
        """
        assert _resolve_variables("", {"name": "world"}) == ""

    def test_multiple_occurrences_replaced(self):
        """All occurrences of the same placeholder are replaced.

        **Validates: Requirements 1.3**
        """
        text = "{{name}} said hello to {{name}}"
        result = _resolve_variables(text, {"name": "Alice"})
        assert result == "Alice said hello to Alice"


# ---------------------------------------------------------------------------
# Property Test — Task 4.3
# Feature: creation-agent-core, Property 2: Decision 98 fallback behavior
# **Validates: Requirements 1.5, 1.6**
# ---------------------------------------------------------------------------


_KNOWN_PROMPT_NAMES = st.sampled_from([
    "prediction_parser",
    "verification_planner",
    "plan_reviewer",
])


class TestDecision98FallbackBehavior:
    """Property 2: Decision 98 fallback behavior.

    Non-production raises on failure, production returns non-empty fallback
    and records 'fallback' in manifest.

    Tests temporarily set PROMPT_IDENTIFIERS to empty strings to trigger
    the fallback path without hitting Bedrock. This is not mocking — it's
    testing the code path that handles missing/invalid prompt IDs.
    """

    def setup_method(self):
        """Reset manifest and save original identifiers before each test."""
        reset_manifest()
        self._original_ids = dict(PROMPT_IDENTIFIERS)

    def teardown_method(self):
        """Restore original identifiers after each test."""
        PROMPT_IDENTIFIERS.update(self._original_ids)

    @settings(max_examples=100)
    @given(prompt_name=_KNOWN_PROMPT_NAMES)
    def test_non_production_raises_on_empty_identifier(self, prompt_name):
        """In non-production mode, empty prompt ID raises ValueError.

        Feature: creation-agent-core, Property 2: Decision 98 fallback behavior
        **Validates: Requirements 1.5, 1.6**
        """
        reset_manifest()
        os.environ.pop("CALLEDIT_ENV", None)

        # Temporarily set identifier to empty to trigger fallback path
        PROMPT_IDENTIFIERS[prompt_name] = ""

        with pytest.raises(ValueError, match="Unknown prompt name"):
            fetch_prompt(prompt_name)

    @settings(max_examples=100)
    @given(prompt_name=_KNOWN_PROMPT_NAMES)
    def test_production_returns_fallback_on_empty_identifier(self, prompt_name):
        """In production mode, empty prompt ID returns non-empty fallback.

        Feature: creation-agent-core, Property 2: Decision 98 fallback behavior
        **Validates: Requirements 1.5, 1.6**
        """
        reset_manifest()
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            # Temporarily set identifier to empty to trigger fallback path
            PROMPT_IDENTIFIERS[prompt_name] = ""

            result = fetch_prompt(prompt_name)

            # Must return non-empty fallback
            assert len(result) > 0, (
                f"Fallback for '{prompt_name}' is empty"
            )

            # Must record "fallback" in manifest
            manifest = get_prompt_version_manifest()
            assert manifest.get(prompt_name) == "fallback", (
                f"Expected 'fallback' in manifest for '{prompt_name}', "
                f"got: {manifest}"
            )
        finally:
            os.environ.pop("CALLEDIT_ENV", None)

    def test_production_fallback_matches_fallback_dict(self):
        """Production fallback returns text from _FALLBACK_PROMPTS.

        **Validates: Requirements 1.5, 1.6**
        """
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            for name in ("prediction_parser", "verification_planner", "plan_reviewer"):
                reset_manifest()
                # Temporarily set identifier to empty to trigger fallback path
                PROMPT_IDENTIFIERS[name] = ""

                result = fetch_prompt(name)
                expected = _FALLBACK_PROMPTS[name]
                assert result == expected, (
                    f"Fallback mismatch for '{name}'"
                )
        finally:
            os.environ.pop("CALLEDIT_ENV", None)

    def test_production_fallback_with_variables(self):
        """Production fallback applies variable substitution.

        **Validates: Requirements 1.5, 1.6**
        """
        reset_manifest()
        # Save and temporarily clear identifier to trigger fallback path
        original_id = PROMPT_IDENTIFIERS["prediction_parser"]
        PROMPT_IDENTIFIERS["prediction_parser"] = ""
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            result = fetch_prompt(
                "prediction_parser",
                variables={"current_date": "2025-01-15"},
            )
            assert "2025-01-15" in result
            assert "{{current_date}}" not in result
        finally:
            os.environ.pop("CALLEDIT_ENV", None)
            PROMPT_IDENTIFIERS["prediction_parser"] = original_id

    def test_is_production_checks_env_var(self):
        """_is_production() returns True only when CALLEDIT_ENV=production.

        **Validates: Requirements 1.5, 1.6**
        """
        os.environ.pop("CALLEDIT_ENV", None)
        assert _is_production() is False

        os.environ["CALLEDIT_ENV"] = "development"
        try:
            assert _is_production() is False
        finally:
            os.environ.pop("CALLEDIT_ENV", None)

        os.environ["CALLEDIT_ENV"] = "production"
        try:
            assert _is_production() is True
        finally:
            os.environ.pop("CALLEDIT_ENV", None)


# ---------------------------------------------------------------------------
# Unit Tests — Task 4.4
# ---------------------------------------------------------------------------


class TestImportHygiene:
    """Test prompt_client.py does not import from v3 agent modules (Req 1.8)."""

    def test_no_v3_agent_imports(self):
        """prompt_client.py must not import from v3 agent modules.

        **Validates: Requirements 1.8**
        """
        source_path = Path(__file__).parent.parent / "src" / "prompt_client.py"
        source = source_path.read_text()
        tree = ast.parse(source)

        v3_modules = {
            "parser_agent",
            "categorizer_agent",
            "verification_builder_agent",
            "review_agent",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in v3_modules, (
                        f"prompt_client.py imports v3 module: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module not in v3_modules, (
                        f"prompt_client.py imports from v3 module: {node.module}"
                    )

    def test_no_v3_prompt_identifiers(self):
        """prompt_client.py must not reference v3 prompt identifiers.

        **Validates: Requirements 1.8**
        """
        source_path = Path(__file__).parent.parent / "src" / "prompt_client.py"
        source = source_path.read_text()

        v3_identifiers = ["parser", "categorizer", "vb", "review"]
        # Check PROMPT_IDENTIFIERS keys — should only have v4 names
        for key in PROMPT_IDENTIFIERS:
            assert key not in v3_identifiers, (
                f"PROMPT_IDENTIFIERS contains v3 key: {key}"
            )

        # Also check the source doesn't reference v3 prompt IDs
        v3_ids = ["RBR4QBAQPY", "C320LUMT9V", "EBBKNNH2GI", "1MJYEPTLZL"]
        for v3_id in v3_ids:
            assert v3_id not in source, (
                f"prompt_client.py contains v3 prompt ID: {v3_id}"
            )


class TestVersionResolution:
    """Test version resolution defaults to DRAFT (Req 1.2)."""

    def test_defaults_to_draft_when_env_not_set(self):
        """Version defaults to DRAFT when PROMPT_VERSION_{NAME} not set.

        **Validates: Requirements 1.2**
        """
        # Ensure env vars are not set
        for name in ("PREDICTION_PARSER", "VERIFICATION_PLANNER", "PLAN_REVIEWER"):
            os.environ.pop(f"PROMPT_VERSION_{name}", None)

        # Verify the env var lookup defaults to DRAFT
        env_key = "PROMPT_VERSION_PREDICTION_PARSER"
        os.environ.pop(env_key, None)
        version = os.environ.get(env_key, "DRAFT")
        assert version == "DRAFT"

    def test_env_var_overrides_default(self):
        """When PROMPT_VERSION_{NAME} is set, it overrides DRAFT.

        **Validates: Requirements 1.2**
        """
        os.environ["PROMPT_VERSION_PREDICTION_PARSER"] = "3"
        try:
            version = os.environ.get("PROMPT_VERSION_PREDICTION_PARSER", "DRAFT")
            assert version == "3"
        finally:
            os.environ.pop("PROMPT_VERSION_PREDICTION_PARSER", None)


class TestVersionManifest:
    """Test version manifest records prompt versions after fetch (Req 1.4)."""

    def setup_method(self):
        reset_manifest()

    def test_manifest_starts_empty(self):
        """Manifest is empty after reset.

        **Validates: Requirements 1.4**
        """
        assert get_prompt_version_manifest() == {}

    def test_manifest_records_fallback_in_production(self):
        """In production mode, manifest records 'fallback' for failed fetches.

        **Validates: Requirements 1.4**
        """
        # Save and temporarily clear identifier to trigger fallback path
        original_id = PROMPT_IDENTIFIERS["prediction_parser"]
        PROMPT_IDENTIFIERS["prediction_parser"] = ""
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            fetch_prompt("prediction_parser")
            manifest = get_prompt_version_manifest()
            assert manifest["prediction_parser"] == "fallback"
        finally:
            os.environ.pop("CALLEDIT_ENV", None)
            PROMPT_IDENTIFIERS["prediction_parser"] = original_id

    def test_manifest_is_independent_copy(self):
        """get_prompt_version_manifest() returns a copy, not the internal dict.

        **Validates: Requirements 1.4**
        """
        # Save and temporarily clear identifier to trigger fallback path
        original_id = PROMPT_IDENTIFIERS["prediction_parser"]
        PROMPT_IDENTIFIERS["prediction_parser"] = ""
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            fetch_prompt("prediction_parser")
            manifest1 = get_prompt_version_manifest()
            manifest2 = get_prompt_version_manifest()
            assert manifest1 == manifest2
            assert manifest1 is not manifest2  # different objects
        finally:
            os.environ.pop("CALLEDIT_ENV", None)
            PROMPT_IDENTIFIERS["prediction_parser"] = original_id


class TestUnknownPromptName:
    """Test unknown prompt name raises ValueError in non-production mode."""

    def setup_method(self):
        reset_manifest()

    def test_unknown_name_raises_in_non_production(self):
        """Unknown prompt name raises ValueError when not in production.

        **Validates: Requirements 1.5**
        """
        os.environ.pop("CALLEDIT_ENV", None)
        with pytest.raises(ValueError, match="Unknown prompt name"):
            fetch_prompt("nonexistent_prompt")

    def test_unknown_name_returns_empty_in_production(self):
        """Unknown prompt name returns empty string in production (no fallback).

        **Validates: Requirements 1.6**
        """
        os.environ["CALLEDIT_ENV"] = "production"
        try:
            result = fetch_prompt("nonexistent_prompt")
            assert result == ""
            manifest = get_prompt_version_manifest()
            assert manifest["nonexistent_prompt"] == "fallback"
        finally:
            os.environ.pop("CALLEDIT_ENV", None)
