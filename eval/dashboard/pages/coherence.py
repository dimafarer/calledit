"""Coherence View page — deterministic vs judge score agreement with multi-judge analysis."""

import json
import streamlit as st
from eval.dashboard.data_loader import EvalDataLoader

# All 6 LLM judge evaluator names + legacy
JUDGE_NAMES = {
    "IntentPreservation", "CriteriaMethodAlignment",
    "IntentExtraction", "CategorizationJustification",
    "ClarificationRelevance", "PipelineCoherence",
    "ReasoningQuality",  # legacy
}

PASS_THRESHOLD = 0.5


def _is_judge(name: str) -> bool:
    """Check if an evaluator is an LLM judge."""
    if name in JUDGE_NAMES:
        return True
    base = name.split("_")[0] if "_" in name else name
    return base in JUDGE_NAMES


def _classify_scores(evaluator_scores: dict) -> tuple[dict[str, float], dict[str, float]]:
    """Split evaluator scores into deterministic and judge dicts.

    Returns:
        (det_scores, judge_scores) — both keyed by evaluator name.
    """
    det = {}
    judge = {}
    for name, val in evaluator_scores.items():
        if name.startswith("_"):
            continue
        if not isinstance(val, dict) or "score" not in val:
            continue
        score = float(val["score"])
        if _is_judge(name):
            judge[name] = score
        else:
            det[name] = score
    return det, judge


def _det_pass(det_scores: dict[str, float]) -> bool:
    """Deterministic average passes threshold."""
    if not det_scores:
        return False
    return (sum(det_scores.values()) / len(det_scores)) >= PASS_THRESHOLD


def _agreement_status(det_scores: dict, judge_scores: dict) -> str:
    """Determine agreement between deterministic and judge evaluators."""
    if not det_scores or not judge_scores:
        return "no_judge"
    d_pass = _det_pass(det_scores)
    j_pass = (sum(judge_scores.values()) / len(judge_scores)) >= PASS_THRESHOLD
    if d_pass and j_pass:
        return "agree_pass"
    elif not d_pass and not j_pass:
        return "agree_fail"
    elif d_pass and not j_pass:
        return "det_pass_judge_fail"
    else:
        return "det_fail_judge_pass"


def _per_judge_agreement(test_cases: list[dict]) -> dict[str, dict]:
    """Compute per-judge agreement rate with deterministic evaluators.

    Returns:
        {judge_name: {"agreement_rate": float, "total": int, "agreed": int}}
    """
    judge_stats = {}
    for tc in test_cases:
        scores = tc.get("evaluator_scores", {})
        det, judges = _classify_scores(scores)
        if not det:
            continue
        d_pass = _det_pass(det)
        for jname, jscore in judges.items():
            j_pass = jscore >= PASS_THRESHOLD
            stats = judge_stats.setdefault(jname, {"agreed": 0, "total": 0})
            stats["total"] += 1
            if d_pass == j_pass:
                stats["agreed"] += 1

    result = {}
    for jname, stats in sorted(judge_stats.items()):
        rate = stats["agreed"] / stats["total"] if stats["total"] > 0 else 0.0
        result[jname] = {
            "agreement_rate": rate,
            "total": stats["total"],
            "agreed": stats["agreed"],
        }
    return result


def _judge_vs_judge_correlation(test_cases: list[dict]) -> dict[tuple[str, str], float]:
    """Compute pairwise agreement rates between LLM judges.

    Returns:
        {(judge_a, judge_b): agreement_rate} — symmetric, only stores a < b.
    """
    # Collect per-test-case judge pass/fail
    tc_judge_pass = []
    for tc in test_cases:
        scores = tc.get("evaluator_scores", {})
        _, judges = _classify_scores(scores)
        if len(judges) < 2:
            continue
        pass_map = {j: s >= PASS_THRESHOLD for j, s in judges.items()}
        tc_judge_pass.append(pass_map)

    if not tc_judge_pass:
        return {}

    # Get all judge names that appear
    all_judges = sorted(set(j for pm in tc_judge_pass for j in pm))
    if len(all_judges) < 2:
        return {}

    correlations = {}
    for i, ja in enumerate(all_judges):
        for jb in all_judges[i + 1:]:
            agreed = 0
            total = 0
            for pm in tc_judge_pass:
                if ja in pm and jb in pm:
                    total += 1
                    if pm[ja] == pm[jb]:
                        agreed += 1
            if total > 0:
                correlations[(ja, jb)] = agreed / total
    return correlations


def render(run_detail: dict, loader: EvalDataLoader):
    """Render coherence analysis between evaluator types."""
    st.header("Coherence View")

    test_cases = run_detail.get("test_cases", []) if run_detail else []
    if not test_cases:
        st.info("No test case data available.")
        return

    # Analyze each test case
    results = []
    for tc in test_cases:
        tc_id = tc.get("test_case_id", "?")
        scores = tc.get("evaluator_scores", {})
        det, judge = _classify_scores(scores)
        status = _agreement_status(det, judge)
        results.append({
            "test_case_id": tc_id,
            "det_avg": sum(det.values()) / len(det) if det else None,
            "judge_avg": sum(judge.values()) / len(judge) if judge else None,
            "judge_scores": judge,
            "status": status,
        })

    # Summary statistics
    has_both = [r for r in results if r["status"] != "no_judge"]
    if not has_both:
        st.info("No test cases have both deterministic and judge scores. Run with --judge to populate.")
        return

    agree = sum(1 for r in has_both if r["status"].startswith("agree"))
    pct = agree / len(has_both)
    st.metric("Overall Agreement Rate", f"{pct:.0%}",
              help="% of test cases where deterministic and judge evaluators agree on pass/fail")

    # --- Per-Judge Agreement Breakdown ---
    st.subheader("Per-Judge Agreement with Deterministic Evaluators")
    per_judge = _per_judge_agreement(test_cases)
    if per_judge:
        cols = st.columns(min(len(per_judge), 3))
        for i, (jname, stats) in enumerate(per_judge.items()):
            with cols[i % len(cols)]:
                st.metric(
                    jname,
                    f"{stats['agreement_rate']:.0%}",
                    help=f"{stats['agreed']}/{stats['total']} test cases agree",
                )
    else:
        st.info("No per-judge data available.")

    # --- Judge-vs-Judge Correlation ---
    correlations = _judge_vs_judge_correlation(test_cases)
    if correlations:
        st.subheader("Judge-vs-Judge Agreement")
        st.caption("How often each pair of LLM judges agree on the same test cases.")
        for (ja, jb), rate in sorted(correlations.items()):
            icon = "🟢" if rate >= 0.8 else "🟡" if rate >= 0.6 else "🔴"
            st.markdown(f"{icon} **{ja}** ↔ **{jb}**: {rate:.0%}")

    # --- Disagreement Details ---
    disagreements = [r for r in has_both if not r["status"].startswith("agree")]
    if disagreements:
        st.subheader(f"Disagreements ({len(disagreements)})")
        for r in disagreements:
            icon = "⚠️" if r["status"] == "det_pass_judge_fail" else "🔄"
            label = (
                "Det ✅ / Judge ❌" if r["status"] == "det_pass_judge_fail"
                else "Det ❌ / Judge ✅"
            )
            st.markdown(
                f"{icon} **{r['test_case_id']}** — {label} "
                f"(det avg: {r['det_avg']:.2f}, judge avg: {r['judge_avg']:.2f})"
            )
    else:
        st.success("All test cases show agreement between deterministic and judge evaluators.")

    # --- Chain of Reasoning with per-agent judge data ---
    eval_run_id = run_detail.get("eval_run_id", "")
    st.subheader("Chain of Reasoning")
    st.caption("Agent outputs and per-agent judge scores for a selected test case.")

    tc_ids = [r["test_case_id"] for r in has_both]
    selected = st.selectbox("Inspect test case", tc_ids, key="coherence_tc")

    if selected:
        # Show per-agent judge scores inline
        tc_result = next((r for r in has_both if r["test_case_id"] == selected), None)
        if tc_result and tc_result["judge_scores"]:
            st.markdown("**Per-agent judge scores:**")
            for jname, jscore in sorted(tc_result["judge_scores"].items()):
                color = "green" if jscore >= 0.7 else "orange" if jscore >= 0.5 else "red"
                st.markdown(f"- {jname}: :{color}[{jscore:.2f}]")

        # DDB agent outputs
        if loader.is_ddb_available() and eval_run_id:
            outputs = loader.load_agent_outputs(eval_run_id, selected)
            if outputs:
                chain = _extract_chain(outputs)
                for agent, fields in chain.items():
                    with st.expander(f"🔗 {agent}"):
                        st.json(fields)

            # DDB judge reasoning
            reasoning = loader.load_judge_reasoning(eval_run_id, selected)
            if reasoning:
                with st.expander("🧑‍⚖️ Judge Reasoning"):
                    for rec in reasoning:
                        agent = rec.get("agent_name", "?")
                        score = rec.get("score", "?")
                        text = rec.get("judge_reasoning", "")
                        st.markdown(f"**{agent}** (score: {score})")
                        st.text(text[:500] if len(text) > 500 else text)
                        st.divider()
        elif not loader.is_ddb_available():
            st.info("DDB unavailable — agent outputs and judge reasoning not available.")


def _extract_chain(outputs: dict) -> dict:
    """Extract key fields from each agent's JSON output."""
    chain = {}
    field_map = {
        "parser": ["prediction", "extracted_date", "time_reference"],
        "categorizer": ["verifiable_category", "reasoning"],
        "verification_builder": ["verification_steps", "verification_type"],
        "review": ["reviewable_sections", "questions"],
    }
    for agent, fields in field_map.items():
        raw = outputs.get(f"{agent}_output", "")
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            extracted = {f: parsed[f] for f in fields if f in parsed}
            if extracted:
                chain[agent] = extracted
        except (json.JSONDecodeError, TypeError):
            chain[agent] = {"raw_preview": raw[:200]}
    return chain
