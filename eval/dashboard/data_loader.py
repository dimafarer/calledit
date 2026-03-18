"""
EvalDataLoader — unified data layer for the eval dashboard.

DDB primary, local file fallback. Handles both old (run_metadata) and new
(report_summary) record types in DDB. Gracefully defaults optional fields.

Local fallback sources:
  - eval/score_history.json — run summaries
  - eval/reports/eval-*.json — per-test-case detail
"""

import glob
import json
import logging
import os
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)

TABLE_NAME = "calledit-eval-reasoning"
# Local file paths — eval runner writes relative to its own directory,
# so we check both the project root and the strands_make_call handler dir.
SCORE_HISTORY_PATHS = [
    "eval/score_history.json",
    "backend/calledit-backend/handlers/strands_make_call/eval/score_history.json",
]
REPORTS_GLOBS = [
    "eval/reports/eval-*.json",
    "backend/calledit-backend/handlers/strands_make_call/eval/reports/eval-*.json",
]

# DDB stores numbers as Decimal; convert to float recursively
def _decimal_to_float(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    return obj


def _clamp_score(val: Any) -> float:
    """Clamp a score value to [0, 1]. Log warning if out of range."""
    try:
        f = float(val)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0 or f > 1.0:
        logger.warning(f"Score {f} outside [0,1], clamping")
        return max(0.0, min(1.0, f))
    return f


def _clamp_evaluator_scores(scores: dict) -> dict:
    """Clamp all evaluator score values in a scores dict."""
    clamped = {}
    for key, val in scores.items():
        if isinstance(val, dict) and "score" in val:
            clamped[key] = {**val, "score": _clamp_score(val["score"])}
        else:
            clamped[key] = val
    return clamped


def _normalize_run_summary(raw: dict) -> dict:
    """Normalize a run summary from either DDB or local into a consistent shape."""
    # per_category_accuracy values may be strings (DDB Decimal→str) or floats
    pca = raw.get("per_category_accuracy", {})
    if isinstance(pca, dict):
        pca = {k: float(v) for k, v in pca.items()}

    # Verification-Builder-centric composite score — None when absent (backward compat)
    raw_vb = raw.get("vb_centric_score")
    vb_centric_score = float(raw_vb) if raw_vb is not None else None

    return {
        "eval_run_id": raw.get("eval_run_id", ""),
        "timestamp": raw.get("timestamp", ""),
        "prompt_version_manifest": raw.get("prompt_version_manifest", {}),
        "dataset_version": raw.get("dataset_version", ""),
        "architecture": raw.get("architecture", "serial"),
        "model_config": raw.get("model_config", {}),
        "per_agent_aggregates": raw.get("per_agent_aggregates", {}),
        "per_category_accuracy": pca,
        "verification_quality_aggregates": raw.get("verification_quality_aggregates", {}),
        "vb_centric_score": vb_centric_score,
        "overall_pass_rate": float(raw.get("overall_pass_rate", raw.get("pass_rate", 0.0))),
        "total_tests": int(raw.get("total_tests", 0)),
        "passed": int(raw.get("passed", 0)),
        "failed": int(raw.get("failed", raw.get("total_tests", 0)) or 0)
                  - int(raw.get("passed", 0))
                  if "failed" not in raw else int(raw.get("failed", 0)),
    }


def _normalize_test_result(raw: dict) -> dict:
    """Normalize a test result from DDB or local report into consistent shape."""
    scores = raw.get("evaluator_scores", {})
    return {
        "test_case_id": raw.get("test_case_id", ""),
        "layer": raw.get("layer", ""),
        "difficulty": raw.get("difficulty", ""),
        "expected_category": raw.get("expected_category", ""),
        "evaluator_scores": _clamp_evaluator_scores(scores),
        "error": raw.get("error", ""),
        "duration_s": float(raw.get("duration_s", 0.0)),
        "execution_time_ms": int(raw.get("execution_time_ms", 0)),
    }


class EvalDataLoader:
    """Load eval data from DDB (primary) with local file fallback."""

    def __init__(self, table_name: str = TABLE_NAME):
        self._ddb_available = False
        self._table = None
        self._table_name = table_name
        try:
            import boto3
            self._table = boto3.resource("dynamodb").Table(table_name)
            self._table.table_status  # fast check
            self._ddb_available = True
            logger.info(f"DDB connected: {table_name}")
        except Exception as e:
            logger.warning(f"DDB unavailable: {e}")

    def is_ddb_available(self) -> bool:
        return self._ddb_available

    # ------------------------------------------------------------------
    # load_all_runs: DDB report_summary/run_metadata → local score_history
    # ------------------------------------------------------------------
    def load_all_runs(self) -> list[dict]:
        """Load all run summaries sorted by timestamp descending.

        Merges DDB and local sources, deduplicating by timestamp.
        Local data enriches DDB records when DDB is missing fields
        (e.g., architecture, vb_centric_score added after initial DDB writes).
        """
        ddb_runs = self._load_runs_from_ddb() or []
        local_runs = self._load_runs_from_local()

        # Build local lookup by timestamp for enrichment
        local_by_ts = {r.get("timestamp", ""): r for r in local_runs}

        # Enrich DDB records with local data for fields DDB may be missing
        enrich_fields = [
            "architecture", "model_config", "vb_centric_score",
            "verification_quality_aggregates", "per_agent_aggregates",
        ]
        for ddb_run in ddb_runs:
            ts = ddb_run.get("timestamp", "")
            local_run = local_by_ts.get(ts)
            if local_run:
                for field in enrich_fields:
                    ddb_val = ddb_run.get(field)
                    local_val = local_run.get(field)
                    # Use local value when DDB has default/empty value
                    if field == "architecture" and ddb_val == "serial" and local_val and local_val != "serial":
                        ddb_run[field] = local_val
                    elif ddb_val in (None, {}, "") and local_val not in (None, {}, ""):
                        ddb_run[field] = local_val

        # Add local-only runs (not in DDB)
        seen_timestamps = {r.get("timestamp", "") for r in ddb_runs}
        for lr in local_runs:
            if lr.get("timestamp", "") not in seen_timestamps:
                ddb_runs.append(lr)
                seen_timestamps.add(lr.get("timestamp", ""))

        runs = ddb_runs
        runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return runs

    def _load_runs_from_ddb(self) -> Optional[list[dict]]:
        if not self._ddb_available:
            return None
        try:
            from boto3.dynamodb.conditions import Attr
            # Scan for both old and new record types
            response = self._table.scan(
                FilterExpression=(
                    Attr("record_key").eq("report_summary#SUMMARY")
                    | Attr("record_key").eq("run_metadata#SUMMARY")
                ),
            )
            items = _decimal_to_float(response.get("Items", []))
            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self._table.scan(
                    FilterExpression=(
                        Attr("record_key").eq("report_summary#SUMMARY")
                        | Attr("record_key").eq("run_metadata#SUMMARY")
                    ),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(_decimal_to_float(response.get("Items", [])))
            return [_normalize_run_summary(item) for item in items]
        except Exception as e:
            logger.warning(f"DDB scan failed, falling back to local: {e}")
            return None

    def _load_runs_from_local(self) -> list[dict]:
        runs = []
        seen_timestamps = set()
        for path in SCORE_HISTORY_PATHS:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for entry in data.get("evaluations", []):
                    ts = entry.get("timestamp", "")
                    if ts not in seen_timestamps:
                        runs.append(_normalize_run_summary(entry))
                        seen_timestamps.add(ts)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load {path}: {e}")
        return runs

    # ------------------------------------------------------------------
    # load_run_detail: DDB test_result records → local eval report file
    # ------------------------------------------------------------------
    def load_run_detail(self, eval_run_id: str, timestamp: str = "") -> dict:
        """Load per-test-case detail for a run.

        Tries DDB first for test_result records. Falls back to local
        report files if DDB has no test_results (even if DDB is available).
        """
        detail = self._load_detail_from_ddb(eval_run_id)
        if detail is None or not detail.get("test_cases"):
            local_detail = self._load_detail_from_local(timestamp)
            if local_detail and local_detail.get("test_cases"):
                return local_detail
        return detail or {"test_cases": [], "eval_run_id": eval_run_id}

    def _load_detail_from_ddb(self, eval_run_id: str) -> Optional[dict]:
        if not self._ddb_available or not eval_run_id:
            return None
        try:
            from boto3.dynamodb.conditions import Key, Attr
            response = self._table.query(
                KeyConditionExpression=Key("eval_run_id").eq(eval_run_id)
                & Key("record_key").begins_with("test_result#"),
            )
            items = _decimal_to_float(response.get("Items", []))
            while "LastEvaluatedKey" in response:
                response = self._table.query(
                    KeyConditionExpression=Key("eval_run_id").eq(eval_run_id)
                    & Key("record_key").begins_with("test_result#"),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                items.extend(_decimal_to_float(response.get("Items", [])))
            if not items:
                return None
            return {
                "eval_run_id": eval_run_id,
                "test_cases": [_normalize_test_result(item) for item in items],
            }
        except Exception as e:
            logger.warning(f"DDB query for test_results failed: {e}")
            return None

    def _load_detail_from_local(self, timestamp: str) -> Optional[dict]:
        """Find a local report file matching the timestamp."""
        for reports_glob in REPORTS_GLOBS:
            for path in sorted(glob.glob(reports_glob)):
                try:
                    with open(path, "r") as f:
                        report = json.load(f)
                    # Required fields check
                    if "timestamp" not in report or "per_test_case_scores" not in report:
                        logger.warning(f"Skipping malformed report: {path}")
                        continue
                    # Match by timestamp if provided, otherwise return first valid
                    if timestamp and report.get("timestamp") != timestamp:
                        continue
                    return {
                        "eval_run_id": report.get("eval_run_id", ""),
                        "timestamp": report.get("timestamp", ""),
                        "prompt_version_manifest": report.get("prompt_version_manifest", {}),
                        "test_cases": [
                            _normalize_test_result(tc)
                            for tc in report.get("per_test_case_scores", [])
                        ],
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON: {path}")
                    continue
                except IOError as e:
                    logger.warning(f"Skipping unreadable file {path}: {e}")
                    continue
        return None

    # ------------------------------------------------------------------
    # DDB-only data (no local fallback)
    # ------------------------------------------------------------------
    def load_agent_outputs(self, eval_run_id: str, test_case_id: str) -> dict:
        """Load agent outputs from DDB. Returns empty dict if unavailable."""
        if not self._ddb_available or not eval_run_id:
            return {}
        try:
            from boto3.dynamodb.conditions import Key
            response = self._table.get_item(
                Key={
                    "eval_run_id": eval_run_id,
                    "record_key": f"agent_output#{test_case_id}",
                }
            )
            item = response.get("Item")
            if not item:
                return {}
            return _decimal_to_float(item)
        except Exception as e:
            logger.warning(f"Failed to load agent outputs: {e}")
            return {}

    def load_judge_reasoning(self, eval_run_id: str, test_case_id: str) -> list[dict]:
        """Load judge reasoning records from DDB. Returns empty list if unavailable."""
        if not self._ddb_available or not eval_run_id:
            return []
        try:
            from boto3.dynamodb.conditions import Key
            response = self._table.query(
                KeyConditionExpression=(
                    Key("eval_run_id").eq(eval_run_id)
                    & Key("record_key").begins_with(f"judge_reasoning#{test_case_id}#")
                ),
            )
            items = _decimal_to_float(response.get("Items", []))
            return items
        except Exception as e:
            logger.warning(f"Failed to load judge reasoning: {e}")
            return []

    def load_token_counts(self, eval_run_id: str, test_case_id: str) -> dict:
        """Load token counts from DDB. Returns empty dict if unavailable."""
        if not self._ddb_available or not eval_run_id:
            return {}
        try:
            from boto3.dynamodb.conditions import Key
            response = self._table.get_item(
                Key={
                    "eval_run_id": eval_run_id,
                    "record_key": f"token_counts#{test_case_id}",
                }
            )
            item = response.get("Item")
            if not item:
                return {}
            return _decimal_to_float(item)
        except Exception as e:
            logger.warning(f"Failed to load token counts: {e}")
            return {}

    # ------------------------------------------------------------------
    # compare_runs
    # ------------------------------------------------------------------
    def compare_runs(self, run_a: dict, run_b: dict) -> dict:
        """Compare two run summaries.

        Args:
            run_a: Current/newer run summary dict.
            run_b: Previous/older run summary dict.

        Returns:
            Dict with overall_pass_rate delta, category_deltas,
            changed_prompts, dataset_version_mismatch, has_regression.
        """
        # Prompt version diff
        manifest_a = run_a.get("prompt_version_manifest", {})
        manifest_b = run_b.get("prompt_version_manifest", {})
        all_keys = set(list(manifest_a.keys()) + list(manifest_b.keys()))
        changed_prompts = {
            k: {"from": manifest_b.get(k, "unknown"), "to": manifest_a.get(k, "unknown")}
            for k in all_keys
            if manifest_a.get(k) != manifest_b.get(k)
        }

        # Category deltas
        pca_a = run_a.get("per_category_accuracy", {})
        pca_b = run_b.get("per_category_accuracy", {})
        all_cats = set(list(pca_a.keys()) + list(pca_b.keys()))
        category_deltas = {}
        has_regression = False
        for cat in all_cats:
            curr = float(pca_a.get(cat, 0.0))
            prev = float(pca_b.get(cat, 0.0))
            delta = round(curr - prev, 4)
            status = "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"
            if status == "regressed":
                has_regression = True
            category_deltas[cat] = {
                "current": curr,
                "previous": prev,
                "delta": delta,
                "status": status,
            }

        # Overall pass rate delta
        rate_a = float(run_a.get("overall_pass_rate", 0.0))
        rate_b = float(run_b.get("overall_pass_rate", 0.0))
        rate_delta = round(rate_a - rate_b, 4)
        if rate_delta < 0:
            has_regression = True

        # Dataset version mismatch
        dv_a = run_a.get("dataset_version", "")
        dv_b = run_b.get("dataset_version", "")

        # Verification-Builder-centric score delta
        vb_a = run_a.get("vb_centric_score")
        vb_b = run_b.get("vb_centric_score")
        if vb_a is not None and vb_b is not None:
            vb_delta = round(float(vb_a) - float(vb_b), 4)
        else:
            vb_delta = None
        vb_centric_delta = {
            "current": float(vb_a) if vb_a is not None else None,
            "previous": float(vb_b) if vb_b is not None else None,
            "delta": vb_delta,
        }

        # Per-agent evaluator deltas — only for evaluators present in both runs
        paa_a = run_a.get("per_agent_aggregates", {})
        paa_b = run_b.get("per_agent_aggregates", {})
        shared_evaluators = set(paa_a.keys()) & set(paa_b.keys())
        per_agent_deltas = {}
        for evaluator in shared_evaluators:
            curr_val = paa_a[evaluator]
            prev_val = paa_b[evaluator]
            # Support both {"avg": float} dict and plain float values
            curr_avg = float(curr_val.get("avg", 0.0) if isinstance(curr_val, dict) else curr_val)
            prev_avg = float(prev_val.get("avg", 0.0) if isinstance(prev_val, dict) else prev_val)
            per_agent_deltas[evaluator] = {
                "current": curr_avg,
                "previous": prev_avg,
                "delta": round(curr_avg - prev_avg, 4),
            }

        return {
            "overall_pass_rate": {
                "current": rate_a,
                "previous": rate_b,
                "delta": rate_delta,
                "status": "improved" if rate_delta > 0 else "regressed" if rate_delta < 0 else "unchanged",
            },
            "category_deltas": category_deltas,
            "changed_prompts": changed_prompts,
            "dataset_version_mismatch": dv_a != dv_b,
            "has_regression": has_regression,
            "vb_centric_delta": vb_centric_delta,
            "per_agent_deltas": per_agent_deltas,
        }
