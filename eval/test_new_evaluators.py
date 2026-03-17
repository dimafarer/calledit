"""POC script to test IntentPreservation and CriteriaMethodAlignment evaluators directly."""
import sys
import os
import json
import traceback

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "calledit-backend", "handlers", "strands_make_call"))

# Test data — base-001: "The sun will rise tomorrow in New York City"
PREDICTION = "The sun will rise tomorrow in New York City"
EXPECTED_CRITERIA = ["The sun appears above the horizon in New York City on the date following the prediction date"]
EXPECTED_METHOD = "Confirm via astronomical calculations based on Earth's rotation and NYC coordinates. Deterministic from orbital mechanics — no external data source needed."

# Simulated VB output (what the agent pipeline would produce)
VB_CRITERIA = ["Sun rises above the horizon in New York City on the specified date"]
VB_METHOD = {
    "source": ["astronomical_calculations"],
    "criteria": ["Sun appears above horizon in NYC"],
    "steps": ["Calculate sunrise time for NYC coordinates", "Confirm sunrise occurs"],
}

print("=== Testing Strands Evals SDK OutputEvaluator ===\n")

# Step 1: Test raw SDK import
print("1. Testing SDK import...")
try:
    from strands_evals.evaluators import OutputEvaluator
    from strands_evals.types import EvaluationData
    print("   OK: OutputEvaluator and EvaluationData imported")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

# Step 2: Test OutputEvaluator instantiation
print("\n2. Testing OutputEvaluator instantiation...")
try:
    evaluator = OutputEvaluator(
        rubric="Score 1.0 if the output matches the expected output semantically. Score 0.0 otherwise.",
        model="us.anthropic.claude-opus-4-6-v1",
        include_inputs=True,
    )
    print(f"   OK: OutputEvaluator created")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test EvaluationData construction
print("\n3. Testing EvaluationData construction...")
try:
    eval_data = EvaluationData(
        input=f"PREDICTION: {PREDICTION}",
        actual_output=json.dumps(VB_CRITERIA),
        expected_output=json.dumps(EXPECTED_CRITERIA),
    )
    print(f"   OK: EvaluationData created")
    print(f"   input: {eval_data.input[:60]}...")
    print(f"   actual_output: {eval_data.actual_output[:60]}...")
    print(f"   expected_output: {eval_data.expected_output[:60]}...")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test evaluate() call
print("\n4. Testing evaluate() call (this calls Bedrock)...")
try:
    results = evaluator.evaluate(eval_data)
    print(f"   OK: evaluate() returned {len(results)} result(s)")
    for i, r in enumerate(results):
        print(f"   Result {i}: score={r.score}, test_pass={r.test_pass}, reason={r.reason[:100]}...")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

# Step 5: Test our wrapper functions
print("\n5. Testing IntentPreservation wrapper...")
try:
    from evaluators.intent_preservation import evaluate_intent_preservation
    result = evaluate_intent_preservation(PREDICTION, VB_CRITERIA, EXPECTED_CRITERIA)
    print(f"   score: {result['score']}")
    print(f"   evaluator: {result['evaluator']}")
    print(f"   judge_reasoning: {result['judge_reasoning'][:150]}...")
    print(f"   judge_model: {result['judge_model']}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("\n6. Testing CriteriaMethodAlignment wrapper...")
try:
    from evaluators.criteria_method_alignment import evaluate_criteria_method_alignment
    result = evaluate_criteria_method_alignment(VB_CRITERIA, VB_METHOD, EXPECTED_METHOD)
    print(f"   score: {result['score']}")
    print(f"   evaluator: {result['evaluator']}")
    print(f"   judge_reasoning: {result['judge_reasoning'][:150]}...")
    print(f"   judge_model: {result['judge_model']}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("\n=== Done ===")
