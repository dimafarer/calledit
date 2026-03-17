"""Extract and rank IntentPreservation + CriteriaMethodAlignment scores from latest report."""
import json
import glob
import os

# Find latest report
reports = sorted(glob.glob("backend/calledit-backend/handlers/strands_make_call/eval/reports/eval-*.json"))
latest = reports[-1]
print(f"Analyzing: {os.path.basename(latest)}\n")

with open(latest) as f:
    data = json.load(f)

rows = []
for tc in data["per_test_case_scores"]:
    tc_id = tc["test_case_id"]
    scores = tc.get("evaluator_scores", {})
    ip = scores.get("IntentPreservation", {})
    cma = scores.get("CriteriaMethodAlignment", {})
    ip_score = ip.get("score") if isinstance(ip, dict) else None
    cma_score = cma.get("score") if isinstance(cma, dict) else None
    ip_reason = ip.get("judge_reasoning", "")[:120] if isinstance(ip, dict) else ""
    cma_reason = cma.get("judge_reasoning", "")[:120] if isinstance(cma, dict) else ""

    if ip_score is not None or cma_score is not None:
        rows.append({
            "id": tc_id,
            "ip": ip_score,
            "cma": cma_score,
            "ip_reason": ip_reason,
            "cma_reason": cma_reason,
        })

# Sort by worst combined score
rows.sort(key=lambda r: (r["ip"] or 0) + (r["cma"] or 0))

print(f"{'ID':<12} {'IP':>5} {'CMA':>5}  Intent Reasoning (truncated)")
print("-" * 90)
for r in rows[:15]:
    print(f"{r['id']:<12} {r['ip'] or 'N/A':>5} {r['cma'] or 'N/A':>5}  {r['ip_reason'][:70]}")

print(f"\n--- Bottom 15 by CriteriaMethodAlignment ---")
rows_cma = sorted(rows, key=lambda r: r["cma"] or 0)
print(f"{'ID':<12} {'CMA':>5}  Method Reasoning (truncated)")
print("-" * 90)
for r in rows_cma[:15]:
    print(f"{r['id']:<12} {r['cma'] or 'N/A':>5}  {r['cma_reason'][:70]}")
