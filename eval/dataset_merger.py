"""Dataset Merger — combines static and dynamic golden datasets.

Merges eval/golden_dataset.json (static, timeless) with
eval/dynamic_golden_dataset.json (time-anchored, regenerated).

Dynamic predictions with a `replaces` field override matching static
predictions that have `time_sensitive: true`. All other static predictions
are preserved. Dynamic predictions use `dyn-` ID prefix.

Usage:
    from eval.dataset_merger import load_and_merge

    # Static only (backward compatible)
    dataset = load_and_merge("eval/golden_dataset.json")

    # Merged
    dataset = load_and_merge("eval/golden_dataset.json", "eval/dynamic_golden_dataset.json")
"""

import json
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def load_and_merge(
    static_path: str,
    dynamic_path: Optional[str] = None,
) -> dict:
    """Load datasets and merge. If dynamic_path is None, returns static only.

    Args:
        static_path: Path to the static golden dataset JSON.
        dynamic_path: Optional path to the dynamic golden dataset JSON.

    Returns:
        Merged dataset dict in schema 4.0 format.
    """
    static_data = _load_json(static_path)

    if dynamic_path is None:
        return static_data

    return merge_datasets(static_path, dynamic_path)


def merge_datasets(static_path: str, dynamic_path: str) -> dict:
    """Merge static and dynamic datasets.

    - Dynamic predictions with `replaces` field override matching static
      predictions that have `time_sensitive: true`.
    - All other static predictions are preserved.
    - All dynamic predictions are included.

    Args:
        static_path: Path to the static golden dataset JSON.
        dynamic_path: Path to the dynamic golden dataset JSON.

    Returns:
        Merged dataset dict in schema 4.0 format.
    """
    static_data = _load_json(static_path)
    dynamic_data = _load_json(dynamic_path)

    static_preds = static_data.get("base_predictions", [])
    dynamic_preds = dynamic_data.get("base_predictions", [])

    # Build replaces index: static_id -> dynamic prediction
    replaces_index = {}
    for dp in dynamic_preds:
        replaces_id = dp.get("replaces")
        if replaces_id:
            replaces_index[replaces_id] = dp

    # Filter static predictions: exclude time_sensitive ones that have replacements
    filtered_static = []
    for sp in static_preds:
        sp_id = sp.get("id", "")
        if sp.get("time_sensitive") and sp_id in replaces_index:
            logger.info(
                "Excluding time-sensitive static prediction %s (replaced by %s)",
                sp_id,
                replaces_index[sp_id].get("id"),
            )
            continue
        filtered_static.append(sp)

    # Warn if replaces references non-existent static IDs
    static_ids = {sp.get("id") for sp in static_preds}
    for replaced_id in replaces_index:
        if replaced_id not in static_ids:
            logger.warning(
                "Dynamic prediction replaces '%s' but no static prediction with that ID exists",
                replaced_id,
            )

    merged_preds = filtered_static + dynamic_preds

    # Build merged dataset using static as base
    merged = dict(static_data)
    merged["base_predictions"] = merged_preds

    # Update metadata with merge info
    meta = dict(merged.get("metadata", {}))
    meta["merged"] = True
    meta["static_count"] = len(filtered_static)
    meta["dynamic_count"] = len(dynamic_preds)
    merged["metadata"] = meta

    return merged


def _load_json(path: str) -> dict:
    """Load and validate a JSON dataset file."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: dataset file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)

    if "base_predictions" not in data:
        print(
            f"Error: dataset {path} missing 'base_predictions' array",
            file=sys.stderr,
        )
        sys.exit(1)

    return data
