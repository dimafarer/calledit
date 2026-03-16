# Eval Framework Comparison: CalledIt Custom vs Strands Evals SDK

**Purpose:** Learning reference for understanding how to instrument and analyze agent-based projects, and how Strands Evals SDK maps to what we built by hand.

---

## 1. Side-by-Side: What We Built vs What Strands Evals Provides

### Test Case Definition

**CalledIt (custom):**
Golden dataset is a JSON file (`eval/golden_dataset.json`) with hand-crafted test cases. Each has `test_case_id`, `layer` (base/fuzzy), `difficulty`, `expected_category`, `raw_prediction`, and optional fields like `clarification_answer`, `expected_outputs`, `personal_context_notes`.

```python
# golden_dataset.json entry
{
  "test_case_id": "base-001",
  "layer": "base",
  "difficulty": "easy",
  "raw_prediction": "The Lakers will beat the Celtics tonight",
  "expected_category": "auto_verifiable"
}
```

**Strands Evals SDK:**
Uses `Case` objects with typed input/output, expected output, expected trajectory, and metadata.

```python
from strands_evals import Case

case = Case[str, str](
    name="base-001",
    input="The Lakers will beat the Celtics tonight",
    expected_output="auto_verifiable",  # or a full expected dict
    metadata={"layer": "base", "difficulty": "easy", "category": "auto_verifiable"}
)
```

**Impact on CalledIt:** Our golden dataset has richer structure (fuzzy variants, clarification answers, personal context notes) than a basic `Case`. We'd either flatten into metadata or extend `Case` with custom fields. The dataset itself doesn't need to change — just the loader that feeds it to the experiment.

---

### Deterministic Evaluators

**CalledIt (custom):**
Hand-written evaluator classes: `CategoryMatch` (exact match on category), `JSONValidity` (per-agent JSON parse check), `ClarificationQuality` (keyword matching), `Convergence` (R1 vs R2 score comparison). Each returns `{"score": float, "evaluator": str, ...}`.

```python
# evaluators/category_match.py
class CategoryMatch:
    def evaluate(self, test_case, agent_output):
        actual = agent_output.get("verifiable_category", "")
        expected = test_case.get("expected_category", "")
        return {"score": 1.0 if actual == expected else 0.0, ...}
```

**Strands Evals SDK:**
Custom evaluators by subclassing `Evaluator`. Returns `EvaluationOutput(score, test_pass, reason, label)`.

```python
from strands_evals.evaluators import Evaluator
from strands_evals.types import EvaluationData, EvaluationOutput

class CategoryMatch(Evaluator[str, str]):
    def evaluate(self, data: EvaluationData[str, str]) -> EvaluationOutput:
        actual = data.actual_output.get("verifiable_category", "")
        expected = data.expected_output
        return EvaluationOutput(
            score=1.0 if actual == expected else 0.0,
            test_pass=actual == expected,
            reason=f"Expected {expected}, got {actual}",
            label="category_match"
        )
```

**Impact on CalledIt:** Nearly 1:1 mapping. Our evaluators would become `Evaluator` subclasses. The structured `EvaluationOutput` is cleaner than our ad-hoc dicts. Migration is straightforward.

---

### LLM-as-Judge

**CalledIt (custom):**
Hand-rolled judge that calls Opus 4.6 with a custom prompt per agent. We build the prompt, parse the JSON response, extract score + reasoning, write to DDB. ~100 lines of custom code in `eval_runner.py`.

```python
# Simplified from eval_runner.py
judge_prompt = f"Score this {agent_name} output on a 0-1 scale..."
response = judge_agent(judge_prompt)
score = parse_json(response)["score"]
reasoning_store.write_judge_reasoning(test_case_id, agent_name, score, reasoning, "opus-4.6")
```

**Strands Evals SDK:**
`OutputEvaluator` with a rubric string. The SDK handles the judge call, response parsing, and structured output. You define WHAT to evaluate, not HOW to call the model.

```python
from strands_evals.evaluators import OutputEvaluator

judge = OutputEvaluator(
    rubric="""
    Evaluate the categorizer's reasoning:
    1. Did it correctly identify the verification path?
    2. Did it consider all aspects of the prediction?
    3. Is the category assignment justified?
    Score 1.0 if excellent, 0.5 if partial, 0.0 if wrong.
    """,
    model="us.anthropic.claude-opus-4-0-20250514-v1:0",
    include_inputs=True
)
```

**Impact on CalledIt:** This is the biggest win. Our hand-rolled judge code (~100 lines) becomes a rubric string + evaluator instantiation. The SDK handles model invocation, response parsing, retry logic. We lose some control over the exact prompt format but gain reliability and less code to maintain. Our per-agent rubrics (parser reasoning, categorizer reasoning, VB plan quality, review relevance) each become an `OutputEvaluator` instance.

---

### Trajectory / Tool Usage Evaluation

**CalledIt (custom):**
We don't have this. The "silo problem" (agents not building on each other's output) is identified but not measured. The Coherence View page is a manual approximation — comparing deterministic vs judge agreement, not actual tool/data flow.

**Strands Evals SDK:**
`TrajectoryEvaluator` with built-in scoring tools (`exact_match_scorer`, `in_order_match_scorer`, `any_order_match_scorer`). Plus `tools_use_extractor` to capture what tools were called and in what order.

```python
from strands_evals.evaluators import TrajectoryEvaluator

trajectory_eval = TrajectoryEvaluator(
    rubric="""
    The agent pipeline should follow: parser → categorizer → vb → review.
    Each agent should reference the previous agent's output.
    Score 1.0 if all agents build on predecessors.
    Score 0.5 if some agents re-interpret from scratch.
    Score 0.0 if agents work in complete silos.
    """,
    include_inputs=True
)
```

**Impact on CalledIt:** This directly addresses the silo problem from Insight 2 in the project update. We could define expected trajectories for our 4-agent pipeline and measure whether each agent actually uses the previous agent's output. This is net-new capability we don't have today.

---

### Experiment Management

**CalledIt (custom):**
- `eval_runner.py` orchestrates everything
- `score_history.json` tracks run summaries
- `eval/reports/eval-*.json` stores per-run detail
- `EvalReasoningStore` writes to DDB
- Manual `--compare` flag for regression detection

**Strands Evals SDK:**
- `Experiment` class manages cases + evaluators
- `experiment.run_evaluations(task_fn)` runs everything
- `experiment.to_file("name")` saves to JSON
- `report.run_display()` prints results
- `report.get_summary()` returns pass_rate, average_score

```python
from strands_evals import Experiment

experiment = Experiment[str, str](
    cases=test_cases,
    evaluators=[category_match, json_validity, judge]
)
reports = experiment.run_evaluations(run_pipeline)
reports[0].run_display()
experiment.to_file("run_2026-03-15_cat_v2")
```

**Impact on CalledIt:** The SDK's experiment management is simpler but less feature-rich than ours. We have DDB persistence, prompt version manifests, architecture tags, dataset versioning, and a visual dashboard. The SDK gives you JSON serialization and console display. For CalledIt specifically, our infrastructure is more valuable. For a new project, the SDK gets you 80% of the way with zero custom code.

---

### Test Case Generation

**CalledIt (custom):**
Hand-crafted golden dataset. 45 base + 23 fuzzy predictions, each with ground truth. Took significant effort to design and validate.

**Strands Evals SDK:**
`ExperimentGenerator` auto-generates test cases from a context description.

```python
from strands_evals.generators import ExperimentGenerator

generator = ExperimentGenerator[str, str](str, str)
experiment = await generator.from_context_async(
    context="4-agent prediction pipeline: parser extracts intent, categorizer assigns verification path...",
    num_cases=20,
    evaluator=OutputEvaluator,
    task_description="Evaluate prediction processing quality",
    num_topics=3
)
```

**Impact on CalledIt:** Interesting for bootstrapping, but our golden dataset is carefully designed with specific edge cases (the "I bet the sun rises tomorrow" intent extraction, the personal-data-vs-private-data categorization boundary). Auto-generated cases wouldn't catch these. Useful for expanding coverage after the core dataset is solid.

---

## 2. What We Have That Strands Evals Doesn't

| Capability | CalledIt Custom | Strands Evals SDK |
|---|---|---|
| DDB reasoning store with TTL | Yes — full agent outputs, judge reasoning, token counts persisted | No — results are in-memory or JSON files |
| Prompt version manifests | Yes — every run records which prompt versions were used | No — no concept of prompt versioning |
| Architecture comparison | Yes — serial/swarm/single tags per run | No — assumes single execution path |
| Dataset versioning | Yes — tracks which dataset version produced each run | No — cases are defined inline |
| Fuzzy prediction rounds | Yes — R1/R2 scoring with clarification simulation | No — single-pass evaluation only |
| Visual dashboard | Yes — 6-page Streamlit dashboard with DDB integration | No — console output and JSON files |
| Regression detection | Yes — automatic comparison with previous run | No — manual comparison |
| Score clamping / malformed data handling | Yes — defensive data loading | No — assumes clean data |

## 3. What Strands Evals Has That We Don't

| Capability | Strands Evals SDK | CalledIt Custom |
|---|---|---|
| Trajectory evaluation | Yes — tool sequence analysis with built-in scorers | No — identified as gap (silo problem) |
| Helpfulness evaluator | Yes — 7-level scoring from user perspective | No — our judge focuses on reasoning quality |
| Faithfulness evaluator | Yes — checks if responses are grounded in context | No |
| Goal success rate evaluator | Yes — did the agent achieve the user's goal? | No — we measure category accuracy, not goal completion |
| Tool parameter accuracy evaluator | Yes — were tool inputs correct? | No |
| Async evaluation | Yes — concurrent test case execution | No — sequential execution |
| Experiment serialization | Yes — save/load experiments as JSON | Partial — we save reports but not the experiment definition |
| Auto test case generation | Yes — from context descriptions | No — hand-crafted only |
| Structured `EvaluationOutput` type | Yes — score, test_pass, reason, label | Partial — ad-hoc dicts |

## 4. How Each Approach Serves CalledIt's Two Goals

### Goal 1: Understand the full intent of the user's raw prediction

**Custom approach:** CategoryMatch evaluator checks if the categorizer got the right verification path. JSONValidity checks structural correctness. The judge evaluates reasoning quality. But none of these directly measure "did the system understand the user's intent?"

**Strands Evals approach:** An `OutputEvaluator` with a rubric specifically about intent preservation would be more targeted:

```python
intent_evaluator = OutputEvaluator(
    rubric="""
    Does the parser's output preserve the user's original intent?
    - "I bet the sun rises tomorrow" → intent is "the sun will rise tomorrow" (not the betting framing)
    - "My flight lands at 3pm" → intent is a specific arrival time prediction
    Score 1.0 if intent is fully preserved and correctly extracted.
    Score 0.5 if intent is partially preserved but some nuance is lost.
    Score 0.0 if intent is misunderstood or lost.
    """
)
```

**Verdict:** The SDK's rubric-based approach makes it easier to write evaluators that directly target intent preservation rather than proxy metrics like category accuracy.

### Goal 2: Repackage with 100% intent preservation in a structure that enables verification

**Custom approach:** The VB output is checked for JSON validity and judge-scored for reasoning quality. But we don't measure whether the verification plan would actually work at the right time.

**Strands Evals approach:** `TrajectoryEvaluator` could verify the pipeline produced a coherent chain: parser extracted X → categorizer used X to determine Y → VB used Y to build plan Z. Plus an `OutputEvaluator` rubric targeting temporal awareness in verification plans.

**Verdict:** Trajectory evaluation is the missing piece for Goal 2. It would directly measure the silo problem.

---

## 5. Recommended Approach for Future Projects

### For a new agent project from scratch:

1. Start with `strands-agents-evals` from day one
2. Define `Case` objects for your test suite
3. Use `OutputEvaluator` for quality assessment — write rubrics, not judge code
4. Use `TrajectoryEvaluator` if your agent uses tools or has multi-step workflows
5. Use `ExperimentGenerator` to bootstrap initial test cases, then curate
6. Add custom `Evaluator` subclasses for domain-specific checks (like our CategoryMatch)
7. Layer on DDB persistence / dashboards only when the SDK's JSON serialization isn't enough

### For CalledIt specifically (hybrid approach):

**Phase 1 — Keep what works:**
- Golden dataset stays (richer than SDK cases)
- DDB reasoning store stays (SDK doesn't persist)
- Dashboard stays (SDK has no visualization)
- Score history + regression detection stays

**Phase 2 — Replace the judge:**
- Swap hand-rolled judge code for `OutputEvaluator` instances
- One per agent with a targeted rubric
- Reduces ~100 lines of judge code to ~4 rubric strings
- Gets structured `EvaluationOutput` for free

**Phase 3 — Add trajectory evaluation:**
- Wrap the 4-agent pipeline execution to capture tool/data flow
- Use `TrajectoryEvaluator` to measure inter-agent coherence
- This directly addresses the silo problem
- Expected trajectory: parser output feeds categorizer, categorizer output feeds VB, etc.

**Phase 4 — Unified experiment runner:**
- Wrap our golden dataset entries as `Case` objects
- Run through `Experiment` for the SDK's orchestration
- Post-process results into our DDB store and dashboard format
- Best of both worlds: SDK evaluation + custom persistence/visualization

---

## 6. Key Takeaway

The Strands Evals SDK is not a replacement for what we built — it's a foundation layer. We built the persistence, versioning, visualization, and domain-specific evaluation logic that the SDK doesn't provide. But the SDK provides cleaner abstractions for the evaluation primitives (judge calls, trajectory analysis, experiment management) that we implemented by hand.

The ideal is a layered architecture:

```
┌─────────────────────────────────────┐
│  Dashboard (Streamlit + DDB)        │  ← CalledIt custom
├─────────────────────────────────────┤
│  Persistence (DDB, score_history)   │  ← CalledIt custom
├─────────────────────────────────────┤
│  Domain Logic (golden dataset,      │  ← CalledIt custom
│  prompt versioning, architecture)   │
├─────────────────────────────────────┤
│  Evaluation Primitives              │  ← Strands Evals SDK
│  (OutputEvaluator, Trajectory,      │
│   Experiment, Case, generators)     │
├─────────────────────────────────────┤
│  Agent Runtime (Strands Agents)     │  ← Strands SDK
└─────────────────────────────────────┘
```

For future projects: start at the bottom two layers (Strands Agents + Strands Evals), add domain logic as needed, and only build custom persistence/visualization when the project demands it.
