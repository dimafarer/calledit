---
inclusion: auto
---

# AgentCore Architecture Standards

## MANDATORY: Build With AgentCore, Not Against It

Every architectural decision in v4 must align with AgentCore's recommended patterns. If we deviate from a recommended pattern, it MUST be a deliberate decision with documented rationale — never accidental.

## Pushback Protocol

When the user requests an architectural decision, the agent MUST:

1. Check if the request aligns with AgentCore recommended patterns
2. If it does NOT align, **flag it immediately** with:
   - What the AgentCore recommended pattern is
   - Why the user's request deviates
   - What the tradeoffs are
   - A recommendation (follow the pattern, or deviate with documented reason)
3. If the user confirms the deviation, document it as a numbered decision in the decision log with the rationale

The agent should NEVER silently implement something that goes against AgentCore patterns.

## Core AgentCore Patterns We Follow

### 1. One Agent = One AgentCore Runtime
Each agent gets its own `agentcore launch` deployment with its own entrypoint, scaling, and observability. Do NOT combine multiple agents into one runtime with mode flags.

**Our implementation:** Two separate runtimes — Creation Agent and Verification Agent.

### 2. BedrockAgentCoreApp Wrapper
Every agent entrypoint uses `BedrockAgentCoreApp` with `@app.entrypoint` decorator and `app.run()`. This is non-negotiable.

### 3. Tools via AgentCore Built-in Tools (Day 1) + Gateway (Phase 2)
Day 1 tools are AgentCore Browser (web search, URL fetching, JS rendering) and Code Interpreter (calculations, data analysis). No external API keys, no Gateway setup. Gateway with domain-specific APIs (Brave, Alpha Vantage, weather, sports) is Phase 2 — add only when built-in tools become a bottleneck. Do NOT use local MCP subprocesses, npm packages, or embedded tool code.

### 4. Memory via AgentCore Memory + DynamoDB (Hybrid Model)
Conversational context and user preferences use AgentCore Memory (STM for conversation turns, LTM for extracted facts/preferences/summaries). Structured prediction bundles use DynamoDB (the exact contract between creation and verification agents). This is intentional — Memory is for fuzzy conversational recall, DDB is for precise structured data. Do NOT put the prediction bundle in Memory alone (semantic approximation loses field precision). Do NOT put conversation context in DDB alone (loses the auto-extraction and semantic search capabilities).

### 5. Observability via AgentCore Observability
Tracing and monitoring use AgentCore's built-in observability. Do NOT build custom OTEL instrumentation. The existing OTEL code from v3 gets removed.

### 6. Prompt Management via Bedrock Prompt Management
All prompt text lives in Bedrock Prompt Management with immutable versions. Do NOT hardcode prompts in agent code. No fallback constants — if Prompt Management is unavailable, the agent should fail clearly, not silently use stale text.

**Deviation from v3:** v3 had hardcoded fallback constants (Decision 61). v4 removes these. If Prompt Management is down, the agent fails with a clear error. This is intentional — silent fallback to stale prompts is worse than a visible failure.

## Documented Deviations

### Deviation 1: Two Agents Instead of One
**AgentCore pattern:** Single agent per use case is simpler.
**Our deviation:** Two separate agents (creation + verification) for the same prediction domain.
**Rationale:** Different prompts, different memory needs (creation needs STM+LTM, verification is primarily DDB-driven with optional Memory enrichment), different scaling profiles (user-facing vs batch), different observability needs. Documented in v4 architecture doc "Why Two Agents, Not One" section.

### Deviation 2: EventBridge → AgentCore Runtime Invocation
**AgentCore pattern:** Agents are invoked by users or other agents (A2A).
**Our deviation:** Verification agent is invoked by EventBridge on a schedule, not by a user or another agent.
**Rationale:** Verification must happen at `verification_date`, which is often days/weeks after prediction creation. No user is present. EventBridge → `InvokeAgentRuntime` API is the cleanest way to trigger batch verification. This is a valid use of the AgentCore Runtime API — it's just not the typical interactive pattern.

### Deviation 3: Hybrid Memory + DynamoDB Storage
**AgentCore pattern:** Use AgentCore Memory for all agent state persistence.
**Our deviation:** Prediction bundles stored in DynamoDB, conversational context in AgentCore Memory.
**Rationale:** The prediction bundle is a structured contract with exact fields (parsed_claim, verification_plan, verifiability_score) that the verification agent must consume precisely. Semantic memory retrieval returns approximate matches — fine for conversational context, not for structured data contracts. DDB provides exact lookup by prediction_id. Memory provides semantic search for enrichment context. Both used for their strengths.

## Three-Layer Eval Architecture

### Layer 1: Strands Evals SDK (Inner Loop)
- Local development, prompt iteration, architecture comparison
- Golden dataset with evaluators
- Fast feedback: minutes per iteration
- Runs via `agentcore dev` + `agentcore invoke --dev`

### Layer 2: AgentCore Evaluations (Bridge)
- Deployed agent evaluation with span-level analysis
- Online eval (every Nth request) + on-demand eval (triggered runs)
- Production-like traffic patterns
- Runs on `agentcore launch` deployed agents

### Layer 3: Bedrock Evaluations (Outer Loop)
- Production quality monitoring at scale
- LLM-as-judge on production samples
- Human evaluation for edge cases
- Trend monitoring over days/weeks

### Dashboard Requirement
The eval dashboard MUST show all three layers for any prompt version or configuration change. This is the hero page — it tells the story of how a change flows from experiment → deployment → production confidence.

## Anti-Patterns to Avoid

- ❌ Local MCP subprocesses (use Gateway)
- ❌ Hardcoded prompt fallbacks (use Prompt Management, fail clearly)
- ❌ Custom OTEL instrumentation (use AgentCore Observability)
- ❌ In-memory session state (use AgentCore Memory)
- ❌ Single runtime with mode flags (separate runtimes per agent)
- ❌ Docker Lambda packaging (AgentCore handles containers)
- ❌ SAM template for agent compute (AgentCore Runtime replaces Lambda for agents)
- ❌ Silent degradation (fail visibly when a dependency is unavailable)
