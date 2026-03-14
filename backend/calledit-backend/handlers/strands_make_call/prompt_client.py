"""
Bedrock Prompt Management Client

Fetches versioned prompts from Bedrock Prompt Management and provides
fallback to bundled hardcoded prompts if the API is unavailable.

API: bedrock-agent client → get_prompt(promptIdentifier, promptVersion)
Response: variants[0].templateConfiguration.text.text → prompt string

PROMPT IDENTIFIERS:
Each agent has a managed prompt in Bedrock Prompt Management:
- calledit-parser → Parser Agent system prompt
- calledit-categorizer → Categorizer Agent system prompt (has {{tool_manifest}} variable)
- calledit-vb → Verification Builder Agent system prompt
- calledit-review → Review Agent system prompt

VERSION NUMBERS:
Read from environment variables (PROMPT_VERSION_PARSER, etc.), defaulting
to "DRAFT" (the working draft). When a version is created via
create_prompt_version(), it gets an immutable numeric version (1, 2, 3...).

FALLBACK:
If the Bedrock API call fails, the client returns the bundled fallback
prompt (the current hardcoded constant from the agent module) and records
"fallback" in the version manifest. This ensures the Lambda always starts.

CACHING:
In production, fetch_prompt() is called during Lambda INIT (at agent
creation time). The fetched text is baked into the agent's system_prompt
attribute and cached by SnapStart. Warm invocations never call this API.
"""

import os
import logging
from typing import Dict, Optional

import boto3

logger = logging.getLogger(__name__)

# Prompt identifiers in Bedrock Prompt Management
# These are the 10-character IDs from the calledit-prompts CloudFormation stack
PROMPT_IDENTIFIERS = {
    "parser": "RBR4QBAQPY",
    "categorizer": "C320LUMT9V",
    "vb": "EBBKNNH2GI",
    "review": "1MJYEPTLZL",
}

# Bundled fallback prompts — current hardcoded constants from agent modules.
# These are the v1 prompts that will be migrated to Bedrock Prompt Management.
# Kept here as a safety net so the Lambda can always start.
_FALLBACK_PROMPTS: Optional[Dict[str, str]] = None


def _load_fallback_prompts() -> Dict[str, str]:
    """Lazy-load fallback prompts from agent modules to avoid circular imports."""
    global _FALLBACK_PROMPTS
    if _FALLBACK_PROMPTS is not None:
        return _FALLBACK_PROMPTS

    try:
        from parser_agent import PARSER_SYSTEM_PROMPT
        from categorizer_agent import CATEGORIZER_SYSTEM_PROMPT
        from verification_builder_agent import VERIFICATION_BUILDER_SYSTEM_PROMPT
        from review_agent import REVIEW_SYSTEM_PROMPT

        _FALLBACK_PROMPTS = {
            "parser": PARSER_SYSTEM_PROMPT,
            "categorizer": CATEGORIZER_SYSTEM_PROMPT,
            "vb": VERIFICATION_BUILDER_SYSTEM_PROMPT,
            "review": REVIEW_SYSTEM_PROMPT,
        }
    except ImportError as e:
        logger.error(f"Failed to load fallback prompts: {e}")
        _FALLBACK_PROMPTS = {}

    return _FALLBACK_PROMPTS


# Module-level state for version tracking
_prompt_version_manifest: Dict[str, str] = {}


def _get_bedrock_agent_client():
    """Create a bedrock-agent client for Prompt Management API."""
    region = os.environ.get("AWS_REGION", "us-west-2")
    return boto3.client("bedrock-agent", region_name=region)


def fetch_prompt(
    agent_name: str,
    version: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """
    Fetch prompt text from Bedrock Prompt Management.

    Args:
        agent_name: One of "parser", "categorizer", "vb", "review".
        version: Prompt version number (e.g., "1", "2") or "DRAFT".
                 Defaults to env var PROMPT_VERSION_{AGENT_NAME} or "DRAFT".
        variables: Optional dict of variable values to resolve in the prompt.
                   e.g., {"tool_manifest": "- web_search: ..."} for categorizer.

    Returns:
        Resolved prompt text string.
        Falls back to bundled hardcoded prompt on API failure.
    """
    prompt_id = PROMPT_IDENTIFIERS.get(agent_name)
    if not prompt_id:
        logger.error(f"Unknown agent name: {agent_name}")
        fallbacks = _load_fallback_prompts()
        return fallbacks.get(agent_name, "")

    # Resolve version from env var or parameter
    if version is None:
        env_key = f"PROMPT_VERSION_{agent_name.upper()}"
        version = os.environ.get(env_key, "DRAFT")

    try:
        client = _get_bedrock_agent_client()

        # Fetch the prompt from Bedrock Prompt Management
        kwargs = {"promptIdentifier": prompt_id}
        if version != "DRAFT":
            kwargs["promptVersion"] = version

        response = client.get_prompt(**kwargs)

        # Extract prompt text from the default variant
        variants = response.get("variants", [])
        if not variants:
            raise ValueError(f"Prompt {prompt_id} version {version} has no variants")

        variant = variants[0]
        template_config = variant.get("templateConfiguration", {})
        text_config = template_config.get("text", {})
        prompt_text = text_config.get("text", "")

        if not prompt_text:
            raise ValueError(f"Prompt {prompt_id} version {version} has empty text")

        # Resolve variables (e.g., {{tool_manifest}} for categorizer)
        if variables:
            for var_name, var_value in variables.items():
                prompt_text = prompt_text.replace("{{" + var_name + "}}", var_value)

        # Record the version in the manifest
        actual_version = response.get("version", version)
        _prompt_version_manifest[agent_name] = str(actual_version)

        logger.info(f"Fetched prompt '{prompt_id}' version {actual_version} ({len(prompt_text)} chars)")
        return prompt_text

    except Exception as e:
        logger.error(
            f"Prompt Management fallback for '{prompt_id}': {type(e).__name__}",
        )
        _prompt_version_manifest[agent_name] = "fallback"

        fallbacks = _load_fallback_prompts()
        prompt_text = fallbacks.get(agent_name, "")

        # Resolve variables on fallback too (categorizer needs tool_manifest)
        if variables and prompt_text:
            for var_name, var_value in variables.items():
                prompt_text = prompt_text.replace("{" + var_name + "}", var_value)

        return prompt_text


def get_prompt_version_manifest() -> Dict[str, str]:
    """
    Return the current prompt version manifest.

    Returns:
        Dict like {"parser": "3", "categorizer": "5", "vb": "2", "review": "4"}
        or {"parser": "fallback", ...} if API calls failed.
    """
    return dict(_prompt_version_manifest)


def reset_manifest():
    """Reset the version manifest. Used in tests."""
    global _prompt_version_manifest
    _prompt_version_manifest = {}
