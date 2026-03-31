#!/usr/bin/env python3
"""Unified Eval Pipeline.

Replaces the 3 separate eval runners with a single pipeline that mirrors
production flow: creation pass → verification timing → verification pass →
evaluation → unified report.

Usage:
    source .env
    /home/wsluser/projects/calledit/venv/bin/python eval/unified_eval.py \
        --dataset eval/golden_dataset.json \
        --dynamic-dataset eval/dynamic_golden_dataset.json \
        --tier full --description "unified baseline"

Requires:
    - COGNITO_USERNAME + COGNITO_PASSWORD env vars (creation agent JWT auth)
    - AWS credentials (verification agent SigV4 auth)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_TABLE_NAME = "calledit-v4-eval"
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

TIER_1_CREATION = [
    "schema_validity", "field_completeness", "score_range",
    "date_resolution", "dimension_count", "tier_consistency",
]
TIER_1_VERIFICATION = [
    "schema_validity", "verdict_validity", "confidence_range",
    "evidence_completeness", "evidence_structure",
]


# ---------------------------------------------------------------------------
# Dataset Audit
# ---------------------------------------------------------------------------

def audit_dataset(predictions: list) -> tuple:
    """Filter predictions with null expected_verification_outcome.

    Returns:
        (qualifying, excluded_ids) — qualifying predictions and list of excluded ids.
    """
    qualifying = []
    excluded_ids = []
    for p in predictions:
        if p.get("expected_verification_outcome") is not None:
            qualifying.append(p)
        else:
            pid = p.get("id", "<unknown>")
            excluded_ids.append(pid)
            logger.warning("Excluding %s: null expected_verification_outcome", pid)
    return qualifying, excluded_ids


# ---------------------------------------------------------------------------
# DDB Helpers
# ---------------------------------------------------------------------------

def _float_to_decimal(obj):
    """Recursively convert floats to Decimal for DDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(v) for v in obj]
    return obj


def get_eval_table():
    """Get the eval DDB table resource."""
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return ddb.Table(EVAL_TABLE_NAME)


def cleanup_eval_table(table, prediction_ids: list) -> None:
    """Batch delete all eval items. Best-effort, logs warnings."""
    if not prediction_ids:
        return
    print(f"Cleaning up {len(prediction_ids)} bundle(s) from eval table...")
    deleted = 0
    for pid in prediction_ids:
        try:
            table.delete_item(Key={"PK": f"PRED#{pid}", "SK": "BUNDLE"})
            deleted += 1
        except Exception as e:
            logger.warning("Failed to delete %s: %s", pid, e)
    print(f"  ✓ Cleaned up {deleted}/{len(prediction_ids)} item(s)")


# ---------------------------------------------------------------------------
# Creation Pass
# ---------------------------------------------------------------------------

def run_creation_pass(
    predictions: list,
    backend,
    eval_table,
    resume_ids: Optional[set] = None,
) -> tuple:
    """Invoke creation agent for each prediction, write bundles to DDB.

    Returns:
        (case_results, duration_seconds)
    """
    start = time.time()
    results = []
    total = len(predictions)

    for i, pred in enumerate(predictions, 1):
        case_id = pred["id"]
        text = pred["prediction_text"]

        result = {
            "case_id": case_id,
            "prediction_text": text,
            "expected_verdict": pred.get("expected_verification_outcome"),
            "verification_mode": pred.get("verification_mode", "immediate"),
            "prediction_id": None,
            "creation_bundle": None,
            "creation_error": None,
            "creation_duration": 0.0,
        }

        # Resume: skip if already in eval table
        if resume_ids and case_id in resume_ids:
            print(f"  [{i}/{total}] {case_id}: skipped (resume)")
            results.append(result)
            continue

        print(f"  [{i}/{total}] {case_id}: {text[:60]}...")
        case_start = time.time()

        try:
            bundle = backend.invoke(text, case_id=case_id)
            result["prediction_id"] = bundle.get("prediction_id")
            result["creation_bundle"] = bundle
            result["creation_duration"] = round(time.time() - case_start, 1)

            # The creation agent already writes to the eval table via table_name override
            # So we don't need to write the bundle ourselves
            print(f"    → created: score={bundle.get('plan_review', {}).get('verifiability_score', '?')}, "
                  f"pid={result['prediction_id']}")

        except Exception as e:
            result["creation_error"] = str(e)
            result["creation_duration"] = round(time.time() - case_start, 1)
            print(f"    ✗ Creation error: {e}")

        results.append(result)

    duration = round(time.time() - start, 1)
    return results, duration


# ---------------------------------------------------------------------------
# Verification Timing
# ---------------------------------------------------------------------------

def compute_verification_wait(case_results: list) -> float:
    """Compute seconds to wait until all verification dates have passed.

    Only considers at_date and before_date modes — immediate and recurring
    don't need to wait. Returns 0 if all dates are in the past.
    Caps at 300s (5 min) to avoid runaway waits from bad data.
    """
    now = datetime.now(timezone.utc)
    latest = now  # default: no wait

    for r in case_results:
        mode = r.get("verification_mode", "immediate")
        if mode in ("immediate", "recurring"):
            continue  # These don't have meaningful verification dates

        bundle = r.get("creation_bundle")
        if not bundle:
            continue
        raw = bundle.get("raw_bundle", {})
        vdate_str = (
            raw.get("parsed_claim", {}).get("verification_date")
            or raw.get("verification_date")
        )
        if not vdate_str:
            continue
        try:
            vdate = datetime.fromisoformat(vdate_str.replace("Z", "+00:00"))
            if vdate > latest:
                latest = vdate
        except (ValueError, AttributeError):
            logger.warning("Unparseable verification_date: %s", vdate_str)

    if latest <= now:
        return 0.0

    wait = (latest - now).total_seconds() + 30  # 30s buffer
    return min(wait, 300.0)  # Cap at 5 minutes


# ---------------------------------------------------------------------------
# Verification Pass
# ---------------------------------------------------------------------------

def run_verification_pass(case_results: list, backend, eval_table_name: str) -> tuple:
    """Invoke verification agent for each successful creation.

    Returns:
        (updated_case_results, duration_seconds)
    """
    start = time.time()
    verifiable = [r for r in case_results if r.get("prediction_id") and not r.get("creation_error")]
    total = len(verifiable)

    print(f"\nRunning verification on {total} case(s)...")

    for i, result in enumerate(verifiable, 1):
        pid = result["prediction_id"]
        case_id = result["case_id"]
        print(f"  [{i}/{total}] {case_id} (pid={pid[:12]}...)...")

        ver_start = time.time()
        try:
            verdict_response = backend.invoke(
                prediction_id=pid,
                table_name=eval_table_name,
                case_id=case_id,
            )
            result["verification_result"] = verdict_response
            result["actual_verdict"] = verdict_response.get("verdict")
            result["actual_confidence"] = verdict_response.get("confidence")
            result["verification_duration"] = round(time.time() - ver_start, 1)
            print(f"    → verdict: {result['actual_verdict']}, confidence: {result['actual_confidence']}")

        except Exception as e:
            result["verification_error"] = str(e)
            result["verification_duration"] = round(time.time() - ver_start, 1)
            print(f"    ✗ Verification error: {e}")

    duration = round(time.time() - start, 1)
    return case_results, duration


# ---------------------------------------------------------------------------
# Evaluation Phase
# ---------------------------------------------------------------------------

def build_creation_evaluators(tier: str) -> dict:
    """Build creation evaluator dict based on tier."""
    from eval.evaluators import (
        schema_validity, field_completeness, score_range,
        date_resolution, dimension_count, tier_consistency,
    )
    evaluators = {
        "schema_validity": schema_validity.evaluate,
        "field_completeness": field_completeness.evaluate,
        "score_range": score_range.evaluate,
        "date_resolution": date_resolution.evaluate,
        "dimension_count": dimension_count.evaluate,
        "tier_consistency": tier_consistency.evaluate,
    }
    if tier in ("smoke+judges", "full"):
        from eval.evaluators import intent_preservation, plan_quality
        evaluators["intent_preservation"] = intent_preservation.evaluate
        evaluators["plan_quality"] = plan_quality.evaluate
    return evaluators


def build_verification_evaluators(tier: str, mode: str) -> dict:
    """Build verification evaluator dict based on tier and verification mode."""
    from eval.evaluators import (
        verification_schema_validity, verification_verdict_validity,
        verification_confidence_range, verification_evidence_completeness,
        verification_evidence_structure,
    )
    evaluators = {
        "schema_validity": verification_schema_validity,
        "verdict_validity": verification_verdict_validity,
        "confidence_range": verification_confidence_range,
        "evidence_completeness": verification_evidence_completeness,
        "evidence_structure": verification_evidence_structure,
    }

    if tier == "smoke":
        return evaluators

    # Tier 2: mode-specific evaluators
    from eval.evaluators import (
        verification_verdict_accuracy, verification_evidence_quality,
    )

    if mode == "immediate":
        evaluators["verdict_accuracy"] = verification_verdict_accuracy
        evaluators["evidence_quality"] = verification_evidence_quality
    elif mode == "at_date":
        from eval.evaluators import verification_at_date_verdict_accuracy
        evaluators["verdict_accuracy"] = verification_at_date_verdict_accuracy
        evaluators["evidence_quality"] = verification_evidence_quality
    elif mode == "before_date":
        from eval.evaluators import verification_before_date_verdict_appropriateness
        evaluators["verdict_appropriateness"] = verification_before_date_verdict_appropriateness
        evaluators["evidence_quality"] = verification_evidence_quality
    elif mode == "recurring":
        from eval.evaluators import verification_recurring_evidence_freshness
        evaluators["verdict_accuracy"] = verification_verdict_accuracy
        evaluators["evidence_quality"] = verification_evidence_quality
        evaluators["evidence_freshness"] = verification_recurring_evidence_freshness
    else:
        evaluators["verdict_accuracy"] = verification_verdict_accuracy
        evaluators["evidence_quality"] = verification_evidence_quality

    return evaluators


def run_evaluation(case_results: list, tier: str) -> tuple:
    """Run all evaluators and compute calibration metrics.

    Returns:
        (creation_scores, verification_scores, calibration_scores, updated_case_results)
    """
    start = time.time()
    creation_evals = build_creation_evaluators(tier)
    tier_2_creation = {"intent_preservation", "plan_quality"}

    # Import calibration functions
    from eval.calibration_eval import compute_calibration_metrics, is_calibration_correct

    for result in case_results:
        result["creation_scores"] = {}
        result["verification_scores"] = {}

        # --- Creation evaluators ---
        bundle = result.get("creation_bundle")
        if bundle and not result.get("creation_error"):
            for name, eval_fn in creation_evals.items():
                try:
                    if name in tier_2_creation:
                        score = eval_fn(bundle, result["prediction_text"])
                    else:
                        score = eval_fn(bundle)
                    result["creation_scores"][name] = score
                except Exception as e:
                    result["creation_scores"][name] = {
                        "score": 0.0, "pass": False, "reason": f"Evaluator error: {e}",
                    }

        # --- Verification evaluators ---
        vresult = result.get("verification_result")
        if vresult and not result.get("verification_error"):
            mode = result.get("verification_mode", "immediate")
            ver_evals = build_verification_evaluators(tier, mode)

            for name, evaluator in ver_evals.items():
                try:
                    if name in ("verdict_accuracy", "verdict_appropriateness"):
                        score = evaluator.evaluate(vresult, result.get("expected_verdict"))
                    elif name in ("evidence_quality", "evidence_freshness"):
                        score = evaluator.evaluate(vresult, result["prediction_text"])
                    else:
                        score = evaluator.evaluate(vresult)
                    if score is not None:
                        result["verification_scores"][name] = score
                except Exception as e:
                    result["verification_scores"][name] = {
                        "score": 0.0, "pass": False, "reason": f"Evaluator error: {e}",
                    }

        # --- Calibration ---
        v_score = None
        if bundle:
            v_score = bundle.get("plan_review", {}).get("verifiability_score")
            if v_score is None:
                v_score = bundle.get("raw_bundle", {}).get("verifiability_score")
        result["verifiability_score"] = v_score

        from calleditv4.src.models import score_to_tier
        if v_score is not None:
            tier_info = score_to_tier(v_score)
            result["score_tier"] = tier_info["tier"]
        else:
            result["score_tier"] = None

        actual = result.get("actual_verdict")
        if result.get("score_tier") and actual:
            result["calibration_correct"] = is_calibration_correct(result["score_tier"], actual)
        else:
            result["calibration_correct"] = None

    # Compute aggregates
    creation_scores = _compute_creation_aggregates(case_results, creation_evals)
    verification_scores = _compute_verification_aggregates(case_results)

    # Calibration metrics — build case dicts matching calibration_eval format
    cal_cases = []
    for r in case_results:
        if r.get("creation_error") or r.get("verification_error"):
            cal_cases.append({"error": r.get("creation_error") or r.get("verification_error")})
        else:
            cal_cases.append({
                "verifiability_score": r.get("verifiability_score", 0.0),
                "score_tier": r.get("score_tier", ""),
                "actual_verdict": r.get("actual_verdict", ""),
                "expected_verdict": r.get("expected_verdict"),
                "calibration_correct": r.get("calibration_correct"),
            })
    calibration_scores = compute_calibration_metrics(cal_cases)

    duration = round(time.time() - start, 1)
    return creation_scores, verification_scores, calibration_scores, case_results, duration


def _compute_creation_aggregates(results: list, evaluators: dict) -> dict:
    """Compute per-evaluator averages for creation scores."""
    scores = {}
    for name in evaluators:
        vals = [
            r["creation_scores"][name]["score"]
            for r in results
            if name in r.get("creation_scores", {})
            and isinstance(r["creation_scores"][name], dict)
            and "score" in r["creation_scores"][name]
        ]
        scores[name] = round(sum(vals) / len(vals), 4) if vals else None

    # Overall Tier 1 pass rate
    t1_passes = []
    for r in results:
        cs = r.get("creation_scores", {})
        if cs:
            passes = all(
                cs.get(n, {}).get("pass", False)
                for n in TIER_1_CREATION
                if n in cs
            )
            t1_passes.append(1.0 if passes else 0.0)
    scores["overall_pass_rate"] = round(sum(t1_passes) / len(t1_passes), 4) if t1_passes else 0.0

    return scores


def _compute_verification_aggregates(results: list) -> dict:
    """Compute per-evaluator averages for verification scores."""
    # Collect all evaluator names seen
    all_names = set()
    for r in results:
        all_names.update(r.get("verification_scores", {}).keys())

    scores = {}
    for name in all_names:
        vals = [
            r["verification_scores"][name]["score"]
            for r in results
            if name in r.get("verification_scores", {})
            and isinstance(r["verification_scores"][name], dict)
            and "score" in r["verification_scores"][name]
        ]
        scores[name] = round(sum(vals) / len(vals), 4) if vals else None

    # Overall Tier 1 pass rate
    t1_passes = []
    for r in results:
        vs = r.get("verification_scores", {})
        if vs:
            passes = all(
                vs.get(n, {}).get("pass", False)
                for n in TIER_1_VERIFICATION
                if n in vs
            )
            t1_passes.append(1.0 if passes else 0.0)
    scores["overall_pass_rate"] = round(sum(t1_passes) / len(t1_passes), 4) if t1_passes else 0.0

    return scores


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _get_git_commit() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_unified_report(
    args, dataset, case_results,
    creation_scores, verification_scores, calibration_scores,
    phase_durations, excluded_ids, total_duration,
) -> dict:
    """Assemble the unified report dict."""
    now = datetime.now(timezone.utc).isoformat()
    description = args.description or f"unified {args.tier} — {now[:19]}"

    # Collect prompt versions from first successful case
    prompt_versions = {}
    for r in case_results:
        bundle = r.get("creation_bundle", {})
        if bundle:
            prompt_versions = bundle.get("prompt_versions", {})
            break

    return {
        "run_metadata": {
            "description": description,
            "agent": "unified",
            "timestamp": now,
            "duration_seconds": round(total_duration, 1),
            "case_count": len(case_results),
            "excluded_count": len(excluded_ids),
            "dataset_version": dataset.get("dataset_version", "unknown"),
            "dataset_sources": [args.dataset] + (
                [args.dynamic_dataset] if getattr(args, "dynamic_dataset", None) else []
            ),
            "run_tier": args.tier,
            "git_commit": _get_git_commit(),
            "prompt_versions": prompt_versions,
            "phase_durations": phase_durations,
        },
        "creation_scores": creation_scores,
        "verification_scores": verification_scores,
        "calibration_scores": calibration_scores,
        "case_results": case_results,
    }


def save_report(report: dict, output_dir: str) -> str:
    """Save report as unified-eval-{YYYYMMDD-HHMMSS}.json."""
    os.makedirs(output_dir, exist_ok=True)
    ts = report["run_metadata"]["timestamp"]
    dt = datetime.fromisoformat(ts)
    filename = f"unified-eval-{dt.strftime('%Y%m%d-%H%M%S')}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def print_summary(report: dict) -> None:
    """Print run summary to stdout."""
    meta = report["run_metadata"]
    cs = report["creation_scores"]
    vs = report["verification_scores"]
    cal = report["calibration_scores"]

    print(f"\n{'='*60}")
    print(f"  UNIFIED EVAL REPORT")
    print(f"{'='*60}")
    print(f"Tier: {meta['run_tier']}  Cases: {meta['case_count']}  "
          f"Excluded: {meta['excluded_count']}  Duration: {meta['duration_seconds']}s")
    print(f"Phases: creation={meta['phase_durations']['creation_seconds']}s, "
          f"wait={meta['phase_durations']['wait_seconds']}s, "
          f"verification={meta['phase_durations']['verification_seconds']}s, "
          f"evaluation={meta['phase_durations']['evaluation_seconds']}s")

    print(f"\n--- Creation Scores ---")
    for name in TIER_1_CREATION:
        val = cs.get(name)
        print(f"  {name}: {val:.2f}" if val is not None else f"  {name}: N/A")
    print(f"  overall_pass_rate: {cs.get('overall_pass_rate', 0):.2f}")
    if meta["run_tier"] in ("smoke+judges", "full"):
        for name in ("intent_preservation", "plan_quality"):
            val = cs.get(name)
            print(f"  {name}: {val:.2f}" if val is not None else f"  {name}: N/A")

    print(f"\n--- Verification Scores ---")
    for name in TIER_1_VERIFICATION:
        val = vs.get(name)
        print(f"  {name}: {val:.2f}" if val is not None else f"  {name}: N/A")
    print(f"  overall_pass_rate: {vs.get('overall_pass_rate', 0):.2f}")
    if meta["run_tier"] in ("smoke+judges", "full"):
        for name in ("verdict_accuracy", "evidence_quality"):
            val = vs.get(name)
            print(f"  {name}: {val:.2f}" if val is not None else f"  {name}: N/A")

    print(f"\n--- Calibration Scores ---")
    print(f"  calibration_accuracy: {cal.get('calibration_accuracy', 0):.4f}")
    print(f"  mean_absolute_error: {cal.get('mean_absolute_error', 0):.4f}")
    print(f"  high_score_confirmation_rate: {cal.get('high_score_confirmation_rate', 0):.4f}")
    print(f"  low_score_failure_rate: {cal.get('low_score_failure_rate', 0):.4f}")

    vd = cal.get("verdict_distribution", {})
    if vd:
        print(f"\n  Verdict Distribution:")
        for k, v in vd.items():
            if v > 0:
                print(f"    {k}: {v}")

    # Per-case summary
    print(f"\n--- Per-Case Results ---")
    for r in report["case_results"]:
        cid = r["case_id"]
        if r.get("creation_error"):
            print(f"  {cid}: CREATION ERROR — {r['creation_error'][:60]}")
        elif r.get("verification_error"):
            score = r.get("verifiability_score", "?")
            print(f"  {cid}: score={score} → VERIFICATION ERROR — {r['verification_error'][:60]}")
        else:
            score = r.get("verifiability_score", "?")
            tier = r.get("score_tier", "?")
            verdict = r.get("actual_verdict", "?")
            conf = r.get("actual_confidence", "?")
            cal_ok = "✓" if r.get("calibration_correct") else "✗" if r.get("calibration_correct") is False else "?"
            print(f"  {cid}: score={score} ({tier}) → {verdict} (conf={conf}) [{cal_ok}]")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Unified Eval Pipeline")
    parser.add_argument("--dataset", default="eval/golden_dataset.json",
                        help="Path to static golden dataset")
    parser.add_argument("--dynamic-dataset", default=None,
                        help="Path to dynamic golden dataset (merged with --dataset)")
    parser.add_argument("--tier", choices=["smoke", "smoke+judges", "full"], default="smoke",
                        help="Run tier (default: smoke)")
    parser.add_argument("--description", default=None,
                        help="One-line description for this run")
    parser.add_argument("--output-dir", default="eval/reports",
                        help="Report output directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="List qualifying cases without executing")
    parser.add_argument("--case", default=None,
                        help="Execute single case by id")
    parser.add_argument("--resume", action="store_true",
                        help="Skip creation for prediction_ids already in eval table")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Leave bundles in eval table after run")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    pipeline_start = time.time()

    # --- Load and merge dataset ---
    from eval.dataset_merger import load_and_merge
    dataset = load_and_merge(args.dataset, getattr(args, "dynamic_dataset", None))
    predictions = dataset.get("base_predictions", [])

    # --- Audit ---
    qualifying, excluded_ids = audit_dataset(predictions)
    print(f"\nDataset: {len(predictions)} total, {len(qualifying)} qualifying, "
          f"{len(excluded_ids)} excluded (null verdict)")

    # Filter by --case if specified
    if args.case:
        qualifying = [p for p in qualifying if p["id"] == args.case]
        if not qualifying:
            print(f"Error: case '{args.case}' not found in qualifying predictions", file=sys.stderr)
            sys.exit(1)

    if not qualifying:
        print("Error: no qualifying predictions to evaluate", file=sys.stderr)
        sys.exit(1)

    # --- Dry run ---
    if args.dry_run:
        print(f"\nDry run — {len(qualifying)} case(s) would be executed:\n")
        for p in qualifying:
            mode = p.get("verification_mode", "?")
            diff = p.get("difficulty", "?")
            expected = p.get("expected_verification_outcome", "?")
            print(f"  {p['id']:15s} | {diff:6s} | {mode:12s} | expected={expected}")
        return

    # --- Auth ---
    from eval.backends.agentcore_backend import AgentCoreBackend, get_cognito_token
    from eval.backends.verification_backend import VerificationBackend

    print("\nAuthenticating with Cognito...")
    try:
        token = get_cognito_token()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    creation_backend = AgentCoreBackend(bearer_token=token, table_name=EVAL_TABLE_NAME)
    verification_backend = VerificationBackend()
    eval_table = get_eval_table()

    # --- Resume check ---
    resume_ids = None
    if args.resume:
        try:
            scan = eval_table.scan(Select="ALL_ATTRIBUTES")
            resume_ids = set()
            for item in scan.get("Items", []):
                pk = item.get("PK", "")
                if pk.startswith("PRED#"):
                    resume_ids.add(pk.replace("PRED#", ""))
            print(f"Resume: found {len(resume_ids)} existing bundle(s) in eval table")
        except Exception as e:
            logger.warning("Resume scan failed: %s — proceeding without resume", e)

    # --- Phase 1: Creation Pass ---
    print(f"\n{'='*40}")
    print(f"  PHASE 1: Creation Pass ({len(qualifying)} cases)")
    print(f"{'='*40}")
    case_results, creation_duration = run_creation_pass(
        qualifying, creation_backend, eval_table, resume_ids
    )

    created_count = sum(1 for r in case_results if r.get("prediction_id") and not r.get("creation_error"))
    print(f"\nCreation complete: {created_count}/{len(qualifying)} succeeded in {creation_duration}s")

    # --- Phase 2: Verification Timing ---
    wait_seconds = compute_verification_wait(case_results)
    if wait_seconds > 0:
        print(f"\nWaiting {wait_seconds:.0f}s for verification dates to arrive...")
        time.sleep(wait_seconds)
    else:
        print("\nAll verification dates are in the past — proceeding immediately")

    # --- Phase 3: Verification Pass ---
    print(f"\n{'='*40}")
    print(f"  PHASE 3: Verification Pass")
    print(f"{'='*40}")
    case_results, verification_duration = run_verification_pass(
        case_results, verification_backend, EVAL_TABLE_NAME
    )

    verified_count = sum(1 for r in case_results if r.get("actual_verdict") and not r.get("verification_error"))
    print(f"\nVerification complete: {verified_count}/{created_count} succeeded in {verification_duration}s")

    # --- Phase 4: Evaluation ---
    print(f"\n{'='*40}")
    print(f"  PHASE 4: Evaluation")
    print(f"{'='*40}")
    creation_scores, verification_scores, calibration_scores, case_results, eval_duration = \
        run_evaluation(case_results, args.tier)

    # --- Phase 5: Report ---
    total_duration = time.time() - pipeline_start
    phase_durations = {
        "creation_seconds": creation_duration,
        "wait_seconds": round(wait_seconds, 1),
        "verification_seconds": verification_duration,
        "evaluation_seconds": eval_duration,
    }

    report = build_unified_report(
        args, dataset, case_results,
        creation_scores, verification_scores, calibration_scores,
        phase_durations, excluded_ids, total_duration,
    )

    report_path = save_report(report, args.output_dir)

    # Fire-and-forget DDB write
    try:
        from eval.report_store import write_report
        write_report("unified", report)
    except Exception as e:
        logger.warning("DDB report write failed (non-fatal): %s", e)

    # --- Phase 6: Cleanup ---
    if not args.skip_cleanup:
        prediction_ids = [r["prediction_id"] for r in case_results if r.get("prediction_id")]
        cleanup_eval_table(eval_table, prediction_ids)
    else:
        print("\nSkipping cleanup (--skip-cleanup)")

    # --- Summary ---
    print_summary(report)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
