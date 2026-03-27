"""
Bedrock Prompt Management Client (v4)

Fetches versioned prompts from Bedrock Prompt Management.
Fallback behavior controlled by CALLEDIT_ENV (Decision 98):
- production: graceful fallback to hardcoded defaults, log warning
- any other value / unset: raise exception, fail clearly
"""

import os
import logging
from typing import Dict, Optional

import boto3

logger = logging.getLogger(__name__)

# v4 creation prompt identifiers — populated after CloudFormation deploy
# These are the 10-character Prompt IDs from the calledit-prompts stack
PROMPT_IDENTIFIERS: Dict[str, str] = {
    "prediction_parser": "GESWTI1IAB",
    "verification_planner": "ZTCOSG04KQ",
    "plan_reviewer": "6OOF6PHFRF",
}

# Default prompt versions — always pin to numbered versions, never DRAFT.
# DRAFT makes eval comparison impossible (Decision 128, Update 32).
# Update these when deploying new prompt versions.
DEFAULT_PROMPT_VERSIONS: Dict[str, str] = {
    "prediction_parser": "2",
    "verification_planner": "1",
    "plan_reviewer": "2",
}

# Hardcoded fallback prompts for production-only graceful degradation
_FALLBACK_PROMPTS: Dict[str, str] = {
    "prediction_parser": (
        "You are a prediction parser. Extract the prediction statement "
        "and resolve dates relative to {{current_date}}. Return JSON with "
        "statement, verification_date (ISO 8601), and date_reasoning."
    ),
    "verification_planner": (
        "You are a verification planner. Build a verification plan with "
        "sources, criteria, and steps. Available tools: {{tool_manifest}}"
    ),
    "plan_reviewer": (
        "You are a plan reviewer. Score verifiability (0.0-1.0) across "
        "5 dimensions and identify assumptions for clarification questions."
    ),
}

_prompt_version_manifest: Dict[str, str] = {}


def _get_bedrock_agent_client():
    """Create a bedrock-agent client for Prompt Management API."""
    return boto3.client("bedrock-agent")


def _is_production() -> bool:
    """Check if running in production mode (Decision 98)."""
    return os.environ.get("CALLEDIT_ENV") == "production"


def fetch_prompt(
    prompt_name: str,
    version: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """
    Fetch prompt text from Bedrock Prompt Management.

    Args:
        prompt_name: One of "prediction_parser", "verification_planner",
                     "plan_reviewer".
        version: Prompt version ("1", "2", ...) or "DRAFT".
                 Defaults to env var PROMPT_VERSION_{NAME} or "DRAFT".
        variables: Variable values to substitute (e.g., {"current_date": "..."}).

    Returns:
        Resolved prompt text string.

    Raises:
        Exception: In non-production mode, if Prompt Management fails.
    """
    prompt_id = PROMPT_IDENTIFIERS.get(prompt_name)
    if not prompt_id:
        msg = f"Unknown prompt name: {prompt_name}"
        if _is_production():
            logger.warning(msg)
            _prompt_version_manifest[prompt_name] = "fallback"
            return _resolve_variables(
                _FALLBACK_PROMPTS.get(prompt_name, ""), variables
            )
        raise ValueError(msg)

    if version is None:
        env_key = f"PROMPT_VERSION_{prompt_name.upper()}"
        version = os.environ.get(env_key, DEFAULT_PROMPT_VERSIONS.get(prompt_name, "1"))

    try:
        client = _get_bedrock_agent_client()
        kwargs = {"promptIdentifier": prompt_id}
        if version != "DRAFT":
            kwargs["promptVersion"] = version

        response = client.get_prompt(**kwargs)
        variants = response.get("variants", [])
        if not variants:
            raise ValueError(
                f"Prompt '{prompt_name}' ({prompt_id}) version {version} "
                f"has no variants"
            )

        prompt_text = (
            variants[0]
            .get("templateConfiguration", {})
            .get("text", {})
            .get("text", "")
        )
        if not prompt_text:
            raise ValueError(
                f"Prompt '{prompt_name}' ({prompt_id}) version {version} "
                f"has empty text"
            )

        actual_version = str(response.get("version", version))
        _prompt_version_manifest[prompt_name] = actual_version
        logger.info(
            f"Fetched prompt '{prompt_name}' version {actual_version} "
            f"({len(prompt_text)} chars)"
        )
        return _resolve_variables(prompt_text, variables)

    except Exception as e:
        if _is_production():
            logger.warning(
                f"Prompt Management fallback for '{prompt_name}': "
                f"{type(e).__name__}: {e}"
            )
            _prompt_version_manifest[prompt_name] = "fallback"
            return _resolve_variables(
                _FALLBACK_PROMPTS.get(prompt_name, ""), variables
            )
        raise


def _resolve_variables(
    text: str, variables: Optional[Dict[str, str]]
) -> str:
    """Replace {{variable_name}} placeholders in prompt text."""
    if not variables or not text:
        return text
    for name, value in variables.items():
        text = text.replace("{{" + name + "}}", value)
    return text


def get_prompt_version_manifest() -> Dict[str, str]:
    """Return the current prompt version manifest."""
    return dict(_prompt_version_manifest)


def reset_manifest():
    """Reset the version manifest. Used in tests."""
    global _prompt_version_manifest
    _prompt_version_manifest = {}
