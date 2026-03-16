"""Quick debug script for the data loader. Run from project root."""
import sys
import os
sys.path.insert(0, os.getcwd())

from eval.dashboard.data_loader import EvalDataLoader

loader = EvalDataLoader()
print(f"DDB available: {loader.is_ddb_available()}")

runs = loader.load_all_runs()
print(f"Runs found: {len(runs)}")
for r in runs:
    rid = r.get("eval_run_id", "?")
    rid_short = rid[:8] if rid else "none"
    print(f"  {r.get('timestamp', '?')} | id={rid_short}... | ds={r.get('dataset_version', '?')} | pass_rate={r.get('overall_pass_rate', '?')}")

if runs:
    first = runs[0]
    print(f"\nLoading detail for first run: id={first.get('eval_run_id', '?')[:8]}... ts={first.get('timestamp', '?')}")
    detail = loader.load_run_detail(first.get("eval_run_id", ""), first.get("timestamp", ""))
    print(f"  test_cases: {len(detail.get('test_cases', []))}")
    if detail.get("test_cases"):
        tc = detail["test_cases"][0]
        print(f"  first test case: {tc.get('test_case_id', '?')} | scores: {list(tc.get('evaluator_scores', {}).keys())[:3]}...")
