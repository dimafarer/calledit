"""Cross-Agent Calibration Eval Runner.

Chains creation agent → verification agent per case.
Measures whether verifiability_score predicts verification success.

Usage:
    python eval/calibration_eval.py --tier smoke --description "baseline"
    python eval/calibration_eval.py --tier full --description "full calibration"
    python eval/calibration_eval.py --dry-run
    python eval/calibration_eval.py --case base-002

Requires:
    - COGNITO_USERNAME + COGNITO_PASSWORD env vars (creation agent JWT auth)
    - AWS credentials (verification agent SigV4 auth)
    - All Python commands use /home/wsluser/projects/calledit/venv/bin/python
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import boto3

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_TABLE_NAME = "calledit-v4-eval"
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

BIAS_WARNING = (
    "All qualifying verification cases have 'confirmed' expected outcomes. "
    "Calibration accuracy for 'refuted' and 'inconclusive' predictions "
    "cannot be measured with the current dataset."
)

GROUND_TRUTH_LIMITATION = (
    "All qualifying golden cases have 'confirmed' expected outcomes. "
    "Verdict accuracy for 'refuted' and 'inconclusive' cannot be measured "
    "deterministically with the current golden dataset."
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CalibrationCase:
    id: str
    prediction_text: str
    expected_verdict: Optional[str]
    ground_truth: dict
    metadata: dict


# ---------------------------------------------------------------------------
# Score tier classification
# ---------------------------------------------------------------------------

def classify_score_tier(score: float) -> str:
    """Map verifiability_score to tier: high (>=0.7), moderate (>=0.4), low (<0.4)."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    return "low"


def is_calibration_correct(score_tier: str, verdict: str) -> bool:
    """Check if score tier prediction aligned with verdict outcome.

    high → confirmed = correct
    low → refuted/inconclusive = correct
    moderate → always correct (indeterminate zone)
    """
    if score_tier == "high":
        return verdict == "confirmed"
    if score_tier == "low":
        return verdict in ("refuted", "inconclusive")
    return True  # moderate is always "correct"


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------

def compute_calibration_metrics(case_results: list[dict]) -> dict:
    """Compute aggregate calibration metrics from case results.

    Returns dict with: calibration_accuracy, mean_absolute_error,
    high_score_confirmation_rate, low_score_failure_rate, verdict_distribution.
    """
    verdict_dist = {
        "confirmed": 0, "refuted": 0, "inconclusive": 0,
        "creation_error": 0, "verification_error": 0,
    }

    correct_count = 0
    total_scored = 0
    mae_sum = 0.0
    mae_count = 0
    high_confirmed = 0
    high_total = 0
    low_failed = 0
    low_total = 0

    for case in case_results:
        error = case.get("error")
        if error:
            if "creation_error" in str(error):
                verdict_dist["creation_error"] += 1
            else:
                verdict_dist["verification_error"] += 1
            continue

        verdict = case.get("actual_verdict", "")
        score_tier = case.get("score_tier", "")
        v_score = case.get("verifiability_score", 0.0)

        if verdict in verdict_dist:
            verdict_dist[verdict] += 1

        # Calibration accuracy
        if is_calibration_correct(score_tier, verdict):
            correct_count += 1
        total_scored += 1

        # MAE: |verifiability_score - binary_outcome|
        binary = 1.0 if verdict == "confirmed" else 0.0
        mae_sum += abs(v_score - binary)
        mae_count += 1

        # High score confirmation rate
        if score_tier == "high":
            high_total += 1
            if verdict == "confirmed":
                high_confirmed += 1

        # Low score failure rate
        if score_tier == "low":
            low_total += 1
            if verdict in ("refuted", "inconclusive"):
                low_failed += 1

    return {
        "calibration_accuracy": round(correct_count / total_scored, 4) if total_scored else 0.0,
        "mean_absolute_error": round(mae_sum / mae_count, 4) if mae_count else 0.0,
        "high_score_confirmation_rate": round(high_confirmed / high_total, 4) if high_total else 0.0,
        "low_score_failure_rate": round(low_failed / low_total, 4) if low_total else 0.0,
        "verdict_distribution": verdict_dist,
    }


# ---------------------------------------------------------------------------
# Dataset loading (reuses verification_eval pattern)
# ---------------------------------------------------------------------------

def load_dataset(path: str) -> dict:
    """Load and validate golden dataset JSON."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Error: dataset file not found: {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"Error: invalid JSON in dataset: {e}")
    if "base_predictions" not in data:
        sys.exit("Error: golden dataset missing 'base_predictions' array")
    return data


def load_cases(dataset: dict, tier: str, case_id: Optional[str] = None) -> list[CalibrationCase]:
    """Load qualifying cases: verification_readiness=immediate + expected_verification_outcome set."""
    qualifying = [
        bp for bp in dataset["base_predictions"]
        if bp.get("verification_readiness") == "immediate"
        and bp.get("expected_verification_outcome") is not None
    ]
    if not qualifying:
        sys.exit("Error: no qualifying cases found")

    cases = [
        CalibrationCase(
            id=bp["id"],
            prediction_text=bp["prediction_text"],
            expected_verdict=bp["expected_verification_outcome"],
            ground_truth=bp.get("ground_truth", {}),
            metadata={
                "id": bp["id"],
                "difficulty": bp.get("difficulty"),
                "smoke_test": bp.get("smoke_test", False),
            },
        )
        for bp in qualifying
    ]

    if case_id:
        matches = [c for c in cases if c.id == case_id]
        if not matches:
            sys.exit(f"Error: case '{case_id}' not found. Available: {[c.id for c in cases]}")
        return matches

    if tier == "smoke":
        smoke = [c for c in cases if c.metadata.get("smoke_test")]
        if not smoke:
            sys.exit("Error: no smoke test cases found among qualifying cases")
        return smoke

    return cases  # full


# ---------------------------------------------------------------------------
# Eval table lifecycle (reuses verification_eval pattern)
# ---------------------------------------------------------------------------

def _ensure_eval_table(ddb) -> object:
    """Create calledit-v4-eval table if needed. Returns table resource."""
    client = ddb.meta.client
    try:
        client.describe_table(TableName=EVAL_TABLE_NAME)
    except client.exceptions.ResourceNotFoundException:
        logger.info(f"Creating eval table '{EVAL_TABLE_NAME}'...")
        try:
            ddb.create_table(
                TableName=EVAL_TABLE_NAME,
                KeySchema=[
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=EVAL_TABLE_NAME)
        except Exception as e:
            sys.exit(f"Error creating eval table: {e}")
    return ddb.Table(EVAL_TABLE_NAME)


def _shape_bundle(case: CalibrationCase, bundle: dict) -> dict:
    """Shape a creation agent bundle into the DDB item format for verification."""
    from decimal import Decimal

    def _to_decimal(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: _to_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_decimal(v) for v in obj]
        return obj

    return _to_decimal({
        "PK": f"PRED#{bundle['prediction_id']}",
        "SK": "BUNDLE",
        "prediction_id": bundle["prediction_id"],
        "status": "pending",
        "verification_mode": "immediate",
        "parsed_claim": bundle.get("parsed_claim", {}),
        "verification_plan": bundle.get("verification_plan", {}),
        "verifiability_score": bundle.get("plan_review", {}).get("verifiability_score", 0.0),
        "prompt_versions": bundle.get("prompt_versions", {}),
    })


def write_bundle(table, item: dict) -> None:
    """Write a shaped bundle to the eval table."""
    table.put_item(Item=item)


def cleanup_bundles(table, prediction_ids: list[str]) -> None:
    """Delete temp bundles from eval table. Best-effort."""
    for pid in prediction_ids:
        try:
            table.delete_item(Key={"PK": f"PRED#{pid}", "SK": "BUNDLE"})
        except Exception as e:
            logger.warning(f"Cleanup failed for {pid}: {e}")


# ---------------------------------------------------------------------------
# Calibration pipeline
# ---------------------------------------------------------------------------

def run_calibration(
    cases: list[CalibrationCase],
    creation_backend,
    verification_backend,
    eval_table,
) -> list[dict]:
    """Run creation→verification pipeline for each case. Returns case_results."""
    results = []
    written_pids = []

    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.id}: {case.prediction_text[:60]}...")
        result = {
            "id": case.id,
            "prediction_text": case.prediction_text,
            "expected_verdict": case.expected_verdict,
            "error": None,
        }

        # Step 1: Creation agent
        creation_start = time.time()
        try:
            bundle = creation_backend.invoke(case.prediction_text, case_id=case.id)
            creation_duration = time.time() - creation_start
        except Exception as e:
            creation_duration = time.time() - creation_start
            result["error"] = f"creation_error: {e}"
            result["creation_duration_seconds"] = round(creation_duration, 1)
            result["verification_duration_seconds"] = 0.0
            result["verifiability_score"] = None
            result["score_tier"] = None
            result["actual_verdict"] = None
            result["actual_confidence"] = None
            result["calibration_correct"] = None
            print(f"  ✗ creation error: {e}")
            results.append(result)
            continue

        v_score = bundle.get("plan_review", {}).get("verifiability_score", 0.0)
        score_tier = classify_score_tier(v_score)
        prediction_id = bundle.get("prediction_id")

        result["verifiability_score"] = v_score
        result["score_tier"] = score_tier
        result["creation_duration_seconds"] = round(creation_duration, 1)

        print(f"  → created: score={v_score}, tier={score_tier}, pid={prediction_id}")

        # Step 2: Write bundle to eval table
        try:
            shaped = _shape_bundle(case, bundle)
            write_bundle(eval_table, shaped)
            written_pids.append(prediction_id)
        except Exception as e:
            result["error"] = f"verification_error: eval table write failed: {e}"
            result["verification_duration_seconds"] = 0.0
            result["actual_verdict"] = None
            result["actual_confidence"] = None
            result["calibration_correct"] = None
            results.append(result)
            continue

        # Step 3: Verification agent
        verification_start = time.time()
        try:
            verdict_result = verification_backend.invoke(
                prediction_id=prediction_id,
                table_name=EVAL_TABLE_NAME,
                case_id=case.id,
            )
            verification_duration = time.time() - verification_start
        except Exception as e:
            verification_duration = time.time() - verification_start
            result["error"] = f"verification_error: {e}"
            result["verification_duration_seconds"] = round(verification_duration, 1)
            result["actual_verdict"] = None
            result["actual_confidence"] = None
            result["calibration_correct"] = None
            print(f"  ✗ verification error: {e}")
            results.append(result)
            continue

        actual_verdict = verdict_result.get("verdict", "unknown")
        actual_confidence = verdict_result.get("confidence", 0.0)
        calibration_correct = is_calibration_correct(score_tier, actual_verdict)

        result["verification_duration_seconds"] = round(verification_duration, 1)
        result["actual_verdict"] = actual_verdict
        result["actual_confidence"] = actual_confidence
        result["calibration_correct"] = calibration_correct

        print(f"  → verified: verdict={actual_verdict}, confidence={actual_confidence}, calibrated={calibration_correct}")
        results.append(result)

    # Cleanup all written bundles
    if written_pids:
        print(f"\nCleaning up {len(written_pids)} bundle(s) from eval table...")
        cleanup_bundles(eval_table, written_pids)
        print("✓ Cleanup complete")

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(
    args, dataset: dict, case_results: list[dict], duration: float
) -> dict:
    """Build the calibration report."""
    now = datetime.now(timezone.utc).isoformat()
    description = args.description or f"calibration {args.tier} — {now[:19]}"

    metrics = compute_calibration_metrics(case_results)

    # Check for dataset bias
    expected_verdicts = set(
        r.get("expected_verdict") for r in case_results if r.get("expected_verdict")
    )
    bias_warning = BIAS_WARNING if len(expected_verdicts) <= 1 else None

    return {
        "run_metadata": {
            "description": description,
            "agent": "calibration",
            "run_tier": args.tier,
            "dataset_version": dataset.get("dataset_version", "unknown"),
            "timestamp": now,
            "duration_seconds": round(duration, 1),
            "case_count": len(case_results),
            "dataset_sources": [args.dataset] + ([args.dynamic_dataset] if getattr(args, 'dynamic_dataset', None) else []),
            "ground_truth_limitation": GROUND_TRUTH_LIMITATION,
        },
        "aggregate_scores": metrics,
        "case_results": case_results,
        "bias_warning": bias_warning,
    }


def save_report(report: dict, output_dir: str) -> str:
    """Save report as calibration-eval-{YYYYMMDD-HHMMSS}.json."""
    os.makedirs(output_dir, exist_ok=True)
    ts = report["run_metadata"]["timestamp"]
    dt = datetime.fromisoformat(ts)
    filename = f"calibration-eval-{dt.strftime('%Y%m%d-%H%M%S')}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Cross-Agent Calibration Eval Runner")
    parser.add_argument("--tier", choices=["smoke", "full"], default="smoke",
                        help="Run tier (default: smoke)")
    parser.add_argument("--dataset", default="eval/golden_dataset.json",
                        help="Path to golden dataset")
    parser.add_argument("--description", default=None,
                        help="One-line description for this run")
    parser.add_argument("--output-dir", default="eval/reports",
                        help="Report output directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="List cases without executing")
    parser.add_argument("--case", default=None,
                        help="Execute single case by id")
    parser.add_argument("--dynamic-dataset", default=None,
                        help="Path to dynamic golden dataset (merged with --dataset)")
    return parser.parse_args()


def print_dry_run(cases: list[CalibrationCase]) -> None:
    """Print cases that would be executed."""
    print(f"\nDry run — {len(cases)} case(s) would be executed:\n")
    for case in cases:
        smoke = "smoke" if case.metadata.get("smoke_test") else "     "
        expected = case.expected_verdict or "N/A"
        diff = case.metadata.get("difficulty") or "?"
        print(f"  [{smoke}] {case.id} ({diff}) expected={expected}")
        print(f"         {case.prediction_text[:80]}")
    print()


def print_summary(report: dict) -> None:
    """Print calibration summary to stdout."""
    meta = report["run_metadata"]
    scores = report["aggregate_scores"]
    print(f"\n=== Cross-Agent Calibration Report ===")
    print(f"Tier: {meta['run_tier']}  Cases: {meta['case_count']}")
    print(f"Duration: {meta['duration_seconds']}s")
    print(f"\nCalibration Metrics:")
    print(f"  calibration_accuracy: {scores['calibration_accuracy']:.4f}")
    print(f"  mean_absolute_error: {scores['mean_absolute_error']:.4f}")
    print(f"  high_score_confirmation_rate: {scores['high_score_confirmation_rate']:.4f}")
    print(f"  low_score_failure_rate: {scores['low_score_failure_rate']:.4f}")
    print(f"\nVerdict Distribution:")
    for k, v in scores["verdict_distribution"].items():
        if v > 0:
            print(f"  {k}: {v}")
    print(f"\nPer-case results:")
    for r in report["case_results"]:
        if r.get("error"):
            print(f"  {r['id']}: ERROR — {r['error'][:80]}")
        else:
            cal = "✓" if r.get("calibration_correct") else "✗"
            print(
                f"  {r['id']}: score={r['verifiability_score']:.2f} "
                f"({r['score_tier']}) → {r['actual_verdict']} "
                f"(conf={r['actual_confidence']}) [{cal}]"
            )
    if report.get("bias_warning"):
        print(f"\n⚠ {report['bias_warning']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.WARNING)
    args = parse_args()

    # Validate credentials early
    cognito_user = os.environ.get("COGNITO_USERNAME", "")
    cognito_pass = os.environ.get("COGNITO_PASSWORD", "")
    if not cognito_user or not cognito_pass:
        sys.exit(
            "Error: Set COGNITO_USERNAME and COGNITO_PASSWORD environment "
            "variables for creation agent JWT auth."
        )

    # Load dataset and cases
    from eval.dataset_merger import load_and_merge
    dataset = load_and_merge(args.dataset, getattr(args, 'dynamic_dataset', None))
    cases = load_cases(dataset, args.tier, args.case)

    if args.dry_run:
        print_dry_run(cases)
        return

    # Initialize backends
    from eval.backends.agentcore_backend import AgentCoreBackend, get_cognito_token
    from eval.backends.verification_backend import VerificationBackend

    print("Authenticating with Cognito...")
    token = get_cognito_token()
    creation_backend = AgentCoreBackend(bearer_token=token)
    verification_backend = VerificationBackend()
    print("Backends initialized (JWT + SigV4)\n")

    # Setup eval table
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    eval_table = _ensure_eval_table(ddb)

    # Run calibration
    print(f"Running {len(cases)} case(s) through creation→verification pipeline...\n")
    start = time.time()
    results = run_calibration(cases, creation_backend, verification_backend, eval_table)
    duration = time.time() - start

    # Build and save report
    report = build_report(args, dataset, results, duration)
    path = save_report(report, args.output_dir)

    # DDB write
    try:
        from eval.report_store import write_report
        write_report("calibration", report)
    except Exception as e:
        logger.warning(f"DDB report write failed (non-fatal): {e}")

    print_summary(report)
    print(f"\nReport saved: {path}")
    print(f"Description: {report['run_metadata']['description']}")


if __name__ == "__main__":
    main()
