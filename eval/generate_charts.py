"""
Static Chart Generator for Eval Reports

Reads score_history.json and individual eval reports to generate
visual dashboards as PNG files. Run after each eval:

    python eval/generate_charts.py

Generates:
1. score_trends.png — Pass rate + per-category accuracy over time
2. heatmap_latest.png — Test case × evaluator score heatmap
3. fuzzy_convergence.png — HITL effectiveness for fuzzy predictions
4. agent_health.png — Per-agent JSON validity + category accuracy

Requires: matplotlib, seaborn, pandas (already in requirements.txt)
"""

import json
import os
import sys
import glob
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for static generation
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import numpy as np

HISTORY_PATH = "eval/score_history.json"
REPORTS_DIR = "eval/reports"
OUTPUT_DIR = "eval/charts"


def load_history():
    """Load score history."""
    if not os.path.exists(HISTORY_PATH):
        print("No score history found. Run an eval first.")
        sys.exit(1)
    with open(HISTORY_PATH) as f:
        return json.load(f)


def load_latest_report():
    """Load the most recent eval report."""
    reports = sorted(glob.glob(os.path.join(REPORTS_DIR, "eval-*.json")))
    if not reports:
        print("No eval reports found.")
        sys.exit(1)
    with open(reports[-1]) as f:
        return json.load(f), reports[-1]


def chart_score_trends(history):
    """Chart 1: Pass rate + per-category accuracy over time."""
    evals = history.get("evaluations", [])
    if len(evals) < 1:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("Eval Score Trends Over Time", fontsize=14, fontweight="bold")

    timestamps = [e.get("timestamp", "")[:16] for e in evals]
    x = range(len(timestamps))

    # Overall pass rate
    pass_rates = [e.get("overall_pass_rate", 0) * 100 for e in evals]
    ax1.plot(x, pass_rates, "o-", color="#2d6a4f", linewidth=2, markersize=8, label="Pass Rate")
    ax1.fill_between(x, pass_rates, alpha=0.1, color="#2d6a4f")
    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_ylim(0, 105)
    ax1.axhline(y=80, color="orange", linestyle="--", alpha=0.5, label="80% threshold")
    ax1.legend(loc="lower right")
    ax1.grid(True, alpha=0.3)

    # Prompt version annotations
    for i, e in enumerate(evals):
        manifest = e.get("prompt_version_manifest", {})
        label = ", ".join(f"{k}:{v}" for k, v in manifest.items() if v != "fallback")
        if not label:
            label = "fallback"
        ax1.annotate(label, (i, pass_rates[i]), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=7, color="gray")

    # Per-category accuracy
    categories = ["auto_verifiable", "automatable", "human_only"]
    colors = {"auto_verifiable": "#1d3557", "automatable": "#457b9d", "human_only": "#e63946"}
    for cat in categories:
        values = [e.get("per_category_accuracy", {}).get(cat, 0) * 100 for e in evals]
        ax2.plot(x, values, "o-", color=colors[cat], linewidth=2, markersize=6, label=cat)

    ax2.set_ylabel("Category Accuracy (%)")
    ax2.set_ylim(0, 105)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(timestamps, rotation=45, ha="right", fontsize=8)
    ax2.set_xlabel("Eval Run")
    ax2.legend(loc="lower right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "score_trends.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("  Generated score_trends.png")


def chart_heatmap(report, report_path):
    """Chart 2: Test case × evaluator score heatmap."""
    test_cases = report.get("per_test_case_scores", [])
    if not test_cases:
        return

    # Build matrix: rows = test cases, columns = evaluator scores
    all_evaluators = set()
    for tc in test_cases:
        all_evaluators.update(tc.get("evaluator_scores", {}).keys())
    evaluators = sorted(all_evaluators)

    data = []
    labels = []
    for tc in test_cases:
        row = []
        tc_id = tc["test_case_id"]
        layer = tc.get("layer", "?")
        labels.append(f"{tc_id} ({layer})")
        for ev in evaluators:
            score_data = tc.get("evaluator_scores", {}).get(ev, {})
            row.append(score_data.get("score", float("nan")))
        data.append(row)

    df = pd.DataFrame(data, index=labels, columns=evaluators)

    fig, ax = plt.subplots(figsize=(max(14, len(evaluators) * 1.5), max(8, len(labels) * 0.4)))
    sns.heatmap(df, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
                linewidths=0.5, ax=ax, cbar_kws={"label": "Score"})
    ax.set_title(f"Eval Heatmap — {os.path.basename(report_path)}", fontsize=12, fontweight="bold")
    ax.set_ylabel("Test Case")
    ax.set_xlabel("Evaluator")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "heatmap_latest.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("  Generated heatmap_latest.png")


def chart_fuzzy_convergence(report):
    """Chart 3: HITL effectiveness — fuzzy prediction convergence."""
    fuzzy_cases = [tc for tc in report.get("per_test_case_scores", []) if tc.get("layer") == "fuzzy"]
    if not fuzzy_cases:
        return

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("HITL Clarification Effectiveness (Fuzzy Predictions)", fontsize=13, fontweight="bold")

    ids = [tc["test_case_id"] for tc in fuzzy_cases]
    x = range(len(ids))

    # Convergence scores
    conv_scores = [tc.get("evaluator_scores", {}).get("Convergence", {}).get("score", 0) for tc in fuzzy_cases]
    colors_conv = ["#2d6a4f" if s >= 0.5 else "#d62828" for s in conv_scores]
    axes[0].bar(x, conv_scores, color=colors_conv)
    axes[0].set_title("Convergence Score")
    axes[0].set_ylim(0, 1.1)
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(ids, rotation=45, ha="right", fontsize=8)
    axes[0].axhline(y=0.5, color="orange", linestyle="--", alpha=0.5)

    # Clarification quality
    cq_scores = [tc.get("evaluator_scores", {}).get("R1_ClarificationQuality", {}).get("score", 0) for tc in fuzzy_cases]
    colors_cq = ["#2d6a4f" if s >= 0.5 else "#d62828" for s in cq_scores]
    axes[1].bar(x, cq_scores, color=colors_cq)
    axes[1].set_title("Clarification Quality (R1)")
    axes[1].set_ylim(0, 1.1)
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(ids, rotation=45, ha="right", fontsize=8)
    axes[1].axhline(y=0.5, color="orange", linestyle="--", alpha=0.5)

    # R2 Category Match (did clarification fix the category?)
    r2_scores = [tc.get("evaluator_scores", {}).get("R2_CategoryMatch", {}).get("score", 0) for tc in fuzzy_cases]
    colors_r2 = ["#2d6a4f" if s >= 0.5 else "#d62828" for s in r2_scores]
    axes[2].bar(x, r2_scores, color=colors_r2)
    axes[2].set_title("Post-Clarification Category Match")
    axes[2].set_ylim(0, 1.1)
    axes[2].set_xticks(list(x))
    axes[2].set_xticklabels(ids, rotation=45, ha="right", fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fuzzy_convergence.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("  Generated fuzzy_convergence.png")


def chart_agent_health(report):
    """Chart 4: Per-agent health — JSON validity + category accuracy."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Agent Health Dashboard", fontsize=13, fontweight="bold")

    # Per-agent JSON validity
    aggregates = report.get("per_agent_aggregates", {})
    agents = list(aggregates.keys())
    jv_scores = [aggregates[a].get("json_validity_avg", 0) * 100 for a in agents]
    colors_jv = ["#2d6a4f" if s >= 90 else "#e9c46a" if s >= 70 else "#d62828" for s in jv_scores]
    ax1.barh(agents, jv_scores, color=colors_jv)
    ax1.set_xlim(0, 105)
    ax1.set_xlabel("JSON Validity (%)")
    ax1.set_title("Per-Agent JSON Validity")
    for i, v in enumerate(jv_scores):
        ax1.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=10)

    # Per-category accuracy
    cat_acc = report.get("per_category_accuracy", {})
    categories = list(cat_acc.keys())
    acc_scores = [cat_acc[c] * 100 for c in categories]
    cat_colors = {"auto_verifiable": "#1d3557", "automatable": "#457b9d", "human_only": "#e63946"}
    colors_cat = [cat_colors.get(c, "#666") for c in categories]
    ax2.barh(categories, acc_scores, color=colors_cat)
    ax2.set_xlim(0, 105)
    ax2.set_xlabel("Accuracy (%)")
    ax2.set_title("Per-Category Accuracy")
    for i, v in enumerate(acc_scores):
        ax2.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "agent_health.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("  Generated agent_health.png")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Generating eval charts...")

    history = load_history()
    report, report_path = load_latest_report()

    chart_score_trends(history)
    chart_heatmap(report, report_path)
    chart_fuzzy_convergence(report)
    chart_agent_health(report)

    print(f"\nAll charts saved to {OUTPUT_DIR}/")
