"""
CalledIt Eval Dashboard — Streamlit entry point.

Launch:
    cd /home/wsluser/projects/calledit
    /home/wsluser/projects/calledit/venv/bin/python -m streamlit run eval/dashboard/app.py
"""

import streamlit as st

st.set_page_config(page_title="CalledIt Eval Dashboard", layout="wide")

# Imports after set_page_config (Streamlit requirement)
import sys
import os
# Ensure project root is on path so eval.dashboard imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.dashboard.data_loader import EvalDataLoader
from eval.dashboard import sidebar
from eval.dashboard.pages import (
    trends,
    heatmap,
    architecture_comparison,
    prompt_correlation,
    reasoning_explorer,
    coherence,
    fuzzy_convergence,
    verification_alignment,
)


def main():
    loader = EvalDataLoader()

    # DDB availability banner
    if not loader.is_ddb_available():
        st.info(
            "DDB unavailable — using local data. Reasoning traces not available."
        )

    # Load all runs
    runs = loader.load_all_runs()

    if not runs:
        st.warning("No eval runs found. Run an evaluation first.")
        return

    # Sidebar selections
    sel = sidebar.render(runs)
    selected_run = sel["selected_run"]
    page = sel["page"]

    if selected_run is None:
        return

    # Load detail for selected run (needed by most pages)
    run_detail = loader.load_run_detail(
        selected_run.get("eval_run_id", ""),
        selected_run.get("timestamp", ""),
    )

    # Apply filters to run_detail test cases
    if run_detail and "test_cases" in run_detail:
        filtered = run_detail["test_cases"]
        if sel["layer"] != "all":
            filtered = [t for t in filtered if t.get("layer") == sel["layer"]]
        if sel["category"] != "all":
            filtered = [
                t for t in filtered if t.get("expected_category") == sel["category"]
            ]
        run_detail = {**run_detail, "test_cases": filtered}

    # Filter runs for trends by dataset version
    filtered_runs = runs
    if sel["dataset_version"] != "all":
        filtered_runs = [
            r for r in runs if r.get("dataset_version", "") == sel["dataset_version"]
        ]

    # Page routing
    if page == "Trends":
        trends.render(filtered_runs, architecture_filter=sel["architecture"])
    elif page == "Heatmap":
        comparison_run = sel["comparison_run"]
        comp_detail = None
        if comparison_run:
            comp_detail = loader.load_run_detail(
                comparison_run.get("eval_run_id", ""),
                comparison_run.get("timestamp", ""),
            )
            if comp_detail:
                comp_detail = {**comp_detail, "architecture": comparison_run.get("architecture", "serial")}
        # Pass architecture from run summary into run_detail for display
        run_detail_with_arch = {**run_detail, "architecture": selected_run.get("architecture", "serial")}
        heatmap.render(run_detail_with_arch, comparison_detail=comp_detail)
    elif page == "Prompt Correlation":
        comparison_run = sel["comparison_run"]
        if comparison_run:
            comp_detail = loader.load_run_detail(
                comparison_run.get("eval_run_id", ""),
                comparison_run.get("timestamp", ""),
            )
            prompt_correlation.render(run_detail, comp_detail, runs)
        else:
            st.info("Select a comparison run in the sidebar to use this page.")
    elif page == "Architecture Comparison":
        comparison_run = sel["comparison_run"]
        if comparison_run:
            comp_detail = loader.load_run_detail(
                comparison_run.get("eval_run_id", ""),
                comparison_run.get("timestamp", ""),
            )
            architecture_comparison.render(
                run_detail, comp_detail,
                selected_run, comparison_run,
            )
        else:
            st.info("Select a comparison run in the sidebar to use this page.")
    elif page == "Reasoning Explorer":
        reasoning_explorer.render(run_detail, loader)
    elif page == "Coherence View":
        coherence.render(run_detail, loader)
    elif page == "Fuzzy Convergence":
        fuzzy_convergence.render(run_detail)
    elif page == "Verification Alignment":
        verification_alignment.render(run_detail, loader)


if __name__ == "__main__":
    main()
