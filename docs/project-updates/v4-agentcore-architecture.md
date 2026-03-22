# CalledIt v4: AgentCore Architecture — Clean Rebuild

> Zero technical debt. Built with Bedrock AgentCore, not against it.

---

## Three Architectural Insights Driving v4

### Insight 1: Two Agents, Shared Infrastructure

The prediction creation agent and the verification agent share the same domain (understanding predictions and their verifiability) but have fundamentally different jobs:

1. **Creation Agent** — collaborative, user-facing. Parses natural language, builds a verification plan, scores verifiability, and interacts with the user through clarification rounds to produce the best possible prediction bundle.
2. **Verification Agent** — investigative, autonomous. Runs at `verification_date`, consumes the prediction bundle from DDB, gathers real evidence using tools, and produces a verdict (confirmed/refuted/inconclusive).

They share the same model, the same tools (via AgentCore Gateway), the same DDB prediction bundle as their contract, and the same Prompt Management infrastructure. But they are separate AgentCore Runtime deployments with separate prompts, separate scaling, and separate observability.

This is an intentional architectural decision, not a shortcut. See the "Why Two Agents, Not One" section below for the full rationale.

### Insight 2: Verifiability Strength, Not Categories

The 3-category system (auto_verifiable / automatable / human_only) is the wrong abstraction. What we actually want is a continuous confidence score — like a password strength indicator — that tells the user: "How likely is the future verification agent to confidently determine true/false based on what you've given it?"

- 🟢 Green: High confidence the verification agent will succeed
- 🟡 Yellow: Moderate confidence — clarification would help
- 🔴 Red: Low confidence — prediction is too vague, subjective, or lacks verifiable criteria

The user sees this indicator after round 1 and can choose to do more clarification rounds to push it toward green.

### Insight 3: Three-Layer Eval Architecture

- **Strands Evals SDK** — inner loop (dev-time, local experiments, prompt iteration)
- **Bedrock Evaluations** — outer loop (production, LLM-as-judge at scale, human eval)
- **AgentCore Evaluations** — bridge (span-level analysis on deployed agents, online + on-demand)

---

## v4 Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        FE[React PWA<br/>Mobile-First]
    end

    subgraph "API Layer"
        APIGW[API Gateway<br/>WebSocket + REST]
    end

    subgraph "AgentCore Runtime"
        PA[Prediction Agent<br/>Creation Mode]
        VA[Prediction Agent<br/>Verification Mode]
    end

    subgraph "AgentCore Gateway — MCP Tools"
        BV[brave_web_search]
        FT[fetch]
        PW[playwright]
        FUTURE[Future tools...]
    end

    subgraph "AgentCore Memory"
        STM[Short-Term Memory<br/>Session conversations]
        LTM[Long-Term Memory<br/>User preferences]
    end

    subgraph "Amazon Bedrock"
        PM[Prompt Management<br/>Immutable Versions]
        SO[Claude Sonnet 4<br/>Agent Model]
        BE[Bedrock Evaluations<br/>Production Eval]
    end

    subgraph "Storage — DynamoDB"
        DB[(Predictions +<br/>Verification Bundles)]
    end

    subgraph "Scheduling"
        EB[EventBridge<br/>Verification Scanner]
    end

    subgraph "Observability"
        ACO[AgentCore Observability<br/>Span-Level Tracing]
        ACE[AgentCore Evaluations<br/>Online + On-Demand]
    end

    FE <-->|WebSocket| APIGW
    APIGW --> PA
    EB --> VA
    PA --> BV
    PA --> FT
    VA --> BV
    VA --> FT
    VA --> PW
    PA --> STM
    PA --> LTM
    PA --> PM
    PA --> SO
    VA --> PM
    VA --> SO
    PA --> DB
    VA --> DB
    PA --> ACO
    VA --> ACO
    ACO --> ACE

    style PA fill:#ff9900,color:#000
    style VA fill:#ff9900,color:#000
    style ACO fill:#ff9900,color:#000
    style ACE fill:#ff9900,color:#000
```

---

## Two Agents, Shared Infrastructure

```mermaid
stateDiagram-v2
    [*] --> CreationAgent: User submits prediction

    state CreationAgent {
        Parse --> BuildPlan
        BuildPlan --> ScoreVerifiability
        ScoreVerifiability --> PresentToUser
        PresentToUser --> UserDecides

        state UserDecides <<choice>>
        UserDecides --> Clarify: User wants to improve score
        UserDecides --> LogPrediction: User accepts
        Clarify --> Parse: With clarification context
    end

    LogPrediction --> DynamoDB: Save prediction bundle
    DynamoDB --> Scheduled: verification_date in future
    DynamoDB --> ImmediateVerify: verification_date is now/past

    state VerificationAgent {
        LoadBundle --> ExecutePlan
        ExecutePlan --> GatherEvidence
        GatherEvidence --> ProduceVerdict
    end

    Scheduled --> VerificationAgent: EventBridge triggers at verification_date
    ImmediateVerify --> VerificationAgent: Verify inline

    VerificationAgent --> Result: confirmed / refuted / inconclusive

```

### Why Two Agents, Not One

This was a deliberate architectural decision. Here's the analysis:

**Option A: Single agent with mode flag** — One `agentcore launch`, payload includes `"mode": "creation"` or `"mode": "verification"`.

**Option B: Two separate agents** — Two `agentcore launch` deployments, each with their own entrypoint, prompt, scaling, and observability.

We chose Option B for these reasons:

| Concern | Single Agent (Option A) | Two Agents (Option B) |
|---------|------------------------|----------------------|
| Prompts | One prompt with conditional sections — makes both modes worse | Focused prompts optimized for each job |
| Memory | Creation needs STM + LTM; verification is stateless — awkward to configure both | Each agent gets exactly the memory config it needs |
| Scaling | User-facing traffic and batch verification compete for the same instances | Creation scales with users, verification scales with EventBridge batch size |
| Observability | Traces mix creation and verification spans — harder to analyze | Clean separation in AgentCore Observability |
| Eval | One eval framework trying to measure two different jobs | Each agent has evaluators tuned to its specific job |
| Cold starts | Verification mode pays for creation mode's memory hooks on every cold start | Each agent loads only what it needs |

**AgentCore alignment:** This matches the recommended multi-agent pattern from AgentCore docs — separate runtimes with independent scaling, each with a focused `@app.entrypoint`. The multi-agent CloudFormation template demonstrates exactly this: orchestrator + specialist as separate deployments.

**What they share (via infrastructure, not code coupling):**
- Same model (Claude Sonnet 4 via Bedrock)
- Same tools (brave_web_search, fetch via AgentCore Gateway)
- Same DDB table (prediction bundle is the contract)
- Same Prompt Management stack (separate prompts, same versioning)
- Same eval methodology (different evaluators, same framework)

### Creation Agent vs Verification Agent

```mermaid
graph LR
    subgraph "Shared Infrastructure"
        MODEL[Claude Sonnet 4<br/>via Bedrock]
        GW[AgentCore Gateway<br/>brave_web_search, fetch, playwright]
        DDB[(DynamoDB<br/>Prediction Bundles)]
        PM[Bedrock Prompt Management]
    end

    subgraph "Creation Agent — AgentCore Runtime #1"
        CP[Creation Prompt]
        UI[WebSocket Streaming<br/>User Interaction]
        VS[Verifiability Scorer]
        MEM1[AgentCore Memory<br/>STM + LTM]
        SAVE[Save Bundle]
    end

    subgraph "Verification Agent — AgentCore Runtime #2"
        VP[Verification Prompt]
        LOAD[Load Bundle]
        EXEC[Execute + Gather Evidence]
        VERDICT[Produce Verdict]
    end

    MODEL --> CP
    MODEL --> VP
    GW --> CP
    GW --> VP
    PM --> CP
    PM --> VP
    SAVE --> DDB
    DDB --> LOAD

    style CP fill:#3b82f6,color:#fff
    style VP fill:#8b5cf6,color:#fff
```

### What Gets Saved to DDB (The Prediction Bundle)

The prediction bundle is the contract between creation mode and verification mode. Everything the verification agent needs to do its job must be in this bundle.

```json
{
    "prediction_id": "pred-uuid",
    "user_id": "user-123",
    "raw_prediction": "Lakers win tonight",
    "parsed_claim": {
        "statement": "The Los Angeles Lakers will win their NBA game tonight",
        "verification_date": "2026-03-22T23:00:00Z",
        "date_reasoning": "Tonight refers to this evening, NBA games typically end by 11pm"
    },
    "verification_plan": {
        "sources": ["NBA scores API", "brave_web_search"],
        "criteria": [
            "Lakers final score > opponent final score in tonight's game"
        ],
        "steps": [
            "Search for tonight's Lakers game schedule to confirm they play",
            "After game completion, search for final score",
            "Compare Lakers score to opponent score"
        ]
    },
    "verifiability_score": 0.92,
    "verifiability_reasoning": "Clear factual claim with specific team, specific timeframe, objective win/loss outcome. NBA scores are publicly available via web search.",
    "clarification_rounds": 0,
    "created_at": "2026-03-22T18:30:00Z",
    "status": "pending",
    "prompt_versions": {
        "creation": "3",
        "scorer": "1"
    }
}
```

---

## Verifiability Strength Indicator

Replaces the 3-category system with a continuous score.

```mermaid
graph TD
    PRED[User Prediction] --> AGENT[Prediction Agent<br/>Creation Mode]
    AGENT --> PLAN[Verification Plan<br/>sources, criteria, steps]
    PLAN --> SCORER[Verifiability Scorer]

    SCORER --> SCORE{Score}

    SCORE -->|0.8 - 1.0| GREEN[🟢 Green<br/>High confidence<br/>Clear criteria, known sources,<br/>objective outcome]
    SCORE -->|0.5 - 0.79| YELLOW[🟡 Yellow<br/>Moderate confidence<br/>Some ambiguity, assumptions made,<br/>clarification would help]
    SCORE -->|0.0 - 0.49| RED[🔴 Red<br/>Low confidence<br/>Subjective, vague, no clear<br/>verification path]

    GREEN --> USER{User Choice}
    YELLOW --> USER
    RED --> USER

    USER -->|Accept| LOG[Log Prediction]
    USER -->|Clarify| AGENT

    style GREEN fill:#22c55e,color:#000
    style YELLOW fill:#f59e0b,color:#000
    style RED fill:#ef4444,color:#fff
```

### What the Scorer Evaluates

The scorer is a separate LLM call (lightweight, fast) that evaluates the verification plan against these dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Criteria Specificity | 30% | Are criteria measurable and unambiguous? |
| Source Availability | 25% | Do the planned sources actually exist and are they accessible? |
| Temporal Clarity | 20% | Is the verification date clear and the claim time-bound? |
| Outcome Objectivity | 15% | Is the outcome binary (true/false) or subjective? |
| Tool Coverage | 10% | Do available MCP tools cover the verification needs? |

The scorer returns a float (0.0 - 1.0) plus reasoning explaining each dimension. The frontend maps this to the green/yellow/red indicator.

### Why This Is Better Than Categories

| Old (Categories) | New (Strength Score) |
|---|---|
| Binary routing decision | Continuous quality signal |
| "auto_verifiable" gives false confidence | 0.72 tells you exactly how confident |
| User has no agency | User can choose to improve the score |
| Categorizer errors cascade | Score errors are visible and correctable |
| 3 buckets hide nuance | Score captures the full spectrum |

---

## AgentCore Built-in Tools: Browser + Code Interpreter

Instead of building Gateway infrastructure with external API dependencies, v4 starts with AgentCore's built-in tools. Zero API keys, zero external dependencies, zero Gateway setup.

```mermaid
graph TB
    subgraph "AgentCore Built-in Tools (Day 1)"
        BROWSER[AgentCore Browser<br/>Chromium in Firecracker microVM<br/>Navigate, click, read, screenshot<br/>No API key needed]
        CODE[AgentCore Code Interpreter<br/>Python/JS in secure sandbox<br/>Calculations, data analysis<br/>No API key needed]
    end

    subgraph "Gateway Tools (Phase 2 — When Needed)"
        BRAVE[Brave Web Search<br/>Fast structured search results<br/>Free: 2,000 queries/month]
        ALPHA[Alpha Vantage<br/>Stock prices, financial data<br/>Free: 25 requests/day]
        WEATHER[wttr.in / OpenWeatherMap<br/>Weather data<br/>Free: unlimited / 1,000/day]
        SPORTS[The Odds API<br/>Sports scores and odds<br/>Free: 500 requests/month]
    end

    subgraph "Agents"
        CA[Creation Agent]
        VA[Verification Agent]
    end

    CA --> BROWSER
    CA --> CODE
    VA --> BROWSER
    VA --> CODE

    style BROWSER fill:#ff9900,color:#000
    style CODE fill:#ff9900,color:#000
    style BRAVE fill:#94a3b8,color:#000
    style ALPHA fill:#94a3b8,color:#000
    style WEATHER fill:#94a3b8,color:#000
    style SPORTS fill:#94a3b8,color:#000
```

### Why Built-in Tools First, Gateway Later

| Concern | Gateway + Brave (v3 approach) | Built-in Tools (v4 approach) |
|---------|------------------------------|------------------------------|
| External dependencies | Brave API key, npm packages | None — fully managed by AWS |
| Setup complexity | Gateway creation, OAuth, Lambda targets, IAM roles | `CodeInterpreter('us-west-2')` and `BrowserClient('us-west-2')` |
| Search capability | Brave returns structured snippets — fast | Browser navigates to search engine — slightly slower but works |
| JavaScript-heavy sites | Needs separate playwright tool | Browser handles natively |
| Numerical verification | Not possible | Code Interpreter runs Python calculations |
| URL fetching | Separate fetch tool needed | Browser navigates to URL directly |
| Cost | Brave free tier (2,000/month) | Included in AgentCore pricing |
| Spec complexity | V4-2 needs Gateway + OAuth + targets | V4-2 just wires built-in tools |

### What Each Built-in Tool Enables

**AgentCore Browser** covers:
- Web search (navigate to search engine, read results)
- URL fetching (navigate to any URL, read rendered content)
- JavaScript-heavy sites (full Chromium rendering)
- Form interaction (login, submit data)
- Screenshot evidence (visual proof of verification)

**AgentCore Code Interpreter** covers:
- Numerical verification ("S&P 500 up 5%" → calculate percentage change)
- Date calculations ("3 business days from now" → compute exact date)
- Data analysis (parse structured data, compare values)
- Statistical checks ("temperature above average" → compute average from data)

### When to Add Gateway (Phase 2)

Add Gateway tools when built-in tools become a bottleneck:
- If Browser is too slow for simple search queries → add Brave Search via Gateway
- If financial predictions need real-time data → add Alpha Vantage via Gateway
- If weather predictions need structured forecasts → add OpenWeatherMap via Gateway
- If sports predictions need live scores → add The Odds API via Gateway

Each Gateway addition graduates a class of predictions from "browser search" to "direct API call" — faster and more reliable for that specific domain.

---

## Hybrid Memory Model: AgentCore Memory + DynamoDB

The prediction bundle lives in two places, each serving a different purpose.

```mermaid
graph TB
    subgraph "Creation Agent"
        CA[User says: Lakers win tonight]
        CA --> PROCESS[Parse, plan, score]
        PROCESS --> SAVE_BOTH[Save to both stores]
    end

    subgraph "DynamoDB — Structured Contract"
        DDB[(Prediction Bundle<br/>Exact JSON fields<br/>parsed_claim, verification_plan,<br/>verifiability_score, verification_date)]
    end

    subgraph "AgentCore Memory — Conversational Context"
        STM[Short-Term Memory<br/>Clarification rounds<br/>within this session]
        LTM_SEM[Semantic Strategy<br/>Extracted facts:<br/>'User predicted Lakers win,<br/>verification date tonight 11pm,<br/>needs NBA score check']
        LTM_PREF[User Preference Strategy<br/>Extracted preferences:<br/>'User follows NBA,<br/>prefers Pacific timezone,<br/>usually predicts sports']
        META[Event Metadata<br/>verification_date: 2026-03-22T23:00<br/>prediction_id: pred-uuid<br/>status: pending]
    end

    SAVE_BOTH --> DDB
    SAVE_BOTH --> STM
    STM -->|Auto-extraction| LTM_SEM
    STM -->|Auto-extraction| LTM_PREF

    subgraph "Verification Agent — Triggered at verification_date"
        LOAD_DDB[Load bundle from DDB<br/>Exact fields for execution]
        LOAD_MEM[Query Memory for context<br/>Semantic search: 'Lakers prediction']
        ENRICH[Enriched verification context<br/>Bundle + conversational nuance]
        VERIFY[Execute verification<br/>with tools]
    end

    DDB --> LOAD_DDB
    LTM_SEM --> LOAD_MEM
    LOAD_DDB --> ENRICH
    LOAD_MEM --> ENRICH
    ENRICH --> VERIFY

    style DDB fill:#ff9900,color:#000
    style LTM_SEM fill:#8b5cf6,color:#fff
    style LTM_PREF fill:#8b5cf6,color:#fff
```

### Why Both, Not Just One

| Concern | DynamoDB Only | Memory Only | Hybrid (Our Choice) |
|---------|--------------|-------------|---------------------|
| Structured data precision | ✅ Exact JSON fields | ❌ Semantic approximation | ✅ DDB for precision |
| Conversational context | ❌ Loses clarification nuance | ✅ Full conversation history | ✅ Memory for context |
| User preferences across sessions | ❌ Would need custom code | ✅ LTM auto-extracts | ✅ Memory for preferences |
| Verification agent needs exact criteria | ✅ Loads exact bundle | ❌ Semantic search may miss fields | ✅ DDB for the contract |
| Future predictions benefit from past ones | ❌ No cross-prediction learning | ✅ Semantic search finds patterns | ✅ Memory for learning |
| EventBridge trigger payload | ✅ prediction_id → DDB lookup | ❌ No direct lookup by ID | ✅ DDB for trigger |
| AgentCore pattern alignment | ❌ Custom storage, not AgentCore-native | ✅ Fully AgentCore-native | ✅ Both patterns used correctly |

### How It Works in Practice

**Creation Agent saves to both stores:**

```python
# 1. Save structured bundle to DynamoDB (the contract)
ddb_table.put_item(Item={
    "PK": f"PRED#{prediction_id}",
    "SK": "BUNDLE",
    "parsed_claim": parsed_claim,
    "verification_plan": verification_plan,
    "verifiability_score": verifiability_score,
    "verification_date": verification_date,
    "status": "pending"
})

# 2. Save conversation to AgentCore Memory (the context)
#    This happens automatically via AgentCoreMemorySessionManager
#    The session_manager saves every turn, and LTM strategies
#    auto-extract facts and preferences
```

**Verification Agent loads from both:**

```python
# 1. Load exact bundle from DynamoDB
bundle = ddb_table.get_item(Key={"PK": f"PRED#{prediction_id}", "SK": "BUNDLE"})

# 2. Optionally enrich with Memory context
#    Semantic search for related context the creation agent discussed
memories = memory_client.retrieve_memories(
    memory_id=MEMORY_ID,
    namespace=f"/predictions/{actor_id}/",
    query=bundle["parsed_claim"]["statement"],
    top_k=3
)
# memories might include: "User clarified they meant regular season, not playoffs"
# This nuance isn't in the structured bundle but helps verification
```

### Memory Strategies for CalledIt

```python
# Memory resource with three strategies
memory = memory_client.create_memory_and_wait(
    name="CalledIt_Predictions",
    strategies=[
        # Extract prediction facts for cross-prediction learning
        {"semanticMemoryStrategy": {
            "name": "PredictionFacts",
            "namespaces": ["/predictions/{actorId}/"]
        }},
        # Extract user preferences (timezone, sports teams, etc.)
        {"userPreferenceMemoryStrategy": {
            "name": "UserPreferences",
            "namespaces": ["/preferences/{actorId}/"]
        }},
        # Summarize clarification sessions
        {"summaryMemoryStrategy": {
            "name": "SessionSummaries",
            "namespaces": ["/summaries/{actorId}/{sessionId}/"]
        }}
    ],
    event_expiry_days=90
)
```

### What Each Strategy Enables

**Semantic (PredictionFacts):** When a user makes a new prediction about the Lakers, the creation agent can search Memory for past Lakers predictions — what worked, what didn't, what clarifications were needed. This makes the agent smarter over time without any custom code.

**User Preferences:** After a few predictions, Memory auto-extracts that the user follows NBA, lives in Pacific timezone, prefers specific weather thresholds for "nice weather." Future predictions get better defaults without asking.

**Session Summaries:** When the verification agent runs, it can retrieve a summary of the clarification session — "User initially said 'Lakers win' but clarified they meant regular season game against the Celtics, not the playoff series." This nuance helps verification accuracy.

### Event Metadata for Scheduling

```python
# When saving the prediction event, include metadata for future queries
memory_client.create_event(
    memory_id=MEMORY_ID,
    actor_id=user_id,
    session_id=prediction_session_id,
    messages=[
        (f"User predicted: {raw_prediction}", "USER"),
        (f"Prediction bundle created: {json.dumps(bundle)}", "ASSISTANT")
    ],
    metadata={
        "prediction_id": {"stringValue": prediction_id},
        "verification_date": {"stringValue": verification_date},
        "status": {"stringValue": "pending"},
        "verifiability_score": {"stringValue": str(verifiability_score)}
    }
)
```

This metadata enables future queries like "find all pending predictions for this user" using the `eventMetadata` filter on `list_events`.

---

## Three-Layer Eval Architecture (Dashboard Hero)

This is the centerpiece of the v4 eval story. The dashboard should make the three layers visible, showing how a prompt change flows from dev-time experiment → deployed agent validation → production monitoring.

```mermaid
graph TB
    subgraph "Layer 1: Inner Loop — Strands Evals SDK"
        direction TB
        L1A[Local development<br/>agentcore dev + invoke]
        L1B[Prompt iteration experiments<br/>Golden dataset, 68 test cases]
        L1C[Architecture comparison<br/>Pluggable backends]
        L1D[Evaluators: OutputEvaluator,<br/>TrajectoryEvaluator, Custom]
        L1E[Fast feedback: minutes<br/>Run locally, iterate fast]
    end

    subgraph "Layer 2: Bridge — AgentCore Evaluations"
        direction TB
        L2A[Deployed agent evaluation<br/>agentcore launch + real traffic]
        L2B[Span-level trace analysis<br/>Per-tool, per-step visibility]
        L2C[Online eval: every Nth request<br/>Continuous quality sampling]
        L2D[On-demand eval: triggered runs<br/>Post-deploy validation]
        L2E[Production-like: real latency,<br/>real tool responses]
    end

    subgraph "Layer 3: Outer Loop — Bedrock Evaluations"
        direction TB
        L3A[Production quality monitoring<br/>Aggregate trends over time]
        L3B[LLM-as-judge at scale<br/>Opus 4.6 scoring production samples]
        L3C[Human evaluation<br/>Edge cases, subjective quality]
        L3D[Custom metrics<br/>Verifiability score accuracy]
        L3E[Compliance and safety<br/>Content policy checks]
    end

    L1E -->|"Promote validated<br/>prompts + config"| L2A
    L2E -->|"Escalate anomalies<br/>for deep analysis"| L3A

    style L1A fill:#3b82f6,color:#fff
    style L1B fill:#3b82f6,color:#fff
    style L1C fill:#3b82f6,color:#fff
    style L1D fill:#3b82f6,color:#fff
    style L1E fill:#3b82f6,color:#fff
    style L2A fill:#8b5cf6,color:#fff
    style L2B fill:#8b5cf6,color:#fff
    style L2C fill:#8b5cf6,color:#fff
    style L2D fill:#8b5cf6,color:#fff
    style L2E fill:#8b5cf6,color:#fff
    style L3A fill:#ff9900,color:#000
    style L3B fill:#ff9900,color:#000
    style L3C fill:#ff9900,color:#000
    style L3D fill:#ff9900,color:#000
    style L3E fill:#ff9900,color:#000
```

### The Eval Lifecycle: From Prompt Change to Production Confidence

```mermaid
sequenceDiagram
    participant DEV as Developer
    participant L1 as Layer 1: Strands Evals
    participant PM as Prompt Management
    participant L2 as Layer 2: AgentCore Evals
    participant L3 as Layer 3: Bedrock Evals
    participant DASH as Eval Dashboard

    DEV->>PM: Create new prompt version (e.g., creation v4)
    DEV->>L1: Run local experiment<br/>68 test cases, all evaluators
    L1->>DASH: Layer 1 results:<br/>IP: 0.85, CMA: 0.78, VScore: 0.72
    DEV->>DEV: Compare against baseline<br/>Decide: promote or iterate

    Note over DEV,L1: Inner loop: minutes per iteration

    DEV->>L2: Deploy to AgentCore staging<br/>agentcore launch
    L2->>L2: Online eval: score every 10th request
    L2->>L2: Span-level analysis:<br/>tool call latency, error rates
    L2->>DASH: Layer 2 results:<br/>Real-world latency, tool success rates

    Note over DEV,L2: Bridge: hours of production-like traffic

    L2->>L3: Escalate: 5 predictions scored < 0.5
    L3->>L3: LLM-as-judge deep analysis<br/>on flagged predictions
    L3->>L3: Human eval on 3 edge cases
    L3->>DASH: Layer 3 results:<br/>Root cause analysis, human agreement

    Note over DEV,L3: Outer loop: days of production monitoring

    DASH->>DEV: Dashboard shows full lifecycle:<br/>L1 experiment → L2 deployment → L3 production
```

### Dashboard: Three-Layer Eval View (The Hero Page)

The dashboard's hero page shows the complete eval lifecycle for any prompt version or configuration change. This is what makes the eval framework a portfolio centerpiece.

```mermaid
graph TB
    subgraph "Dashboard: Three-Layer Eval Lifecycle"
        subgraph "Panel 1: Layer 1 — Experiment Results"
            P1A[Prompt Version: creation v4]
            P1B[Golden Dataset: 68 cases]
            P1C[Scores: IP 0.85 / CMA 0.78 / VScore 0.72]
            P1D[vs Baseline: IP +0.04 / CMA +0.03 / VScore +0.05]
            P1E[Status: ✅ Promoted to Layer 2]
        end

        subgraph "Panel 2: Layer 2 — Deployed Agent"
            P2A[Runtime: creation-agent-staging]
            P2B[Online Eval: 142 requests sampled]
            P2C[Avg Latency: 2.3s / Tool Success: 98%]
            P2D[Span Analysis: 3 slow tool calls flagged]
            P2E[Status: ✅ Promoted to Layer 3]
        end

        subgraph "Panel 3: Layer 3 — Production"
            P3A[Production Traffic: 1,247 predictions]
            P3B[LLM Judge: 50 samples scored]
            P3C[Human Eval: 5 edge cases reviewed]
            P3D[Anomalies: 2 predictions flagged]
            P3E[Status: 🟢 Healthy]
        end
    end

    P1E --> P2A
    P2E --> P3A
```

### How Evaluators Map Across Layers

| Evaluator | Layer 1 (Strands Evals) | Layer 2 (AgentCore Evals) | Layer 3 (Bedrock Evals) |
|---|---|---|---|
| IntentPreservation | OutputEvaluator with rubric | Span-level on creation traces | LLM-as-judge on production samples |
| VerifiabilityScore accuracy | Custom evaluator (score vs actual verification outcome) | Online eval every 10th request | Human eval on edge cases |
| Tool usage efficiency | TrajectoryEvaluator (tool sequence, parameters) | Span-level tool call analysis (latency, errors) | — |
| Verification success rate | Custom (plan vs outcome on golden dataset) | On-demand after verification batch runs | Aggregate quality monitoring |
| Clarification quality | OutputEvaluator (are questions specific and useful?) | — | Human eval for subjective quality |
| Plan-execution fidelity | ToolAlignment + SourceAccuracy (deterministic) | Span-level comparison (planned vs actual tools) | — |
| End-to-end prediction quality | Composite score (weighted evaluators) | Online composite on sampled requests | LLM-as-judge + human agreement rate |

### Layer 1 Detail: Strands Evals SDK

This is the existing eval framework, upgraded for v4's two-agent architecture.

**Creation Agent evaluators:**
- IntentPreservation (OutputEvaluator) — does the verification plan preserve the user's intent?
- VerifiabilityScoreAccuracy (Custom) — does the score predict actual verification success?
- ClarificationQuality (OutputEvaluator) — are clarification suggestions specific and useful?
- PlanCompleteness (OutputEvaluator) — does the plan have sufficient sources, criteria, steps?
- ToolSelection (TrajectoryEvaluator) — did the agent reference appropriate tools?

**Verification Agent evaluators:**
- VerificationAccuracy (Custom) — did the agent reach the correct verdict?
- ToolAlignment (Custom deterministic) — planned tools vs actually used tools
- SourceAccuracy (Custom deterministic) — planned sources vs actually consulted sources
- EvidenceQuality (OutputEvaluator) — is the gathered evidence sufficient for the verdict?
- AdaptiveReasoning (OutputEvaluator) — when the plan was insufficient, did the agent adapt?

**Cross-agent evaluators:**
- BundleFidelity (Custom) — does the verification agent successfully consume the creation agent's bundle?
- ScorePredictiveness (Custom) — correlation between verifiability score and verification success

### Layer 2 Detail: AgentCore Evaluations

AgentCore Observability provides span-level tracing on deployed agents. Layer 2 uses this data for:

- **Online evaluation**: Score every Nth request automatically. The scoring uses the same evaluator rubrics from Layer 1, but runs against real production-like traffic instead of golden dataset cases.
- **Span-level analysis**: Per-tool-call latency, error rates, retry patterns. Identifies which tools are bottlenecks.
- **On-demand evaluation**: Triggered after a deployment or prompt change. Runs a curated test suite against the deployed agent.
- **Anomaly detection**: Flag requests where the verifiability score is unusually low or tool calls fail unexpectedly.

### Layer 3 Detail: Bedrock Evaluations

The outer loop for production confidence:

- **LLM-as-judge at scale**: Opus 4.6 scores a sample of production predictions using the same rubrics. This catches quality drift that Layer 2's automated checks might miss.
- **Human evaluation**: For edge cases flagged by Layer 2 or Layer 3's LLM judge. Human evaluators assess whether the prediction bundle would actually enable successful verification.
- **Custom metrics**: Verifiability score accuracy measured against actual verification outcomes over time. This is the empirical grounding for composite score weights (Decision 62).
- **Trend monitoring**: Aggregate quality metrics over days/weeks. Detects gradual degradation that per-request checks miss.

---

## What Carries Forward vs What Gets Rebuilt

### Carries Forward (Proven Value)
- Golden dataset (68 test cases with ground truth metadata)
- Evaluator rubrics (the scoring criteria, not the code)
- Prompt text (from Bedrock Prompt Management, already versioned)
- DynamoDB schema patterns (predictions table, eval reasoning table)
- Frontend (React PWA, WebSocket streaming, clarification UI)
- 85 architectural decisions (institutional knowledge)
- Eval methodology (isolated single-variable testing, composite scoring)

### Gets Rebuilt (Clean Slate on AgentCore)
- Agent code → two separate agents with BedrockAgentCoreApp wrappers (creation + verification)
- MCP tool hosting → AgentCore Gateway (Lambda targets, not subprocess)
- Session state → AgentCore Memory (STM + LTM) on creation agent only
- Categorizer → Verifiability Scorer (continuous score, not categories)
- Verification executor → dedicated verification agent (separate AgentCore Runtime)
- Lambda handler → two AgentCore Runtime entrypoints
- Eval runner → three-layer architecture (Strands + AgentCore + Bedrock)
- Observability → AgentCore Observability (replaces custom OTEL)

### Gets Removed (Technical Debt Eliminated)
- Docker Lambda with Node.js (no more MCP subprocesses)
- MCP Manager module (Gateway handles tool lifecycle)
- 4 separate agent factory modules (two focused agents replace four)
- Strands Graph (no graph needed — creation agent is a single agent, not a pipeline)
- Hardcoded prompt fallback constants (Prompt Management is the source of truth)
- Verification scanner Lambda (EventBridge invokes verification agent directly)
- SnapStart configuration (AgentCore manages cold starts)

---

## AgentCore Entrypoints

### Creation Agent (`creation_agent.py`)

```python
"""
CalledIt v4 — Prediction Creation Agent on AgentCore
Handles user-facing prediction creation with clarification rounds.
"""
import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.hooks import HookProvider, AgentInitializedEvent, MessageAddedEvent

app = BedrockAgentCoreApp()

memory_client = MemoryClient(region_name='us-west-2')
MEMORY_ID = os.getenv('MEMORY_ID')


class CreationMemoryHook(HookProvider):
    """Loads conversation history and user preferences for creation sessions."""

    def on_agent_initialized(self, event):
        if not MEMORY_ID:
            return
        turns = memory_client.get_last_k_turns(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            k=5
        )
        if turns:
            context = "\n".join(
                f"{m['role']}: {m['content']['text']}"
                for t in turns for m in t
            )
            event.agent.system_prompt += f"\n\nPrevious conversation:\n{context}"

    def on_message_added(self, event):
        if not MEMORY_ID:
            return
        msg = event.agent.messages[-1]
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            messages=[(str(msg["content"]), msg["role"])]
        )

    def register_hooks(self, registry):
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)


@app.entrypoint
def invoke(payload, context):
    """
    Creation agent entrypoint.
    
    Payload:
    {
        "prompt": "Lakers win tonight",
        "round": 1,
        "previous_output": null,
        "clarifications": null
    }
    """
    from prompt_client import fetch_prompt

    session_id = getattr(context, 'session_id', 'default')
    system_prompt = fetch_prompt("creation")

    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt,
        hooks=[CreationMemoryHook()] if MEMORY_ID else [],
        state={"session_id": session_id}
        # Tools come from AgentCore Gateway — no local MCP subprocess
    )

    prompt = payload.get("prompt", "")
    round_num = payload.get("round", 1)

    if round_num == 1:
        user_prompt = f"PREDICTION: {prompt}"
    else:
        user_prompt = (
            f"PREDICTION: {prompt}\n\n"
            f"PREVIOUS OUTPUT:\n{payload.get('previous_output')}\n\n"
            f"USER CLARIFICATIONS:\n{payload.get('clarifications')}"
        )

    response = agent(user_prompt)
    return str(response)


if __name__ == "__main__":
    app.run()
```

### Verification Agent (`verification_agent.py`)

```python
"""
CalledIt v4 — Prediction Verification Agent on AgentCore
Runs at verification_date to produce a verdict. No user interaction, no memory.
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """
    Verification agent entrypoint.
    
    Payload:
    {
        "prediction_bundle": {
            "parsed_claim": { "statement": "...", "verification_date": "..." },
            "verification_plan": { "sources": [...], "criteria": [...], "steps": [...] },
            "verifiability_score": 0.92,
            "verifiability_reasoning": "..."
        }
    }
    """
    from prompt_client import fetch_prompt

    system_prompt = fetch_prompt("verification")
    bundle = payload.get("prediction_bundle", {})

    agent = Agent(
        model="us.anthropic.claude-sonnet-4-20250514-v1:0",
        system_prompt=system_prompt,
        callback_handler=None  # No streaming — batch execution
        # Tools come from AgentCore Gateway
    )

    verification_prompt = (
        f"VERIFY THIS PREDICTION:\n"
        f"Claim: {bundle.get('parsed_claim', {}).get('statement', '')}\n"
        f"Verification Plan: {bundle.get('verification_plan', {})}\n"
        f"Verifiability Score: {bundle.get('verifiability_score', 'unknown')}\n"
        f"Verifiability Reasoning: {bundle.get('verifiability_reasoning', '')}\n\n"
        f"Use your tools to gather evidence and determine: confirmed, refuted, or inconclusive.\n"
        f"If the plan is insufficient, adapt — use your own judgment to find evidence."
    )

    response = agent(verification_prompt)
    return str(response)


if __name__ == "__main__":
    app.run()
```

---

## Migration Sequence

```mermaid
graph TD
    S1[Phase 1: AgentCore Foundation] --> S2[Phase 2: Gateway + Tools]
    S2 --> S3[Phase 3: Unified Agent]
    S3 --> S4[Phase 4: Verifiability Scorer]
    S4 --> S5[Phase 5: Memory Integration]
    S5 --> S6[Phase 6: Three-Layer Eval]
    S6 --> S7[Phase 7: Frontend Updates]
    S7 --> S8[Phase 8: Production Cutover]

    S1 ---|"agentcore create, dev server,<br/>basic invoke working"| S1
    S2 ---|"Gateway with brave_web_search,<br/>fetch as Lambda targets"| S2
    S3 ---|"Single agent, creation + verification<br/>modes, DDB bundle contract"| S3
    S4 ---|"Replace categorizer with<br/>continuous score + reasoning"| S4
    S5 ---|"STM for sessions,<br/>LTM for user preferences"| S5
    S6 ---|"Strands Evals + AgentCore Evals<br/>+ Bedrock Evaluations wired"| S6
    S7 ---|"Strength indicator UI,<br/>clarification flow updates"| S7
    S8 ---|"agentcore launch,<br/>EventBridge wiring, DNS cutover"| S8
```

### Phase Details

| Phase | What | Depends On | Validates |
|-------|------|-----------|-----------|
| 1. Foundation | `agentcore create`, dev server, basic invoke | Nothing | AgentCore CLI works, agent responds |
| 2. Gateway + Tools | brave_web_search + fetch as Gateway targets | Phase 1 | Tools accessible via MCP over HTTP |
| 3. Unified Agent | Single agent with creation/verification modes | Phase 2 | Both modes produce correct output |
| 4. Verifiability Scorer | Replace categorizer with continuous score | Phase 3 | Score correlates with verification success |
| 5. Memory | STM for sessions, LTM for preferences | Phase 3 | Conversation persists, preferences extracted |
| 6. Three-Layer Eval | Strands + AgentCore + Bedrock eval wiring | Phase 3 | All three layers produce eval data |
| 7. Frontend | Strength indicator, updated clarification flow | Phase 4 | User sees score, can clarify to improve |
| 8. Production | agentcore launch, EventBridge, DNS | All above | End-to-end production traffic |

---

## Open Questions for Spec Planning

1. Should the verifiability scorer be a separate lightweight LLM call, or a section of the main agent's output that gets extracted?
2. How should the EventBridge scanner invoke the AgentCore agent in verification mode? Direct HTTP invoke? Or a separate "verification scheduler" agent?
3. Should we keep the existing DynamoDB table schema or redesign for the new bundle format?
4. What's the right LTM extraction strategy? User preferences only, or also prediction patterns?
5. How do we handle the transition period where v3 predictions in DDB need to be verifiable by the v4 agent?
