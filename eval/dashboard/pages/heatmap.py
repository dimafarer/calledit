"""Heatmap page — per-test-case evaluator score matrix with evaluator grouping."""

import plotly.graph_objects as go
import streamlit as st

# Evaluator group taxonomy — matches eval runner's evaluator_groups
EVALUATOR_GROUPS = {
    "Final-Output": ["IntentPreservation", "CriteriaMethodAlignment"],
    "Per-Agent": ["IntentExtraction", "CategorizationJustification", "ClarificationRelevance"],
    "Cross-Pipeline": ["PipelineCoherence"],
    "Deterministic": [
        "CategoryMatch", "JSONValidity", "ClarificationQuality", "Convergence",
    ],
}

# Flat set of all known evaluator names for classification
_ALL_KNOWN = {name for names in EVALUATOR_GROUPS.values() for name in names}

# Judge evaluator names (non-deterministic)
_JUDGE_NAMES = set(EVALUATOR_GROUPS["Final-Output"]
                   + EVALUATOR_GROUPS["Per-Agent"]
                   + EVALUATOR_GROUPS["Cross-Pipeline"])
# Legacy judge name
_JUDGE_NAMES.add("ReasoningQuality")


def _classify_evaluator(name: str) -> str:
    """Return the group label for an evaluator name."""
    for group, members in EVALUATOR_GROUPS.items():
        if name in members:
            return group
    # Handle agent-suffixed names like JSONValidity_parser
    base = name.split("_")[0] if "_" in name else name
    for group, members in EVALUATOR_GROUPS.items():
        if base in members:
            return group
    return "Other"


def _order_evaluators(evaluator_names: set[str]) -> tuple[list[str], list[tuple[str, int, int]]]:
    """Order evaluators by group and return group boundary info.

    Returns:
        (ordered_evaluators, group_boundaries)
        group_boundaries: list of (group_label, start_idx, end_idx)
    """
    grouped = {}
    for name in evaluator_names:
        group = _classify_evaluator(name)
        grouped.setdefault(group, []).append(name)

    # Sort within each group
    for g in grouped:
        grouped[g].sort()

    # Order: Final-Output, Per-Agent, Cross-Pipeline, Deterministic, Other
    group_order = ["Final-Output", "Per-Agent", "Cross-Pipeline", "Deterministic", "Other"]
    ordered = []
    boundaries = []
    for g in group_order:
        if g in grouped:
            start = len(ordered)
            ordered.extend(grouped[g])
            boundaries.append((g, start, len(ordered) - 1))

    return ordered, boundaries


def _build_matrix(
    test_cases: list[dict],
    evaluators: list[str],
) -> tuple[list[str], list[list[float | None]]]:
    """Build heatmap matrix from test cases using a fixed evaluator order.

    Returns:
        (test_case_ids, score_matrix)
        Test cases sorted by ascending average score (worst first).
    """
    rows = []
    for tc in test_cases:
        tc_id = tc.get("test_case_id", "?")
        scores = tc.get("evaluator_scores", {})
        row_scores = []
        valid_scores = []
        for ev in evaluators:
            val = scores.get(ev)
            if isinstance(val, dict) and "score" in val:
                s = float(val["score"])
                row_scores.append(s)
                valid_scores.append(s)
            else:
                row_scores.append(None)
        avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        rows.append((tc_id, row_scores, avg))

    rows.sort(key=lambda r: r[2])
    tc_ids = [r[0] for r in rows]
    matrix = [r[1] for r in rows]
    return tc_ids, matrix


def _render_heatmap(
    test_cases: list[dict],
    evaluators: list[str],
    boundaries: list[tuple[str, int, int]],
    title: str,
):
    """Render a single heatmap figure."""
    tc_ids, matrix = _build_matrix(test_cases, evaluators)

    if not tc_ids:
        st.info("No test case data available.")
        return

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=evaluators,
        y=tc_ids,
        colorscale=[
            [0.0, "rgb(220, 50, 50)"],
            [0.5, "rgb(240, 220, 60)"],
            [1.0, "rgb(50, 180, 50)"],
        ],
        zmin=0,
        zmax=1,
        hoverongaps=False,
        hovertemplate="Test: %{y}<br>Evaluator: %{x}<br>Score: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Score"),
    ))

    # Add vertical separators between groups
    for i in range(1, len(boundaries)):
        _, start, _ = boundaries[i]
        fig.add_vline(
            x=start - 0.5,
            line_dash="dash",
            line_color="white",
            line_width=2,
        )

    # Add group label annotations above the chart
    for group_label, start, end in boundaries:
        mid = (start + end) / 2
        fig.add_annotation(
            x=mid,
            y=-0.05,
            yref="paper",
            text=group_label,
            showarrow=False,
            font=dict(size=10, color="gray"),
        )

    fig.update_layout(
        title=title,
        xaxis_title="Evaluator",
        yaxis_title="Test Case",
        height=max(400, len(tc_ids) * 22 + 100),
        yaxis=dict(autorange="reversed"),
        margin=dict(b=80),
    )

    st.plotly_chart(fig, use_container_width=True)


def render(run_detail: dict, comparison_detail: dict = None):
    """Render heatmap for a run, with optional side-by-side architecture comparison."""
    st.header("Heatmap")

    # Architecture label
    arch = "unknown"
    if run_detail:
        arch = run_detail.get("architecture", "serial")
        # Try to get from test cases metadata if not at top level
        if arch == "serial" and run_detail.get("test_cases"):
            pass  # default is fine
    st.caption(f"Architecture: {arch}")

    test_cases = run_detail.get("test_cases", []) if run_detail else []
    if not test_cases:
        st.info("No test case data available for this run.")
        return

    # Collect all evaluator names across both runs (for consistent columns)
    all_evaluators = set()
    for tc in test_cases:
        for key in tc.get("evaluator_scores", {}).keys():
            if not key.startswith("_"):
                all_evaluators.add(key)

    comp_cases = []
    comp_arch = None
    if comparison_detail:
        comp_cases = comparison_detail.get("test_cases", [])
        comp_arch = comparison_detail.get("architecture", "serial")
        for tc in comp_cases:
            for key in tc.get("evaluator_scores", {}).keys():
                if not key.startswith("_"):
                    all_evaluators.add(key)

    evaluators, boundaries = _order_evaluators(all_evaluators)

    # Side-by-side mode when comparison has different architecture
    if comp_cases and comp_arch and comp_arch != arch:
        col1, col2 = st.columns(2)
        with col1:
            _render_heatmap(
                test_cases, evaluators, boundaries,
                f"Evaluator Scores — {arch} (worst first)",
            )
        with col2:
            _render_heatmap(
                comp_cases, evaluators, boundaries,
                f"Evaluator Scores — {comp_arch} (worst first)",
            )
    else:
        _render_heatmap(
            test_cases, evaluators, boundaries,
            "Evaluator Scores by Test Case (worst first)",
        )

    st.caption("Select a test case in the Reasoning Explorer page to see full details.")
