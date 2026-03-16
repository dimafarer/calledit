"""Coherence View page — deterministic vs judge score agreement."""

import json
import streamlit as st
from eval.dashboard.data_loader import EvalDataLoader


def _classify_scores(evaluator_scores: dict) -> tuple[list[float], list[float]]:
    """Split evaluator scores into deterministic and judge lists."""
    det_scores = []
    judge_scores = []
    for name, val in evaluator_scores.items():
        if not isinstance(val, dict) or "score" not in val:
            continue
        score = float(val["score"])
        if "ReasoningQuality" in name:
            judge_scores.append(score)
        else:
            det_scores.append(score)
    return det_scores, judge_scores


def _agreement_status(det_scores: list[float], judge_scores: list[float]) -> str:
    """Determine agreement between deterministic and judge evaluators.

    Pass threshold: average >= 0.5
    """
    if not det_scores or not judge_scores:
        return "no_judge"  # Can't compare without both

    det_pass = (sum(det_scores) / len(det_scores)) >= 0.5
    judge_pass = (sum(judge_scores) / len(judge_scores)) >= 0.5

    if det_pass and judge_pass:
        return "agree_pass"
    elif not det_pass and not judge_pass:
        return "agree_fail"
    elif det_pass and not judge_pass:
        return "det_pass_judge_fail"
    else:
        return "det_fail_judge_pass"


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
            "det_avg": sum(det) / len(det) if det else None,
            "judge_avg": sum(judge) / len(judge) if judge else None,
            "status": status,
        })

    # Summary statistics
    has_both = [r for r in results if r["status"] != "no_judge"]
    if has_both:
        agree = sum(1 for r in has_both if r["status"].startswith("agree"))
        pct = agree / len(has_both)
        st.metric("Agreement Rate", f"{pct:.0%}", help="% of test cases where deterministic and judge evaluators agree")

        # Disagreement breakdown
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
    else:
        st.info("No test cases have both deterministic and judge scores. Run with --judge to populate.")

    # Agent chain of reasoning (DDB only)
    if loader.is_ddb_available() and has_both:
        eval_run_id = run_detail.get("eval_run_id", "")
        st.subheader("Chain of Reasoning")
        st.caption("Key fields extracted from each agent's output to show the reasoning chain.")

        # Let user pick a test case to inspect
        tc_ids = [r["test_case_id"] for r in has_both]
        selected = st.selectbox("Inspect test case", tc_ids, key="coherence_tc")

        if selected and eval_run_id:
            outputs = loader.load_agent_outputs(eval_run_id, selected)
            if outputs:
                chain = _extract_chain(outputs)
                for agent, fields in chain.items():
                    with st.expander(f"🔗 {agent}"):
                        st.json(fields)
            else:
                st.info("No agent outputs available for this test case.")


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
