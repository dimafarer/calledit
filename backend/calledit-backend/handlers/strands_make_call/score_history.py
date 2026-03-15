"""
Score History — persistent tracking and regression detection.

Stores evaluation results keyed by timestamp and prompt version manifest.
Supports comparison between consecutive runs to detect regressions and
correlate them with specific prompt version changes.

Storage: JSON file at eval/score_history.json (committed to repo).
Atomic writes via temp file + rename to prevent corruption.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_PATH = "eval/score_history.json"


def _load_history(path: str) -> dict:
    """Load existing history file, or return empty structure."""
    if not os.path.exists(path):
        return {"evaluations": []}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Score history corrupted, starting fresh: {e}")
        return {"evaluations": []}


def append_score(report: dict, path: str = DEFAULT_HISTORY_PATH) -> None:
    """Append evaluation scores to the history file.

    Extracts the key metrics from the report and stores them with the
    prompt version manifest for regression detection.

    Args:
        report: Full evaluation report from run_on_demand_evaluation().
        path: Path to the score history JSON file.
    """
    history = _load_history(path)

    entry = {
        "timestamp": report.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "prompt_version_manifest": report.get("prompt_version_manifest", {}),
        "dataset_version": report.get("dataset_version", ""),
        "per_agent_aggregates": report.get("per_agent_aggregates", {}),
        "per_category_accuracy": report.get("per_category_accuracy", {}),
        "overall_pass_rate": report.get("overall_pass_rate", 0.0),
        "total_tests": report.get("total_tests", 0),
        "passed": report.get("passed", 0),
    }

    history["evaluations"].append(entry)

    # Atomic write: temp file + rename
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(history, f, indent=2)
        os.replace(tmp_path, path)
        logger.info(f"Appended score to history ({len(history['evaluations'])} entries)")
    except Exception:
        os.unlink(tmp_path)
        raise


def compare_latest(path: str = DEFAULT_HISTORY_PATH) -> Optional[dict]:
    """Compare the two most recent evaluations.

    Returns:
        Dict with delta indicators per metric, changed prompt versions,
        and regression flags. None if fewer than 2 evaluations exist.
    """
    history = _load_history(path)
    evals = history.get("evaluations", [])

    if len(evals) < 2:
        return None

    current = evals[-1]
    previous = evals[-2]

    # Compare overall pass rate
    curr_rate = current.get("overall_pass_rate", 0.0)
    prev_rate = previous.get("overall_pass_rate", 0.0)

    # Compare per-category accuracy
    category_deltas = {}
    all_cats = set(list(current.get("per_category_accuracy", {}).keys()) +
                   list(previous.get("per_category_accuracy", {}).keys()))
    for cat in all_cats:
        curr_val = current.get("per_category_accuracy", {}).get(cat, 0.0)
        prev_val = previous.get("per_category_accuracy", {}).get(cat, 0.0)
        category_deltas[cat] = {
            "current": curr_val, "previous": prev_val,
            "delta": round(curr_val - prev_val, 4),
            "status": "improved" if curr_val > prev_val else "regressed" if curr_val < prev_val else "unchanged",
        }

    # Identify which prompt versions changed
    curr_manifest = current.get("prompt_version_manifest", {})
    prev_manifest = previous.get("prompt_version_manifest", {})
    changed_prompts = {
        k: {"from": prev_manifest.get(k, "unknown"), "to": curr_manifest.get(k, "unknown")}
        for k in set(list(curr_manifest.keys()) + list(prev_manifest.keys()))
        if curr_manifest.get(k) != prev_manifest.get(k)
    }

    # Flag regressions with prompt correlation
    regressions = []
    for cat, delta in category_deltas.items():
        if delta["status"] == "regressed":
            regressions.append({
                "metric": f"per_category_accuracy.{cat}",
                "delta": delta["delta"],
                "changed_prompts": changed_prompts,
            })

    if curr_rate < prev_rate:
        regressions.append({
            "metric": "overall_pass_rate",
            "delta": round(curr_rate - prev_rate, 4),
            "changed_prompts": changed_prompts,
        })

    return {
        "current_timestamp": current.get("timestamp"),
        "previous_timestamp": previous.get("timestamp"),
        "dataset_version_mismatch": (
            current.get("dataset_version", "") != previous.get("dataset_version", "")
        ),
        "dataset_version_warning": (
            f"Dataset version changed: '{previous.get('dataset_version', 'unknown')}' → "
            f"'{current.get('dataset_version', 'unknown')}' — score deltas may not be meaningful"
            if current.get("dataset_version", "") != previous.get("dataset_version", "")
            else None
        ),
        "overall_pass_rate": {
            "current": curr_rate, "previous": prev_rate,
            "delta": round(curr_rate - prev_rate, 4),
            "status": "improved" if curr_rate > prev_rate else "regressed" if curr_rate < prev_rate else "unchanged",
        },
        "category_deltas": category_deltas,
        "changed_prompts": changed_prompts,
        "regressions": regressions,
        "has_regression": len(regressions) > 0,
    }
