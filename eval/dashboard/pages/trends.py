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


def render(runs: list[dict]):
    """Render trend charts from run summaries."""
    st.header("Trends")

    if not runs:
        st.info("No runs to display.")
        return

    # Sort chronologically for charting (oldest first)
    sorted_runs = sorted(runs, key=lambda r: r.get("timestamp", ""))

    timestamps = [r.get("timestamp", "") for r in sorted_runs]
    pass_rates = [r.get("overall_pass_rate", 0.0) for r in sorted_runs]

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
    st.plotly_chart(fig_overall, use_container_width=True)

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
        st.plotly_chart(fig_cat, use_container_width=True)
