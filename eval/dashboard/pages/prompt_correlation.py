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

    # Architecture comparison warning
    arch_a = summary_a.get("architecture", "serial")
    arch_b = summary_b.get("architecture", "serial")
    if arch_a != arch_b:
        st.warning(
            f"Comparing different architectures ({arch_a} vs {arch_b}) — "
            f"score differences may reflect architecture effects, not just prompt changes."
        )

    # Architecture labels
    st.subheader("Architecture")
    st.markdown(f"Run A: **{arch_a}** | Run B: **{arch_b}**")

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

    # Verification-Builder-centric score delta
    vb_delta = comparison.get("vb_centric_delta", {})
    vb_curr = vb_delta.get("current")
    vb_prev = vb_delta.get("previous")
    if vb_curr is not None or vb_prev is not None:
        st.subheader("Verification-Builder-Centric Score")
        d = vb_delta.get("delta")
        if d is not None:
            ind = "↑" if d > 0 else "↓" if d < 0 else "="
            c = "green" if d > 0 else "red" if d < 0 else "grey"
            st.markdown(
                f"**{vb_prev:.2f}** → **{vb_curr:.2f}** "
                f"(:{c}[{ind} {d:+.3f}])"
            )
        else:
            curr_str = f"{vb_curr:.2f}" if vb_curr is not None else "N/A"
            prev_str = f"{vb_prev:.2f}" if vb_prev is not None else "N/A"
            st.markdown(f"**{prev_str}** → **{curr_str}**")

    # Per-agent evaluator deltas
    pa_deltas = comparison.get("per_agent_deltas", {})
    if pa_deltas:
        # Group by effect type when architectures differ
        cross_arch = arch_a != arch_b
        if cross_arch:
            # Determine which evaluators are architecture effects vs prompt effects
            pa_a = summary_a.get("per_agent_aggregates", {})
            pa_b = summary_b.get("per_agent_aggregates", {})
            changed_prompts = comparison.get("changed_prompts", {})

            arch_effects = {}
            prompt_effects = {}
            for ev, info in pa_deltas.items():
                # If evaluator only exists in one run's aggregates, it's architecture effect
                in_a = ev in pa_a
                in_b = ev in pa_b
                if not in_a or not in_b:
                    arch_effects[ev] = info
                else:
                    prompt_effects[ev] = info

            if arch_effects:
                st.subheader("Architecture Effect")
                st.caption("Evaluators affected by architecture differences.")
                for ev, info in sorted(arch_effects.items()):
                    _render_evaluator_delta(ev, info)

            if prompt_effects:
                st.subheader("Prompt Effect")
                st.caption("Evaluators present in both architectures — deltas reflect prompt changes.")
                for ev, info in sorted(prompt_effects.items()):
                    _render_evaluator_delta(ev, info)
        else:
            st.subheader("Per-Agent Evaluator Deltas")
            for ev, info in sorted(pa_deltas.items()):
                _render_evaluator_delta(ev, info)

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


def _render_evaluator_delta(evaluator_name: str, info: dict):
    """Render a single evaluator delta line."""
    d = info.get("delta", 0)
    curr = info.get("current", 0)
    prev = info.get("previous", 0)
    icon = "🟢" if d > 0 else "🔴" if d < 0 else "⚪"
    st.markdown(
        f"{icon} **{evaluator_name}**: "
        f"{prev:.2f} → {curr:.2f} ({d:+.3f})"
    )
