"""
Golden Dataset Schema and Loader

Defines the data model for evaluation test cases and provides loading,
validation, and filtering functions.

SCHEMA:
- BasePrediction (Layer 1): Fully-specified, no clarification needed.
  Has expected per-agent outputs, difficulty, tool manifest config, optional rubric.
- FuzzyPrediction (Layer 2): Degraded version of a base prediction.
  Has simulated clarifications, expected topics, expected post-clarification outputs.
- GoldenDataset: Top-level container with schema_version.

VALIDATION:
- Schema version must be "1.0"
- All required fields present and correctly typed
- Fuzzy predictions must reference existing base prediction IDs
- Verifiability categories must be one of: auto_verifiable, automatable, human_only
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"auto_verifiable", "automatable", "human_only"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
SUPPORTED_SCHEMA_VERSION = "1.0"


@dataclass
class ExpectedAgentOutputs:
    """Expected outputs for each agent individually."""
    parser: Dict[str, Any] = field(default_factory=dict)
    categorizer: Dict[str, Any] = field(default_factory=dict)
    verification_builder: Dict[str, Any] = field(default_factory=dict)
    review: Optional[Dict[str, Any]] = None


@dataclass
class BasePrediction:
    """Layer 1: Fully-specified prediction requiring zero clarification."""
    id: str
    prediction_text: str
    difficulty: str  # "easy", "medium", "hard"
    tool_manifest_config: Dict[str, Any] = field(default_factory=dict)
    expected_per_agent_outputs: ExpectedAgentOutputs = field(default_factory=ExpectedAgentOutputs)
    evaluation_rubric: Optional[str] = None


@dataclass
class FuzzyPrediction:
    """Layer 2: Degraded prediction requiring clarification to converge."""
    id: str
    fuzzy_text: str
    base_prediction_id: str
    simulated_clarifications: List[str] = field(default_factory=list)
    expected_clarification_topics: List[str] = field(default_factory=list)
    expected_post_clarification_outputs: ExpectedAgentOutputs = field(default_factory=ExpectedAgentOutputs)
    evaluation_rubric: Optional[str] = None


@dataclass
class GoldenDataset:
    """Top-level dataset container."""
    schema_version: str = SUPPORTED_SCHEMA_VERSION
    base_predictions: List[BasePrediction] = field(default_factory=list)
    fuzzy_predictions: List[FuzzyPrediction] = field(default_factory=list)


def _parse_expected_outputs(data: dict) -> ExpectedAgentOutputs:
    """Parse an expected_per_agent_outputs dict into an ExpectedAgentOutputs."""
    return ExpectedAgentOutputs(
        parser=data.get("parser", {}),
        categorizer=data.get("categorizer", {}),
        verification_builder=data.get("verification_builder", {}),
        review=data.get("review"),
    )


def _validate_base_prediction(bp: dict, idx: int) -> BasePrediction:
    """Validate and parse a single base prediction dict."""
    bp_id = bp.get("id")
    if not bp_id or not isinstance(bp_id, str):
        raise ValueError(f"Base prediction [{idx}]: missing or invalid 'id'")

    text = bp.get("prediction_text")
    if not text or not isinstance(text, str):
        raise ValueError(f"Base prediction '{bp_id}': missing or invalid 'prediction_text'")

    difficulty = bp.get("difficulty", "medium")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"Base prediction '{bp_id}': invalid difficulty '{difficulty}', must be one of {VALID_DIFFICULTIES}")

    expected = bp.get("expected_per_agent_outputs", {})
    cat = expected.get("categorizer", {}).get("verifiable_category", "")
    if cat and cat not in VALID_CATEGORIES:
        raise ValueError(f"Base prediction '{bp_id}': invalid category '{cat}', must be one of {VALID_CATEGORIES}")

    return BasePrediction(
        id=bp_id,
        prediction_text=text,
        difficulty=difficulty,
        tool_manifest_config=bp.get("tool_manifest_config", {}),
        expected_per_agent_outputs=_parse_expected_outputs(expected),
        evaluation_rubric=bp.get("evaluation_rubric"),
    )


def _validate_fuzzy_prediction(fp: dict, idx: int, base_ids: set) -> FuzzyPrediction:
    """Validate and parse a single fuzzy prediction dict."""
    fp_id = fp.get("id")
    if not fp_id or not isinstance(fp_id, str):
        raise ValueError(f"Fuzzy prediction [{idx}]: missing or invalid 'id'")

    text = fp.get("fuzzy_text")
    if not text or not isinstance(text, str):
        raise ValueError(f"Fuzzy prediction '{fp_id}': missing or invalid 'fuzzy_text'")

    base_id = fp.get("base_prediction_id")
    if not base_id or base_id not in base_ids:
        raise ValueError(f"Fuzzy prediction '{fp_id}': base_prediction_id '{base_id}' not found in base predictions")

    clarifications = fp.get("simulated_clarifications", [])
    if not clarifications or not isinstance(clarifications, list):
        raise ValueError(f"Fuzzy prediction '{fp_id}': missing or empty 'simulated_clarifications'")

    topics = fp.get("expected_clarification_topics", [])
    if not topics or not isinstance(topics, list):
        raise ValueError(f"Fuzzy prediction '{fp_id}': missing or empty 'expected_clarification_topics'")

    expected = fp.get("expected_post_clarification_outputs", {})

    return FuzzyPrediction(
        id=fp_id,
        fuzzy_text=text,
        base_prediction_id=base_id,
        simulated_clarifications=clarifications,
        expected_clarification_topics=topics,
        expected_post_clarification_outputs=_parse_expected_outputs(expected),
        evaluation_rubric=fp.get("evaluation_rubric"),
    )


def load_golden_dataset(path: str = "eval/golden_dataset.json") -> GoldenDataset:
    """
    Load and validate the golden dataset from a JSON file.

    Validates:
    - schema_version is supported
    - All base predictions have required fields and valid types
    - All fuzzy predictions reference existing base prediction IDs
    - Verifiability categories are valid

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        Validated GoldenDataset object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If validation fails (with descriptive message).
    """
    with open(path, "r") as f:
        data = json.load(f)

    # Validate schema version
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema version '{version}', expected '{SUPPORTED_SCHEMA_VERSION}'"
        )

    # Parse and validate base predictions
    base_predictions = []
    for idx, bp in enumerate(data.get("base_predictions", [])):
        base_predictions.append(_validate_base_prediction(bp, idx))

    base_ids = {bp.id for bp in base_predictions}

    # Parse and validate fuzzy predictions (cross-reference base IDs)
    fuzzy_predictions = []
    for idx, fp in enumerate(data.get("fuzzy_predictions", [])):
        fuzzy_predictions.append(_validate_fuzzy_prediction(fp, idx, base_ids))

    dataset = GoldenDataset(
        schema_version=version,
        base_predictions=base_predictions,
        fuzzy_predictions=fuzzy_predictions,
    )

    logger.info(
        f"Loaded golden dataset v{version}: "
        f"{len(base_predictions)} base, {len(fuzzy_predictions)} fuzzy predictions"
    )
    return dataset


def filter_test_cases(
    dataset: GoldenDataset,
    name: Optional[str] = None,
    category: Optional[str] = None,
    layer: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> List[Union[BasePrediction, FuzzyPrediction]]:
    """
    Filter test cases by name, category, layer, or difficulty.

    Args:
        dataset: The loaded GoldenDataset.
        name: Filter by test case ID (substring match).
        category: Filter by expected verifiable_category.
        layer: Filter by layer — "base" or "fuzzy".
        difficulty: Filter by difficulty — "easy", "medium", "hard".

    Returns:
        List of matching BasePrediction and/or FuzzyPrediction objects.
    """
    results: List[Union[BasePrediction, FuzzyPrediction]] = []

    # Collect base predictions
    if layer is None or layer == "base":
        for bp in dataset.base_predictions:
            if name and name not in bp.id:
                continue
            if difficulty and bp.difficulty != difficulty:
                continue
            if category:
                expected_cat = bp.expected_per_agent_outputs.categorizer.get("verifiable_category", "")
                if expected_cat != category:
                    continue
            results.append(bp)

    # Collect fuzzy predictions
    if layer is None or layer == "fuzzy":
        for fp in dataset.fuzzy_predictions:
            if name and name not in fp.id:
                continue
            if category:
                expected_cat = fp.expected_post_clarification_outputs.categorizer.get("verifiable_category", "")
                if expected_cat != category:
                    continue
            # Fuzzy predictions don't have their own difficulty — use base prediction's
            if difficulty:
                base_bp = next((bp for bp in dataset.base_predictions if bp.id == fp.base_prediction_id), None)
                if base_bp and base_bp.difficulty != difficulty:
                    continue
            results.append(fp)

    return results


def dataset_to_dict(dataset: GoldenDataset) -> dict:
    """Serialize a GoldenDataset to a JSON-compatible dict. Used for round-trip testing."""
    return {
        "schema_version": dataset.schema_version,
        "base_predictions": [
            {
                "id": bp.id,
                "prediction_text": bp.prediction_text,
                "difficulty": bp.difficulty,
                "tool_manifest_config": bp.tool_manifest_config,
                "expected_per_agent_outputs": {
                    "parser": bp.expected_per_agent_outputs.parser,
                    "categorizer": bp.expected_per_agent_outputs.categorizer,
                    "verification_builder": bp.expected_per_agent_outputs.verification_builder,
                    "review": bp.expected_per_agent_outputs.review,
                },
                "evaluation_rubric": bp.evaluation_rubric,
            }
            for bp in dataset.base_predictions
        ],
        "fuzzy_predictions": [
            {
                "id": fp.id,
                "fuzzy_text": fp.fuzzy_text,
                "base_prediction_id": fp.base_prediction_id,
                "simulated_clarifications": fp.simulated_clarifications,
                "expected_clarification_topics": fp.expected_clarification_topics,
                "expected_post_clarification_outputs": {
                    "parser": fp.expected_post_clarification_outputs.parser,
                    "categorizer": fp.expected_post_clarification_outputs.categorizer,
                    "verification_builder": fp.expected_post_clarification_outputs.verification_builder,
                    "review": fp.expected_post_clarification_outputs.review,
                },
                "evaluation_rubric": fp.evaluation_rubric,
            }
            for fp in dataset.fuzzy_predictions
        ],
    }
