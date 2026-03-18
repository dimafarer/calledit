"""Trends page — pass rate and per-category accuracy over time."""

import plotly.graph_objects as go
import streamlit as st


def _prompt_change_annotations(runs: list[dict]) -> list[dict]:
    """Find runs where prompt versions changed from the previous run."""
    annotations = []
    for i in range(1, len(runs)):
        prev_manifest = runs[i - 1].get("prompt_version_manifest", {})
        curr_manifest = runs[i].get("prompt_version_manifest", {})
        changes = []
        for key in set(list(prev_manifest.keys()) + list(curr_manifest.keys())):
            pv = prev_manifest.get(key, "?")
            cv = curr_manifest.get(key, "?")
            if pv != cv:
                changes.append(f"{key}: {pv} → {cv}")
        if changes:
            annotations.append({
                "x": runs[i].get("timestamp", ""),
                "text": "\n".join(changes),
            })
    return annotations


def render(runs: list[dict], architecture_filter: str = "all"):
    """Render trend charts from run summaries."""
    st.header("Trends")

    if not runs:
        st.info("No runs to display.")
        return

    # Apply architecture filter
    if architecture_filter != "all":
        runs = [r for r in runs if r.get("architecture", "serial") == architecture_filter]
        if not runs:
            st.info(f"No runs with architecture '{architecture_filter}'.")
            return

    # Sort chronologically for charting (oldest first)
    sorted_runs = sorted(runs, key=lambda r: r.get("timestamp", ""))

    timestamps = [r.get("timestamp", "") for r in sorted_runs]
    pass_rates = [r.get("overall_pass_rate", 0.0) for r in sorted_runs]
    architectures = [r.get("architecture", "serial") for r in sorted_runs]

    # --- Verification-Builder-centric score chart (primary metric) ---
    vb_scores = [r.get("vb_centric_score") for r in sorted_runs]
    if any(v is not None for v in vb_scores):
        fig_vb = go.Figure()
        fig_vb.add_trace(go.Scatter(
            x=timestamps, y=vb_scores,
            mode="lines+markers", name="VB-Centric Score",
            connectgaps=True,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "VB-Centric Score: %{y:.2f}<br>"
                "%{customdata}"
                "<extra></extra>"
            ),
            customdata=[
                f"Architecture: {a}" for a in architectures
            ],
        ))
        fig_vb.update_layout(
            title="Verification-Builder-Centric Score Over Time (Primary Metric)",
            xaxis_title="Run",
            yaxis_title="Composite Score",
            yaxis=dict(range=[0, 1.05]),
            hovermode="x unified",
        )
        st.plotly_chart(fig_vb, width="stretch")

    # --- Overall pass rate line chart ---
    fig_overall = go.Figure()
    fig_overall.add_trace(go.Scatter(
        x=timestamps,
        y=pass_rates,
        mode="lines+markers",
        name="Overall Pass Rate",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Pass Rate: %{y:.1%}<br>"
            "%{customdata}"
            "<extra></extra>"
        ),
        customdata=[
            f"Architecture: {r.get('architecture', 'serial')}<br>"
            f"Tests: {r.get('total_tests', 0)} | "
            f"Passed: {r.get('passed', 0)} | "
            f"Dataset: {r.get('dataset_version', '?')}<br>"
            f"Prompts: {r.get('prompt_version_manifest', {})}"
            for r in sorted_runs
        ],
    ))

    # Prompt change annotations
    for ann in _prompt_change_annotations(sorted_runs):
        fig_overall.add_annotation(
            x=ann["x"],
            y=next(
                (r.get("overall_pass_rate", 0) for r in sorted_runs
                 if r.get("timestamp") == ann["x"]),
                0,
            ),
            text="📝",
            hovertext=ann["text"],
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-30,
        )

    fig_overall.update_layout(
        title="Overall Pass Rate Over Time",
        xaxis_title="Run",
        yaxis_title="Pass Rate",
        yaxis=dict(range=[0, 1.05], tickformat=".0%"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_overall, width="stretch")

    # --- Per-category accuracy chart ---
    categories = set()
    for r in sorted_runs:
        categories.update(r.get("per_category_accuracy", {}).keys())
    categories = sorted(categories)

    if categories:
        fig_cat = go.Figure()
        for cat in categories:
            values = [
                r.get("per_category_accuracy", {}).get(cat, None)
                for r in sorted_runs
            ]
            fig_cat.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                mode="lines+markers",
                name=cat,
                connectgaps=True,
            ))

        fig_cat.update_layout(
            title="Per-Category Accuracy Over Time",
            xaxis_title="Run",
            yaxis_title="Accuracy",
            yaxis=dict(range=[0, 1.05], tickformat=".0%"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_cat, width="stretch")

    # --- Final-Output Evaluators chart (IntentPreservation, CriteriaMethodAlignment) ---
    ip_values = [
        r.get("verification_quality_aggregates", {}).get("intent_preservation_avg")
        for r in sorted_runs
    ]
    cma_values = [
        r.get("verification_quality_aggregates", {}).get("criteria_method_alignment_avg")
        for r in sorted_runs
    ]
    if any(v is not None for v in ip_values + cma_values):
        fig_fo = go.Figure()
        fig_fo.add_trace(go.Scatter(
            x=timestamps, y=ip_values,
            mode="lines+markers", name="IntentPreservation",
            connectgaps=True,
        ))
        fig_fo.add_trace(go.Scatter(
            x=timestamps, y=cma_values,
            mode="lines+markers", name="CriteriaMethodAlignment",
            connectgaps=True,
        ))
        fig_fo.update_layout(
            title="Final-Output Evaluators Over Time",
            xaxis_title="Run",
            yaxis_title="Average Score",
            yaxis=dict(range=[0, 1.05]),
            hovermode="x unified",
        )
        st.plotly_chart(fig_fo, width="stretch")

    # --- Per-Agent & Cross-Pipeline Evaluators chart ---
    per_agent_judges = [
        ("IntentExtraction", "intent_extraction_avg"),
        ("CategorizationJustification", "categorization_justification_avg"),
        ("ClarificationRelevance", "clarification_relevance_avg"),
        ("PipelineCoherence", "pipeline_coherence_avg"),
    ]

    # Extract per-agent judge averages from per_agent_aggregates or
    # verification_quality_aggregates (whichever has the data)
    judge_traces = {}
    for display_name, agg_key in per_agent_judges:
        values = []
        for r in sorted_runs:
            pa = r.get("per_agent_aggregates", {})
            vqa = r.get("verification_quality_aggregates", {})
            # Check per_agent_aggregates first (keyed by evaluator name)
            val = None
            if display_name in pa:
                avg = pa[display_name]
                val = avg.get("avg") if isinstance(avg, dict) else avg
            elif agg_key in vqa:
                val = vqa[agg_key]
            values.append(val)
        judge_traces[display_name] = values

    # Only show if at least one run has any per-agent judge data
    all_values = [v for vals in judge_traces.values() for v in vals]
    if any(v is not None for v in all_values):
        fig_pa = go.Figure()
        for name, values in judge_traces.items():
            fig_pa.add_trace(go.Scatter(
                x=timestamps, y=values,
                mode="lines+markers", name=name,
                connectgaps=True,
            ))
        fig_pa.update_layout(
            title="Per-Agent & Cross-Pipeline Evaluators Over Time",
            xaxis_title="Run",
            yaxis_title="Average Score",
            yaxis=dict(range=[0, 1.05]),
            hovermode="x unified",
        )
        st.plotly_chart(fig_pa, width="stretch")
