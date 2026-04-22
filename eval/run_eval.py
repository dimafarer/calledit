"""CLI entry point — Strands Evals SDK eval runner.

Replaces eval/unified_eval.py. Constructs an Experiment with Cases and
Evaluators, runs the two-agent pipeline via task function, computes
calibration, writes report to DDB, and prints summary.

Usage:
    python eval/run_eval.py --dataset eval/golden_dataset.json --tier smoke
    python eval/run_eval.py --tier full --description "SDK migration baseline"
    python eval/run_eval.py --dry-run
    python eval/run_eval.py --case base-002 --tier full
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from strands_evals import Case, Experiment

from eval.backends.agentcore_backend import AgentCoreBackend, get_cognito_token
from eval.backends.verification_backend import VerificationBackend
from eval.calibration import compute_calibration
from eval.case_loader import load_cases
from eval.task_function import TaskFunctionFactory, compute_wait_seconds

# Evaluator imports
from eval.evaluators.creation import (
    SchemaValidityEvaluator,
    FieldCompletenessEvaluator,
    ScoreRangeEvaluator,
    DateResolutionEvaluator,
    DimensionCountEvaluator,
    TierConsistencyEvaluator,
    create_intent_preservation_evaluator,
    create_plan_quality_evaluator,
)
from eval.evaluators.verification import (
    VerificationSchemaEvaluator,
    VerdictValidityEvaluator,
    ConfidenceRangeEvaluator,
    EvidenceCompletenessEvaluator,
    EvidenceStructureEvaluator,
    AtDateVerdictEvaluator,
    BeforeDateVerdictEvaluator,
    RecurringFreshnessEvaluator,
    VerdictAccuracyEvaluator,
    create_evidence_quality_evaluator,
)

logger = logging.getLogger(__name__)

EVAL_TABLE_NAME = os.environ.get("EVAL_TABLE", "calledit-v4-eval")


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="CalledIt Eval — Strands Evals SDK")
    parser.add_argument("--dataset", default="eval/golden_dataset.json",
                        help="Path to static golden dataset")
    parser.add_argument("--dynamic-dataset", default=None,
                        help="Path to dynamic golden dataset (merged with --dataset)")
    parser.add_argument("--tier", choices=["smoke", "smoke+judges", "full"],
                        default="smoke", help="Run tier (default: smoke)")
    parser.add_argument("--description", default=None,
                        help="One-line description for this run")
    parser.add_argument("--dry-run", action="store_true",
                        help="List qualifying cases without executing")
    parser.add_argument("--case", default=None,
                        help="Execute single case by id")
    parser.add_argument("--resume", action="store_true",
                        help="Skip creation for prediction_ids already in eval table")
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Leave bundles in eval table after run")
    parser.add_argument("--qualifying-only", action="store_true",
                        help="Only run cases with non-null expected outcomes")
    parser.add_argument("--creation-only", action="store_true",
                        help="Run creation phase only — skip verification and evaluation")
    parser.add_argument("--verify-only", action="store_true",
                        help="Skip creation — verify existing bundles in eval DDB table")
    parser.add_argument("--local-backup", action="store_true",
                        help="Write local JSON report to eval/reports/")
    return parser.parse_args()


def build_evaluators(tier: str) -> list:
    """Build evaluator list based on tier.

    smoke: 6 creation deterministic + 5 verification deterministic + 3 mode-specific
    smoke+judges: smoke + 3 LLM judges + verdict accuracy
    full: smoke+judges (calibration is post-experiment, not an evaluator)
    """
    # Tier 1: Deterministic (always included)
    evaluators = [
        # Creation
        SchemaValidityEvaluator(),
        FieldCompletenessEvaluator(),
        ScoreRangeEvaluator(),
        DateResolutionEvaluator(),
        DimensionCountEvaluator(),
        TierConsistencyEvaluator(),
        # Verification
        VerificationSchemaEvaluator(),
        VerdictValidityEvaluator(),
        ConfidenceRangeEvaluator(),
        EvidenceCompletenessEvaluator(),
        EvidenceStructureEvaluator(),
        # Mode-specific
        AtDateVerdictEvaluator(),
        BeforeDateVerdictEvaluator(),
        RecurringFreshnessEvaluator(),
    ]

    if tier in ("smoke+judges", "full"):
        evaluators.extend([
            create_intent_preservation_evaluator(),
            create_plan_quality_evaluator(),
            create_evidence_quality_evaluator(),
            VerdictAccuracyEvaluator(),
        ])

    return evaluators


def _get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _get_prompt_versions() -> dict:
    """Get current prompt versions from env or defaults."""
    return {
        "prediction_parser": os.environ.get("PROMPT_VERSION_PREDICTION_PARSER", "2"),
        "verification_planner": os.environ.get("PROMPT_VERSION_VERIFICATION_PLANNER", "2"),
        "plan_reviewer": os.environ.get("PROMPT_VERSION_PLAN_REVIEWER", "3"),
        "verification_executor": os.environ.get("PROMPT_VERSION_VERIFICATION_EXECUTOR", "2"),
    }


def build_report(
    args,
    case_results: list[dict],
    evaluator_results: dict,
    calibration_scores: dict,
    duration: float,
) -> dict:
    """Assemble the report dict for DDB storage.

    Args:
        args: CLI args.
        case_results: List of task function output dicts.
        evaluator_results: Per-evaluator aggregate scores.
        calibration_scores: Calibration metrics dict.
        duration: Total run duration in seconds.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    dataset_sources = [args.dataset]
    if args.dynamic_dataset:
        dataset_sources.append(args.dynamic_dataset)

    return {
        "run_metadata": {
            "description": args.description or f"SDK eval — tier={args.tier}",
            "run_tier": args.tier,
            "timestamp": timestamp,
            "duration_seconds": round(duration, 1),
            "case_count": len(case_results),
            "dataset_sources": dataset_sources,
            "git_commit": _get_git_commit(),
            "prompt_versions": _get_prompt_versions(),
        },
        "creation_scores": evaluator_results.get("creation", {}),
        "verification_scores": evaluator_results.get("verification", {}),
        "calibration_scores": calibration_scores,
        "case_results": case_results,
    }


CREATION_EVALUATOR_NAMES = {
    "SchemaValidityEvaluator", "FieldCompletenessEvaluator", "ScoreRangeEvaluator",
    "DateResolutionEvaluator", "DimensionCountEvaluator", "TierConsistencyEvaluator",
    "OutputEvaluator",  # intent_preservation and plan_quality are OutputEvaluator instances
}

CREATION_LABEL_PREFIXES = {
    "schema_validity", "field_completeness", "score_range",
    "date_resolution", "dimension_count", "tier_consistency",
    "intent_preservation", "plan_quality",
}

VERIFICATION_LABEL_PREFIXES = {
    "verification_schema_validity", "verification_verdict_validity",
    "verification_confidence_range", "verification_evidence_completeness",
    "verification_evidence_structure", "verdict_accuracy",
    "at_date_verdict", "before_date_verdict", "recurring_freshness",
    "evidence_quality",
}


def extract_evaluator_scores(evaluators: list, reports: list) -> dict:
    """Extract per-evaluator aggregate scores from SDK EvaluationReport list.

    Args:
        evaluators: The evaluator instances used in the experiment.
        reports: List of EvaluationReport objects (one per evaluator).

    Returns:
        Dict with "creation" and "verification" sub-dicts mapping
        evaluator label to average score.
    """
    creation_scores = {}
    verification_scores = {}

    for evaluator, report in zip(evaluators, reports):
        # Determine the label from the evaluator's detailed results
        label = _get_evaluator_label(evaluator, report)
        score = report.overall_score

        if label in CREATION_LABEL_PREFIXES:
            creation_scores[label] = round(score, 4)
        elif label in VERIFICATION_LABEL_PREFIXES:
            verification_scores[label] = round(score, 4)
        else:
            # Fallback: use class name
            name = type(evaluator).__name__
            if any(name.startswith(p) for p in ("Schema", "Field", "Score", "Date", "Dimension", "Tier")):
                creation_scores[label] = round(score, 4)
            else:
                verification_scores[label] = round(score, 4)

    # Compute overall pass rates (exclude the pass_rate key itself)
    if creation_scores:
        score_values = [v for k, v in creation_scores.items() if k != "overall_pass_rate"]
        creation_scores["overall_pass_rate"] = round(
            sum(1 for v in score_values if v == 1.0) / len(score_values), 4
        ) if score_values else 0.0
    if verification_scores:
        score_values = [v for k, v in verification_scores.items() if k != "overall_pass_rate"]
        verification_scores["overall_pass_rate"] = round(
            sum(1 for v in score_values if v == 1.0) / len(score_values), 4
        ) if score_values else 0.0

    return {"creation": creation_scores, "verification": verification_scores}


def _get_evaluator_label(evaluator, report) -> str:
    """Extract a human-readable label from an evaluator + its report."""
    # Check detailed_results for labels
    if report.detailed_results:
        for case_outputs in report.detailed_results:
            for output in case_outputs:
                if hasattr(output, "label") and output.label:
                    return output.label

    # Fallback to class name → snake_case
    import re
    name = type(evaluator).__name__
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower().replace("_evaluator", "")


def extract_case_results(cases: list, task_fn_results: list[dict]) -> list[dict]:
    """Build per-case result dicts from task function outputs.

    Flattens key fields to top level for dashboard compatibility.
    Includes full nested data for local backup, slim version for DDB.
    """
    results = []
    for case, tf_result in zip(cases, task_fn_results):
        bundle = tf_result.get("creation_bundle") or {}
        vresult = tf_result.get("verification_result") or {}
        review = bundle.get("plan_review", {})

        entry = {
            "case_id": case.name,
            "id": case.name,
            "prediction_text": case.input,
            "expected_output": case.expected_output,
            "expected_verdict": case.expected_output,
            "verification_mode": (case.metadata or {}).get("verification_mode"),
            # Flat fields for dashboard compatibility
            "verifiability_score": review.get("verifiability_score"),
            "score_tier": review.get("score_tier"),
            "actual_verdict": vresult.get("verdict"),
            "confidence": vresult.get("confidence"),
            # Durations
            "creation_duration": tf_result.get("creation_duration", 0.0),
            "verification_duration": tf_result.get("verification_duration", 0.0),
            # Errors
            "creation_error": tf_result.get("creation_error"),
            "verification_error": tf_result.get("verification_error"),
            "prediction_id": tf_result.get("prediction_id"),
            # Full nested data (for local backup — stripped for DDB)
            "creation_bundle": bundle or None,
            "verification_result": vresult or None,
        }
        results.append(entry)
    return results


def slim_case_results(case_results: list[dict]) -> list[dict]:
    """Strip large nested data for DDB storage. Keeps flat summary fields only."""
    slim = []
    for cr in case_results:
        entry = {k: v for k, v in cr.items()
                 if k not in ("creation_bundle", "verification_result")}
        slim.append(entry)
    return slim


def print_summary(report: dict) -> None:
    """Print eval summary to stdout."""
    meta = report["run_metadata"]
    print(f"\n{'='*60}")
    print(f"CalledIt Eval — Strands Evals SDK")
    print(f"{'='*60}")
    print(f"Description: {meta['description']}")
    print(f"Tier: {meta['run_tier']}  Cases: {meta['case_count']}  "
          f"Duration: {meta['duration_seconds']}s")
    print(f"Git: {meta['git_commit']}  Prompts: {meta['prompt_versions']}")

    print(f"\n--- Creation Scores ---")
    for k, v in report.get("creation_scores", {}).items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    print(f"\n--- Verification Scores ---")
    for k, v in report.get("verification_scores", {}).items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    if report.get("calibration_scores"):
        print(f"\n--- Calibration ---")
        for k, v in report["calibration_scores"].items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")

    print(f"\n{'='*60}")


def print_dry_run(cases: list[Case]) -> None:
    """Print qualifying cases without executing."""
    qualifying = [c for c in cases if c.metadata.get("qualifying")]
    non_qualifying = [c for c in cases if not c.metadata.get("qualifying")]

    print(f"\nDry run — {len(cases)} total cases")
    print(f"  Qualifying (non-null expected): {len(qualifying)}")
    print(f"  Non-qualifying: {len(non_qualifying)}")
    print(f"\nQualifying cases:")
    for c in qualifying:
        print(f"  {c.name}: mode={c.metadata.get('verification_mode')}, "
              f"expected={c.expected_output}, "
              f"smoke={c.metadata.get('smoke_test')}")
    if non_qualifying:
        print(f"\nNon-qualifying cases (creation-only eval):")
        for c in non_qualifying[:10]:
            print(f"  {c.name}: mode={c.metadata.get('verification_mode')}")
        if len(non_qualifying) > 10:
            print(f"  ... and {len(non_qualifying) - 10} more")


def _load_existing_bundles(cases: list, eval_table_name: str) -> list[dict]:
    """Load existing creation bundles from DDB for --verify-only mode."""
    import boto3
    ddb = boto3.resource("dynamodb", region_name="us-west-2")
    table = ddb.Table(eval_table_name)

    results = []
    for case in cases:
        case_id = case.name or "unknown"
        # Try to find a bundle by scanning for this prediction text
        # The prediction_id is stored in the bundle, not predictable from case_id
        # For verify-only, we need the bundles to already exist from a previous creation run
        try:
            # Query by prediction text match in the eval table
            resp = table.scan(
                FilterExpression="raw_prediction = :pt",
                ExpressionAttributeValues={":pt": case.input},
                Limit=1,
            )
            items = resp.get("Items", [])
            if items:
                item = items[0]
                prediction_id = item.get("prediction_id") or item["PK"].replace("PRED#", "")
                bundle = {
                    "parsed_claim": item.get("parsed_claim", {}),
                    "verification_plan": item.get("verification_plan", {}),
                    "plan_review": {
                        "verifiability_score": float(item.get("verifiability_score", 0)),
                        "score_tier": item.get("score_tier"),
                        "dimension_assessments": item.get("dimension_assessments", []),
                    },
                    "prompt_versions": item.get("prompt_versions", {}),
                    "prediction_id": prediction_id,
                }
                results.append({
                    "case": case,
                    "creation_bundle": bundle,
                    "prediction_id": prediction_id,
                    "creation_error": None,
                    "creation_duration": 0.0,
                })
                logger.info("Case %s: loaded existing bundle (prediction_id=%s)", case_id, prediction_id)
            else:
                results.append({
                    "case": case,
                    "creation_bundle": None,
                    "prediction_id": None,
                    "creation_error": "No existing bundle found in eval table",
                    "creation_duration": 0.0,
                })
                logger.warning("Case %s: no existing bundle found", case_id)
        except Exception as e:
            results.append({
                "case": case,
                "creation_bundle": None,
                "prediction_id": None,
                "creation_error": str(e),
                "creation_duration": 0.0,
            })

    found = sum(1 for r in results if r.get("creation_bundle"))
    print(f"Loaded {found}/{len(cases)} existing bundles from DDB")
    return results


def run_creation_phase(cases: list, creation_backend, token_refresher=None) -> tuple[list[dict], float]:
    """Phase 1: Run creation agent for all cases. Returns (results, duration)."""
    results = []
    token_time = time.time()
    token_ttl = 3000  # Refresh after 50 min

    start = time.time()
    for i, case in enumerate(cases):
        case_id = case.name or "unknown"

        # Refresh token if needed
        if token_refresher and (time.time() - token_time) > token_ttl:
            logger.info("Refreshing Cognito token")
            try:
                creation_backend.set_token(token_refresher())
                token_time = time.time()
            except Exception as e:
                logger.error("Token refresh failed: %s", e)

        print(f"  [{i+1}/{len(cases)}] Creating {case_id}...", end=" ", flush=True)
        case_start = time.time()
        try:
            bundle = creation_backend.invoke(prediction_text=case.input, case_id=case_id)
            dur = time.time() - case_start
            print(f"OK ({dur:.0f}s, id={bundle.get('prediction_id', '?')[:12]})")
            results.append({
                "case": case,
                "creation_bundle": bundle,
                "prediction_id": bundle.get("prediction_id"),
                "creation_error": None,
                "creation_duration": dur,
            })
        except Exception as e:
            dur = time.time() - case_start
            print(f"FAILED ({dur:.0f}s)")
            logger.error("Case %s: creation failed: %s", case_id, e)
            results.append({
                "case": case,
                "creation_bundle": None,
                "prediction_id": None,
                "creation_error": str(e),
                "creation_duration": dur,
            })

    return results, time.time() - start


def run_verification_phase(creation_results: list, verification_backend, eval_table: str) -> tuple[list[dict], float]:
    """Phase 3: Run verification agent for qualifying cases only.

    Non-qualifying cases (no expected outcome) skip verification — they're
    in the dataset for creation agent testing only, matching production where
    verification runs on a separate schedule.
    """
    results = []
    start = time.time()
    verify_count = 0

    for i, cr in enumerate(creation_results):
        case = cr["case"]
        case_id = case.name or "unknown"
        prediction_id = cr.get("prediction_id")
        qualifying = (case.metadata or {}).get("qualifying", False)

        entry = {
            "creation_bundle": cr.get("creation_bundle"),
            "verification_result": None,
            "creation_error": cr.get("creation_error"),
            "verification_error": None,
            "prediction_id": prediction_id,
            "creation_duration": cr.get("creation_duration", 0.0),
            "verification_duration": 0.0,
        }

        # Skip verification for non-qualifying cases or creation failures
        if cr.get("creation_error") or not prediction_id:
            entry["verification_error"] = cr.get("creation_error") or "No prediction_id"
            results.append(entry)
            continue

        if not qualifying:
            entry["verification_error"] = "Skipped — non-qualifying case"
            results.append(entry)
            continue

        verify_count += 1
        print(f"  [{verify_count}] Verifying {case_id}...", end=" ", flush=True)
        v_start = time.time()
        try:
            vresult = verification_backend.invoke(
                prediction_id=prediction_id, table_name=eval_table, case_id=case_id,
            )
            dur = time.time() - v_start
            print(f"OK ({dur:.0f}s, verdict={vresult.get('verdict')})")
            entry["verification_result"] = vresult
            entry["verification_duration"] = dur
        except Exception as e:
            dur = time.time() - v_start
            print(f"FAILED ({dur:.0f}s)")
            logger.error("Case %s: verification failed: %s", case_id, e)
            entry["verification_error"] = str(e)
            entry["verification_duration"] = dur

        results.append(entry)

    return results, time.time() - start


def main():
    """Main entry point — three-phase batched pipeline.

    Mirrors production architecture:
    1. Creation phase: all predictions created (like user submissions)
    2. Wait phase: single global wait for verification dates (like EventBridge gap)
    3. Verification phase: all predictions verified (like scanner batch)
    4. Evaluation: SDK evaluators score the results
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    args = parse_args()

    # 1. Load cases
    cases = load_cases(
        args.dataset,
        args.dynamic_dataset,
        tier="smoke" if args.tier == "smoke" else None,
        case_id=args.case,
    )

    if args.dry_run:
        print_dry_run(cases)
        return

    if args.qualifying_only:
        cases = [c for c in cases if c.metadata.get("qualifying")]
        if not cases:
            print("Error: no qualifying cases after filtering", file=sys.stderr)
            sys.exit(1)
        print(f"Qualifying-only mode: {len(cases)} cases")

    # 2. Auth
    print("Authenticating with Cognito...")
    token = get_cognito_token()
    creation_backend = AgentCoreBackend(bearer_token=token, table_name=EVAL_TABLE_NAME)
    verification_backend = VerificationBackend()

    # 3. Build evaluators
    evaluators = build_evaluators(args.tier)
    print(f"Evaluators: {len(evaluators)} ({args.tier} tier)")

    start_time = time.time()

    # --- Phase 1: Creation (batch) ---
    if not args.verify_only:
        print(f"\n=== Phase 1: Creation ({len(cases)} cases) ===")
        creation_results, creation_duration = run_creation_phase(
            cases, creation_backend, token_refresher=get_cognito_token,
        )
        successful = sum(1 for r in creation_results if not r.get("creation_error"))
        print(f"Creation complete: {successful}/{len(cases)} OK in {creation_duration:.0f}s")
    else:
        # Verify-only: build creation_results from existing DDB bundles
        print(f"\n=== Phase 1: Skipped (--verify-only) ===")
        creation_results = _load_existing_bundles(cases, EVAL_TABLE_NAME)
        creation_duration = 0.0

    if args.creation_only:
        # Creation-only: skip verification, run creation evaluators only
        print(f"\n=== Phases 2-3: Skipped (--creation-only) ===")
        task_outputs = [{
            "creation_bundle": cr.get("creation_bundle"),
            "verification_result": None,
            "creation_error": cr.get("creation_error"),
            "verification_error": "Skipped — creation-only mode",
            "prediction_id": cr.get("prediction_id"),
            "creation_duration": cr.get("creation_duration", 0.0),
            "verification_duration": 0.0,
        } for cr in creation_results]
        wait_seconds = 0.0
        verification_duration = 0.0
    else:
        # --- Phase 2: Wait (single global wait) ---
        wait_seconds = 0.0
        qualifying_results = [cr for cr in creation_results
                              if (cr["case"].metadata or {}).get("qualifying")]
        for cr in qualifying_results:
            bundle = cr.get("creation_bundle")
            if not bundle:
                continue
            mode = (cr["case"].metadata or {}).get("verification_mode", "immediate")
            w = compute_wait_seconds(bundle, mode)
            wait_seconds = max(wait_seconds, w)

        if wait_seconds > 0:
            print(f"\n=== Phase 2: Wait ({wait_seconds:.0f}s for verification dates) ===")
            time.sleep(wait_seconds)
        else:
            print(f"\n=== Phase 2: No wait needed ===")

        # --- Phase 3: Verification (qualifying cases only) ---
        qualifying_count = sum(1 for cr in creation_results
                               if (cr["case"].metadata or {}).get("qualifying"))
        print(f"\n=== Phase 3: Verification ({qualifying_count} qualifying of {len(creation_results)} total) ===")
        task_outputs, verification_duration = run_verification_phase(
            creation_results, verification_backend, EVAL_TABLE_NAME,
        )

    # --- Phase 4: Evaluation (SDK) ---
    print(f"\n=== Phase 4: Evaluation ({len(evaluators)} evaluators) ===")

    # Build SDK-compatible task outputs for evaluators
    def make_precomputed_task_fn(outputs_by_name):
        """Return a task function that returns precomputed results."""
        def task_fn(case):
            result = outputs_by_name.get(case.name, {
                "creation_bundle": None, "verification_result": None,
                "creation_error": "not run", "verification_error": "not run",
                "prediction_id": None, "creation_duration": 0, "verification_duration": 0,
            })
            return {"output": result}
        return task_fn

    outputs_by_name = {cases[i].name: task_outputs[i] for i in range(len(cases))}
    precomputed_fn = make_precomputed_task_fn(outputs_by_name)

    experiment = Experiment(cases=cases, evaluators=evaluators)
    reports = experiment.run_evaluations(precomputed_fn)

    total_duration = time.time() - start_time
    print(f"\nAll phases complete in {total_duration:.0f}s "
          f"(creation={creation_duration:.0f}s, wait={wait_seconds:.0f}s, "
          f"verification={verification_duration:.0f}s)")

    # 5. Extract evaluator scores
    evaluator_scores = extract_evaluator_scores(evaluators, reports)

    # 6. Calibration (full tier only)
    calibration_scores = {}
    if args.tier == "full" and task_outputs:
        calibration_scores = compute_calibration(task_outputs)

    # 7. Build report
    case_results = extract_case_results(cases, task_outputs)
    report = build_report(args, case_results, evaluator_scores, calibration_scores, total_duration)

    # Add phase durations to metadata
    report["run_metadata"]["phase_durations"] = {
        "creation_seconds": round(creation_duration, 1),
        "wait_seconds": round(wait_seconds, 1),
        "verification_seconds": round(verification_duration, 1),
    }

    # 8. Write to DDB
    try:
        from eval.report_store import write_report
        write_report("unified", report)
        print("Report written to DDB")
    except Exception as e:
        logger.warning("DDB write failed: %s", e)

    # 9. Optional local backup
    if args.local_backup:
        os.makedirs("eval/reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = f"eval/reports/sdk-eval-{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Local backup: {path}")

    # 10. Cleanup
    if not args.skip_cleanup:
        pass  # TODO: cleanup eval table bundles

    # 11. Print summary
    print_summary(report)


if __name__ == "__main__":
    main()
