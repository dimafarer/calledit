# CalledIt: An AWS AI Solutions Architecture Case Study

> From the perspective of a PE AI Solutions Architect advising a portfolio company on building production-grade agentic AI systems with measurable quality guarantees.

---

## The Business Problem

A portfolio company wants to build an AI-powered prediction verification platform. Users make natural language predictions ("Lakers win tonight", "Bitcoin hits $100k by Friday"), and the system must:

1. Understand the user's intent precisely
2. Determine if the prediction can be machine-verified
3. Build an actionable verification plan
4. Execute that plan using real data sources at the right time
5. Prove the system works through measurable evaluation

The PE firm needs confidence that this AI system delivers reliable, measurable value — not just impressive demos.

---

## Architecture Evolution: Three Phases of Maturity

```mermaid
graph LR
    subgraph "v1: Monolith"
        A1[Single Agent<br/>Does Everything]
    end

    subgraph "v2: Multi-Agent Graph"
        B1[Parser] --> B2[Categorizer]
        B2 --> B3[Verification<br/>Builder]
        B3 --> B4[Review<br/>Agent]
    end

    subgraph "v3: MCP-Powered Verification"
        C1[Prediction Pipeline<br/>4 Agents] --> C2[Verification Executor<br/>Real Tools via MCP]
        C2 --> C3[brave_web_search]
        C2 --> C4[fetch]
    end

    A1 -.->|"Debugging impossible<br/>Can't isolate failures"| B1
    B4 -.->|"Plans exist but<br/>never executed"| C1
```

### Why This Matters for PE

Each phase represents a common maturity curve PE portfolio companies go through:

- **v1 → v2**: Moving from prototype to debuggable system. The eval framework proved multi-agent didn't improve output quality — but it made the system observable and each component independently improvable.
- **v2 → v3**: Moving from planning to execution. The system now actually verifies predictions using real tools, not just writes plans about how it would.

---

## AWS Service Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        FE[React PWA<br/>Mobile-First]
    end

    subgraph "API Layer"
        APIGW[API Gateway<br/>WebSocket]
    end

    subgraph "Compute — AWS Lambda"
        WS[WebSocket<br/>Connect/Disconnect]
        MC[MakeCallStream<br/>Docker Lambda<br/>Python + Node.js]
        WR[Write to DB<br/>Log Call]
        LP[List Predictions]
        AT[Auth Token]
        VS[Verification Scanner<br/>EventBridge 15min]
    end

    subgraph "AI Services — Amazon Bedrock"
        PM[Prompt Management<br/>Immutable Versions]
        SO[Claude Sonnet 4<br/>Agent Model]
        OP[Claude Opus 4.6<br/>Judge Model]
    end

    subgraph "Tool Layer — MCP Servers"
        BV[brave_web_search]
        FT[fetch]
    end

    subgraph "Storage — DynamoDB"
        DB[(calledit-db<br/>Predictions)]
        ER[(calledit-eval-reasoning<br/>Eval Traces)]
    end

    subgraph "Auth"
        COG[Amazon Cognito]
    end

    FE <-->|WebSocket| APIGW
    APIGW --> WS
    APIGW --> MC
    FE -->|REST| WR
    FE -->|REST| LP
    FE -->|REST| AT
    MC --> PM
    MC --> SO
    MC --> BV
    MC --> FT
    VS --> MC
    MC --> DB
    MC --> ER
    AT --> COG

    style MC fill:#ff9900,color:#000
    style PM fill:#ff9900,color:#000
    style SO fill:#ff9900,color:#000
    style OP fill:#ff9900,color:#000
```

### Key Architecture Decisions for PE Context

| Decision | Rationale | PE Relevance |
|----------|-----------|--------------|
| Serverless (Lambda + DynamoDB) | Near-zero idle cost, pay-per-use | Portfolio companies need cost efficiency during validation phase |
| Docker Lambda for MCP | Enables real tool execution via Node.js subprocesses | Stepping stone to AgentCore — shows migration planning |
| Bedrock Prompt Management | Immutable prompt versions tied to eval runs | Audit trail — you can prove which prompts produced which results |
| Cognito Auth | Managed auth with mobile auto-refresh | Enterprise-ready auth without custom implementation |

---

## The Agent Pipeline: How Predictions Flow

```mermaid
sequenceDiagram
    participant U as User
    participant P as Parser Agent
    participant C as Categorizer Agent
    participant VB as Verification Builder
    participant R as Review Agent
    participant U2 as User (Clarify)
    participant VE as Verification Executor
    participant T as MCP Tools

    U->>P: "Lakers win tonight"
    P->>C: Structured claim + date parse
    C->>VB: Category: auto_verifiable
    VB->>R: Verification plan (sources, criteria, steps)
    R->>U2: "The plan checks NBA scores. Is this an NBA game?"
    U2->>P: "Yes, NBA regular season"
    Note over P,R: Pipeline re-runs with clarification
    R->>U2: Final plan ready — Log Call

    Note over VE,T: Later, when verification_date arrives
    VE->>T: brave_web_search("NBA Lakers score")
    T->>VE: Score data
    VE->>VE: Compare against criteria
    VE-->>U: Prediction confirmed/refuted
```

### Three Verifiability Categories

```mermaid
graph TD
    PRED[User Prediction] --> CAT{Categorizer}

    CAT -->|"Tools exist NOW"| AV[auto_verifiable<br/>Verify immediately or schedule]
    CAT -->|"Tools could exist"| AM[automatable<br/>Queue for future tool development]
    CAT -->|"Requires human judgment"| HO[human_only<br/>Self-report verification]

    AV --> EXEC[Verification Executor<br/>MCP Tools]
    AM --> QUEUE[Tool Development Queue]
    HO --> SELF[Self-Report Prompt]

    style AV fill:#22c55e,color:#000
    style AM fill:#f59e0b,color:#000
    style HO fill:#ef4444,color:#fff
```

---

## The Eval Framework: Proving AI Quality to Stakeholders

This is the most transferable artifact for PE portfolio companies. It answers the question every PE firm asks: **"How do you know this AI system actually works?"**

```mermaid
graph TB
    subgraph "Golden Dataset — 68 Test Cases"
        GD[45 Base + 23 Fuzzy Predictions<br/>Ground Truth Metadata per Case]
    end

    subgraph "Prediction Pipeline"
        PP[Serial Graph or Single Agent<br/>Pluggable Backend Architecture]
    end

    subgraph "Evaluator Tiers"
        DET[Tier 1: Deterministic<br/>6 evaluators — fast, cheap<br/>JSON validity, category match]
        LLM[Tier 2: LLM-as-Judge<br/>6 evaluators — Opus 4.6<br/>Intent, coherence, relevance]
        VER[Tier 3: Verification Alignment<br/>4 evaluators — plan vs execution<br/>Tool alignment, source accuracy]
    end

    subgraph "Outputs"
        RPT[Eval Report<br/>Per-test scores + aggregates]
        DDB[(DynamoDB<br/>Full reasoning traces)]
        DASH[Streamlit Dashboard<br/>8 pages of visual analysis]
        HIST[Score History<br/>Regression detection]
    end

    GD --> PP
    PP --> DET
    PP --> LLM
    PP --> VER
    DET --> RPT
    LLM --> RPT
    VER --> RPT
    RPT --> DDB
    RPT --> DASH
    RPT --> HIST

    style DET fill:#94a3b8,color:#000
    style LLM fill:#3b82f6,color:#fff
    style VER fill:#8b5cf6,color:#fff
```

### Evaluator Coverage Map

```mermaid
graph LR
    subgraph "Parser Stage"
        E1[IntentExtraction<br/>LLM Judge]
        E2[JSON Validity<br/>Deterministic]
    end

    subgraph "Categorizer Stage"
        E3[CategorizationJustification<br/>LLM Judge]
        E4[CategoryMatch<br/>Deterministic]
    end

    subgraph "Verification Builder Stage"
        E5[IntentPreservation<br/>LLM Judge — 25% weight]
        E6[CriteriaMethodAlignment<br/>LLM Judge — 25% weight]
    end

    subgraph "Review Stage"
        E7[ClarificationRelevance<br/>LLM Judge]
        E8[ClarificationQuality<br/>Deterministic]
    end

    subgraph "Cross-Pipeline"
        E9[PipelineCoherence<br/>LLM Judge]
    end

    subgraph "Verification Alignment"
        E10[ToolAlignment<br/>Deterministic]
        E11[SourceAccuracy<br/>Deterministic]
        E12[CriteriaQuality<br/>LLM Judge]
        E13[StepFidelity<br/>LLM Judge]
    end

    E1 ~~~ E3
    E3 ~~~ E5
    E5 ~~~ E7
    E7 ~~~ E9
    E9 ~~~ E10
```

### The Composite Score: What Actually Predicts Success

```mermaid
pie title "Verification-Builder-Centric Composite Score Weights"
    "IntentPreservation" : 25
    "CriteriaMethodAlignment" : 25
    "PipelineCoherence" : 15
    "IntentExtraction" : 10
    "CategorizationJustification" : 10
    "ClarificationRelevance" : 10
    "CategoryMatch" : 2.5
    "JSONValidity" : 2.5
```

The weights reflect a key insight: **categorization accuracy is a routing hint, not the goal.** The real question is whether the Verification Builder produces a plan that actually works when executed. IntentPreservation and CriteriaMethodAlignment get the highest weight because they directly measure "can this plan be executed to verify the prediction?"

---

## Architecture Comparison: Data-Driven Decisions

```mermaid
graph LR
    subgraph "Same Eval Framework"
        EF[15 Evaluators<br/>68 Test Cases<br/>Same Scoring]
    end

    subgraph "Serial Graph"
        S1[4 Specialized Agents<br/>Each with focused prompt]
    end

    subgraph "Single Agent"
        S2[1 Agent<br/>4 prompt turns in conversation]
    end

    S1 --> EF
    S2 --> EF
    EF --> COMPARE[Architecture Comparison<br/>Dashboard]
```

### Results: Architectures Are Essentially Tied

| Metric | Serial Graph | Single Agent |
|--------|-------------|--------------|
| Pass Rate | 35% | 37% |
| Composite Score | 0.52 | 0.52 |
| Intent Preservation | 0.81 | 0.79 |
| Criteria-Method Alignment | 0.75 | 0.77 |
| auto_verifiable accuracy | 100% | 71% |
| Parser JSON validity | 96% | 94% |

The key finding: **the shared failure profile.** Both architectures fail on the same predictions for the same reasons. ClarificationRelevance (the Review Agent asking useful questions) is the bottleneck on both. The architecture doesn't matter as much as the prompts.

This is exactly the kind of data-driven insight PE firms need — it prevents portfolio companies from spending months on architecture rewrites when the real issue is prompt quality.

---

## Prompt Management: Audit Trail for AI Decisions

```mermaid
graph TB
    subgraph "Bedrock Prompt Management"
        PP1[Parser v1]
        PC1[Categorizer v1] --> PC2[Categorizer v2]
        PV1[VB v1] --> PV2[VB v2] --> PV3[VB v3<br/>Tool-Aware]
        PR1[Review v1] --> PR2[Review v2] --> PR3[Review v3] --> PR4[Review v4<br/>Tool-Aware]
    end

    subgraph "Eval Runs"
        R7[Run 7: VB v1<br/>IP: 0.69]
        R8[Run 8: VB v2<br/>IP: 0.82 ✓]
        R15[Run 15: Review v3<br/>+13% pass rate]
        R17[Run 17: VB v3 + Review v4<br/>Baseline stable]
    end

    PV1 -.-> R7
    PV2 -.-> R8
    PR3 -.-> R15
    PV3 -.-> R17
    PR4 -.-> R17

    style R8 fill:#22c55e,color:#000
    style R15 fill:#22c55e,color:#000
```

Every eval run records which prompt versions produced which scores. This creates an audit trail: you can prove that VB v2 improved IntentPreservation from 0.69 to 0.82, and that Review v3 produced the biggest single-prompt gain in the project (+13% pass rate).

---

## Migration Path: Lambda → AgentCore

```mermaid
graph LR
    subgraph "Current: Docker Lambda"
        DL[Docker Lambda<br/>Python + Node.js]
        MCP1[MCP Servers<br/>Cold start in subprocess<br/>~30s penalty]
    end

    subgraph "Next: Amazon Bedrock AgentCore"
        AC[AgentCore Runtime<br/>Containerized Agent]
        MCP2[MCP Servers<br/>Always-warm network services<br/>~0s penalty]
        OBS[Built-in Observability]
        SCALE[Auto-scaling]
    end

    DL -->|"Container transfers directly"| AC
    MCP1 -->|"Same tools, different hosting"| MCP2

    style AC fill:#ff9900,color:#000
    style MCP2 fill:#22c55e,color:#000
```

The Docker Lambda architecture was deliberately chosen as a stepping stone. The container-based packaging transfers directly to AgentCore's deployment model, but with always-warm MCP servers instead of cold-starting subprocesses. The 30-second cold start on Lambda validates this migration as the right next step.

---

## What This Demonstrates for PE Portfolio Companies

### 1. Systematic AI Quality Measurement
Not "the demo looked good" but "here are 68 test cases, 15 evaluators, and 17 eval runs showing measurable improvement over time." This is how you de-risk AI investments.

### 2. Cost-Efficient Architecture Choices
Serverless-first (near-zero idle cost), with a clear migration path to managed services (AgentCore) as the system matures. Portfolio companies don't need to over-invest in infrastructure during validation.

### 3. Prompt Management as Version Control for AI
Immutable prompt versions tied to eval runs create an audit trail. When a PE firm asks "what changed and why did quality improve?", you can point to specific prompt versions and their measured impact.

### 4. Architecture Decisions Driven by Data, Not Opinions
The pluggable backend system proved that serial graph and single agent architectures are essentially tied — preventing a costly architecture rewrite. The eval framework is the decision-making tool.

### 5. Production Readiness Indicators
- Real tool execution (not mocked)
- EventBridge-triggered verification (decoupled from user interaction)
- DynamoDB reasoning traces (full observability)
- Cognito auth (enterprise-ready)
- All tests hit real services (Decision 78: no mocks)

---

## AWS Services Used (Complete List)

| Service | Purpose | Why This Service |
|---------|---------|-----------------|
| Amazon Bedrock | Foundation model inference (Sonnet 4, Opus 4.6) | Managed, multi-model, prompt management built-in |
| Bedrock Prompt Management | Immutable prompt versions | Audit trail, rollback capability, eval correlation |
| AWS Lambda | Compute (6 functions) | Serverless, pay-per-use, Docker support for MCP |
| Amazon DynamoDB | Predictions, eval reasoning, tool registry | Serverless, pay-per-request, TTL for eval data |
| Amazon API Gateway | WebSocket API | Real-time streaming to mobile client |
| Amazon Cognito | Authentication | Managed auth with mobile token refresh |
| Amazon EventBridge | Verification scheduler (15-min rule) | Serverless cron, decouples verification from prediction |
| AWS CloudFormation/SAM | Infrastructure as Code | Reproducible deployments, prompt stack separation |
| Strands Agents SDK | Agent framework | Open-source, Bedrock-native, graph + tools support |
| Strands Evals SDK | Evaluation framework | OutputEvaluator, TrajectoryEvaluator base classes |
| MCP (Model Context Protocol) | Tool execution | Standard protocol, portable across runtimes |

---

## 85 Architectural Decisions, Documented

Every decision in this project is numbered, sourced to a project update, and includes rationale. Examples relevant to PE advisory:

- **Decision 44**: Verification criteria is the primary eval target, not categorization — reframed the entire measurement strategy
- **Decision 50**: Isolated single-variable testing — change one thing per eval run, know exactly what helped
- **Decision 62**: Composite score weights need empirical grounding — don't optimize against judgment-call metrics
- **Decision 78**: No mocks — all tests hit real services, because mocks hide real bugs
- **Decision 81**: Scanner-only verification in production — simplicity over cleverness

This level of decision documentation is what PE firms should expect from portfolio companies building AI systems. It's the difference between "we built an AI thing" and "we made 85 deliberate architectural choices, each with documented rationale and measured impact."
