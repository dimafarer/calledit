"""
On-Demand Evaluation Runner

Loads the golden dataset, executes test cases through the OTEL-instrumented
test graph, applies evaluators, and produces a scored report.

USAGE:
    python eval_runner.py                          # Run all test cases
    python eval_runner.py --layer base             # Base predictions only
    python eval_runner.py --category auto_verifiable
    python eval_runner.py --difficulty hard
    python eval_runner.py --name base-001
    python eval_runner.py --dry-run                # List cases without executing
    python eval_runner.py --no-judge               # Skip Tier 2 LLM-as-judge

For base predictions: executes round 1, applies deterministic evaluators.
For fuzzy predictions: executes round 1 + round 2 with simulated clarifications,
applies convergence evaluator.
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from golden_dataset import (
    load_golden_dataset, filter_test_cases,
    BasePrediction, FuzzyPrediction, GoldenDataset,
)
from evaluators.category_match import evaluate_category_match
from evaluators.json_validity import evaluate_json_validity
from evaluators.convergence import evaluate_convergence
from evaluators.clarification_quality import evaluate_clarification_quality

logger = logging.getLogger(__name__)


def _build_tool_manifest_from_config(config: dict) -> str:
    """Build a tool manifest string from a golden dataset tool_manifest_config.

    Mirrors the format produced by tool_registry.build_tool_manifest() so the
    categorizer sees the same format it would in production.

    Args:
        config: {"tools": [{"name": "web_search", "description": "...", "capabilities": [...]}]}

    Returns:
        Formatted manifest string, or "" if no tools.
    """
    tools = config.get("tools", [])
    if not tools:
        return ""
    lines = []
    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "No description")
        caps = tool.get("capabilities", [])
        caps_str = ", ".join(caps) if caps else "general"
        lines.append(f"- {name}: {desc}")
        lines.append(f"  Capabilities: {caps_str}")
    return "\n".join(lines)


def _evaluate_base_prediction(
    bp: BasePrediction, result: dict, use_judge: bool = False
) -> dict:
    """Apply evaluators to a base prediction result."""
    scores = {}
    # V2: expected_per_agent_outputs is a plain dict, category at .categorizer
    expected_cat = bp.expected_per_agent_outputs.get("categorizer", {})
    scores["CategoryMatch"] = evaluate_category_match(result, expected_cat)
    scores["JSONValidity_parser"] = evaluate_json_validity(result, "parser")
    scores["JSONValidity_categorizer"] = evaluate_json_validity(result, "categorizer")
    scores["JSONValidity_vb"] = evaluate_json_validity(result, "verification_builder")
    # V2: review expected outputs are optional rubric guidance
    review_expected = bp.expected_per_agent_outputs.get("review", {})
    scores["ClarificationQuality"] = evaluate_clarification_quality(
        result, review_expected.get("reviewable_sections", [])
        if review_expected else []
    )

    if use_judge:
        try:
            from evaluators.reasoning_quality import evaluate_reasoning_quality
            for agent in ["categorizer", "verification_builder", "review"]:
                scores[f"ReasoningQuality_{agent}"] = evaluate_reasoning_quality(
                    result, agent, bp.prediction_text, bp.evaluation_rubric
                )
        except Exception as e:
            logger.warning(f"Judge evaluator failed: {e}")

    return scores


def _evaluate_fuzzy_prediction(
    fp: FuzzyPrediction, r1_result: dict, r2_result: dict,
    base_expected: dict, use_judge: bool = False
) -> dict:
    """Apply evaluators to a fuzzy prediction (round 1 + round 2)."""
    scores = {}
    # Round 1: JSON validity + clarification quality
    scores["R1_JSONValidity_parser"] = evaluate_json_validity(r1_result, "parser")
    scores["R1_JSONValidity_categorizer"] = evaluate_json_validity(r1_result, "categorizer")
    scores["R1_ClarificationQuality"] = evaluate_clarification_quality(
        r1_result, fp.expected_clarification_topics
    )
    # Round 2: convergence to base prediction
    scores["Convergence"] = evaluate_convergence(r2_result, base_expected)
    scores["R2_CategoryMatch"] = evaluate_category_match(
        r2_result, fp.expected_post_clarification_outputs.get("categorizer", {})
    )

    if use_judge:
        try:
            from evaluators.reasoning_quality import evaluate_reasoning_quality
            for agent in ["categorizer", "verification_builder"]:
                scores[f"R2_ReasoningQuality_{agent}"] = evaluate_reasoning_quality(
                    r2_result, agent, fp.fuzzy_text, fp.evaluation_rubric
                )
        except Exception as e:
            logger.warning(f"Judge evaluator failed: {e}")

    return scores


def _aggregate_report(test_results: list, manifest: dict,
                      dataset_version: str = "", schema_version: str = "",
                      eval_run_id: str = "") -> dict:
    """Build the evaluation report from per-test-case results."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Per-category accuracy (CategoryMatch scores grouped by expected category)
    cat_scores = {}
    for tr in test_results:
        cat = tr.get("expected_category", "")
        cm = tr.get("evaluator_scores", {}).get("CategoryMatch", {})
        if cm and cat:
            cat_scores.setdefault(cat, []).append(cm.get("score", 0.0))

    per_category_accuracy = {
        cat: sum(s) / len(s) if s else 0.0
        for cat, s in cat_scores.items()
    }

    # Per-agent JSON validity averages
    agent_jv = {"parser": [], "categorizer": [], "vb": []}
    for tr in test_results:
        scores = tr.get("evaluator_scores", {})
        for key, agent in [("JSONValidity_parser", "parser"),
                           ("JSONValidity_categorizer", "categorizer"),
                           ("JSONValidity_vb", "vb"),
                           ("R1_JSONValidity_parser", "parser"),
                           ("R1_JSONValidity_categorizer", "categorizer")]:
            if key in scores:
                agent_jv[agent].append(scores[key].get("score", 0.0))

    per_agent_aggregates = {
        agent: {"json_validity_avg": sum(s) / len(s) if s else 0.0}
        for agent, s in agent_jv.items()
    }

    # Overall pass rate (all evaluator scores > 0.5)
    passed = 0
    for tr in test_results:
        scores = tr.get("evaluator_scores", {})
        all_pass = all(
            s.get("score", 0.0) >= 0.5
            for s in scores.values()
            if isinstance(s, dict) and "score" in s
        )
        if all_pass:
            passed += 1

    total = len(test_results) if test_results else 1
    overall_pass_rate = passed / total

    return {
        "timestamp": timestamp,
        "schema_version": schema_version,
        "dataset_version": dataset_version,
        "eval_run_id": eval_run_id,
        "prompt_version_manifest": manifest,
        "per_test_case_scores": test_results,
        "per_agent_aggregates": per_agent_aggregates,
        "per_category_accuracy": per_category_accuracy,
        "overall_pass_rate": round(overall_pass_rate, 4),
        "total_tests": len(test_results),
        "passed": passed,
        "failed": len(test_results) - passed,
    }


def run_on_demand_evaluation(
    dataset_path: str = "eval/golden_dataset.json",
    filter_name: str = None,
    filter_category: str = None,
    filter_layer: str = None,
    filter_difficulty: str = None,
    dry_run: bool = False,
    use_judge: bool = False,
) -> dict:
    """Run on-demand evaluation against the golden dataset.

    Returns:
        Report dict with per-test scores, aggregates, and prompt version manifest.
    """
    from test_prediction_graph import run_test_graph
    from prompt_client import get_prompt_version_manifest

    dataset = load_golden_dataset(dataset_path)
    test_cases = filter_test_cases(
        dataset, name=filter_name, category=filter_category,
        layer=filter_layer, difficulty=filter_difficulty,
    )

    if dry_run:
        base_count = sum(1 for tc in test_cases if isinstance(tc, BasePrediction))
        fuzzy_count = sum(1 for tc in test_cases if isinstance(tc, FuzzyPrediction))
        return {
            "dry_run": True,
            "test_cases": [
                {"id": tc.id, "type": "base" if isinstance(tc, BasePrediction) else "fuzzy"}
                for tc in test_cases
            ],
            "estimated_invocations": base_count + (fuzzy_count * 2),
            "base_count": base_count,
            "fuzzy_count": fuzzy_count,
        }

    # V2: Initialize reasoning store (fire-and-forget DDB writes)
    try:
        from eval_reasoning_store import EvalReasoningStore
        reasoning_store = EvalReasoningStore()
    except Exception as e:
        logger.warning(f"Reasoning store unavailable: {e}")
        reasoning_store = None

    run_start = time.time()

    # Build base prediction lookup for fuzzy convergence scoring
    base_lookup = {bp.id: bp for bp in dataset.base_predictions}
    test_results = []

    for tc in test_cases:
        tc_start = time.time()
        try:
            if isinstance(tc, BasePrediction):
                manifest_str = _build_tool_manifest_from_config(tc.tool_manifest_config)
                result = run_test_graph(tc.prediction_text, tool_manifest=manifest_str)
                if result.get("error"):
                    raise RuntimeError(result["error"])
                scores = _evaluate_base_prediction(tc, result, use_judge)
                # V2: expected_category field path
                expected_cat = tc.expected_per_agent_outputs.get(
                    "categorizer", {}
                ).get("expected_category", "")
                test_results.append({
                    "test_case_id": tc.id, "layer": "base",
                    "difficulty": tc.difficulty, "expected_category": expected_cat,
                    "evaluator_scores": scores, "error": None,
                    "duration_s": round(time.time() - tc_start, 2),
                })

                # V2: Write agent outputs to reasoning store
                if reasoning_store:
                    reasoning_store.write_agent_outputs(tc.id, {
                        k: str(v) for k, v in result.items()
                        if k in ("parser", "categorizer", "verification_builder", "review")
                    })
                    reasoning_store.write_test_result(
                        test_case_id=tc.id, layer="base",
                        difficulty=tc.difficulty, expected_category=expected_cat,
                        evaluator_scores=scores,
                        duration_s=round(time.time() - tc_start, 2),
                    )

            elif isinstance(tc, FuzzyPrediction):
                # Use the base prediction's tool manifest for fuzzy tests
                base_bp_for_manifest = base_lookup.get(tc.base_prediction_id)
                manifest_str = _build_tool_manifest_from_config(
                    base_bp_for_manifest.tool_manifest_config if base_bp_for_manifest else {}
                )
                # Round 1
                r1 = run_test_graph(tc.fuzzy_text, tool_manifest=manifest_str)
                if r1.get("error"):
                    raise RuntimeError(r1["error"])

                # Round 2 with simulated clarifications
                prev_outputs = {
                    k: v for k, v in r1.items()
                    if k not in ("reviewable_sections", "error")
                }
                r2 = run_test_graph(
                    tc.fuzzy_text, tool_manifest=manifest_str, round_num=2,
                    clarifications=tc.simulated_clarifications,
                    prev_outputs=prev_outputs,
                )
                if r2.get("error"):
                    raise RuntimeError(r2["error"])

                base_bp = base_lookup.get(tc.base_prediction_id)
                # V2: expected_per_agent_outputs is a plain dict
                base_expected = {
                    "parser": base_bp.expected_per_agent_outputs.get("parser", {}) if base_bp else {},
                    "categorizer": base_bp.expected_per_agent_outputs.get("categorizer", {}) if base_bp else {},
                    "verification_builder": base_bp.expected_per_agent_outputs.get("verification_builder", {}) if base_bp else {},
                }
                scores = _evaluate_fuzzy_prediction(tc, r1, r2, base_expected, use_judge)
                # V2: expected_category field path
                expected_cat = tc.expected_post_clarification_outputs.get(
                    "categorizer", {}
                ).get("expected_category", "")
                test_results.append({
                    "test_case_id": tc.id, "layer": "fuzzy",
                    "difficulty": base_bp.difficulty if base_bp else "unknown",
                    "expected_category": expected_cat,
                    "evaluator_scores": scores, "error": None,
                    "duration_s": round(time.time() - tc_start, 2),
                })

                # Write fuzzy test result to DDB
                if reasoning_store:
                    reasoning_store.write_test_result(
                        test_case_id=tc.id, layer="fuzzy",
                        difficulty=base_bp.difficulty if base_bp else "unknown",
                        expected_category=expected_cat,
                        evaluator_scores=scores,
                        duration_s=round(time.time() - tc_start, 2),
                    )

        except Exception as e:
            logger.error(f"Test case {tc.id} failed: {e}", exc_info=True)
            test_results.append({
                "test_case_id": tc.id,
                "layer": "base" if isinstance(tc, BasePrediction) else "fuzzy",
                "difficulty": getattr(tc, "difficulty", "unknown"),
                "expected_category": "",
                "evaluator_scores": {},
                "error": str(e),
                "duration_s": round(time.time() - tc_start, 2),
            })

        # Progress
        print(f"  [{len(test_results)}/{len(test_cases)}] {tc.id}: "
              f"{'PASS' if not test_results[-1].get('error') else 'FAIL'}")

    # Read manifest AFTER test cases run (populated during agent creation)
    manifest = get_prompt_version_manifest()
    report = _aggregate_report(
        test_results, manifest,
        dataset_version=dataset.dataset_version,
        schema_version=dataset.schema_version,
        eval_run_id=reasoning_store.eval_run_id if reasoning_store else "",
    )

    # V2: Write run metadata to reasoning store
    if reasoning_store:
        reasoning_store.write_run_metadata(
            manifest=manifest,
            dataset_version=dataset.dataset_version,
            schema_version=dataset.schema_version,
            total_tests=report["total_tests"],
            pass_rate=report["overall_pass_rate"],
            duration_s=round(time.time() - run_start, 2),
            per_agent_aggregates=report.get("per_agent_aggregates"),
            per_category_accuracy=report.get("per_category_accuracy"),
            passed=report.get("passed", 0),
            failed=report.get("failed", 0),
        )

    return report


def print_report(report: dict):
    """Print a human-readable summary of the evaluation report."""
    if report.get("dry_run"):
        print(f"\n=== DRY RUN ===")
        print(f"Would execute {len(report['test_cases'])} test cases")
        print(f"  Base: {report['base_count']}, Fuzzy: {report['fuzzy_count']}")
        print(f"  Estimated graph invocations: {report['estimated_invocations']}")
        for tc in report["test_cases"]:
            print(f"  - {tc['id']} ({tc['type']})")
        return

    print(f"\n=== EVALUATION REPORT ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Prompt versions: {json.dumps(report['prompt_version_manifest'])}")
    print(f"\nResults: {report['passed']}/{report['total_tests']} passed "
          f"({report['overall_pass_rate']:.0%})")

    print(f"\nPer-category accuracy:")
    for cat, acc in report.get("per_category_accuracy", {}).items():
        print(f"  {cat}: {acc:.0%}")

    print(f"\nPer-agent JSON validity:")
    for agent, metrics in report.get("per_agent_aggregates", {}).items():
        print(f"  {agent}: {metrics.get('json_validity_avg', 0):.0%}")

    # Show failures
    failures = [tr for tr in report.get("per_test_case_scores", []) if tr.get("error")]
    if failures:
        print(f"\nFailures:")
        for f in failures:
            print(f"  {f['test_case_id']}: {f['error']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description="CalledIt Prompt Evaluation Runner")
    parser.add_argument("--dataset", default="eval/golden_dataset.json")
    parser.add_argument("--name", help="Filter by test case ID")
    parser.add_argument("--category", help="Filter by verifiable_category")
    parser.add_argument("--layer", choices=["base", "fuzzy"], help="Filter by layer")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    parser.add_argument("--dry-run", action="store_true", help="List cases without executing")
    parser.add_argument("--judge", action="store_true", help="Enable Tier 2 LLM-as-judge")
    parser.add_argument("--compare", action="store_true", help="Compare with previous eval run")
    args = parser.parse_args()

    report = run_on_demand_evaluation(
        dataset_path=args.dataset,
        filter_name=args.name,
        filter_category=args.category,
        filter_layer=args.layer,
        filter_difficulty=args.difficulty,
        dry_run=args.dry_run,
        use_judge=args.judge,
    )
    print_report(report)

    # Save report and score history
    if not report.get("dry_run"):
        import os
        from score_history import append_score, compare_latest

        ts = report["timestamp"].replace(":", "-")
        report_path = f"eval/reports/eval-{ts}.json"
        os.makedirs("eval/reports", exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {report_path}")

        # Append to score history
        append_score(report)
        print("Score appended to eval/score_history.json")

        # Compare with previous run if requested
        if args.compare:
            comparison = compare_latest()
            if comparison:
                print(f"\n=== COMPARISON vs {comparison['previous_timestamp']} ===")
                opr = comparison["overall_pass_rate"]
                status_icon = {"improved": "↑", "regressed": "↓", "unchanged": "="}
                print(f"Overall pass rate: {opr['previous']:.0%} → {opr['current']:.0%} "
                      f"{status_icon[opr['status']]} ({opr['delta']:+.1%})")
                for cat, delta in comparison.get("category_deltas", {}).items():
                    print(f"  {cat}: {delta['previous']:.0%} → {delta['current']:.0%} "
                          f"{status_icon[delta['status']]}")
                if comparison.get("changed_prompts"):
                    print(f"\nChanged prompts: {json.dumps(comparison['changed_prompts'])}")
                if comparison.get("has_regression"):
                    print(f"\n⚠️  REGRESSION DETECTED in {len(comparison['regressions'])} metric(s)")
            else:
                print("\nNo previous evaluation to compare against.")
