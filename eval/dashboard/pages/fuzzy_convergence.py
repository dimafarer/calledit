"""Fuzzy Convergence page — round 1 vs round 2 score comparison."""

import plotly.graph_objects as go
import streamlit as st


def _separate_scores(evaluator_scores: dict) -> tuple[dict, dict, dict]:
    """Separate evaluator scores into R1, R2, and clarification quality.

    Returns:
        (r1_scores, r2_scores, clarification_scores)
        Each is {evaluator_name: score_value}
    """
    r1 = {}
    r2 = {}
    clarification = {}

    for key, val in evaluator_scores.items():
        if not isinstance(val, dict) or "score" not in val:
            continue
        score = float(val["score"])

        if key.startswith("R1_"):
            # Strip R1_ prefix for comparison
            base_name = key[3:]
            if "ClarificationQuality" in base_name:
                clarification[key] = score
            else:
                r1[base_name] = score
        elif key.startswith("R2_"):
            r2[key[3:]] = score
        elif key == "Convergence":
            r2["Convergence"] = score
        elif "ClarificationQuality" in key:
            clarification[key] = score
        else:
            # Non-prefixed scores go to R1 for fuzzy cases
            r1[key] = score

    return r1, r2, clarification


def render(run_detail: dict):
    """Render fuzzy prediction convergence analysis."""
    st.header("Fuzzy Convergence")

    test_cases = run_detail.get("test_cases", []) if run_detail else []

    # Filter to fuzzy only
    fuzzy_cases = [tc for tc in test_cases if tc.get("layer") == "fuzzy"]

    if not fuzzy_cases:
        st.info("No fuzzy test cases in this run. Fuzzy predictions are evaluated in two rounds.")
        return

    st.markdown(f"**{len(fuzzy_cases)} fuzzy test cases**")

    # Build comparison data
    rows = []
    for tc in fuzzy_cases:
        tc_id = tc.get("test_case_id", "?")
        r1, r2, clar = _separate_scores(tc.get("evaluator_scores", {}))

        r1_avg = sum(r1.values()) / len(r1) if r1 else None
        r2_avg = sum(r2.values()) / len(r2) if r2 else None
        clar_avg = sum(clar.values()) / len(clar) if clar else None

        rows.append({
            "test_case_id": tc_id,
            "category": tc.get("expected_category", "?"),
            "r1_avg": r1_avg,
            "r2_avg": r2_avg,
            "clarification": clar_avg,
            "convergence": r2.get("Convergence"),
            "improved": (r2_avg or 0) > (r1_avg or 0) if r1_avg is not None and r2_avg is not None else None,
        })

    # Convergence bar chart: R1 vs R2 per test case
    tc_ids = [r["test_case_id"] for r in rows]
    r1_vals = [r["r1_avg"] for r in rows]
    r2_vals = [r["r2_avg"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Round 1",
        x=tc_ids,
        y=r1_vals,
        marker_color="rgb(180, 120, 220)",
    ))
    fig.add_trace(go.Bar(
        name="Round 2",
        x=tc_ids,
        y=r2_vals,
        marker_color="rgb(80, 160, 220)",
    ))
    fig.update_layout(
        title="Round 1 vs Round 2 Average Scores",
        barmode="group",
        xaxis_title="Test Case",
        yaxis_title="Average Score",
        yaxis=dict(range=[0, 1.05]),
    )
    st.plotly_chart(fig, width="stretch")

    # Per-category grouping
    categories = sorted(set(r["category"] for r in rows))
    if len(categories) > 1:
        st.subheader("By Category")
        for cat in categories:
            cat_rows = [r for r in rows if r["category"] == cat]
            improved = sum(1 for r in cat_rows if r.get("improved") is True)
            degraded = sum(1 for r in cat_rows if r.get("improved") is False)
            st.markdown(
                f"**{cat}** — {len(cat_rows)} cases: "
                f"🟢 {improved} improved, 🔴 {degraded} degraded"
            )

    # Detail table
    st.subheader("Detail")
    for r in rows:
        icon = "🟢" if r.get("improved") else "🔴" if r.get("improved") is False else "⚪"
        conv = f", convergence: {r['convergence']:.2f}" if r["convergence"] is not None else ""
        clar = f", clarification: {r['clarification']:.2f}" if r["clarification"] is not None else ""
        st.markdown(
            f"{icon} **{r['test_case_id']}** ({r['category']}) — "
            f"R1: {r['r1_avg']:.2f}, R2: {r['r2_avg']:.2f}"
            f"{conv}{clar}"
            if r["r1_avg"] is not None and r["r2_avg"] is not None
            else f"⚪ **{r['test_case_id']}** — incomplete score data"
        )
