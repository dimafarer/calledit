"""Architecture Comparison page — side-by-side metrics for two runs from different architectures."""

import plotly.graph_objects as go
import streamlit as st


EVALUATOR_GROUPS = {
    "final_output": ["IntentPreservation", "CriteriaMethodAlignment"],
    "per_agent": ["IntentExtraction", "CategorizationJustification", "ClarificationRelevance"],
    "cross_pipeline": ["PipelineCoherence"],
    "deterministic": ["CategoryMatch", "JSONValidity", "ClarificationQuality", "Convergence"],
}

# Flat lookup: evaluator name → group name
_EVALUATOR_TO_GROUP = {}
for _group, _names in EVALUATOR_GROUPS.items():
    for _name in _names:
        _EVALUATOR_TO_GROUP[_name] = _group


def _get_evaluator_avg(per_agent_agg: dict, name: str) -> float | None:
    """Extract average score for an evaluator from per_agent_aggregates.

    Supports both {"avg": float} dict and plain float values.
    Returns None if the evaluator is absent.
    """
    val = per_agent_agg.get(name)
    if val is None:
        return None
    if isinstance(val, dict):
        return float(val.get("avg", 0.0))
    return float(val)


def render(run_a_detail: dict, run_b_detail: dict, run_a_summary: dict, run_b_summary: dict):
    """Render architecture comparison between two runs.

    Args:
        run_a_detail: Selected run detail (has test_cases).
        run_b_detail: Comparison run detail (has test_cases).
        run_a_summary: Selected run summary.
        run_b_summary: Comparison run summary.
    """
    st.header("Architecture Comparison")

    if not run_a_summary or not run_b_summary:
        st.info("Select two runs to compare.")
        return

    arch_a = run_a_summary.get("architecture", "serial")
    arch_b = run_b_summary.get("architecture", "serial")
    ts_a = run_a_summary.get("timestamp", "?")
    ts_b = run_b_summary.get("timestamp", "?")
    label_a = f"Run A — {arch_a} ({ts_a})"
    label_b = f"Run B — {arch_b} ({ts_b})"

    # --- Same-architecture guard ---
    if arch_a == arch_b:
        st.info(
            "Both runs use the same architecture — "
            "use Prompt Correlation for prompt-level comparison."
        )

    # --- Verification-Builder-Centric Score ---
    st.subheader("Verification Builder-Centric Score")
    vb_a = run_a_summary.get("vb_centric_score")
    vb_b = run_b_summary.get("vb_centric_score")

    col1, col2 = st.columns(2)
    with col1:
        if vb_a is not None:
            delta_val = round(vb_a - vb_b, 4) if vb_b is not None else None
            st.metric(label_a, f"{vb_a:.3f}", delta=f"{delta_val:+.3f}" if delta_val is not None else None)
        else:
            st.metric(label_a, "N/A")
    with col2:
        if vb_b is not None:
            delta_val = round(vb_b - vb_a, 4) if vb_a is not None else None
            st.metric(label_b, f"{vb_b:.3f}", delta=f"{delta_val:+.3f}" if delta_val is not None else None)
        else:
            st.metric(label_b, "N/A")

    # --- Per-Evaluator Score Comparison (grouped bar chart) ---
    _render_evaluator_comparison(run_a_summary, run_b_summary, label_a, label_b)

    # --- Per-Agent Evaluator Scores ---
    _render_per_agent_scores(run_a_summary, run_b_summary, label_a, label_b)

    # --- PipelineCoherence Callout ---
    _render_pipeline_coherence_callout(run_a_summary, run_b_summary, label_a, label_b)

    # --- Per-Category Accuracy ---
    _render_category_accuracy(run_a_summary, run_b_summary, label_a, label_b)

    # --- Execution Time ---
    _render_execution_time(run_a_detail, run_b_detail, label_a, label_b)


def _render_evaluator_comparison(
    run_a_summary: dict, run_b_summary: dict, label_a: str, label_b: str
):
    """Grouped bar chart of evaluator scores, grouped by EVALUATOR_GROUPS taxonomy."""
    st.subheader("Per-Evaluator Score Comparison")

    paa_a = run_a_summary.get("per_agent_aggregates", {})
    paa_b = run_b_summary.get("per_agent_aggregates", {})
    vqa_a = run_a_summary.get("verification_quality_aggregates", {})
    vqa_b = run_b_summary.get("verification_quality_aggregates", {})

    # Build ordered evaluator list and scores
    evaluator_names = []
    scores_a = []
    scores_b = []
    group_boundaries = []  # (start_idx, group_label)

    # Map from evaluator name to verification_quality_aggregates key
    vqa_key_map = {
        "IntentPreservation": "intent_preservation_avg",
        "CriteriaMethodAlignment": "criteria_method_alignment_avg",
    }

    for group_name, evaluators in EVALUATOR_GROUPS.items():
        group_boundaries.append((len(evaluator_names), group_name.replace("_", " ").title()))
        for ev in evaluators:
            evaluator_names.append(ev)
            # Try per_agent_aggregates first, then verification_quality_aggregates
            sa = _get_evaluator_avg(paa_a, ev)
            if sa is None and ev in vqa_key_map:
                raw = vqa_a.get(vqa_key_map[ev])
                sa = float(raw) if raw is not None else None
            sb = _get_evaluator_avg(paa_b, ev)
            if sb is None and ev in vqa_key_map:
                raw = vqa_b.get(vqa_key_map[ev])
                sb = float(raw) if raw is not None else None
            scores_a.append(sa)
            scores_b.append(sb)

    if not any(s is not None for s in scores_a + scores_b):
        st.info("No evaluator score data available for either run.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=evaluator_names, y=scores_a, name=label_a,
        marker_color="steelblue",
    ))
    fig.add_trace(go.Bar(
        x=evaluator_names, y=scores_b, name=label_b,
        marker_color="coral",
    ))

    # Add vertical separators between groups
    for i, (start_idx, _) in enumerate(group_boundaries[1:], 1):
        fig.add_vline(
            x=start_idx - 0.5,
            line_dash="dash",
            line_color="grey",
            line_width=1,
        )

    # Add group label annotations
    for i, (start_idx, group_label) in enumerate(group_boundaries):
        end_idx = group_boundaries[i + 1][0] if i + 1 < len(group_boundaries) else len(evaluator_names)
        mid = (start_idx + end_idx - 1) / 2
        fig.add_annotation(
            x=mid, y=1.08, text=group_label,
            showarrow=False, yref="paper",
            font=dict(size=11, color="grey"),
        )

    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 1.05], title="Score"),
        xaxis_title="Evaluator",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_per_agent_scores(
    run_a_summary: dict, run_b_summary: dict, label_a: str, label_b: str
):
    """Show per-agent evaluator scores, N/A for missing evaluators."""
    st.subheader("Per-Agent Evaluator Scores")

    paa_a = run_a_summary.get("per_agent_aggregates", {})
    paa_b = run_b_summary.get("per_agent_aggregates", {})

    if not paa_a and not paa_b:
        st.info("No per-agent evaluator data available for either run.")
        return

    all_evaluators = sorted(set(list(paa_a.keys()) + list(paa_b.keys())))

    header_cols = st.columns([2, 1, 1])
    header_cols[0].markdown("**Evaluator**")
    header_cols[1].markdown(f"**{label_a}**")
    header_cols[2].markdown(f"**{label_b}**")

    for ev in all_evaluators:
        cols = st.columns([2, 1, 1])
        cols[0].write(ev)
        val_a = _get_evaluator_avg(paa_a, ev)
        val_b = _get_evaluator_avg(paa_b, ev)
        cols[1].write(f"{val_a:.3f}" if val_a is not None else "N/A")
        cols[2].write(f"{val_b:.3f}" if val_b is not None else "N/A")


def _render_pipeline_coherence_callout(
    run_a_summary: dict, run_b_summary: dict, label_a: str, label_b: str
):
    """Dedicated PipelineCoherence section explaining the silo problem."""
    st.subheader("PipelineCoherence")

    paa_a = run_a_summary.get("per_agent_aggregates", {})
    paa_b = run_b_summary.get("per_agent_aggregates", {})
    pc_a = _get_evaluator_avg(paa_a, "PipelineCoherence")
    pc_b = _get_evaluator_avg(paa_b, "PipelineCoherence")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label_a, f"{pc_a:.3f}" if pc_a is not None else "N/A")
    with col2:
        st.metric(label_b, f"{pc_b:.3f}" if pc_b is not None else "N/A")

    st.info(
        "PipelineCoherence quantifies the silo problem — whether agents build on "
        "each other's work or re-interpret from scratch. A higher score means better "
        "information flow between pipeline stages."
    )


def _render_category_accuracy(
    run_a_summary: dict, run_b_summary: dict, label_a: str, label_b: str
):
    """Grouped bar chart of per-category accuracy."""
    st.subheader("Per-Category Accuracy")

    pca_a = run_a_summary.get("per_category_accuracy", {})
    pca_b = run_b_summary.get("per_category_accuracy", {})

    all_cats = sorted(set(list(pca_a.keys()) + list(pca_b.keys())))
    if not all_cats:
        st.info("No per-category accuracy data available.")
        return

    vals_a = [pca_a.get(c) for c in all_cats]
    vals_b = [pca_b.get(c) for c in all_cats]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=all_cats, y=vals_a, name=label_a, marker_color="steelblue"))
    fig.add_trace(go.Bar(x=all_cats, y=vals_b, name=label_b, marker_color="coral"))
    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 1.05], title="Accuracy", tickformat=".0%"),
        xaxis_title="Category",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_execution_time(
    run_a_detail: dict, run_b_detail: dict, label_a: str, label_b: str
):
    """Total and per-test-case average execution time for both runs."""
    st.subheader("Execution Time")

    def _compute_times(detail: dict) -> tuple[float, float, int]:
        """Return (total_ms, avg_ms, count) from test cases."""
        tcs = detail.get("test_cases", []) if detail else []
        times = [tc.get("execution_time_ms", 0) for tc in tcs]
        total = sum(times)
        count = len(times)
        avg = total / count if count else 0
        return total, avg, count

    total_a, avg_a, count_a = _compute_times(run_a_detail)
    total_b, avg_b, count_b = _compute_times(run_b_detail)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{label_a}** ({count_a} test cases)")
        st.metric("Total", f"{total_a / 1000:.1f}s")
        st.metric("Avg per test case", f"{avg_a / 1000:.2f}s")
    with col2:
        st.markdown(f"**{label_b}** ({count_b} test cases)")
        st.metric("Total", f"{total_b / 1000:.1f}s")
        st.metric("Avg per test case", f"{avg_b / 1000:.2f}s")
