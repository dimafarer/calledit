"""Reasoning Explorer page — drill into individual test cases."""

import json
import streamlit as st
from eval.dashboard.data_loader import EvalDataLoader

# Fixed pipeline order for agent outputs
PIPELINE_ORDER = ["parser", "categorizer", "verification_builder", "review"]


def render(run_detail: dict, loader: EvalDataLoader):
    """Render test case detail with agent outputs and judge reasoning."""
    st.header("Reasoning Explorer")

    test_cases = run_detail.get("test_cases", []) if run_detail else []
    if not test_cases:
        st.info("No test case data available.")
        return

    eval_run_id = run_detail.get("eval_run_id", "")

    # Test case selector
    tc_ids = [tc.get("test_case_id", "?") for tc in test_cases]
    selected_id = st.selectbox("Test Case", tc_ids, key="re_test_case")

    selected_tc = next(
        (tc for tc in test_cases if tc.get("test_case_id") == selected_id), None
    )
    if not selected_tc:
        return

    # Evaluator scores summary
    st.subheader("Evaluator Scores")
    scores = selected_tc.get("evaluator_scores", {})
    score_rows = []
    for name, val in sorted(scores.items()):
        if isinstance(val, dict) and "score" in val:
            score_rows.append({"Evaluator": name, "Score": f"{val['score']:.2f}"})
    if score_rows:
        st.table(score_rows)

    # Agent outputs (DDB only)
    st.subheader("Agent Outputs")
    if not loader.is_ddb_available():
        st.info("Reasoning traces not available — DDB unavailable.")
    else:
        outputs = loader.load_agent_outputs(eval_run_id, selected_id)
        if outputs:
            for agent in PIPELINE_ORDER:
                key = f"{agent}_output"
                text = outputs.get(key, "")
                if text:
                    with st.expander(f"🔹 {agent}", expanded=False):
                        # Try to pretty-print JSON, fall back to raw text
                        try:
                            parsed = json.loads(text)
                            st.json(parsed)
                        except (json.JSONDecodeError, TypeError):
                            st.text(text)
        else:
            st.info("No agent outputs found for this test case.")

    # Judge reasoning (DDB only)
    st.subheader("Judge Reasoning")
    if not loader.is_ddb_available():
        st.info("Judge reasoning not available — DDB unavailable.")
    else:
        reasoning = loader.load_judge_reasoning(eval_run_id, selected_id)
        if reasoning:
            for item in reasoning:
                agent = item.get("agent_name", "?")
                with st.expander(f"⚖️ Judge: {agent}", expanded=False):
                    st.markdown(f"**Score:** {item.get('score', '?')}")
                    st.markdown(f"**Model:** {item.get('judge_model', '?')}")
                    st.text(item.get("judge_reasoning", ""))
        else:
            st.info("No judge reasoning found for this test case.")

    # Token counts (DDB only)
    st.subheader("Token Counts")
    if not loader.is_ddb_available():
        st.info("Token counts not available — DDB unavailable.")
    else:
        tokens = loader.load_token_counts(eval_run_id, selected_id)
        if tokens:
            token_rows = []
            for agent in PIPELINE_ORDER:
                inp = tokens.get(f"{agent}_input_tokens", 0)
                out = tokens.get(f"{agent}_output_tokens", 0)
                if inp or out:
                    token_rows.append({
                        "Agent": agent,
                        "Input Tokens": inp,
                        "Output Tokens": out,
                    })
            if token_rows:
                st.table(token_rows)
        else:
            st.info("No token counts found for this test case.")
