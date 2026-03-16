"""
Golden Dataset V2 Schema and Loader

Defines the v2 data model for evaluation test cases with ground truth metadata,
dimension tags, fuzziness levels, and dataset versioning. Provides loading,
validation, serialization, and filtering functions.

SCHEMA V2:
- GroundTruthMetadata: WHY a prediction has its expected category.
- DimensionTags: 5-axis classification for coverage analysis.
- DatasetMetadata: Optional integrity checking counts.
- BasePrediction (v2): Ground truth, dimension tags, boundary cases.
- FuzzyPrediction (v2): Fuzziness levels 0-3.
- GoldenDataset (v2): dataset_version, metadata, schema 2.0 only.

VALIDATION:
- Schema version must be "2.0" (v1 not supported — clean break)
- All ground truth fields present and correctly typed
- Fuzziness levels in {0, 1, 2, 3}
- expected_category required on every prediction
- Fuzzy base_prediction_id references must resolve
- Count integrity against metadata if present
- dataset_version required and non-empty
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

# --- Constants ---

SUPPORTED_SCHEMA_VERSION = "3.0"
VALID_CATEGORIES = {"auto_verifiable", "automatable", "human_only"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_OBJECTIVITY = {"objective", "subjective", "mixed"}
VALID_STAKES = {"life-changing", "significant", "moderate", "trivial"}
VALID_TIME_HORIZONS = {"minutes-to-hours", "days", "weeks-to-months", "months-to-years"}
VALID_FUZZINESS_LEVELS = {0, 1, 2, 3}


# --- Dataclasses ---


@dataclass
class GroundTruthMetadata:
    """WHY a prediction has its expected category — the stable foundation."""
    verifiability_reasoning: str
    date_derivation: str
    verification_sources: List[str]
    objectivity_assessment: str
    verification_criteria: List[str]
    verification_steps: List[str]
    verification_timing: str  # WHEN to verify: "immediate", "after_event", "scheduled_prompt", etc.
    # V3: verification-centric eval fields
    expected_verification_criteria: List[str] = field(default_factory=list)  # checkable true/false conditions
    expected_verification_method: str = ""  # approach for proving true/false


@dataclass
class DimensionTags:
    """5-axis classification for cross-section coverage analysis."""
    domain: str
    stakes: str
    time_horizon: str
    persona: str


@dataclass
class DatasetMetadata:
    """Optional metadata for integrity checking."""
    expected_base_count: Optional[int] = None
    expected_fuzzy_count: Optional[int] = None


@dataclass
class BasePrediction:
    """V2 base prediction with ground truth metadata and dimension tags."""
    id: str
    prediction_text: str
    difficulty: str  # "easy", "medium", "hard"
    ground_truth: GroundTruthMetadata
    dimension_tags: DimensionTags
    tool_manifest_config: Dict[str, Any] = field(default_factory=dict)
    expected_per_agent_outputs: Dict[str, Any] = field(default_factory=dict)
    evaluation_rubric: Optional[str] = None
    is_boundary_case: bool = False
    boundary_description: Optional[str] = None


@dataclass
class FuzzyPrediction:
    """V2 fuzzy prediction with fuzziness level."""
    id: str
    fuzzy_text: str
    base_prediction_id: str
    fuzziness_level: int  # 0, 1, 2, or 3
    simulated_clarifications: List[str] = field(default_factory=list)
    expected_clarification_topics: List[str] = field(default_factory=list)
    expected_post_clarification_outputs: Dict[str, Any] = field(default_factory=dict)
    evaluation_rubric: Optional[str] = None


@dataclass
class GoldenDataset:
    """V2 top-level dataset container."""
    schema_version: str = SUPPORTED_SCHEMA_VERSION
    dataset_version: str = ""
    base_predictions: List[BasePrediction] = field(default_factory=list)
    fuzzy_predictions: List[FuzzyPrediction] = field(default_factory=list)
    metadata: Optional[DatasetMetadata] = None


# --- Internal validation helpers ---


def _validate_ground_truth(gt_data: dict, prediction_id: str) -> GroundTruthMetadata:
    """Validate and parse ground truth metadata for a base prediction."""
    if not isinstance(gt_data, dict):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth' must be a dict"
        )

    # verifiability_reasoning
    vr = gt_data.get("verifiability_reasoning")
    if not vr or not isinstance(vr, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.verifiability_reasoning' "
            f"must be a non-empty string"
        )

    # date_derivation
    dd = gt_data.get("date_derivation")
    if not dd or not isinstance(dd, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.date_derivation' "
            f"must be a non-empty string"
        )

    # verification_sources
    vs = gt_data.get("verification_sources")
    if not vs or not isinstance(vs, list) or not all(isinstance(s, str) for s in vs):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.verification_sources' "
            f"must be a non-empty list of strings"
        )

    # objectivity_assessment
    oa = gt_data.get("objectivity_assessment")
    if oa not in VALID_OBJECTIVITY:
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.objectivity_assessment' "
            f"must be one of {VALID_OBJECTIVITY}, got '{oa}'"
        )

    # verification_criteria
    vc = gt_data.get("verification_criteria")
    if not vc or not isinstance(vc, list) or not all(isinstance(c, str) for c in vc):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.verification_criteria' "
            f"must be a non-empty list of strings"
        )

    # verification_steps
    vsteps = gt_data.get("verification_steps")
    if not vsteps or not isinstance(vsteps, list) or not all(isinstance(s, str) for s in vsteps):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.verification_steps' "
            f"must be a non-empty list of strings"
        )

    # verification_timing
    vtiming = gt_data.get("verification_timing")
    if not vtiming or not isinstance(vtiming, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.verification_timing' "
            f"must be a non-empty string"
        )

    # V3: expected_verification_criteria
    evc = gt_data.get("expected_verification_criteria")
    if not evc or not isinstance(evc, list) or not all(isinstance(c, str) and c for c in evc):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.expected_verification_criteria' "
            f"must be a non-empty list of non-empty strings"
        )

    # V3: expected_verification_method
    evm = gt_data.get("expected_verification_method")
    if not evm or not isinstance(evm, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'ground_truth.expected_verification_method' "
            f"must be a non-empty string"
        )

    return GroundTruthMetadata(
        verifiability_reasoning=vr,
        date_derivation=dd,
        verification_sources=vs,
        objectivity_assessment=oa,
        verification_criteria=vc,
        verification_steps=vsteps,
        verification_timing=vtiming,
        expected_verification_criteria=evc,
        expected_verification_method=evm,
    )


def _validate_dimension_tags(dt_data: dict, prediction_id: str) -> DimensionTags:
    """Validate and parse dimension tags for a base prediction."""
    if not isinstance(dt_data, dict):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'dimension_tags' must be a dict"
        )

    domain = dt_data.get("domain")
    if not domain or not isinstance(domain, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'dimension_tags.domain' "
            f"must be a non-empty string"
        )

    stakes = dt_data.get("stakes")
    if stakes not in VALID_STAKES:
        raise ValueError(
            f"Base prediction '{prediction_id}': 'dimension_tags.stakes' "
            f"must be one of {VALID_STAKES}, got '{stakes}'"
        )

    time_horizon = dt_data.get("time_horizon")
    if time_horizon not in VALID_TIME_HORIZONS:
        raise ValueError(
            f"Base prediction '{prediction_id}': 'dimension_tags.time_horizon' "
            f"must be one of {VALID_TIME_HORIZONS}, got '{time_horizon}'"
        )

    persona = dt_data.get("persona")
    if not persona or not isinstance(persona, str):
        raise ValueError(
            f"Base prediction '{prediction_id}': 'dimension_tags.persona' "
            f"must be a non-empty string"
        )

    return DimensionTags(
        domain=domain,
        stakes=stakes,
        time_horizon=time_horizon,
        persona=persona,
    )


def _validate_base_prediction(bp: dict, idx: int) -> BasePrediction:
    """Validate and parse a single v2 base prediction dict."""
    bp_id = bp.get("id")
    if not bp_id or not isinstance(bp_id, str):
        raise ValueError(f"Base prediction [{idx}]: missing or invalid 'id'")

    text = bp.get("prediction_text")
    if not text or not isinstance(text, str):
        raise ValueError(f"Base prediction '{bp_id}': missing or invalid 'prediction_text'")

    difficulty = bp.get("difficulty", "medium")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"Base prediction '{bp_id}': invalid difficulty '{difficulty}', "
            f"must be one of {VALID_DIFFICULTIES}"
        )

    # Ground truth — required for v2
    gt_data = bp.get("ground_truth")
    if gt_data is None:
        raise ValueError(f"Base prediction '{bp_id}': missing required 'ground_truth'")
    ground_truth = _validate_ground_truth(gt_data, bp_id)

    # Dimension tags — required for v2
    dt_data = bp.get("dimension_tags")
    if dt_data is None:
        raise ValueError(f"Base prediction '{bp_id}': missing required 'dimension_tags'")
    dimension_tags = _validate_dimension_tags(dt_data, bp_id)

    # expected_category — required in expected_per_agent_outputs.categorizer
    expected = bp.get("expected_per_agent_outputs", {})
    cat_data = expected.get("categorizer", {})
    expected_category = cat_data.get("expected_category")
    if expected_category not in VALID_CATEGORIES:
        raise ValueError(
            f"Base prediction '{bp_id}': "
            f"'expected_per_agent_outputs.categorizer.expected_category' "
            f"must be one of {VALID_CATEGORIES}, got '{expected_category}'"
        )

    # Boundary case validation
    is_boundary = bp.get("is_boundary_case", False)
    boundary_desc = bp.get("boundary_description")
    if is_boundary and (not boundary_desc or not isinstance(boundary_desc, str)):
        raise ValueError(
            f"Base prediction '{bp_id}': 'boundary_description' must be a "
            f"non-empty string when 'is_boundary_case' is True"
        )

    return BasePrediction(
        id=bp_id,
        prediction_text=text,
        difficulty=difficulty,
        ground_truth=ground_truth,
        dimension_tags=dimension_tags,
        tool_manifest_config=bp.get("tool_manifest_config", {}),
        expected_per_agent_outputs=expected,
        evaluation_rubric=bp.get("evaluation_rubric"),
        is_boundary_case=is_boundary,
        boundary_description=boundary_desc,
    )


def _validate_fuzzy_prediction(
    fp: dict, idx: int, base_ids: set
) -> FuzzyPrediction:
    """Validate and parse a single v2 fuzzy prediction dict."""
    fp_id = fp.get("id")
    if not fp_id or not isinstance(fp_id, str):
        raise ValueError(f"Fuzzy prediction [{idx}]: missing or invalid 'id'")

    text = fp.get("fuzzy_text")
    if not text or not isinstance(text, str):
        raise ValueError(f"Fuzzy prediction '{fp_id}': missing or invalid 'fuzzy_text'")

    base_id = fp.get("base_prediction_id")
    if not base_id or base_id not in base_ids:
        raise ValueError(
            f"Fuzzy prediction '{fp_id}': base_prediction_id '{base_id}' "
            f"not found in base predictions"
        )

    # fuzziness_level — required, must be 0-3
    fuzziness_level = fp.get("fuzziness_level")
    if fuzziness_level not in VALID_FUZZINESS_LEVELS:
        raise ValueError(
            f"Fuzzy prediction '{fp_id}': 'fuzziness_level' must be one of "
            f"{VALID_FUZZINESS_LEVELS}, got '{fuzziness_level}'"
        )

    clarifications = fp.get("simulated_clarifications", [])
    if fuzziness_level == 0:
        # Level 0 = control case, empty clarifications allowed
        if not isinstance(clarifications, list):
            raise ValueError(
                f"Fuzzy prediction '{fp_id}': 'simulated_clarifications' must be a list"
            )
    else:
        if not clarifications or not isinstance(clarifications, list):
            raise ValueError(
                f"Fuzzy prediction '{fp_id}': missing or empty 'simulated_clarifications'"
            )

    topics = fp.get("expected_clarification_topics", [])
    if fuzziness_level == 0:
        # Level 0 = control case, empty topics allowed
        if not isinstance(topics, list):
            raise ValueError(
                f"Fuzzy prediction '{fp_id}': 'expected_clarification_topics' must be a list"
            )
    else:
        if not topics or not isinstance(topics, list):
            raise ValueError(
                f"Fuzzy prediction '{fp_id}': missing or empty 'expected_clarification_topics'"
            )

    # expected_category — required in expected_post_clarification_outputs.categorizer
    expected = fp.get("expected_post_clarification_outputs", {})
    cat_data = expected.get("categorizer", {})
    expected_category = cat_data.get("expected_category")
    if expected_category not in VALID_CATEGORIES:
        raise ValueError(
            f"Fuzzy prediction '{fp_id}': "
            f"'expected_post_clarification_outputs.categorizer.expected_category' "
            f"must be one of {VALID_CATEGORIES}, got '{expected_category}'"
        )

    return FuzzyPrediction(
        id=fp_id,
        fuzzy_text=text,
        base_prediction_id=base_id,
        fuzziness_level=fuzziness_level,
        simulated_clarifications=clarifications,
        expected_clarification_topics=topics,
        expected_post_clarification_outputs=expected,
        evaluation_rubric=fp.get("evaluation_rubric"),
    )


# --- Public API ---


def load_golden_dataset(path: str = "eval/golden_dataset.json") -> GoldenDataset:
    """Load and validate golden dataset. Only supports schema version 2.0.

    Validates:
    - schema_version is "2.0"
    - dataset_version is present and non-empty
    - All base predictions have required v2 fields (ground_truth, dimension_tags)
    - All ground truth fields present and correctly typed
    - All fuzzy predictions have valid fuzziness_level and reference existing base IDs
    - expected_category present on every base and fuzzy prediction
    - Count integrity against metadata if present

    Args:
        path: Path to the golden dataset JSON file.

    Returns:
        Validated GoldenDataset object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If validation fails.
    """
    with open(path, "r") as f:
        data = json.load(f)

    # Validate schema version — v2 only
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema version '{version}', "
            f"expected '{SUPPORTED_SCHEMA_VERSION}'. "
            f"V1/V2 datasets must be migrated to v3 schema."
        )

    # Validate dataset_version
    dataset_version = data.get("dataset_version")
    if not dataset_version or not isinstance(dataset_version, str):
        raise ValueError(
            "Missing or empty 'dataset_version' — required for v2 schema."
        )

    # Parse and validate base predictions
    base_predictions = []
    for idx, bp in enumerate(data.get("base_predictions", [])):
        base_predictions.append(_validate_base_prediction(bp, idx))

    base_ids = {bp.id for bp in base_predictions}

    # Check for duplicate base IDs
    raw_base_ids = [bp.get("id") for bp in data.get("base_predictions", [])]
    if len(raw_base_ids) != len(set(raw_base_ids)):
        seen = set()
        dupes = []
        for bid in raw_base_ids:
            if bid in seen:
                dupes.append(bid)
            seen.add(bid)
        raise ValueError(f"Duplicate base prediction IDs: {dupes}")

    # Parse and validate fuzzy predictions
    fuzzy_predictions = []
    for idx, fp in enumerate(data.get("fuzzy_predictions", [])):
        fuzzy_predictions.append(_validate_fuzzy_prediction(fp, idx, base_ids))

    # Check for duplicate fuzzy IDs
    raw_fuzzy_ids = [fp.get("id") for fp in data.get("fuzzy_predictions", [])]
    if len(raw_fuzzy_ids) != len(set(raw_fuzzy_ids)):
        seen = set()
        dupes = []
        for fid in raw_fuzzy_ids:
            if fid in seen:
                dupes.append(fid)
            seen.add(fid)
        raise ValueError(f"Duplicate fuzzy prediction IDs: {dupes}")

    # Check base/fuzzy ID namespace collisions
    collisions = base_ids & set(raw_fuzzy_ids)
    if collisions:
        raise ValueError(f"ID collision between base and fuzzy predictions: {collisions}")

    # Parse metadata and check count integrity
    metadata = None
    meta_data = data.get("metadata")
    if meta_data and isinstance(meta_data, dict):
        expected_base = meta_data.get("expected_base_count")
        expected_fuzzy = meta_data.get("expected_fuzzy_count")
        metadata = DatasetMetadata(
            expected_base_count=expected_base,
            expected_fuzzy_count=expected_fuzzy,
        )
        if expected_base is not None and len(base_predictions) != expected_base:
            raise ValueError(
                f"Count mismatch: metadata.expected_base_count={expected_base}, "
                f"actual base predictions={len(base_predictions)}"
            )
        if expected_fuzzy is not None and len(fuzzy_predictions) != expected_fuzzy:
            raise ValueError(
                f"Count mismatch: metadata.expected_fuzzy_count={expected_fuzzy}, "
                f"actual fuzzy predictions={len(fuzzy_predictions)}"
            )

    dataset = GoldenDataset(
        schema_version=version,
        dataset_version=dataset_version,
        base_predictions=base_predictions,
        fuzzy_predictions=fuzzy_predictions,
        metadata=metadata,
    )

    logger.info(
        f"Loaded golden dataset v{version} (dataset {dataset_version}): "
        f"{len(base_predictions)} base, {len(fuzzy_predictions)} fuzzy predictions"
    )
    return dataset


def dataset_to_dict(dataset: GoldenDataset) -> dict:
    """Serialize GoldenDataset to JSON-compatible dict. V2 only."""
    result = {
        "schema_version": dataset.schema_version,
        "dataset_version": dataset.dataset_version,
        "base_predictions": [_serialize_base(bp) for bp in dataset.base_predictions],
        "fuzzy_predictions": [_serialize_fuzzy(fp) for fp in dataset.fuzzy_predictions],
    }
    if dataset.metadata:
        result["metadata"] = {
            "expected_base_count": dataset.metadata.expected_base_count,
            "expected_fuzzy_count": dataset.metadata.expected_fuzzy_count,
        }
    return result


def _serialize_base(bp: BasePrediction) -> dict:
    """Serialize a single v2 base prediction."""
    d = {
        "id": bp.id,
        "prediction_text": bp.prediction_text,
        "difficulty": bp.difficulty,
        "ground_truth": {
            "verifiability_reasoning": bp.ground_truth.verifiability_reasoning,
            "date_derivation": bp.ground_truth.date_derivation,
            "verification_sources": bp.ground_truth.verification_sources,
            "objectivity_assessment": bp.ground_truth.objectivity_assessment,
            "verification_criteria": bp.ground_truth.verification_criteria,
            "verification_steps": bp.ground_truth.verification_steps,
            "verification_timing": bp.ground_truth.verification_timing,
            "expected_verification_criteria": bp.ground_truth.expected_verification_criteria,
            "expected_verification_method": bp.ground_truth.expected_verification_method,
        },
        "dimension_tags": {
            "domain": bp.dimension_tags.domain,
            "stakes": bp.dimension_tags.stakes,
            "time_horizon": bp.dimension_tags.time_horizon,
            "persona": bp.dimension_tags.persona,
        },
        "tool_manifest_config": bp.tool_manifest_config,
        "expected_per_agent_outputs": bp.expected_per_agent_outputs,
        "evaluation_rubric": bp.evaluation_rubric,
        "is_boundary_case": bp.is_boundary_case,
        "boundary_description": bp.boundary_description,
    }
    return d


def _serialize_fuzzy(fp: FuzzyPrediction) -> dict:
    """Serialize a single v2 fuzzy prediction."""
    return {
        "id": fp.id,
        "fuzzy_text": fp.fuzzy_text,
        "base_prediction_id": fp.base_prediction_id,
        "fuzziness_level": fp.fuzziness_level,
        "simulated_clarifications": fp.simulated_clarifications,
        "expected_clarification_topics": fp.expected_clarification_topics,
        "expected_post_clarification_outputs": fp.expected_post_clarification_outputs,
        "evaluation_rubric": fp.evaluation_rubric,
    }


def filter_test_cases(
    dataset: GoldenDataset,
    name: Optional[str] = None,
    category: Optional[str] = None,
    layer: Optional[str] = None,
    difficulty: Optional[str] = None,
    fuzziness_level: Optional[int] = None,
) -> List[Union[BasePrediction, FuzzyPrediction]]:
    """Filter test cases by name, category, layer, difficulty, or fuzziness_level.

    Args:
        dataset: The loaded GoldenDataset.
        name: Filter by test case ID (substring match).
        category: Filter by expected_category.
        layer: Filter by layer — "base" or "fuzzy".
        difficulty: Filter by difficulty — "easy", "medium", "hard".
        fuzziness_level: Filter fuzzy predictions by fuzziness level (0-3).

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
                expected_cat = bp.expected_per_agent_outputs.get(
                    "categorizer", {}
                ).get("expected_category", "")
                if expected_cat != category:
                    continue
            # fuzziness_level filter only applies to fuzzy predictions
            if fuzziness_level is not None:
                continue
            results.append(bp)

    # Collect fuzzy predictions
    if layer is None or layer == "fuzzy":
        for fp in dataset.fuzzy_predictions:
            if name and name not in fp.id:
                continue
            if fuzziness_level is not None and fp.fuzziness_level != fuzziness_level:
                continue
            if category:
                expected_cat = fp.expected_post_clarification_outputs.get(
                    "categorizer", {}
                ).get("expected_category", "")
                if expected_cat != category:
                    continue
            if difficulty:
                base_bp = next(
                    (bp for bp in dataset.base_predictions
                     if bp.id == fp.base_prediction_id),
                    None,
                )
                if base_bp and base_bp.difficulty != difficulty:
                    continue
            results.append(fp)

    return results
