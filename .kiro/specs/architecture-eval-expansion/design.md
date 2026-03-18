# Design Document: Architecture Backend Abstraction + Per-Agent Evaluators

## Overview

This design covers two interconnected systems: (1) a pluggable backend abstraction that lets any architecture produce evaluable output, and (2) four new LLM judge evaluators that complete per-agent coverage so every agent is evaluated against the two system goals.

The design prioritizes the evaluators — they work immediately with the existing serial backend. The backend abstraction enables architecture comparison but depends on the evaluators being in place first.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        eval_runner.py                           │
│  --backend serial|single|swarm|<custom>  --judge                │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │ Backend       │    │ Evaluator Engine                     │   │
│  │ Registry      │    │                                      │   │
│  │               │    │ final_output evaluators (always run): │   │
│  │ backends/     │    │   IntentPreservation (existing)       │   │
│  │  serial.py    │───>│   CriteriaMethodAlignment (existing)  │   │
│  │  single.py    │    │                                      │   │
│  │  swarm.py     │    │ per-agent evaluators (if key exists): │   │
│  │  <custom>.py  │    │   IntentExtraction (parser)           │   │
│  └──────────────┘    │   CategorizationJustification (cat)   │   │
│                      │   ClarificationRelevance (review)     │   │
│         │            │                                      │   │
│         │            │ cross-pipeline (always run):          │   │
│         ▼            │   PipelineCoherence                   │   │
│  ┌──────────────┐    └──────────────────────────────────────┘   │
│  │OutputContract │                    │                          │
│  │              │                    ▼                          │
│  │ final_output │    ┌──────────────────────────────────────┐   │
│  │ agent_outputs│    │ Report + DDB + Dashboard              │   │
│  │ metadata     │    │ Verification-Builder-centric score    │   │
│  └──────────────┘    └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Component 1: Output Contract

The output contract is the interface between backends and evaluators. Every backend must return this shape.

```python
class OutputContract(TypedDict):
    final_output: dict          # Required — the pipeline's end result
    agent_outputs: dict         # Optional — per-agent outputs, keys vary by backend
    metadata: OutputMetadata    # Required — architecture info

class OutputMetadata(TypedDict):
    architecture: str           # Backend name (e.g., "serial", "single", "swarm")
    model_config: dict          # Agent/role → model ID mapping
    execution_time_ms: int      # Wall clock time
    # Backend-specific fields allowed (e.g., collaboration_rounds for swarm)
```

### final_output Required Fields

These are the fields that the primary evaluators (IntentPreservation, CriteriaMethodAlignment) need:

```python
final_output = {
    "prediction_statement": str,       # Extracted claim
    "verifiable_category": str,        # Routing label
    "category_reasoning": str,         # Why this category
    "verification_method": {
        "criteria": list,              # Checkable conditions (PRIMARY eval target)
        "source": list | str,          # Data sources
        "steps": list,                 # Verification steps
    },
    "prediction_date": str,            # When prediction was made
    "verification_date": str,          # When to verify
    "date_reasoning": str,             # How date was derived
    "initial_status": str,             # pending/verified/etc.
    "reviewable_sections": list,       # Review questions (if review agent ran)
}
```

### agent_outputs Examples

```python
# Serial backend (4 agents)
agent_outputs = {
    "parser": {"prediction_statement": ..., "prediction_date": ..., ...},
    "categorizer": {"verifiable_category": ..., "category_reasoning": ..., ...},
    "verification_builder": {"verification_method": ..., ...},
    "review": {"reviewable_sections": [...], ...},
}

# Single-agent backend (1 agent)
agent_outputs = {
    "agent": {<full response with all fields>},
}

# Hypothetical 2-agent backend
agent_outputs = {
    "parser_categorizer": {"prediction_statement": ..., "verifiable_category": ..., ...},
    "vb_review": {"verification_method": ..., "reviewable_sections": ..., ...},
}
```

## Component 2: Backend Registry

Backends live in `backends/` directory under the eval framework. Each is a Python module with two required functions.

### Backend Interface

```python
# backends/serial.py
def run(prediction_text: str, tool_manifest: str) -> OutputContract:
    """Execute the prediction pipeline and return structured output."""
    ...

def metadata() -> dict:
    """Return backend metadata for reports."""
    return {
        "name": "serial",
        "description": "4-agent sequential graph (Parser → Categorizer → Verification Builder → Review)",
        "model_config": {
            "parser": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "categorizer": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "verification_builder": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "review": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        },
    }
```

### Discovery

```python
# In eval_runner.py
import importlib
import os

def discover_backends() -> dict:
    """Discover all backend modules in backends/ directory."""
    backends = {}
    backends_dir = os.path.join(os.path.dirname(__file__), "backends")
    for f in os.listdir(backends_dir):
        if f.endswith(".py") and not f.startswith("_"):
            name = f[:-3]
            mod = importlib.import_module(f"backends.{name}")
            backends[name] = mod
    return backends
```

### Serial Backend (wraps existing code)

```python
# backends/serial.py
from test_prediction_graph import run_test_graph, _parse_pipeline_results, _parse_review_results

def run(prediction_text: str, tool_manifest: str) -> dict:
    result = run_test_graph(prediction_text, tool_manifest=tool_manifest)
    # result is already the flat pipeline output dict
    return {
        "final_output": result,
        "agent_outputs": {
            "parser": {k: result[k] for k in ["prediction_statement", "prediction_date",
                        "local_prediction_date", "date_reasoning"] if k in result},
            "categorizer": {k: result[k] for k in ["verifiable_category",
                            "category_reasoning"] if k in result},
            "verification_builder": {k: result[k] for k in ["verification_method",
                                     "verification_date", "initial_status"] if k in result},
            "review": {k: result[k] for k in ["reviewable_sections"] if k in result},
        },
        "metadata": {
            "architecture": "serial",
            "model_config": metadata()["model_config"],
            "execution_time_ms": 0,  # filled by caller
        },
    }
```

### Single-Agent Backend

```python
# backends/single.py
from strands import Agent

SINGLE_AGENT_PROMPT = """You are a prediction analysis system. Given a user's prediction,
produce a complete structured analysis covering all four steps:

1. PARSING: Extract the factual claim, strip framing language ("I bet", "I think"),
   resolve temporal references to concrete dates.
2. CATEGORIZATION: Classify as auto_verifiable, automatable, or human_only based on
   available tools: {tool_manifest}
3. VERIFICATION BUILDING: Create verification criteria (checkable true/false conditions)
   and a verification method (specific data sources, timing, steps). Operationalize
   vague terms into measurable conditions.
4. REVIEW: Identify what clarification questions would improve the verification plan.
   Target specific assumptions in the verification criteria, not generic questions.

Return ONLY valid JSON with this structure:
{
  "prediction_statement": "extracted factual claim",
  "prediction_date": "YYYY-MM-DD",
  "local_prediction_date": "YYYY-MM-DD",
  "date_reasoning": "how date was derived",
  "verifiable_category": "auto_verifiable|automatable|human_only",
  "category_reasoning": "why this category",
  "verification_method": {
    "source": ["specific data sources"],
    "criteria": ["checkable conditions"],
    "steps": ["ordered verification steps"]
  },
  "verification_date": "YYYY-MM-DD",
  "initial_status": "pending",
  "reviewable_sections": [
    {"section": "section_name", "questions": ["targeted questions"]}
  ]
}"""

def run(prediction_text: str, tool_manifest: str) -> dict:
    agent = Agent(
        model="us.anthropic.claude-opus-4-6-v1",
        system_prompt=SINGLE_AGENT_PROMPT.replace("{tool_manifest}", tool_manifest),
    )
    response = agent(f"Analyze this prediction: {prediction_text}")
    result = json.loads(str(response))
    return {
        "final_output": result,
        "agent_outputs": {"agent": result},
        "metadata": {
            "architecture": "single",
            "model_config": metadata()["model_config"],
            "execution_time_ms": 0,
        },
    }

def metadata() -> dict:
    return {
        "name": "single",
        "description": "Single Opus 4.6 agent, one context, all four steps",
        "model_config": {"agent": "us.anthropic.claude-opus-4-6-v1"},
    }
```

## Component 3: IntentExtraction Evaluator

Scores the Parser's contribution to Goal 1: did it give the Verification Builder clean intent to work with?

```python
# evaluators/intent_extraction.py

INTENT_EXTRACTION_RUBRIC = """
Evaluate whether the Parser correctly extracted the factual claim from the raw prediction,
giving the Verification Builder clean intent to work with.

The Parser's job is to:
- Strip framing language: "I bet", "I think", "I predict" are framing, not intent
- Resolve temporal references: "tomorrow" → concrete date, "next week" → date range
- Preserve the factual claim without distortion or addition

Context: The Parser's output feeds directly into the Categorizer and Verification Builder. If the Parser
loses temporal info or keeps framing language, the Verification Builder builds a plan for the wrong thing.

Scoring:
- 1.0: Factual claim extracted cleanly, framing stripped, temporal refs resolved to dates
- 0.8: Claim extracted correctly but temporal resolution is approximate (e.g., "tomorrow"
       kept as relative instead of resolved to YYYY-MM-DD)
- 0.5: Claim partially extracted — some framing kept or key detail lost
- 0.3: Claim distorted — meaning changed from what user intended
- 0.0: Parser output doesn't represent the user's prediction at all
"""

def evaluate_intent_extraction(
    prediction_text: str,
    parser_output: dict,
    expected_criteria: list,
    judge_model: str = "us.anthropic.claude-opus-4-6-v1",
) -> dict:
    from strands_evals.evaluators import OutputEvaluator
    from strands_evals.types import EvaluationData

    evaluator = OutputEvaluator(
        rubric=INTENT_EXTRACTION_RUBRIC,
        model=judge_model,
        include_inputs=True,
    )

    eval_data = EvaluationData(
        input=f"RAW PREDICTION: {prediction_text}",
        actual_output=json.dumps(parser_output),
        expected_output=json.dumps(expected_criteria),
    )

    results = evaluator.evaluate(eval_data)
    result = results[0] if results else None
    score = max(0.0, min(1.0, float(result.score))) if result else 0.0

    return {
        "score": score,
        "evaluator": "IntentExtraction",
        "judge_reasoning": result.reason if result else "No result",
        "judge_model": judge_model,
    }
```

## Component 4: CategorizationJustification Evaluator

Scores the Categorizer's contribution to Goal 2: did its routing set up the Verification Builder for success?

```python
# evaluators/categorization_justification.py

CATEGORIZATION_JUSTIFICATION_RUBRIC = """
Evaluate whether the Categorizer's routing decision sets up the Verification Builder
to produce the best possible verification plan.

This is NOT about whether the category label matches a ground truth label. It's about
whether the routing decision enables the Verification Builder to build the most automated, actionable
verification plan given the available tools.

Context provided:
- Parser's extracted claim (what the categorizer received as input)
- Categorizer's output (category + reasoning)
- Tool manifest (what tools are available)
- Verification Builder's actual output (to assess downstream impact)

Scoring:
- 1.0: Routing decision clearly enables the Verification Builder to build the best plan. The category
       correctly reflects what's automatable given available tools, and the Verification Builder produced
       a strong plan as a result.
- 0.8: Routing is reasonable but a different category might have led to a slightly
       better Verification Builder plan (e.g., categorized as automatable when auto_verifiable was possible
       with available tools, but Verification Builder still produced a decent plan).
- 0.5: Routing is defensible but the Verification Builder's plan suffers because of it (e.g., categorized
       as human_only when tools could partially automate verification).
- 0.3: Routing actively misled the Verification Builder — the Verification Builder built a plan for the wrong verification
       path because the category was wrong.
- 0.0: Routing is completely wrong and the Verification Builder's plan is useless as a result.
"""

def evaluate_categorization_justification(
    parser_output: dict,
    categorizer_output: dict,
    tool_manifest: str,
    final_output: dict,
    judge_model: str = "us.anthropic.claude-opus-4-6-v1",
) -> dict:
    from strands_evals.evaluators import OutputEvaluator
    from strands_evals.types import EvaluationData

    evaluator = OutputEvaluator(
        rubric=CATEGORIZATION_JUSTIFICATION_RUBRIC,
        model=judge_model,
        include_inputs=True,
    )

    context = json.dumps({
        "parser_claim": parser_output.get("prediction_statement", ""),
        "tool_manifest": tool_manifest,
        "vb_criteria": final_output.get("verification_method", {}).get("criteria", []),
        "vb_method": final_output.get("verification_method", {}),
    })

    eval_data = EvaluationData(
        input=f"CONTEXT: {context}",
        actual_output=json.dumps(categorizer_output),
        expected_output="Routing should enable the best possible verification plan",
    )

    results = evaluator.evaluate(eval_data)
    result = results[0] if results else None
    score = max(0.0, min(1.0, float(result.score))) if result else 0.0

    return {
        "score": score,
        "evaluator": "CategorizationJustification",
        "judge_reasoning": result.reason if result else "No result",
        "judge_model": judge_model,
    }
```

## Component 5: ClarificationRelevance Evaluator

Scores the ReviewAgent's contribution to both goals: do its questions help the Verification Builder improve?

```python
# evaluators/clarification_relevance.py

CLARIFICATION_RELEVANCE_RUBRIC = """
Evaluate whether the ReviewAgent's clarification questions target the Verification
Builder's specific operationalization assumptions, rather than being generic.

The ReviewAgent's job is to catch when the Verification Builder made assumptions that need user validation.
Good questions target specific Verification Builder assumptions. Bad questions are generic ("what location?",
"what time?") that could apply to any prediction.

Context provided:
- The prediction text
- The Verification Builder's verification criteria (with operationalized assumptions)
- The ReviewAgent's clarification questions

Scoring:
- 1.0: Questions directly target specific Verification Builder assumptions. E.g., if Verification Builder operationalized
       "nice weather" as "60-80°F, sunny", the question asks "Do you consider 60°F nice?"
- 0.8: Questions are relevant to the Verification Builder's plan but not laser-focused on specific
       assumptions (e.g., "What weather conditions matter to you?")
- 0.5: Mix of targeted and generic questions
- 0.3: Mostly generic questions that don't reference the Verification Builder's specific plan
- 0.0: Questions are irrelevant or would not improve the verification plan if answered
"""

def evaluate_clarification_relevance(
    prediction_text: str,
    vb_criteria: list,
    review_output: dict,
    judge_model: str = "us.anthropic.claude-opus-4-6-v1",
) -> dict:
    from strands_evals.evaluators import OutputEvaluator
    from strands_evals.types import EvaluationData

    questions = []
    for section in review_output.get("reviewable_sections", []):
        questions.extend(section.get("questions", []))

    evaluator = OutputEvaluator(
        rubric=CLARIFICATION_RELEVANCE_RUBRIC,
        model=judge_model,
        include_inputs=True,
    )

    eval_data = EvaluationData(
        input=f"PREDICTION: {prediction_text}\nVB CRITERIA: {json.dumps(vb_criteria)}",
        actual_output=json.dumps(questions),
        expected_output="Questions should target specific Verification Builder operationalization assumptions",
    )

    results = evaluator.evaluate(eval_data)
    result = results[0] if results else None
    score = max(0.0, min(1.0, float(result.score))) if result else 0.0

    return {
        "score": score,
        "evaluator": "ClarificationRelevance",
        "judge_reasoning": result.reason if result else "No result",
        "judge_model": judge_model,
    }
```

## Component 6: PipelineCoherence Evaluator

Scores cross-agent coherence — does each agent build on the previous agent's work?

```python
# evaluators/pipeline_coherence.py

PIPELINE_COHERENCE_RUBRIC = """
Evaluate whether the agents in this pipeline built on each other's work to produce
a coherent verification plan, or whether they worked in silos re-interpreting the
prediction from scratch.

For multi-agent pipelines: check that each agent's output references or builds on
the previous agent's output. The chain should be:
- Parser extracts claim + resolves dates
- Categorizer uses parser's claim and dates to determine verification path
- Verification Builder uses categorizer's reasoning and parser's dates to build the plan
- ReviewAgent targets gaps in the Verification Builder's specific plan, not the original prediction

For single-agent pipelines: check that the response sections are internally coherent
(dates in parsing section match dates in verification plan, category reasoning aligns
with verification method chosen, etc.)

Scoring:
- 1.0: Clear chain of reasoning — each step builds on the previous. Dates, claims,
       and reasoning flow coherently through the pipeline.
- 0.8: Mostly coherent but one agent slightly re-interprets instead of building on
       predecessor (e.g., Verification Builder uses a slightly different date than parser extracted).
- 0.5: Some agents build on predecessors, others re-interpret from scratch. Mixed.
- 0.3: Agents mostly work in silos — each re-analyzes the original prediction
       independently, leading to inconsistencies.
- 0.0: Agents contradict each other (e.g., parser says date is March 18, Verification Builder says
       verify on March 20 with no explanation for the discrepancy).
"""

def evaluate_pipeline_coherence(
    prediction_text: str,
    agent_outputs: dict,
    final_output: dict,
    judge_model: str = "us.anthropic.claude-opus-4-6-v1",
) -> dict:
    from strands_evals.evaluators import OutputEvaluator
    from strands_evals.types import EvaluationData

    evaluator = OutputEvaluator(
        rubric=PIPELINE_COHERENCE_RUBRIC,
        model=judge_model,
        include_inputs=True,
    )

    eval_data = EvaluationData(
        input=f"PREDICTION: {prediction_text}\nARCHITECTURE AGENTS: {list(agent_outputs.keys())}",
        actual_output=json.dumps({
            "agent_outputs": agent_outputs,
            "final_output": final_output,
        }),
        expected_output="Coherent chain of reasoning from first agent to last",
    )

    results = evaluator.evaluate(eval_data)
    result = results[0] if results else None
    score = max(0.0, min(1.0, float(result.score))) if result else 0.0

    return {
        "score": score,
        "evaluator": "PipelineCoherence",
        "judge_reasoning": result.reason if result else "No result",
        "judge_model": judge_model,
    }
```

## Component 7: Eval Runner Integration

The eval runner changes to support pluggable backends and the new evaluators.

### CLI Changes

```
# Existing
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge --compare

# New
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge --compare --backend serial
python eval_runner.py --dataset ../../../../eval/golden_dataset.json --judge --backend single
python eval_runner.py --list-backends
```

### Evaluator Dispatch Logic

```python
def _evaluate_with_judges(output_contract: dict, bp: BasePrediction, tool_manifest: str) -> dict:
    """Run all applicable LLM judge evaluators based on available agent keys."""
    scores = {}
    final = output_contract["final_output"]
    agents = output_contract.get("agent_outputs", {})
    gt = bp.ground_truth

    # --- Final-output evaluators (always run) ---
    vb_method = final.get("verification_method", {})
    vb_criteria = vb_method.get("criteria", []) if isinstance(vb_method, dict) else []

    if gt.expected_verification_criteria:
        scores["IntentPreservation"] = evaluate_intent_preservation(
            bp.prediction_text, vb_criteria, gt.expected_verification_criteria)
    if gt.expected_verification_method:
        scores["CriteriaMethodAlignment"] = evaluate_criteria_method_alignment(
            vb_criteria, vb_method, gt.expected_verification_method)

    # --- Per-agent evaluators (only if agent key exists) ---
    if "parser" in agents:
        scores["IntentExtraction"] = evaluate_intent_extraction(
            bp.prediction_text, agents["parser"],
            gt.expected_verification_criteria or [])

    if "categorizer" in agents:
        scores["CategorizationJustification"] = evaluate_categorization_justification(
            agents.get("parser", {}), agents["categorizer"],
            tool_manifest, final)

    if "review" in agents:
        scores["ClarificationRelevance"] = evaluate_clarification_relevance(
            bp.prediction_text, vb_criteria, agents["review"])

    # --- Cross-pipeline evaluator (always runs) ---
    scores["PipelineCoherence"] = evaluate_pipeline_coherence(
        bp.prediction_text, agents, final)

    return scores
```

### Verification-Builder-Centric Composite Score

```python
EVALUATOR_WEIGHTS = {
    # Primary — Verification Builder output quality (what the verification agent actually uses)
    "IntentPreservation": 0.25,
    "CriteriaMethodAlignment": 0.25,
    # Secondary — upstream agent contribution to Verification Builder success
    "IntentExtraction": 0.10,
    "CategorizationJustification": 0.10,
    "ClarificationRelevance": 0.10,
    # Cross-pipeline — coherence
    "PipelineCoherence": 0.15,
    # Legacy deterministic (cheap regression catches)
    "CategoryMatch": 0.025,
    "JSONValidity": 0.025,
}

def compute_vb_centric_score(scores: dict) -> float:
    """Weighted composite score centered on Verification Builder output quality."""
    total_weight = 0.0
    weighted_sum = 0.0
    for evaluator, weight in EVALUATOR_WEIGHTS.items():
        if evaluator in scores:
            weighted_sum += scores[evaluator].get("score", 0.0) * weight
            total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0
```

## Component 8: Dashboard Architecture Comparison

### Sidebar Filter

Add an "Architecture" multiselect to the sidebar, populated from `architecture` field across all loaded runs. Default: all architectures selected.

### Trends Page

Filter trend lines by architecture. When multiple architectures are selected, show separate lines per architecture (color-coded). Add architecture label to tooltip.

### Prompt Correlation Page

When comparing two runs with different architectures, show a banner: "Comparing different architectures — score differences may reflect architecture effects, not just prompt changes." Show architecture alongside prompt version diffs in the comparison table.

### Heatmap Page

Add architecture column to the heatmap. When filtering by architecture, only show runs from that architecture.

## Component 9: Report Schema Changes

```python
# Added fields to eval report
report = {
    # ... existing fields ...
    "architecture": "serial",                    # From backend metadata
    "model_config": {"parser": "sonnet-4", ...}, # From backend metadata
    "vb_centric_score": 0.78,                    # Weighted composite
    "evaluator_groups": {
        "final_output": ["IntentPreservation", "CriteriaMethodAlignment"],
        "per_agent": ["IntentExtraction", "CategorizationJustification", "ClarificationRelevance"],
        "cross_pipeline": ["PipelineCoherence"],
        "deterministic": ["CategoryMatch", "JSONValidity", "ClarificationQuality"],
    },
    "skipped_evaluators": {                      # Evaluators not run + reason
        "IntentExtraction": "No 'parser' key in agent_outputs",
    },
}
```

## Correctness Properties

### Property 1: Output Contract Completeness
For any backend, `run()` must return a dict with `final_output` containing at minimum `prediction_statement`, `verifiable_category`, and `verification_method` with `criteria`. If any required field is missing, the eval runner should report a structural failure rather than silently scoring 0.

### Property 2: Evaluator Adaptability
For any set of agent_output keys, the evaluator dispatch should invoke exactly the evaluators whose target agent key is present, plus all "always run" evaluators (IntentPreservation, CriteriaMethodAlignment, PipelineCoherence). No evaluator should crash when its target key is absent.

### Property 3: Backend Discovery Completeness
For any Python module in `backends/` that implements `run()` and `metadata()`, `discover_backends()` should find it and `--list-backends` should display it. Modules missing either function should be skipped with a warning.

### Property 4: Verification-Builder-Centric Score Stability
For any set of evaluator scores, the Verification-Builder-centric composite score should be deterministic (same inputs → same output) and bounded [0.0, 1.0]. Missing evaluators should reduce the weight denominator, not the score.

### Property 5: Architecture Tag Propagation
For any backend, the `architecture` field from `metadata()` must appear in the eval report, score_history entry, and DDB reasoning store record. Dashboard filtering by architecture must match exactly.

### Property 6: Evaluator Result Schema
Every evaluator (new and existing) must return a dict with at minimum: `score` (float 0.0-1.0), `evaluator` (str label). LLM judge evaluators must additionally return `judge_reasoning` (str) and `judge_model` (str).

## File Structure

```
backend/calledit-backend/handlers/strands_make_call/
├── backends/                          # NEW: pluggable backends
│   ├── __init__.py
│   ├── serial.py                      # Wraps existing run_test_graph()
│   ├── single.py                      # Single Opus 4.6 agent
│   └── swarm.py                       # Collaborative multi-round
├── evaluators/
│   ├── __init__.py                    # Existing
│   ├── category_match.py             # Existing (deterministic)
│   ├── clarification_quality.py      # Existing (deterministic)
│   ├── convergence.py                # Existing (deterministic)
│   ├── criteria_method_alignment.py  # Existing (LLM judge)
│   ├── intent_preservation.py        # Existing (LLM judge)
│   ├── json_validity.py              # Existing (deterministic)
│   ├── reasoning_quality.py          # Existing (LLM judge, legacy)
│   ├── intent_extraction.py          # NEW: Parser judge
│   ├── categorization_justification.py  # NEW: Categorizer judge
│   ├── clarification_relevance.py    # NEW: ReviewAgent judge
│   └── pipeline_coherence.py         # NEW: Cross-agent judge
├── eval_runner.py                     # Modified: backend dispatch, new evaluator integration
├── test_prediction_graph.py           # Existing (used by serial backend)
└── ...
```

## Implementation Order

1. Output contract types + backend interface (foundation)
2. Serial backend (wrap existing code, validate contract)
3. Four new evaluators (IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence)
4. Eval runner integration (backend dispatch, evaluator dispatch, Verification-Builder-centric score, report schema)
5. Single-agent backend
6. Swarm backend
7. Dashboard architecture comparison
8. Run comparative eval: serial vs single with all judges
