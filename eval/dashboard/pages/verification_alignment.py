"""
Verification Alignment — dashboard page for plan-execution comparison.

Visualizes the four verification alignment evaluators (ToolAlignment,
SourceAccuracy, CriteriaQuality, StepFidelity), delta classification
breakdown, and per-prediction plan vs outcome details.

Only shows data when eval runs include --verify mode results.
"""

import streamlit as st


VERIFY_EVALUATORS = ["ToolAlignment", "SourceAccuracy", "CriteriaQuality", "StepFidelity"]
DELTA_CATEGORIES = ["plan_error", "new_information", "tool_drift"]


def render(run_detail: dict, loader=None):
    """Render the Verification Alignment dashboard page."""
    st.header("Verification Alignment")

    if not run_detail or not run_detail.get("test_cases"):
        st.info("No test case data available for this run.")
        return

    test_cases = run_detail["test_cases"]

    # Separate verified, skipped, and no-data cases
    verified = []
    skipped = []
    for tc in test_cases:
        scores = tc.get("evaluator_scores", {})
        has_verify = any(vn in scores for vn in VERIFY_EVALUATORS)
        is_skipped = scores.get("_skipped_evaluators", {}).get("ToolAlignment") == "future_dated"
        if has_verify:
            verified.append(tc)
        elif is_skipped:
            skipped.append(tc)

    if not verified and not skipped:
        st.info("No verification data in this run. Use `--verify` flag to enable.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Verified", len(verified))
    col2.metric("Skipped (future)", len(skipped))
    col3.metric("Total", len(test_cases))

    # Evaluator score averages bar chart
    if verified:
        st.subheader("Alignment Scores")
        eval_avgs = {}
        for vn in VERIFY_EVALUATORS:
            scores_list = []
            for tc in verified:
                val = tc.get("evaluator_scores", {}).get(vn)
                if isinstance(val, dict) and "score" in val:
                    scores_list.append(float(val["score"]))
            if scores_list:
                eval_avgs[vn] = sum(scores_list) / len(scores_list)

        if eval_avgs:
            import pandas as pd
            df = pd.DataFrame([
                {"Evaluator": k, "Mean Score": round(v, 3)}
                for k, v in eval_avgs.items()
            ])
            st.bar_chart(df.set_index("Evaluator"))

    # Delta classification breakdown
    if verified:
        st.subheader("Delta Classification Breakdown")
        delta_counts = {cat: 0 for cat in DELTA_CATEGORIES}
        for tc in verified:
            for vn in VERIFY_EVALUATORS:
                val = tc.get("evaluator_scores", {}).get(vn)
                if isinstance(val, dict):
                    dc = val.get("delta_classification")
                    if dc in delta_counts:
                        delta_counts[dc] += 1

        total_deltas = sum(delta_counts.values())
        if total_deltas > 0:
            import pandas as pd
            df_delta = pd.DataFrame([
                {"Category": k, "Count": v}
                for k, v in delta_counts.items()
            ])
            st.bar_chart(df_delta.set_index("Category"))
        else:
            st.info("No deltas detected — all plans matched execution perfectly.")

    # Per-test-case detail table
    if verified:
        st.subheader("Per-Prediction Details")
        for tc in verified:
            tc_id = tc.get("test_case_id", "unknown")
            scores = tc.get("evaluator_scores", {})
            score_summary = ", ".join(
                f"{vn}: {scores.get(vn, {}).get('score', '?'):.2f}"
                if isinstance(scores.get(vn), dict) and isinstance(scores.get(vn, {}).get("score"), (int, float))
                else f"{vn}: ?"
                for vn in VERIFY_EVALUATORS
            )
            with st.expander(f"{tc_id} — {score_summary}"):
                # Show plan vs outcome
                vplan = tc.get("verification_plan", {})
                voutcome = tc.get("verification_outcome", {})
                if vplan:
                    st.write("**Plan:**")
                    st.json(vplan)
                if voutcome:
                    st.write("**Outcome:**")
                    st.json(voutcome)
                # Show evaluator details
                for vn in VERIFY_EVALUATORS:
                    val = scores.get(vn)
                    if isinstance(val, dict):
                        st.write(f"**{vn}:** score={val.get('score', '?')}")
                        if val.get("judge_reasoning"):
                            st.caption(val["judge_reasoning"][:500])
                        if val.get("delta_classification"):
                            st.write(f"Delta: {val['delta_classification']}")

    # Skipped cases
    if skipped:
        st.subheader("Skipped (Future-Dated)")
        skipped_ids = [tc.get("test_case_id", "?") for tc in skipped]
        st.write(", ".join(skipped_ids))
