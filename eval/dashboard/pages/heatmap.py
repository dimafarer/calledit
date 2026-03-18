"""Heatmap page — per-test-case evaluator score matrix."""

import plotly.graph_objects as go
import streamlit as st


def _is_judge_evaluator(name: str) -> bool:
    """Check if an evaluator is an LLM judge (vs deterministic)."""
    judge_names = {
        "ReasoningQuality", "IntentPreservation", "CriteriaMethodAlignment",
        "IntentExtraction", "CategorizationJustification",
        "ClarificationRelevance", "PipelineCoherence",
    }
    # Handle agent-suffixed names like ReasoningQuality_categorizer
    base_name = name.split("_")[0] if "_" in name else name
    return base_name in judge_names or name in judge_names


def _build_matrix(test_cases: list[dict]) -> tuple[list[str], list[str], list[list[float | None]]]:
    """Build heatmap matrix from test cases.

    Returns:
        (test_case_ids, evaluator_names, score_matrix)
        Evaluators sorted: deterministic first, then judge, separated.
        Test cases sorted by ascending average score (worst first).
    """
    # Collect all evaluator names (exclude internal keys)
    all_evaluators = set()
    for tc in test_cases:
        for key in tc.get("evaluator_scores", {}).keys():
            if not key.startswith("_"):
                all_evaluators.add(key)

    # Split into deterministic and judge
    det = sorted(e for e in all_evaluators if not _is_judge_evaluator(e))
    judge = sorted(e for e in all_evaluators if _is_judge_evaluator(e))
    evaluators = det + judge

    # Build rows with average score for sorting
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

    # Sort by ascending average (worst first)
    rows.sort(key=lambda r: r[2])

    tc_ids = [r[0] for r in rows]
    matrix = [r[1] for r in rows]

    return tc_ids, evaluators, matrix


def render(run_detail: dict):
    """Render heatmap for a single run's test cases."""
    st.header("Heatmap")

    test_cases = run_detail.get("test_cases", []) if run_detail else []
    if not test_cases:
        st.info("No test case data available for this run.")
        return

    tc_ids, evaluators, matrix = _build_matrix(test_cases)

    # Find separator position between deterministic and judge
    det_count = sum(1 for e in evaluators if not _is_judge_evaluator(e))

    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=evaluators,
        y=tc_ids,
        colorscale=[
            [0.0, "rgb(220, 50, 50)"],    # red
            [0.5, "rgb(240, 220, 60)"],    # yellow
            [1.0, "rgb(50, 180, 50)"],     # green
        ],
        zmin=0,
        zmax=1,
        hoverongaps=False,
        hovertemplate="Test: %{y}<br>Evaluator: %{x}<br>Score: %{z:.2f}<extra></extra>",
        colorbar=dict(title="Score"),
    ))

    # Add vertical line separator between deterministic and judge columns
    if 0 < det_count < len(evaluators):
        fig.add_vline(
            x=det_count - 0.5,
            line_dash="dash",
            line_color="white",
            line_width=2,
        )

    fig.update_layout(
        title="Evaluator Scores by Test Case (worst first)",
        xaxis_title="Evaluator",
        yaxis_title="Test Case",
        height=max(400, len(tc_ids) * 22 + 100),
        yaxis=dict(autorange="reversed"),  # worst at top
    )

    st.plotly_chart(fig, use_container_width=True)

    # Click-to-drill hint
    st.caption("Select a test case in the Reasoning Explorer page to see full details.")
