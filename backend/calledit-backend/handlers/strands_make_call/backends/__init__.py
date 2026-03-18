"""Pluggable backend abstraction for the CalledIt eval framework.

Each backend is a Python module in this directory that implements:
  - run(prediction_text: str, tool_manifest: str) -> OutputContract
  - metadata() -> dict with name, description, model_config

Adding a new architecture (2-agent, 5-agent, swarm, etc.) means adding
a new module here. No changes to the eval runner, evaluators, or dashboard.

The OutputContract is the interface between backends and evaluators:
  - final_output: the pipeline's end result (what evaluators score)
  - agent_outputs: per-agent outputs, keys vary by backend
  - metadata: architecture info, model config, timing
"""

import importlib
import logging
import os
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


class OutputMetadata(TypedDict, total=False):
    """Metadata about the backend execution."""
    architecture: str       # Backend name (e.g., "serial", "single", "swarm")
    model_config: dict      # Agent/role name -> model ID mapping
    execution_time_ms: int  # Wall clock execution time
    # Backend-specific fields are allowed (e.g., collaboration_rounds for swarm)


class OutputContract(TypedDict, total=False):
    """The standard output shape all backends must return.

    - final_output: Required. The pipeline's end result containing at minimum
      prediction_statement, verifiable_category, and verification_method with criteria.
      This is what the primary evaluators (IntentPreservation, CriteriaMethodAlignment) score.

    - agent_outputs: Optional. Dict where keys are agent names and values are each
      agent's structured output. Keys vary by backend:
        Serial: parser, categorizer, verification_builder, review
        Single: agent
        Custom 2-agent: parser_categorizer, vb_review
      Per-agent evaluators only run when their target key exists.

    - metadata: Required. Architecture name, model config, execution time.
    """
    final_output: dict
    agent_outputs: Dict[str, Any]
    metadata: OutputMetadata


# Required fields in final_output — used for structural validation
REQUIRED_FINAL_OUTPUT_FIELDS = [
    "prediction_statement",
    "verifiable_category",
    "verification_method",
]


def validate_output_contract(output: dict) -> List[str]:
    """Validate that a backend's output conforms to the OutputContract.

    Returns a list of error messages. Empty list means valid.
    """
    errors = []

    if "final_output" not in output:
        errors.append("Missing required key: final_output")
        return errors  # Can't validate further without final_output

    final = output["final_output"]
    for field in REQUIRED_FINAL_OUTPUT_FIELDS:
        if field not in final:
            errors.append(f"final_output missing required field: {field}")

    # Check verification_method has criteria
    vm = final.get("verification_method", {})
    if isinstance(vm, dict) and "criteria" not in vm:
        errors.append("final_output.verification_method missing required field: criteria")

    if "metadata" not in output:
        errors.append("Missing required key: metadata")
    else:
        meta = output["metadata"]
        if "architecture" not in meta:
            errors.append("metadata missing required field: architecture")

    return errors


def discover_backends() -> Dict[str, Any]:
    """Discover all backend modules in this directory.

    Each backend module must implement:
      - run(prediction_text: str, tool_manifest: str) -> OutputContract
      - metadata() -> dict

    Modules missing either function are skipped with a warning.

    Returns:
        Dict mapping backend name -> module object
    """
    backends = {}
    backends_dir = os.path.dirname(__file__)

    for filename in sorted(os.listdir(backends_dir)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        module_name = filename[:-3]  # Strip .py
        try:
            mod = importlib.import_module(f"backends.{module_name}")
        except ImportError as e:
            logger.warning(f"Failed to import backend '{module_name}': {e}")
            continue

        # Validate the module has the required interface
        has_run = hasattr(mod, "run") and callable(mod.run)
        has_metadata = hasattr(mod, "metadata") and callable(mod.metadata)

        if not has_run or not has_metadata:
            missing = []
            if not has_run:
                missing.append("run()")
            if not has_metadata:
                missing.append("metadata()")
            logger.warning(
                f"Skipping backend '{module_name}': missing {', '.join(missing)}"
            )
            continue

        backends[module_name] = mod
        logger.debug(f"Discovered backend: {module_name}")

    return backends
