"""Quick comparison of two eval report files."""
import json
import sys

serial_path = "backend/calledit-backend/handlers/strands_make_call/eval/reports/eval-2026-03-18T03-06-13Z.json"
single_path = "backend/calledit-backend/handlers/strands_make_call/eval/reports/eval-2026-03-18T16-01-01Z.json"

serial = json.load(open(serial_path))
single = json.load(open(single_path))

print("=== SERIAL vs SINGLE ===")
print(f"Architecture: {serial.get('architecture')} vs {single.get('architecture')}")
print(f"Pass rate: {serial['overall_pass_rate']:.0%} vs {single['overall_pass_rate']:.0%}")
print(f"VB-centric: {serial.get('vb_centric_score', 'N/A')} vs {single.get('vb_centric_score', 'N/A')}")

vqa_s = serial.get("verification_quality_aggregates", {})
vqa_i = single.get("verification_quality_aggregates", {})
print(f"IP: {vqa_s.get('intent_preservation_avg', 'N/A')} vs {vqa_i.get('intent_preservation_avg', 'N/A')}")
print(f"CMA: {vqa_s.get('criteria_method_alignment_avg', 'N/A')} vs {vqa_i.get('criteria_method_alignment_avg', 'N/A')}")

pca_s = serial.get("per_category_accuracy", {})
pca_i = single.get("per_category_accuracy", {})
for cat in sorted(set(list(pca_s.keys()) + list(pca_i.keys()))):
    sv = pca_s.get(cat, 0)
    iv = pca_i.get(cat, 0)
    print(f"  {cat}: {sv:.0%} vs {iv:.0%}")

print()
print("=== SINGLE BACKEND FAILURE ANALYSIS ===")
fails = {}
for tc in single["per_test_case_scores"]:
    for ev, val in tc.get("evaluator_scores", {}).items():
        if ev.startswith("_"):
            continue
        if isinstance(val, dict) and "score" in val and float(val["score"]) < 0.5:
            fails[ev] = fails.get(ev, 0) + 1

for ev, count in sorted(fails.items(), key=lambda x: -x[1]):
    print(f"  {ev}: {count} failures")
