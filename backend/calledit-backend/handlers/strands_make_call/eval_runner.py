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
import sys
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

        # V3: Verification-centric evaluators (Strands Evals SDK)
        try:
            from evaluators.intent_preservation import evaluate_intent_preservation
            from evaluators.criteria_method_alignment import evaluate_criteria_method_alignment
            import json as _json

            # The result dict IS the pipeline output — VB fields are at top level
            # (same as how reasoning_quality.py accesses result.get("verification_method"))
            vb_method = result.get("verification_method", {})
            if isinstance(vb_method, str):
                try:
                    vb_method = _json.loads(vb_method)
                except _json.JSONDecodeError:
                    vb_method = {}
            vb_criteria = vb_method.get("criteria", [])

            # Ground truth v3 fields
            gt = bp.ground_truth
            expected_criteria = gt.expected_verification_criteria
            expected_method = gt.expected_verification_method

            if expected_criteria:
                scores["IntentPreservation"] = evaluate_intent_preservation(
                    bp.prediction_text, vb_criteria, expected_criteria
                )
                logger.info(f"IntentPreservation for {bp.id}: {scores['IntentPreservation'].get('score', '?')}")
            if expected_method:
                scores["CriteriaMethodAlignment"] = evaluate_criteria_method_alignment(
                    vb_criteria, vb_method, expected_method
                )
                logger.info(f"CriteriaMethodAlignment for {bp.id}: {scores['CriteriaMethodAlignment'].get('score', '?')}")
        except Exception as e:
            logger.warning(f"Verification evaluators failed: {e}")

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


# --- Verification-Builder-centric evaluator weights ---
EVALUATOR_WEIGHTS = {
    # Primary — Verification Builder output quality
    "IntentPreservation": 0.25,
    "CriteriaMethodAlignment": 0.25,
    # Secondary — upstream agent contribution to Verification Builder success
    "IntentExtraction": 0.10,
    "CategorizationJustification": 0.10,
    "ClarificationRelevance": 0.10,
    # Cross-pipeline — coherence
    "PipelineCoherence": 0.15,
    # Legacy deterministic (cheap regression catches)
    "CategoryMatch": 0.025,
    "JSONValidity": 0.025,
}


def compute_vb_centric_score(scores: dict) -> float:
    """Weighted composite score centered on Verification Builder output quality.

    Missing evaluators reduce the weight denominator, not the score.
    Returns a value in [0.0, 1.0].
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for evaluator, weight in EVALUATOR_WEIGHTS.items():
        if evaluator in scores:
            score_val = scores[evaluator]
            # Handle both dict results and raw floats
            if isinstance(score_val, dict):
                score_val = score_val.get("score", 0.0)
            weighted_sum += float(score_val) * weight
            total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _evaluate_with_judges(
    output_contract: dict, bp: "BasePrediction", tool_manifest: str
) -> dict:
    """Run all applicable per-agent LLM judge evaluators.

    Dispatches evaluators based on which agent keys exist in agent_outputs.
    Final-output evaluators (IntentPreservation, CriteriaMethodAlignment)
    are handled in _evaluate_base_prediction. This function handles the
    NEW per-agent and cross-pipeline judges.
    """
    scores = {}
    final = output_contract.get("final_output", {})
    agents = output_contract.get("agent_outputs", {})
    gt = bp.ground_truth
    skipped = {}

    # Extract Verification Builder criteria from final output
    vb_method = final.get("verification_method", {})
    if isinstance(vb_method, str):
        try:
            vb_method = json.loads(vb_method)
        except json.JSONDecodeError:
            vb_method = {}
    vb_criteria = vb_method.get("criteria", []) if isinstance(vb_method, dict) else []

    # --- Per-agent evaluators (only if agent key exists) ---
    if "parser" in agents:
        try:
            from evaluators.intent_extraction import evaluate_intent_extraction
            scores["IntentExtraction"] = evaluate_intent_extraction(
                bp.prediction_text, agents["parser"],
                gt.expected_verification_criteria or [],
            )
            logger.info(
                f"IntentExtraction for {bp.id}: "
                f"{scores['IntentExtraction'].get('score', '?')}"
            )
        except Exception as e:
            logger.warning(f"IntentExtraction failed for {bp.id}: {e}")
    else:
        skipped["IntentExtraction"] = "No 'parser' key in agent_outputs"

    if "categorizer" in agents:
        try:
            from evaluators.categorization_justification import (
                evaluate_categorization_justification,
            )
            scores["CategorizationJustification"] = evaluate_categorization_justification(
                agents.get("parser", {}), agents["categorizer"],
                tool_manifest, final,
            )
            logger.info(
                f"CategorizationJustification for {bp.id}: "
                f"{scores['CategorizationJustification'].get('score', '?')}"
            )
        except Exception as e:
            logger.warning(f"CategorizationJustification failed for {bp.id}: {e}")
    else:
        skipped["CategorizationJustification"] = "No 'categorizer' key in agent_outputs"

    if "review" in agents:
        try:
            from evaluators.clarification_relevance import (
                evaluate_clarification_relevance,
            )
            scores["ClarificationRelevance"] = evaluate_clarification_relevance(
                bp.prediction_text, vb_criteria, agents["review"],
            )
            logger.info(
                f"ClarificationRelevance for {bp.id}: "
                f"{scores['ClarificationRelevance'].get('score', '?')}"
            )
        except Exception as e:
            logger.warning(f"ClarificationRelevance failed for {bp.id}: {e}")
    else:
        skipped["ClarificationRelevance"] = "No 'review' key in agent_outputs"

    # --- Cross-pipeline evaluator (always runs) ---
    try:
        from evaluators.pipeline_coherence import evaluate_pipeline_coherence
        scores["PipelineCoherence"] = evaluate_pipeline_coherence(
            bp.prediction_text, agents, final,
        )
        logger.info(
            f"PipelineCoherence for {bp.id}: "
            f"{scores['PipelineCoherence'].get('score', '?')}"
        )
    except Exception as e:
        logger.warning(f"PipelineCoherence failed for {bp.id}: {e}")

    # Store skipped info for reporting
    if skipped:
        scores["_skipped_evaluators"] = skipped

    return scores


def _aggregate_report(test_results: list, manifest: dict,
                      dataset_version: str = "", schema_version: str = "",
                      eval_run_id: str = "", backend_meta: dict = None) -> dict:
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

    # V3: Verification quality averages
    ip_scores = []
    cma_scores = []
    for tr in test_results:
        scores = tr.get("evaluator_scores", {})
        ip = scores.get("IntentPreservation", {})
        if isinstance(ip, dict) and "score" in ip:
            ip_scores.append(ip["score"])
        cma = scores.get("CriteriaMethodAlignment", {})
        if isinstance(cma, dict) and "score" in cma:
            cma_scores.append(cma["score"])

    verification_quality_aggregates = {
        "intent_preservation_avg": sum(ip_scores) / len(ip_scores) if ip_scores else None,
        "criteria_method_alignment_avg": sum(cma_scores) / len(cma_scores) if cma_scores else None,
    }

    # Verification-Builder-centric composite score (per test case + aggregate)
    vb_centric_scores = []
    for tr in test_results:
        scores = tr.get("evaluator_scores", {})
        vb_score = compute_vb_centric_score(scores)
        tr["vb_centric_score"] = round(vb_score, 4)
        vb_centric_scores.append(vb_score)

    vb_centric_avg = (
        sum(vb_centric_scores) / len(vb_centric_scores)
        if vb_centric_scores else 0.0
    )

    # Collect skipped evaluators across all test cases
    all_skipped = {}
    for tr in test_results:
        skipped = tr.get("evaluator_scores", {}).get("_skipped_evaluators", {})
        all_skipped.update(skipped)

    return {
        "timestamp": timestamp,
        "schema_version": schema_version,
        "dataset_version": dataset_version,
        "eval_run_id": eval_run_id,
        "prompt_version_manifest": manifest,
        "architecture": backend_meta.get("name", "unknown") if backend_meta else "serial",
        "model_config": backend_meta.get("model_config", {}) if backend_meta else {},
        "vb_centric_score": round(vb_centric_avg, 4),
        "evaluator_groups": {
            "final_output": ["IntentPreservation", "CriteriaMethodAlignment"],
            "per_agent": ["IntentExtraction", "CategorizationJustification", "ClarificationRelevance"],
            "cross_pipeline": ["PipelineCoherence"],
            "deterministic": ["CategoryMatch", "JSONValidity", "ClarificationQuality"],
        },
        "skipped_evaluators": all_skipped,
        "per_test_case_scores": test_results,
        "per_agent_aggregates": per_agent_aggregates,
        "per_category_accuracy": per_category_accuracy,
        "verification_quality_aggregates": verification_quality_aggregates,
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
    backend_name: str = "serial",
    model_id: str = None,
) -> dict:
    """Run on-demand evaluation against the golden dataset.

    Args:
        backend_name: Name of the backend to use. Must match a module in backends/.
        model_id: Model ID override for the backend. If None, backend uses its default.

    Returns:
        Report dict with per-test scores, aggregates, and prompt version manifest.
    """
    # Resolve backend
    from backends import discover_backends, validate_output_contract
    backends = discover_backends()
    if backend_name not in backends:
        available = list(backends.keys())
        raise ValueError(
            f"Unknown backend '{backend_name}'. Available: {available}"
        )
    backend = backends[backend_name]
    backend_meta = backend.metadata(model_id) if model_id else backend.metadata()
    logger.info(f"Using backend: {backend_meta['name']} — {backend_meta.get('description', '')}")
    if model_id:
        logger.info(f"Model override: {model_id}")

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
                # Use the pluggable backend instead of run_test_graph directly
                output_contract = backend.run(tc.prediction_text, manifest_str,
                                              model_id=model_id)
                # Validate the output contract
                contract_errors = validate_output_contract(output_contract)
                if contract_errors:
                    raise RuntimeError(f"Backend output contract errors: {contract_errors}")
                result = output_contract["final_output"]
                if result.get("error"):
                    raise RuntimeError(result["error"])
                scores = _evaluate_base_prediction(tc, result, use_judge)

                # New per-agent judge evaluators (only when --judge is enabled)
                if use_judge:
                    agent_judge_scores = _evaluate_with_judges(
                        output_contract, tc, manifest_str
                    )
                    scores.update(agent_judge_scores)
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
        backend_meta=backend_meta,
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
    print(f"Architecture: {report.get('architecture', 'serial')}")
    print(f"Prompt versions: {json.dumps(report['prompt_version_manifest'])}")
    print(f"\nResults: {report['passed']}/{report['total_tests']} passed "
          f"({report['overall_pass_rate']:.0%})")

    vb_score = report.get("vb_centric_score")
    if vb_score is not None:
        print(f"Verification-Builder-centric score: {vb_score:.2f}")

    print(f"\nPer-category accuracy:")
    for cat, acc in report.get("per_category_accuracy", {}).items():
        print(f"  {cat}: {acc:.0%}")

    print(f"\nPer-agent JSON validity:")
    for agent, metrics in report.get("per_agent_aggregates", {}).items():
        print(f"  {agent}: {metrics.get('json_validity_avg', 0):.0%}")

    # V3: Verification quality averages
    vqa = report.get("verification_quality_aggregates", {})
    ip_avg = vqa.get("intent_preservation_avg")
    cma_avg = vqa.get("criteria_method_alignment_avg")
    if ip_avg is not None or cma_avg is not None:
        print(f"\nVerification quality:")
        if ip_avg is not None:
            print(f"  IntentPreservation avg: {ip_avg:.2f}")
        if cma_avg is not None:
            print(f"  CriteriaMethodAlignment avg: {cma_avg:.2f}")

    # Show failures
    failures = [tr for tr in report.get("per_test_case_scores", []) if tr.get("error")]
    if failures:
        print(f"\nFailures:")
        for f in failures:
            print(f"  {f['test_case_id']}: {f['error']}")

    # Show skipped evaluators
    skipped = report.get("skipped_evaluators", {})
    if skipped:
        print(f"\nSkipped evaluators:")
        for ev, reason in skipped.items():
            print(f"  {ev}: {reason}")


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
    parser.add_argument("--backend", default="serial", help="Backend to use (default: serial). Use --list-backends to see available.")
    parser.add_argument("--model", default=None, help="Model ID override for the backend (e.g., us.anthropic.claude-opus-4-6-v1). If not set, each backend uses its default.")
    parser.add_argument("--list-backends", action="store_true", help="List available backends and exit")
    args = parser.parse_args()

    # Handle --list-backends
    if args.list_backends:
        from backends import discover_backends
        backends = discover_backends()
        print(f"\n=== AVAILABLE BACKENDS ({len(backends)}) ===")
        for name, mod in backends.items():
            meta = mod.metadata()
            print(f"\n  {name}: {meta.get('description', 'No description')}")
            print(f"    Models: {json.dumps(meta.get('model_config', {}))}")
        sys.exit(0)

    report = run_on_demand_evaluation(
        dataset_path=args.dataset,
        filter_name=args.name,
        filter_category=args.category,
        filter_layer=args.layer,
        filter_difficulty=args.difficulty,
        dry_run=args.dry_run,
        use_judge=args.judge,
        backend_name=args.backend,
        model_id=args.model,
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
