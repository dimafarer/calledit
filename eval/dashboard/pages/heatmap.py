"""Heatmap page — per-test-case evaluator score matrix ordered by agent pipeline."""

import plotly.graph_objects as go
import streamlit as st

# Pipeline-ordered evaluator groups: left to right follows the agent pipeline
# Within each agent group, both LLM judges and deterministic evaluators are mixed
PIPELINE_GROUPS = [
    ("Parser", [
        "IntentExtraction",          # LLM judge
        "JSONValidity_parser",       # deterministic
        "R1_JSONValidity_parser",    # deterministic (round 1)
    ]),
    ("Categorizer", [
        "CategorizationJustification",       # LLM judge
        "CategoryMatch",                     # deterministic
        "ReasoningQuality_categorizer",      # LLM judge
        "R2_CategoryMatch",                  # deterministic (round 2)
        "R2_ReasoningQuality_categorizer",   # LLM judge (round 2)
    ]),
    ("Verification Builder", [
        "IntentPreservation",                        # LLM judge
        "CriteriaMethodAlignment",                   # LLM judge
        "JSONValidity_vb",                           # deterministic
        "ReasoningQuality_verification_builder",     # LLM judge
        "R2_ReasoningQuality_verification_builder",  # LLM judge (round 2)
    ]),
    ("Review", [
        "ClarificationRelevance",        # LLM judge
        "ClarificationQuality",          # deterministic
        "R1_ClarificationQuality",       # deterministic (round 1)
        "ReasoningQuality_review",       # LLM judge
    ]),
    ("Cross-Pipeline", [
        "PipelineCoherence",    # LLM judge
        "Convergence",          # deterministic
    ]),
]

# LLM judge evaluator names — used for label coloring
LLM_JUDGES = {
    "IntentExtraction", "CategorizationJustification",
    "IntentPreservation", "CriteriaMethodAlignment",
    "ClarificationRelevance", "PipelineCoherence",
    "ReasoningQuality_categorizer", "ReasoningQuality_verification_builder",
    "ReasoningQuality_review",
    "R2_ReasoningQuality_categorizer", "R2_ReasoningQuality_verification_builder",
    "ReasoningQuality",  # legacy
}

# Evaluator descriptions — shown on hover
EVALUATOR_DESCRIPTIONS = {
    "IntentExtraction": "Did the parser extract the factual claim and resolve temporal refs? (10% weight — LLM judge)",
    "JSONValidity_parser": "Is the parser output valid JSON? (2.5% weight — deterministic)",
    "R1_JSONValidity_parser": "Round 1: Is the parser output valid JSON? (deterministic)",
    "CategorizationJustification": "Does the routing decision set up the best verification plan? (10% weight — LLM judge)",
    "CategoryMatch": "Did the categorizer pick the expected label? (2.5% weight — deterministic)",
    "ReasoningQuality_categorizer": "Is the categorizer's reasoning sound? (LLM judge)",
    "R2_CategoryMatch": "Round 2: Correct category after clarification? (deterministic)",
    "R2_ReasoningQuality_categorizer": "Round 2: Categorizer reasoning quality (LLM judge)",
    "IntentPreservation": "Does the verification plan capture the user's intent? (25% weight — LLM judge)",
    "CriteriaMethodAlignment": "Does the method enable proving true/false? (25% weight — LLM judge)",
    "JSONValidity_vb": "Is the Verification Builder output valid JSON? (deterministic)",
    "ReasoningQuality_verification_builder": "Is the Verification Builder's reasoning sound? (LLM judge)",
    "R2_ReasoningQuality_verification_builder": "Round 2: Verification Builder reasoning quality (LLM judge)",
    "ClarificationRelevance": "Do review questions target specific assumptions? (10% weight — LLM judge)",
    "ClarificationQuality": "Do review questions contain expected keywords? (deterministic)",
    "R1_ClarificationQuality": "Round 1: Review question keyword check (deterministic)",
    "ReasoningQuality_review": "Is the ReviewAgent's reasoning sound? (LLM judge)",
    "PipelineCoherence": "Do agents build on each other's work? (15% weight — LLM judge)",
    "Convergence": "Does round 2 converge toward the base prediction? (deterministic)",
}


def _is_judge(name: str) -> bool:
    """Check if an evaluator is an LLM judge."""
    if name in LLM_JUDGES:
        return True
    base = name.split("_")[0] if "_" in name else name
    return base in LLM_JUDGES


def _order_evaluators(evaluator_names: set[str]) -> tuple[list[str], list[tuple[str, int, int]]]:
    """Order evaluators by pipeline stage, return group boundaries.

    Evaluators not in the known pipeline groups go into an "Other" group at the end.
    """
    # Build the known set for detecting unknowns
    known = set()
    for _, members in PIPELINE_GROUPS:
        known.update(members)

    ordered = []
    boundaries = []

    for group_label, members in PIPELINE_GROUPS:
        # Only include members that actually appear in the data
        present = [m for m in members if m in evaluator_names]
        if present:
            start = len(ordered)
            ordered.extend(present)
            boundaries.append((group_label, start, len(ordered) - 1))

    # Collect unknowns
    unknowns = sorted(evaluator_names - known)
    if unknowns:
        start = len(ordered)
        ordered.extend(unknowns)
        boundaries.append(("Other", start, len(ordered) - 1))

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


def _color_coded_labels(evaluators: list[str]) -> list[str]:
    """Return evaluator labels with color coding via HTML.

    LLM judges get blue labels, deterministic get gray.
    Plotly supports basic HTML in tick labels.
    """
    labels = []
    for ev in evaluators:
        if _is_judge(ev):
            labels.append(f"<span style='color:#1f77b4'>{ev}</span>")
        else:
            labels.append(f"<span style='color:#7f7f7f'>{ev}</span>")
    return labels


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

    colored_labels = _color_coded_labels(evaluators)

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=colored_labels,
        y=tc_ids,
        colorscale=[
            [0.0, "rgb(220, 50, 50)"],
            [0.5, "rgb(240, 220, 60)"],
            [1.0, "rgb(50, 180, 50)"],
        ],
        zmin=0,
        zmax=1,
        hoverongaps=False,
        customdata=[
            [f"{ev} — {EVALUATOR_DESCRIPTIONS.get(ev, '')}" if ev in EVALUATOR_DESCRIPTIONS else ev for ev in evaluators]
            for _ in tc_ids
        ],
        hovertemplate="Test: %{y}<br>%{customdata}<br>Score: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Score"),
    ))

    # Add vertical separators between pipeline groups
    for i in range(1, len(boundaries)):
        _, start, _ = boundaries[i]
        fig.add_vline(
            x=start - 0.5,
            line_dash="dash",
            line_color="white",
            line_width=2,
        )

    # Add pipeline group labels above the chart
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

    # Legend for label colors
    st.markdown(
        "<span style='color:#1f77b4'>■</span> LLM Judge &nbsp;&nbsp; "
        "<span style='color:#7f7f7f'>■</span> Deterministic",
        unsafe_allow_html=True,
    )

    st.plotly_chart(fig, width="stretch")


def render(run_detail: dict, comparison_detail: dict = None):
    """Render heatmap for a run, with optional side-by-side architecture comparison."""
    st.header("Heatmap")

    # Architecture label
    arch = run_detail.get("architecture", "serial") if run_detail else "unknown"
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
