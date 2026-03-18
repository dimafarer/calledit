"""
Sidebar — run selector, comparison selector, and filters.

Stores all selections in st.session_state so pages can read them.
"""

import streamlit as st
from typing import Optional


def render(runs: list[dict]) -> dict:
    """Render sidebar controls and return current selections.

    Args:
        runs: List of run summary dicts, sorted by timestamp descending.

    Returns:
        Dict with keys: selected_run, comparison_run, layer, category,
        dataset_version, page.
    """
    with st.sidebar:
        st.title("CalledIt Eval")

        if not runs:
            st.warning("No eval runs found.")
            return {
                "selected_run": None,
                "comparison_run": None,
                "layer": "all",
                "category": "all",
                "dataset_version": "all",
                "architecture": "all",
                "page": "Trends",
            }

        # Run selector
        run_labels = [
            f"{r.get('timestamp', 'unknown')} ({r.get('dataset_version', '?')})"
            for r in runs
        ]
        selected_idx = st.selectbox(
            "Run", range(len(runs)), format_func=lambda i: run_labels[i], key="run_idx"
        )

        # Comparison run selector (optional, for Prompt Correlation)
        compare_options = [None] + list(range(len(runs)))
        compare_labels = ["None"] + run_labels
        compare_idx = st.selectbox(
            "Compare with",
            compare_options,
            format_func=lambda i: compare_labels[0] if i is None else compare_labels[i + 1],
            key="compare_idx",
        )

        st.divider()

        # Filters
        layer = st.selectbox("Layer", ["all", "base", "fuzzy"], key="filter_layer")
        category = st.selectbox(
            "Category",
            ["all", "auto_verifiable", "automatable", "human_only"],
            key="filter_category",
        )

        # Dataset version filter from available versions
        versions = sorted(set(r.get("dataset_version", "") for r in runs))
        version_options = ["all"] + [v for v in versions if v]
        dataset_version = st.selectbox(
            "Dataset version", version_options, key="filter_dataset_version"
        )

        # Architecture filter from available architectures
        architectures = sorted(set(r.get("architecture", "serial") for r in runs))
        arch_options = ["all"] + [a for a in architectures if a]
        architecture = st.selectbox(
            "Architecture", arch_options, key="filter_architecture"
        )

        st.divider()

        # Page navigation
        page = st.radio(
            "Page",
            [
                "Trends",
                "Heatmap",
                "Architecture Comparison",
                "Prompt Correlation",
                "Reasoning Explorer",
                "Coherence View",
                "Fuzzy Convergence",
            ],
            key="page_nav",
        )

    return {
        "selected_run": runs[selected_idx] if selected_idx is not None else None,
        "comparison_run": runs[compare_idx] if compare_idx is not None else None,
        "layer": layer,
        "category": category,
        "dataset_version": dataset_version,
        "architecture": architecture,
        "page": page,
    }
