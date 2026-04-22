"""Re-evaluate an existing report with updated evaluators.

Reads a local backup JSON, feeds the stored case results through the SDK
evaluators, and writes a new report. No agent invocations — just evaluation.

Usage:
    python -m eval.re_evaluate eval/reports/sdk-eval-20260420-190639.json --tier full --description "re-eval with skip fix"
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from strands_evals import Case, Experiment

from eval.calibration import compute_calibration
from eval.case_loader import load_cases
from eval.run_eval import (
    build_evaluators,
    build_report,
    extract_case_results,
    extract_evaluator_scores,
    print_summary,
)

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Re-evaluate existing report")
    parser.add_argument("report_path", help="Path to local backup JSON")
    parser.add_argument("--tier", default="full", choices=["smoke", "smoke+judges", "full"])
    parser.add_argument("--description", default=None)
    parser.add_argument("--dataset", default="eval/golden_dataset.json")
    parser.add_argument("--dynamic-dataset", default=None)
    parser.add_argument("--local-backup", action="store_true")
    args = parser.parse_args()

    # Load the existing report
    with open(args.report_path) as f:
        old_report = json.load(f)

    old_cases = old_report.get("case_results", [])
    print(f"Loaded {len(old_cases)} case results from {args.report_path}")

    # Load the golden dataset to get Case objects with metadata
    cases = load_cases(args.dataset, args.dynamic_dataset)
    cases_by_name = {c.name: c for c in cases}

    # Build precomputed task function from stored results
    outputs_by_name = {}
    for cr in old_cases:
        name = cr.get("case_id") or cr.get("id")
        outputs_by_name[name] = {
            "creation_bundle": cr.get("creation_bundle"),
            "verification_result": cr.get("verification_result"),
            "creation_error": cr.get("creation_error"),
            "verification_error": cr.get("verification_error"),
            "prediction_id": cr.get("prediction_id"),
            "creation_duration": cr.get("creation_duration", 0),
            "verification_duration": cr.get("verification_duration", 0),
        }

    # Match cases to stored results
    matched_cases = []
    matched_outputs = []
    for cr in old_cases:
        name = cr.get("case_id") or cr.get("id")
        if name in cases_by_name:
            matched_cases.append(cases_by_name[name])
            matched_outputs.append(outputs_by_name[name])
        else:
            logger.warning("Case %s not found in dataset — skipping", name)

    print(f"Matched {len(matched_cases)} cases to dataset")

    # Build evaluators
    evaluators = build_evaluators(args.tier)
    print(f"Evaluators: {len(evaluators)} ({args.tier} tier)")

    # Run SDK evaluation with precomputed results
    def precomputed_fn(case):
        result = outputs_by_name.get(case.name, {})
        return {"output": result}

    print(f"\nRunning evaluation...")
    start = time.time()
    experiment = Experiment(cases=matched_cases, evaluators=evaluators)
    reports = experiment.run_evaluations(precomputed_fn)
    eval_duration = time.time() - start
    print(f"Evaluation complete in {eval_duration:.0f}s")

    # Extract scores
    evaluator_scores = extract_evaluator_scores(evaluators, reports)

    # Calibration
    calibration_scores = {}
    if args.tier == "full":
        calibration_scores = compute_calibration(matched_outputs)

    # Build report
    case_results = extract_case_results(matched_cases, matched_outputs)
    total_duration = old_report.get("run_metadata", {}).get("duration_seconds", 0)

    # Use a fake args for build_report
    class FakeArgs:
        pass
    fake_args = FakeArgs()
    fake_args.dataset = args.dataset
    fake_args.dynamic_dataset = args.dynamic_dataset
    fake_args.tier = args.tier
    fake_args.description = args.description or f"Re-eval of {os.path.basename(args.report_path)}"

    report = build_report(fake_args, case_results, evaluator_scores, calibration_scores, total_duration)
    report["run_metadata"]["phase_durations"] = old_report.get("run_metadata", {}).get("phase_durations", {})
    report["run_metadata"]["re_evaluation"] = True
    report["run_metadata"]["source_report"] = args.report_path

    # Write to DDB
    try:
        from eval.report_store import write_report
        write_report("unified", report)
        print("Report written to DDB")
    except Exception as e:
        logger.warning("DDB write failed: %s", e)

    # Local backup
    if args.local_backup:
        os.makedirs("eval/reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = f"eval/reports/sdk-reeval-{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Local backup: {path}")

    print_summary(report)


if __name__ == "__main__":
    main()
