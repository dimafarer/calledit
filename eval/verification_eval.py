"""Verification Agent Eval Runner (V4-7a-3).

CLI-driven eval runner for the v4 verification agent. Invokes the deployed
agent via HTTPS with JWT auth, applies tiered evaluators, and produces JSON
reports.

Scope: verification_mode=immediate only. See backlog item 0 for other modes.

Usage:
    # Smoke run (2 cases, Tier 1 only)
    python eval/verification_eval.py --tier smoke

    # Smoke with judges
    python eval/verification_eval.py --tier smoke+judges --description "baseline"

    # Full run
    python eval/verification_eval.py --tier full --description "full baseline"

    # DDB mode (live predictions, no ground truth)
    python eval/verification_eval.py --source ddb

    # Dry run
    python eval/verification_eval.py --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from eval.backends.verification_backend import VerificationBackend
from eval.evaluators import (
    verification_schema_validity,
    verification_verdict_validity,
    verification_confidence_range,
    verification_evidence_completeness,
    verification_evidence_structure,
    verification_verdict_accuracy,
    verification_evidence_quality,
)

logger = logging.getLogger(__name__)

EVAL_TABLE_NAME = "calledit-v4-eval"
PROD_TABLE_NAME = "calledit-v4"
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")

GROUND_TRUTH_LIMITATION = (
    "All 7 qualifying golden cases have 'confirmed' expected outcomes. "
    "Verdict accuracy for 'refuted' and 'inconclusive' cannot be measured "
    "deterministically with the current golden dataset."
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class EvalCase:
    prediction_id: str
    prediction_text: str
    expected_verdict: Optional[str]   # None in ddb mode
    ground_truth: dict
    metadata: dict


# ---------------------------------------------------------------------------
# Dataset loading
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


def load_golden_cases(
    dataset: dict, tier: str, case_id: Optional[str] = None
) -> list:
    """Load qualifying cases from golden dataset.

    Qualifying = verification_readiness=immediate AND expected_verification_outcome non-null.
    """
    qualifying = [
        bp for bp in dataset["base_predictions"]
        if bp.get("verification_readiness") == "immediate"
        and bp.get("expected_verification_outcome") is not None
    ]

    if not qualifying:
        sys.exit(
            "Error: no qualifying cases found in golden dataset "
            "(need verification_readiness=immediate and expected_verification_outcome set)"
        )

    cases = [
        EvalCase(
            prediction_id=bp["id"],
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
        matches = [c for c in cases if c.prediction_id == case_id]
        if not matches:
            sys.exit(
                f"Error: case '{case_id}' not found in qualifying cases. "
                f"Available: {[c.prediction_id for c in cases]}"
            )
        return matches

    if tier in ("smoke", "smoke+judges"):
        smoke_cases = [c for c in cases if c.metadata.get("smoke_test")]
        if not smoke_cases:
            sys.exit("Error: no smoke test cases found among qualifying cases")
        return smoke_cases

    return cases  # full tier


def load_ddb_cases() -> list:
    """Query calledit-v4 table for verification_readiness=immediate items."""
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = ddb.Table(PROD_TABLE_NAME)

    try:
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr(
                "verification_readiness"
            ).eq("immediate")
        )
        items = response.get("Items", [])
    except Exception as e:
        sys.exit(f"Error querying {PROD_TABLE_NAME}: {e}")

    if not items:
        sys.exit(
            f"Error: no items with verification_readiness=immediate found in {PROD_TABLE_NAME}"
        )

    return [
        EvalCase(
            prediction_id=item.get("prediction_id", item.get("PK", "").replace("PRED#", "")),
            prediction_text=item.get("parsed_claim", {}).get("statement", ""),
            expected_verdict=None,  # no ground truth in ddb mode
            ground_truth={},
            metadata={"id": item.get("prediction_id", ""), "difficulty": None, "smoke_test": False},
        )
        for item in items
    ]


# ---------------------------------------------------------------------------
# Eval table manager
# ---------------------------------------------------------------------------

def _ensure_table_exists(ddb) -> object:
    """Create calledit-v4-eval table if it doesn't exist, return table resource."""
    client = ddb.meta.client
    try:
        client.describe_table(TableName=EVAL_TABLE_NAME)
        logger.info(f"Eval table '{EVAL_TABLE_NAME}' already exists")
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
            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=EVAL_TABLE_NAME)
            logger.info(f"Eval table '{EVAL_TABLE_NAME}' created")
        except Exception as e:
            sys.exit(f"Error creating eval table '{EVAL_TABLE_NAME}': {e}")

    return ddb.Table(EVAL_TABLE_NAME)


def _shape_bundle(case: EvalCase) -> dict:
    """Shape a golden case into the DDB item format the verification agent expects.

    The bundle must satisfy load_bundle_from_ddb() (strips PK/SK, returns rest)
    and the agent's status='pending' condition check.
    verification_mode='immediate' is always set — V4-7a-3 scope.
    """
    gt = case.ground_truth
    return {
        "PK": f"PRED#{case.prediction_id}",
        "SK": "BUNDLE",
        "prediction_id": case.prediction_id,
        "status": "pending",
        "verification_mode": "immediate",
        "parsed_claim": {
            "statement": case.prediction_text,
            "verification_date": gt.get("verification_timing", ""),
            "date_reasoning": gt.get("date_derivation", ""),
        },
        "verification_plan": {
            "sources": gt.get("verification_sources", []),
            "criteria": gt.get(
                "expected_verification_criteria",
                gt.get("verification_criteria", []),
            ),
            "steps": gt.get("verification_steps", []),
        },
        "prompt_versions": {},
    }


def setup_eval_table(cases: list) -> None:
    """Create eval table if needed and write all case bundles.

    Exits with error if any write fails — do not run partial eval.
    """
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = _ensure_table_exists(ddb)

    print(f"Writing {len(cases)} bundle(s) to eval table '{EVAL_TABLE_NAME}'...")
    for case in cases:
        bundle = _shape_bundle(case)
        try:
            table.put_item(Item=bundle)
        except Exception as e:
            sys.exit(
                f"Error writing bundle for case '{case.prediction_id}' to eval table: {e}"
            )
    print(f"  ✓ {len(cases)} bundle(s) written")


def cleanup_eval_table(cases: list) -> None:
    """Delete all items written during this run. Best-effort — logs on failure."""
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = ddb.Table(EVAL_TABLE_NAME)

    print(f"Cleaning up {len(cases)} item(s) from eval table...")
    for case in cases:
        try:
            table.delete_item(
                Key={"PK": f"PRED#{case.prediction_id}", "SK": "BUNDLE"}
            )
        except Exception as e:
            logger.warning(
                f"Cleanup failed for case '{case.prediction_id}': {e} — continuing"
            )
    print("  ✓ Cleanup complete")


# ---------------------------------------------------------------------------
# Evaluator list builder
# ---------------------------------------------------------------------------

def build_evaluator_list(args) -> dict:
    """Build the evaluator dict based on source mode and tier.

    Returns:
        dict mapping evaluator name -> evaluator module
    """
    tier1 = {
        "schema_validity": verification_schema_validity,
        "verdict_validity": verification_verdict_validity,
        "confidence_range": verification_confidence_range,
        "evidence_completeness": verification_evidence_completeness,
        "evidence_structure": verification_evidence_structure,
    }

    if args.tier == "smoke" and args.source == "golden":
        return tier1

    # smoke+judges, full (golden), or any ddb run — add Tier 2
    evaluators = dict(tier1)
    # Verdict accuracy only in golden mode (requires ground truth)
    if args.source == "golden":
        evaluators["verdict_accuracy"] = verification_verdict_accuracy
    evaluators["evidence_quality"] = verification_evidence_quality
    return evaluators


# ---------------------------------------------------------------------------
# Eval orchestration
# ---------------------------------------------------------------------------

def run_eval(cases: list, backend, evaluators: dict, source: str) -> list:
    """Run eval for all cases. Catches per-case errors without aborting."""
    results = []
    total = len(cases)

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{total}] {case.prediction_id}: {case.prediction_text[:60]}...")
        result = {"id": case.prediction_id, "prediction_text": case.prediction_text,
                  "expected_verdict": case.expected_verdict, "scores": {}}

        # Invoke backend
        try:
            table_name = EVAL_TABLE_NAME if source == "golden" else None
            verdict_response = backend.invoke(
                prediction_id=case.prediction_id,
                table_name=table_name,
                case_id=case.prediction_id,
            )
        except Exception as e:
            result["error"] = str(e)
            print(f"    ✗ Backend error: {e}")
            results.append(result)
            continue

        actual_verdict = verdict_response.get("verdict", "unknown")
        print(f"    → verdict: {actual_verdict}, confidence: {verdict_response.get('confidence')}")

        # Run Tier 1 evaluators
        for name, evaluator in evaluators.items():
            if name == "verdict_accuracy":
                score = evaluator.evaluate(verdict_response, case.expected_verdict)
                if score is not None:
                    result["scores"][name] = score
            elif name == "evidence_quality":
                score = evaluator.evaluate(verdict_response, case.prediction_text)
                result["scores"][name] = score
            else:
                result["scores"][name] = evaluator.evaluate(verdict_response)

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def compute_aggregates(results: list, evaluators: dict) -> dict:
    """Compute per-evaluator averages and overall pass rate."""
    evaluator_names = list(evaluators.keys())
    tier1_names = [
        "schema_validity", "verdict_validity", "confidence_range",
        "evidence_completeness", "evidence_structure",
    ]

    aggregates = {}
    for name in evaluator_names:
        scores = [
            r["scores"][name]["score"]
            for r in results
            if name in r.get("scores", {}) and r["scores"][name] is not None
        ]
        aggregates[name] = round(sum(scores) / len(scores), 4) if scores else None

    # Overall pass rate: fraction where all T1 evaluators = 1.0
    pass_count = sum(
        1 for r in results
        if all(
            r.get("scores", {}).get(n, {}).get("score", 0.0) == 1.0
            for n in tier1_names
            if n in evaluators
        )
        and "error" not in r
    )
    aggregates["overall_pass_rate"] = round(pass_count / len(results), 4) if results else 0.0

    return aggregates


def build_run_metadata(args, dataset: dict, results: list, duration: float) -> dict:
    """Build structured run metadata."""
    description = args.description
    if not description:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        description = f"Verification eval — {args.source} / {args.tier} — {ts}"

    dataset_version = dataset.get("dataset_version", "unknown") if dataset else "ddb-live"
    run_tier = args.tier if args.source == "golden" else "all"

    return {
        "description": description,
        "agent": "verification",
        "source": args.source,
        "run_tier": run_tier,
        "dataset_version": dataset_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 1),
        "case_count": len(results),
        "ground_truth_limitation": GROUND_TRUTH_LIMITATION,
    }


def build_report(metadata: dict, results: list, evaluators: dict) -> dict:
    """Build the full eval report."""
    return {
        "run_metadata": metadata,
        "aggregate_scores": compute_aggregates(results, evaluators),
        "case_results": results,
    }


def save_report(report: dict, output_dir: str) -> str:
    """Save report as verification-eval-{YYYYMMDD-HHMMSS}.json."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"verification-eval-{ts}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Verification Agent Eval Runner")
    parser.add_argument("--source", choices=["golden", "ddb"], default="golden",
                        help="Data source: golden dataset or live DDB (default: golden)")
    parser.add_argument("--dataset", default="eval/golden_dataset.json",
                        help="Path to golden dataset (default: eval/golden_dataset.json)")
    parser.add_argument("--tier", choices=["smoke", "smoke+judges", "full"], default="smoke",
                        help="Run tier (golden mode only, default: smoke)")
    parser.add_argument("--description", default=None,
                        help="One-line description for this run")
    parser.add_argument("--output-dir", default="eval/reports",
                        help="Report output directory (default: eval/reports)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List cases without executing")
    parser.add_argument("--case", default=None,
                        help="Execute single case by id (golden mode only)")
    return parser.parse_args()


def print_dry_run(cases: list) -> None:
    """Print cases that would be executed without running anything."""
    print(f"\nDry run — {len(cases)} case(s) would be executed:\n")
    for case in cases:
        smoke = "smoke" if case.metadata.get("smoke_test") else "     "
        expected = case.expected_verdict or "N/A"
        diff = case.metadata.get("difficulty") or "?"
        print(f"  [{smoke}] {case.prediction_id} ({diff}) expected={expected}")
        print(f"         {case.prediction_text[:80]}")
    print()


def print_summary(report: dict) -> None:
    """Print run summary to stdout."""
    meta = report["run_metadata"]
    agg = report["aggregate_scores"]
    print(f"\n=== Verification Agent Eval Report ===")
    print(f"Source: {meta['source']}  Tier: {meta['run_tier']}  Cases: {meta['case_count']}")
    print(f"Duration: {meta['duration_seconds']}s")
    print(f"\nTier 1 (deterministic):")
    for name in ["schema_validity", "verdict_validity", "confidence_range",
                 "evidence_completeness", "evidence_structure"]:
        if name in agg and agg[name] is not None:
            print(f"  {name}: {agg[name]:.2f}")
    print(f"  overall_pass_rate: {agg.get('overall_pass_rate', 0.0):.2f}")
    print(f"\nTier 2:")
    for name in ["verdict_accuracy", "evidence_quality"]:
        if name in agg and agg[name] is not None:
            print(f"  {name}: {agg[name]:.2f}")
        elif name in agg:
            print(f"  {name}: (not run)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.WARNING)
    args = parse_args()

    # Load dataset and cases
    dataset = None
    if args.source == "golden":
        dataset = load_dataset(args.dataset)
        cases = load_golden_cases(dataset, args.tier, args.case)
    else:
        cases = load_ddb_cases()

    if args.dry_run:
        print_dry_run(cases)
        return

    # Setup eval table (golden mode only)
    if args.source == "golden":
        setup_eval_table(cases)

    # Build evaluator list
    evaluators = build_evaluator_list(args)

    # Initialize backend (SigV4 — uses AWS credentials, no Cognito token needed)
    backend = VerificationBackend()
    print("Backend initialized (SigV4 auth)\n")

    # Run eval
    print(f"Running {len(cases)} case(s) with {len(evaluators)} evaluator(s)...\n")
    start = time.time()
    results = run_eval(cases, backend, evaluators, args.source)
    duration = time.time() - start

    # Cleanup eval table (golden mode only — always runs, even after errors)
    if args.source == "golden":
        cleanup_eval_table(cases)

    # Build and save report
    metadata = build_run_metadata(args, dataset, results, duration)
    report = build_report(metadata, results, evaluators)
    path = save_report(report, args.output_dir)

    # Fire-and-forget DDB write
    try:
        from eval.report_store import write_report
        write_report("verification", report)
    except Exception as e:
        logger.warning(f"DDB report write failed (non-fatal): {e}")

    print_summary(report)
    print(f"\nReport saved: {path}")
    print(f"Description: {metadata['description']}")


if __name__ == "__main__":
    main()
