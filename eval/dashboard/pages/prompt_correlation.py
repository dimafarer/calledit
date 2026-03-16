"""Prompt Correlation page — side-by-side run comparison."""

import streamlit as st
from eval.dashboard.data_loader import EvalDataLoader


def render(run_a: dict, run_b: dict, runs: list[dict]):
    """Render prompt version diff and category deltas between two runs.

    Args:
        run_a: Current/selected run detail (has test_cases).
        run_b: Comparison run detail (has test_cases).
        runs: All run summaries (for metadata lookup).
    """
    st.header("Prompt Correlation")

    if not run_a or not run_b:
        st.info("Select two runs to compare.")
        return

    # Find run summaries for comparison (run_a/run_b may be detail dicts)
    # Use the loader's compare_runs which works on summary dicts
    loader = EvalDataLoader.__new__(EvalDataLoader)
    loader._ddb_available = False  # compare_runs is pure logic, no DDB needed

    # Build summary-like dicts from whatever we have
    summary_a = _to_summary(run_a, runs)
    summary_b = _to_summary(run_b, runs)

    comparison = loader.compare_runs(summary_a, summary_b)

    # Dataset version mismatch warning
    if comparison.get("dataset_version_mismatch"):
        st.warning(
            "Dataset versions differ between runs — score comparisons may not be meaningful."
        )

    # Prompt version diff
    st.subheader("Prompt Changes")
    changed = comparison.get("changed_prompts", {})
    if changed:
        for agent, diff in changed.items():
            st.markdown(f"- **{agent}**: {diff['from']} → {diff['to']}")
    else:
        st.info("No prompt version changes between these runs.")

    # Overall pass rate delta
    st.subheader("Overall Pass Rate")
    opr = comparison.get("overall_pass_rate", {})
    delta = opr.get("delta", 0)
    indicator = "↑" if delta > 0 else "↓" if delta < 0 else "="
    color = "green" if delta > 0 else "red" if delta < 0 else "grey"
    st.markdown(
        f"**{opr.get('previous', 0):.1%}** → **{opr.get('current', 0):.1%}** "
        f"(:{color}[{indicator} {delta:+.1%}])"
    )

    # Category deltas table
    st.subheader("Category Accuracy Deltas")
    cat_deltas = comparison.get("category_deltas", {})
    if cat_deltas:
        for cat, info in sorted(cat_deltas.items()):
            d = info["delta"]
            status_icon = "🟢" if d > 0 else "🔴" if d < 0 else "⚪"
            st.markdown(
                f"{status_icon} **{cat}**: "
                f"{info['previous']:.1%} → {info['current']:.1%} "
                f"({d:+.1%})"
            )
    else:
        st.info("No category data available.")


def _to_summary(run_detail: dict, runs: list[dict]) -> dict:
    """Extract or find a summary dict for comparison."""
    # If it already has per_category_accuracy, it's summary-like
    if "per_category_accuracy" in run_detail:
        return run_detail
    # Try to find matching summary by eval_run_id or timestamp
    rid = run_detail.get("eval_run_id", "")
    ts = run_detail.get("timestamp", "")
    for r in runs:
        if rid and r.get("eval_run_id") == rid:
            return r
        if ts and r.get("timestamp") == ts:
            return r
    return run_detail
