#!/usr/bin/env python3
"""Creation Agent Eval Runner — V4-7a-2

Invokes the deployed v4 creation agent via AgentCore HTTP streaming,
applies tiered evaluators, and produces JSON reports.

Run tiers (Decision 125):
  smoke         — smoke_test cases only, Tier 1 deterministic only
  smoke+judges  — smoke_test cases only, Tier 1 + Tier 2 LLM judges
  full          — all cases, Tier 1 + Tier 2 LLM judges

Usage:
  python eval/creation_eval.py                          # smoke (default)
  python eval/creation_eval.py --tier smoke+judges      # smoke with judges
  python eval/creation_eval.py --tier full              # all cases + judges
  python eval/creation_eval.py --case base-001          # single case
  python eval/creation_eval.py --dry-run                # list cases only
  python eval/creation_eval.py --description "baseline"  # custom description

Decisions: 122 (tiered evaluators), 125 (smoke subset), 126 (priority metrics),
           127 (structured run metadata)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from eval.backends.agentcore_backend import (
    AgentCoreBackend, get_cognito_token, CREATION_AGENT_MODEL_ID,
    CREATION_AGENT_ARN,
)
from eval.evaluators import (
    schema_validity,
    field_completeness,
    score_range,
    date_resolution,
    dimension_count,
    tier_consistency,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
)


# --- Data Classes ---

@dataclass
class EvalCase:
    id: str
    input: str  # prediction_text
    expected_output: dict  # ground_truth
    metadata: dict  # dimension_tags, difficulty, smoke_test, evaluation_rubric


# --- Tier 1 Evaluators (always run) ---

TIER_1_EVALUATORS = {
    "schema_validity": schema_validity.evaluate,
    "field_completeness": field_completeness.evaluate,
    "score_range": score_range.evaluate,
    "date_resolution": date_resolution.evaluate,
    "dimension_count": dimension_count.evaluate,
    "tier_consistency": tier_consistency.evaluate,
}


# --- Dataset Loading ---

def load_dataset(path: str) -> dict:
    """Load and validate golden dataset JSON."""
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
            f"Error: dataset missing 'base_predictions' array",
            file=sys.stderr,
        )
        sys.exit(1)

    return data


def _to_eval_case(bp: dict) -> EvalCase:
    """Convert a base prediction dict to an EvalCase."""
    return EvalCase(
        id=bp["id"],
        input=bp["prediction_text"],
        expected_output=bp.get("ground_truth", {}),
        metadata={
            "dimension_tags": bp.get("dimension_tags", {}),
            "difficulty": bp.get("difficulty"),
            "smoke_test": bp.get("smoke_test", False),
            "id": bp["id"],
            "evaluation_rubric": bp.get("evaluation_rubric", ""),
        },
    )


def filter_cases(
    dataset: dict, tier: str, case_id: str = None
) -> list[EvalCase]:
    """Filter cases by run tier or specific case id."""
    cases = [_to_eval_case(bp) for bp in dataset["base_predictions"]]

    if case_id:
        matches = [c for c in cases if c.id == case_id]
        if not matches:
            print(
                f"Error: case '{case_id}' not found in dataset",
                file=sys.stderr,
            )
            sys.exit(1)
        return matches

    if tier in ("smoke", "smoke+judges"):
        return [c for c in cases if c.metadata.get("smoke_test")]

    return cases  # full tier


def build_evaluator_list(tier: str) -> dict:
    """Build evaluator dict based on run tier."""
    evaluators = dict(TIER_1_EVALUATORS)

    if tier in ("smoke+judges", "full"):
        from eval.evaluators import intent_preservation, plan_quality
        evaluators["intent_preservation"] = intent_preservation.evaluate
        evaluators["plan_quality"] = plan_quality.evaluate

    return evaluators


# --- Eval Orchestration ---

def run_eval(
    cases: list[EvalCase],
    backend: AgentCoreBackend,
    evaluators: dict,
) -> list[dict]:
    """Run all cases through backend and evaluators. Returns per-case results."""
    results = []
    tier_2_names = {"intent_preservation", "plan_quality"}

    for i, case in enumerate(cases, 1):
        logger.info(f"[{i}/{len(cases)}] Running case {case.id}")
        case_result = {"id": case.id, "input": case.input, "scores": {}}

        # Invoke backend
        try:
            bundle = backend.invoke(case.input, case_id=case.id)
            case_result["prediction_id"] = bundle.get("prediction_id")
        except Exception as e:
            logger.error(f"Backend failed for {case.id}: {e}")
            case_result["error"] = str(e)
            # Score all evaluators as 0 on backend failure
            for name in evaluators:
                case_result["scores"][name] = {
                    "score": 0.0,
                    "pass": False,
                    "reason": f"Backend error: {e}",
                }
            results.append(case_result)
            continue

        # Run evaluators
        for name, eval_fn in evaluators.items():
            try:
                if name in tier_2_names:
                    # Tier 2 judges need the original prediction text
                    score = eval_fn(bundle, case.input)
                else:
                    score = eval_fn(bundle)
                case_result["scores"][name] = score
            except Exception as e:
                logger.error(f"Evaluator {name} failed for {case.id}: {e}")
                case_result["scores"][name] = {
                    "score": 0.0,
                    "pass": False,
                    "reason": f"Evaluator error: {e}",
                }

        # Extract prompt_versions and verification_mode from bundle for metadata
        case_result["prompt_versions"] = bundle.get("prompt_versions", {})
        case_result["verification_mode"] = bundle.get("verification_mode", "immediate")
        results.append(case_result)

    return results


# --- Report Generation ---

def compute_aggregates(results: list[dict], evaluators: dict) -> dict:
    """Compute per-evaluator averages, overall pass rate, and per-mode breakdowns."""
    agg = {}
    tier_1_names = set(TIER_1_EVALUATORS.keys())

    for name in evaluators:
        scores = [
            r["scores"].get(name, {}).get("score", 0.0)
            for r in results
            if "error" not in r or name in r.get("scores", {})
        ]
        agg[name] = sum(scores) / len(scores) if scores else None

    # Overall pass rate: fraction where ALL Tier 1 evaluators scored 1.0
    pass_count = 0
    for r in results:
        if "error" in r and not r.get("scores"):
            continue
        all_t1_pass = all(
            r["scores"].get(name, {}).get("score", 0.0) == 1.0
            for name in tier_1_names
            if name in r.get("scores", {})
        )
        if all_t1_pass:
            pass_count += 1

    total = len([r for r in results if "error" not in r or r.get("scores")])
    agg["overall_pass_rate"] = pass_count / total if total else 0.0

    # Per-mode breakdowns
    mode_groups = {}
    for r in results:
        mode = r.get("verification_mode", "immediate")
        if mode not in mode_groups:
            mode_groups[mode] = []
        mode_groups[mode].append(r)

    by_mode = {}
    for mode, mode_results in mode_groups.items():
        mode_agg = {}
        all_eval_names = set()
        for r in mode_results:
            all_eval_names.update(r.get("scores", {}).keys())
        for name in all_eval_names:
            scores = [
                r["scores"][name]["score"]
                for r in mode_results
                if name in r.get("scores", {}) and r["scores"][name] is not None
            ]
            if scores:
                mode_agg[name] = round(sum(scores) / len(scores), 4)
        if mode_agg:
            by_mode[mode] = mode_agg

    if by_mode:
        agg["by_mode"] = by_mode

    return agg


def compute_smoke_summary(
    results: list[dict], cases: list[EvalCase]
) -> dict:
    """Compute aggregate scores for smoke test cases only."""
    smoke_ids = {c.id for c in cases if c.metadata.get("smoke_test")}
    smoke_results = [r for r in results if r["id"] in smoke_ids]

    if not smoke_results:
        return {"case_count": 0}

    summary = {"case_count": len(smoke_results)}
    tier_1_names = set(TIER_1_EVALUATORS.keys())

    for name in tier_1_names:
        scores = [
            r["scores"].get(name, {}).get("score", 0.0)
            for r in smoke_results
        ]
        summary[name] = sum(scores) / len(scores) if scores else 0.0

    pass_count = sum(
        1 for r in smoke_results
        if all(
            r["scores"].get(n, {}).get("score", 0.0) == 1.0
            for n in tier_1_names
            if n in r.get("scores", {})
        )
    )
    summary["overall_pass_rate"] = pass_count / len(smoke_results)

    return summary


def build_run_metadata(
    args, dataset: dict, results: list[dict], duration: float
) -> dict:
    """Build structured run metadata per Decision 127."""
    # Get prompt_versions from first successful result
    prompt_versions = {}
    for r in results:
        if r.get("prompt_versions"):
            prompt_versions = r["prompt_versions"]
            break

    description = args.description
    if not description:
        description = f"creation {args.tier} run at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

    return {
        "description": description,
        "prompt_versions": prompt_versions,
        "model_id": CREATION_AGENT_MODEL_ID,
        "agent_runtime_arn": CREATION_AGENT_ARN,
        "git_commit": _get_git_commit(),
        "run_tier": args.tier,
        "dataset_version": dataset.get("dataset_version", "unknown"),
        "agent": "creation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 1),
        "case_count": len(results),
        "features": {
            "long_term_memory": False,
            "short_term_memory": False,
            "tools": ["browser", "code_interpreter", "current_time"],
        },
    }


def _get_git_commit() -> str:
    """Get the current git commit SHA. Returns 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_report(
    metadata: dict,
    results: list[dict],
    cases: list[EvalCase],
    evaluators: dict,
) -> dict:
    """Build the complete eval report."""
    return {
        "run_metadata": metadata,
        "aggregate_scores": compute_aggregates(results, evaluators),
        "case_results": results,
        "smoke_test_summary": compute_smoke_summary(results, cases),
    }


def save_report(report: dict, output_dir: str) -> str:
    """Save report as JSON. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"creation-eval-{ts}.json"
    path = os.path.join(output_dir, filename)

    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
        f.write("\n")

    return path


# --- CLI ---

def parse_args():
    parser = argparse.ArgumentParser(
        description="V4 Creation Agent Eval Runner"
    )
    parser.add_argument(
        "--dataset",
        default="eval/golden_dataset.json",
        help="Path to golden dataset (default: eval/golden_dataset.json)",
    )
    parser.add_argument(
        "--tier",
        default="smoke",
        choices=["smoke", "smoke+judges", "full"],
        help="Run tier (default: smoke)",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="One-line description for this run",
    )
    parser.add_argument(
        "--output-dir",
        default="eval/reports",
        help="Report output directory (default: eval/reports)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List cases without executing",
    )
    parser.add_argument(
        "--case",
        default=None,
        help="Run a single case by id (e.g., base-001)",
    )
    return parser.parse_args()


def print_dry_run(cases: list[EvalCase]) -> None:
    """Print case list for dry run."""
    print(f"\n=== Dry Run: {len(cases)} cases ===\n")
    for c in cases:
        domain = c.metadata.get("dimension_tags", {}).get("domain", "?")
        diff = c.metadata.get("difficulty", "?")
        smoke = "smoke" if c.metadata.get("smoke_test") else ""
        print(f"  {c.id:10s} | {diff:6s} | {domain:15s} | {smoke}")
    print()


def main():
    args = parse_args()

    # Load and filter cases
    dataset = load_dataset(args.dataset)
    cases = filter_cases(dataset, args.tier, args.case)

    if args.dry_run:
        print_dry_run(cases)
        return

    # Build evaluator list based on tier
    evaluators = build_evaluator_list(args.tier)
    tier_names = ", ".join(evaluators.keys())
    logger.info(
        f"Running {len(cases)} cases with {len(evaluators)} evaluators "
        f"[{args.tier}]: {tier_names}"
    )

    # Get Cognito token for agent invocation
    logger.info("Authenticating with Cognito...")
    try:
        token = get_cognito_token()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(
            "Set COGNITO_USERNAME and COGNITO_PASSWORD environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run eval
    backend = AgentCoreBackend()
    backend.set_token(token)
    start_time = time.time()
    results = run_eval(cases, backend, evaluators)
    duration = time.time() - start_time

    # Build and save report
    metadata = build_run_metadata(args, dataset, results, duration)
    report = build_report(metadata, results, cases, evaluators)
    report_path = save_report(report, args.output_dir)

    # Fire-and-forget DDB write
    try:
        from eval.report_store import write_report
        write_report("creation", report)
    except Exception as e:
        logger.warning(f"DDB report write failed (non-fatal): {e}")

    # Print summary
    agg = report["aggregate_scores"]
    print(f"\n=== Creation Agent Eval Report ===")
    print(f"Tier: {args.tier}")
    print(f"Cases: {len(results)}")
    print(f"Duration: {duration:.1f}s")
    print(f"\nTier 1 (deterministic):")
    for name in TIER_1_EVALUATORS:
        val = agg.get(name)
        print(f"  {name}: {val:.2f}" if val is not None else f"  {name}: N/A")
    print(f"  overall_pass_rate: {agg.get('overall_pass_rate', 0):.2f}")

    if args.tier in ("smoke+judges", "full"):
        print(f"\nTier 2 (LLM judges):")
        for name in ("intent_preservation", "plan_quality"):
            val = agg.get(name)
            print(
                f"  {name}: {val:.2f}"
                if val is not None
                else f"  {name}: N/A"
            )

    print(f"\nReport saved: {report_path}")
    print(f"Description: {metadata['description']}")


if __name__ == "__main__":
    main()
