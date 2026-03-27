"""
Bedrock Prompt Management Client — Verification Agent

Fetches versioned prompts from Bedrock Prompt Management.
No fallback prompts — if Prompt Management is unavailable, fail clearly.
This follows the AgentCore steering doc: no hardcoded prompt fallbacks.

Duplicated from calleditv4/src/prompt_client.py with verification-specific
config (Decision 106).
"""

import logging
import os
from typing import Dict, Optional

import boto3

logger = logging.getLogger(__name__)

# Verification prompt identifier — populated after CloudFormation deploy
PROMPT_IDENTIFIERS: Dict[str, str] = {
    "verification_executor": "ZQQNZIP6SK",
}

# Default prompt versions — always pin to numbered versions, never DRAFT.
# DRAFT makes eval comparison impossible (Decision 128, Update 32).
# Update these when deploying new prompt versions.
DEFAULT_PROMPT_VERSIONS: Dict[str, str] = {
    "verification_executor": "2",
}

_prompt_version_manifest: Dict[str, str] = {}


def _get_bedrock_agent_client():
    """Create a bedrock-agent client for Prompt Management API."""
    return boto3.client("bedrock-agent")


def fetch_prompt(
    prompt_name: str,
    version: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """Fetch prompt text from Bedrock Prompt Management.

    Args:
        prompt_name: "verification_executor"
        version: Prompt version or "DRAFT". Defaults to env var.
        variables: Variable values to substitute.

    Returns:
        Resolved prompt text string.

    Raises:
        Exception: Always raises on failure — no fallbacks.
    """
    prompt_id = PROMPT_IDENTIFIERS.get(prompt_name)
    if not prompt_id or prompt_id == "PLACEHOLDER":
        raise ValueError(
            f"Unknown or unconfigured prompt: {prompt_name}. "
            "Update PROMPT_IDENTIFIERS after CloudFormation deploy."
        )

    if version is None:
        env_key = f"PROMPT_VERSION_{prompt_name.upper()}"
        version = os.environ.get(env_key, DEFAULT_PROMPT_VERSIONS.get(prompt_name, "1"))

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
