"""Serial backend — wraps the existing 4-agent sequential graph.

Pipeline: Parser → Categorizer → Verification Builder → ReviewAgent
Each agent is a Strands Agent node in a GraphBuilder graph.
This is the default backend for the eval framework.

Model is configurable via the model_id parameter to run() — defaults to
Sonnet 4 (matching production), but can be overridden for architecture
comparison experiments where all backends should use the same model.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default model — matches production deployment
DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Keys in the flat result dict that belong to each agent's output
PARSER_KEYS = [
    "prediction_statement", "prediction_date",
    "local_prediction_date", "date_reasoning",
]
CATEGORIZER_KEYS = [
    "verifiable_category", "category_reasoning",
]
VERIFICATION_BUILDER_KEYS = [
    "verification_method", "verification_date", "initial_status",
]
REVIEW_KEYS = [
    "reviewable_sections",
]


def metadata(model_id: Optional[str] = None) -> dict:
    """Return backend metadata for reports and discovery."""
    model = model_id or DEFAULT_MODEL
    return {
        "name": "serial",
        "description": (
            "4-agent sequential graph "
            "(Parser → Categorizer → Verification Builder → ReviewAgent)"
        ),
        "model_config": {
            "parser": model,
            "categorizer": model,
            "verification_builder": model,
            "review": model,
        },
    }


def _extract_agent_output(result: dict, keys: list) -> dict:
    """Extract a subset of keys from the flat result dict for one agent."""
    return {k: result[k] for k in keys if k in result}


def run(prediction_text: str, tool_manifest: str = "",
        model_id: Optional[str] = None) -> dict:
    """Execute the serial 4-agent graph and return an OutputContract.

    Args:
        prediction_text: The raw prediction to process.
        tool_manifest: Tool manifest string for the categorizer.
        model_id: Model to use for all agents. If None, uses DEFAULT_MODEL.
            Note: the serial backend currently wraps run_test_graph() which
            uses agents created by factory functions that read from Bedrock
            Prompt Management. The model_id override requires the factory
            functions to accept a model parameter — for now this is recorded
            in metadata but the actual agents use whatever model the factory
            functions specify. Full model override support is a future task.

    Returns:
        OutputContract dict with final_output, agent_outputs, and metadata.
    """
    from test_prediction_graph import run_test_graph

    model = model_id or DEFAULT_MODEL
    start_ms = int(time.time() * 1000)

    result = run_test_graph(
        prediction_text=prediction_text,
        tool_manifest=tool_manifest,
        model_id=model,
    )

    elapsed_ms = int(time.time() * 1000) - start_ms

    agent_outputs = {
        "parser": _extract_agent_output(result, PARSER_KEYS),
        "categorizer": _extract_agent_output(result, CATEGORIZER_KEYS),
        "verification_builder": _extract_agent_output(
            result, VERIFICATION_BUILDER_KEYS
        ),
        "review": _extract_agent_output(result, REVIEW_KEYS),
    }

    return {
        "final_output": result,
        "agent_outputs": agent_outputs,
        "metadata": {
            "architecture": "serial",
            "model_config": metadata(model)["model_config"],
            "execution_time_ms": elapsed_ms,
        },
    }
