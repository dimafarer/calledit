# CalledIt: Building an Agentic Prediction Verification Platform

> A learning journal disguised as a codebase. This project documents the evolution from a simple prediction app to a multi-agent verification system — every architectural decision, wrong turn, and hard-won insight preserved in 19 project updates and 85 decisions.

## What This Project Is

CalledIt is a prediction verification platform. You make a prediction ("Lakers win tonight", "it'll rain tomorrow", "Bitcoin hits $100k by Friday"), and the system:

1. Parses your natural language into a structured claim
2. Categorizes it by verifiability (can a machine check this?)
3. Builds a verification plan (what to check, where, when)
4. Reviews the plan for gaps and asks clarifying questions
5. Executes the verification using real tools (web search, data APIs)
6. Scores how well the plan translated into actual verification

The interesting part isn't the app — it's the agent architecture, the eval framework, and the decisions that got us here.

## The Architecture Journey

This project has gone through three major architectural phases, each teaching different lessons about building agentic systems.

### v1: Monolith Agent (January 2025)
One big agent prompt doing everything — parsing, categorizing, building verification plans. It worked, but you couldn't tell which part was failing when output quality dropped. The agent would sometimes re-interpret the prediction from scratch at each stage, losing context from earlier reasoning.

**Lesson learned:** A single agent doing multiple jobs makes debugging impossible. When the categorization is wrong, is it because the parsing was bad, or because the categorization logic is flawed? You can't tell.

### v2: Multi-Agent Graph (March 2026)
Split into four specialized agents in a Strands Graph: Parser → Categorizer → Verification Builder → Review Agent. Each agent has one job, one prompt, and one output contract. The graph handles sequencing and data flow.

**Key insight:** The silo problem. Each agent re-interprets from scratch instead of building on the previous agent's work. The Parser extracts "nice weather Saturday" → the Categorizer ignores the Parser's date reasoning and re-derives it → the VB ignores both and starts fresh. We built a PipelineCoherence evaluator specifically to measure this.

**Lesson learned:** Multi-agent doesn't automatically mean better. The serial graph and a single-agent baseline scored within 1% of each other on our eval framework. The value of multi-agent is debuggability and isolated iteration, not inherently better output.

### v3: MCP-Powered Verification Pipeline (March 2026, current)
Added real tool execution via Model Context Protocol (MCP). The Verification Builder doesn't just say "check weather.gov" — the Verification Executor actually invokes `brave_web_search` and `fetch` to gather evidence and produce a verdict.

**The container trade-off:** MCP servers are npm packages that need Node.js. Lambda's Python runtime doesn't include Node.js. We switched MakeCallStreamFunction to a Docker Lambda image with both Python 3.12 and Node.js. This killed SnapStart (cold starts went from 444ms back to ~30s) but was necessary for MCP subprocess support.

> **This is a transient architecture.** Docker Lambda with MCP subprocesses is a stepping stone to Amazon Bedrock AgentCore, where tools run as always-warm network services instead of cold-starting inside the Lambda. The 30s cold start validates this migration as the right next step.
>
> **Pre-container checkpoint:** If you want the zip-packaged Lambda version with SnapStart (before MCP tools), see commit [`978c304`](../../commit/978c304) — "feat: wire production Lambda to Bedrock Prompt Management". Everything after that commit introduces Docker Lambda packaging.

## Tech Stack

- **Frontend:** React + TypeScript, mobile-first PWA, WebSocket streaming
- **Backend:** AWS Lambda (Python 3.12, Docker image for MCP), SAM/CloudFormation
- **AI:** Strands Agents SDK, Amazon Bedrock (Claude Sonnet 4), 4-agent graph
- **Tools:** MCP servers (brave_web_search, fetch, playwright) via npx subprocesses
- **Storage:** DynamoDB (predictions, eval reasoning, tool registry)
- **Auth:** Cognito with auto-refresh for mobile UX
- **Eval:** Custom framework with 15 evaluators, Strands Evals SDK, Streamlit dashboard
- **Prompts:** Bedrock Prompt Management with immutable versions

## The Agent Pipeline

Four specialized agents in a Strands Graph, each with a focused prompt and clear output contract:

```
User prediction → Parser → Categorizer → Verification Builder → Review Agent
                    ↓           ↓                ↓                    ↓
              Structured    Route to         Build plan          Identify gaps,
              claim +     auto_verifiable/   (sources,          ask clarifying
              date parse  automatable/       criteria,           questions
                          human_only         steps)
```

After the user logs the prediction, the Verification Executor runs separately:

```
Verification Plan → Verification Executor → brave_web_search, fetch → Verdict
                         (Strands Agent with MCP tools)
```

The executor is triggered by an EventBridge scanner every 15 minutes — it finds predictions whose `verification_date` has passed and verifies them. This decouples verification from prediction creation, which matters because most predictions can't be verified immediately ("nice weather Saturday" can't be checked on Wednesday).

## The Eval Framework (Portfolio Centerpiece)

The eval framework is the most transferable artifact in this project. It's a complete system for measuring multi-agent pipeline quality:

- **Golden dataset:** 45 base + 23 fuzzy predictions with ground truth metadata (verifiability reasoning, date derivation, verification sources, objectivity assessment, verification criteria, verification steps)
- **15 evaluators** across four tiers:
  - 6 deterministic (CategoryMatch, JSONValidity, ClarificationQuality, ToolAlignment, SourceAccuracy, Convergence)
  - 6 LLM-as-judge using Opus 4.6 (IntentPreservation, CriteriaMethodAlignment, IntentExtraction, CategorizationJustification, ClarificationRelevance, PipelineCoherence)
  - 2 verification alignment judges (CriteriaQuality, StepFidelity)
  - 1 delta classifier (plan_error vs new_information vs tool_drift)
- **Pluggable backends:** Serial graph vs single-agent, same evaluators score both
- **8-page Streamlit dashboard:** Trends, Heatmap, Architecture Comparison, Prompt Correlation, Reasoning Explorer, Coherence View, Fuzzy Convergence, Verification Alignment
- **DynamoDB reasoning store:** Full model traces for every eval run
- **Bedrock Prompt Management:** Immutable prompt versions, eval runs record which versions produced which scores
- **Verification alignment:** `--verify` flag runs the actual Verification Executor and measures plan-execution fidelity

### What the Eval Framework Taught Us

1. **Categorization is a routing hint, not the goal.** We spent weeks optimizing category accuracy before realizing the real question is: does the Verification Builder produce a plan that actually works? Category labels just route predictions to the right verification path.

2. **The VB-centric composite score** weights IntentPreservation and CriteriaMethodAlignment highest because they directly measure "can this plan be executed to verify the prediction?" Other evaluators are weighted by how much they contribute to VB output quality.

3. **Isolated single-variable testing** is the only way to iterate on prompts. Change one thing per eval run. When you change two things and the score goes up, you don't know which change helped.

4. **The shared failure profile** was the biggest surprise. Serial graph and single-agent architectures fail on the same predictions. ClarificationRelevance (the Review Agent asking useful questions) is the bottleneck on both. The architecture doesn't matter as much as the prompts.

5. **Verification evaluator scores need empirical grounding** before they can be weighted in the composite. We deliberately excluded the 4 new verification evaluators from the composite score — they'll accumulate data first, then we'll derive weights from correlation with actual verification success.

## Key Decisions and Lessons

85 architectural decisions are documented in `docs/project-updates/decision-log.md`. Here are the ones that shaped the project most:

**On agent architecture:**
- Decision 7: Simple sequential graph, no conditional edges. The pipeline is linear — when VB completes, Parser and Categorizer have already completed by definition. Overengineering the graph topology was a waste.
- Decision 8: Frontend holds session state, Lambda is stateless. The refinement loop (user clarifies → agents refine) lives in the browser. DynamoDB stores only the final prediction. This keeps the backend simple.
- Decision 49: Pluggable backend abstraction. Any architecture (2-agent, 5-agent, single-agent) can be tested through the same eval framework by dropping a module in `backends/`.

**On evaluation:**
- Decision 30: Two-tier evaluator strategy. Deterministic evaluators catch structural regressions fast and cheap. LLM judges catch nuanced quality issues. The 80% → 30% pass rate drop when adding the judge proves the judge adds real signal.
- Decision 44: Verification criteria is the primary eval target, not categorization. This reframe changed everything about how we measure quality.
- Decision 50: Isolated single-variable testing. Every eval iteration changes exactly one variable. This is now standard practice.
- Decision 62: Composite score weights need empirical grounding. The initial weights were a judgment call. After the verification pipeline produces real outcomes, weights will be derived from data.

**On verification:**
- Decision 76: Two-mode verification trigger. Most predictions can't be verified at creation time. The `verification_date` from the parser determines whether to verify immediately or schedule for later.
- Decision 78: No mocks. All tests hit real Bedrock, real MCP servers, real DynamoDB. Mocks hide real bugs. The DynamoDB float→Decimal bug (Decision 82) would never have been caught by mocks.
- Decision 81: Scanner-only in production. The "Log Call" handler is a lightweight REST Lambda — it can't run MCP tools. Rather than adding Lambda-to-Lambda invocation complexity, all production verification goes through the EventBridge scanner.

**On infrastructure:**
- Decision 65: Docker Lambda for MCP subprocess support. A necessary trade-off — lost SnapStart, gained real tool execution.
- Decision 68: AgentCore as post-verification migration target. The Docker Lambda architecture transfers directly to AgentCore's containerized agent model, but with always-warm MCP servers instead of cold-starting subprocesses.

## Project Documentation

This project is extensively documented as a learning journal:

- `docs/project-updates/01-19*.md` — 19 numbered project updates, each a detailed narrative of what happened, what was learned, and what to do next
- `docs/project-updates/decision-log.md` — 85 architectural decisions with rationale
- `docs/project-updates/project-summary.md` — Condensed narrative of the full project arc
- `docs/project-updates/common-commands.md` — Every command you need to run anything
- `docs/project-updates/backlog.md` — Open items and future work
- `.kiro/specs/` — 17 Kiro specs (requirements → design → tasks) covering every feature

Each project update is written for "future self context pickup" — a new agent (or human) can read the latest update and know exactly where things stand and what to do next.

## Running the Eval Framework

```bash
# From the strands_make_call directory
cd backend/calledit-backend/handlers/strands_make_call

# Dry run (no Bedrock calls, check test case count)
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --dry-run

# Deterministic evaluators only (~$3, ~15 min)
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial

# With LLM judges (~$13, ~30 min)
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --judge

# With verification execution (runs real MCP tools on immediate test cases)
source /home/wsluser/projects/calledit/.env
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --verify

# Single test case with verification (fast iteration, ~20-120s)
source /home/wsluser/projects/calledit/.env
PROMPT_VERSION_PARSER=1 PROMPT_VERSION_CATEGORIZER=2 PROMPT_VERSION_VB=3 PROMPT_VERSION_REVIEW=4 \
/home/wsluser/projects/calledit/venv/bin/python eval_runner.py \
    --dataset ../../../../eval/golden_dataset.json --backend serial --verify --name base-002

# Launch the dashboard
/home/wsluser/projects/calledit/venv/bin/python -m streamlit run eval/dashboard/app.py
```

## What's Next

**Amazon Bedrock AgentCore migration.** The current Docker Lambda + MCP subprocess architecture works but has a 30-second cold start. AgentCore manages MCP servers as always-warm network services, eliminating the cold start penalty entirely. The containerized architecture we built for Lambda transfers directly to AgentCore's deployment model.

**Composite score recalibration.** The 4 new verification alignment evaluators are accumulating data. Once we have enough `--verify` runs, we'll derive empirical weights from correlation between evaluator scores and actual verification success rates, replacing the current judgment-call weights.

## Version History

| Version | Date | What Changed |
|---------|------|-------------|
| v0.8 | Jan 2025 | Core prediction system, Cognito auth, DynamoDB |
| v0.9 | Jan 2025 | WebSocket streaming, Strands agent integration |
| v1.0 | Jan 2025 | 5-category verifiability system, automated testing |
| v1.3 | Jan 2025 | "Crying" notification system for verified predictions |
| v1.5 | Aug 2025 | Production deployment, security hardening, VPSS |
| v1.6 | Jan 2026 | 3-agent graph architecture (Parser → Categorizer → VB) |
| v2.0 | Mar 2026 | Unified 4-agent graph with Review Agent, SnapStart, eval framework |
| v3.0 | Mar 2026 | MCP-powered verification pipeline, Docker Lambda, 15 evaluators |

## Repository Structure

```
├── backend/calledit-backend/
│   ├── handlers/
│   │   ├── strands_make_call/       # Main prediction pipeline (Docker Lambda)
│   │   │   ├── prediction_graph.py  # 4-agent Strands Graph
│   │   │   ├── parser_agent.py      # Parser Agent factory
│   │   │   ├── categorizer_agent.py # Categorizer Agent factory
│   │   │   ├── verification_builder_agent.py  # VB Agent factory
│   │   │   ├── review_agent.py      # Review Agent factory
│   │   │   ├── verification_executor_agent.py # Verification Executor (B1)
│   │   │   ├── verification_scanner.py        # EventBridge scanner (B2)
│   │   │   ├── verification_store.py          # DynamoDB storage utility (B2)
│   │   │   ├── mcp_manager.py       # MCP server lifecycle management
│   │   │   ├── eval_runner.py       # Eval framework CLI (--verify, --judge, --backend)
│   │   │   ├── eval_reasoning_store.py # DynamoDB eval data store
│   │   │   ├── golden_dataset.py    # Dataset schema, loader, validation
│   │   │   ├── evaluators/          # 15 evaluator modules
│   │   │   └── backends/            # Pluggable eval backends (serial, single)
│   │   ├── auth_token/              # Cognito token exchange
│   │   ├── list_predictions/        # Prediction retrieval API
│   │   ├── write_to_db/             # DynamoDB write (Log Call)
│   │   └── websocket/               # WebSocket connect/disconnect
│   ├── template.yaml               # SAM template (all AWS resources)
│   └── tests/                       # Integration tests (no mocks)
├── frontend/src/                    # React + TypeScript PWA
├── eval/
│   ├── golden_dataset.json          # 45 base + 23 fuzzy predictions
│   ├── dashboard/                   # 8-page Streamlit dashboard
│   └── reports/                     # Eval run reports (gitignored)
├── infrastructure/
│   └── prompt-management/           # Bedrock Prompt Management CloudFormation
├── docs/project-updates/            # 19 project updates + decision log
└── .kiro/specs/                     # 17 Kiro specs (requirements → design → tasks)
```

## Disclaimers

This is a demonstration/educational project. Not intended for production use. See [DISCLAIMER.md](DISCLAIMER.md) for full details.

## License

See [LICENSE](LICENSE) for details.
