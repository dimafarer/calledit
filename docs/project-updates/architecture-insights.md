# Architecture Insights

Captures what each backend architecture is good at, what it struggles with, and what prompt/config changes each one needs. Updated as comparative eval data comes in.

---

## Serial Graph (4 agents: Parser → Categorizer → Verification Builder → Review)

### Strengths
- Clean JSON output — each agent has a focused prompt that produces well-structured JSON (parser JSON validity ~100%)
- Category routing accuracy — auto_verifiable consistently 100%
- Stable, predictable behavior — same prompts produce consistent results across runs

### Weaknesses
- The silo problem — agents tend to re-interpret from scratch rather than building on the previous agent's output (Decision 52, PipelineCoherence evaluator built to quantify this)
- CriteriaMethodAlignment at 0.73 — the Verification Builder doesn't always produce methods that match its own criteria, possibly because it doesn't see the full reasoning chain from earlier agents
- Information loss between agents — the graph passes text between nodes, but context/nuance can be lost in the handoff

### Prompt Needs
- Each agent's prompt should explicitly reference what the previous agent produced and instruct "build on this, don't redo it"
- The Verification Builder prompt needs the parser's extracted intent AND the categorizer's routing reasoning as explicit context, not just the final output text
- Consider passing structured data (not just text) between agents so downstream agents can reference specific fields

### Key Metrics (Run 15 — serial with review v3, all 6 judges)
- Pass rate: 38% | IP: 0.81 | CMA: 0.74 | Verification-Builder-centric: 0.53
- auto_v: 100% | auto_m: 71% | human: 94%

---

## Single Agent (1 agent, 4 prompt-managed conversation turns)

### Strengths
- Better verification method quality — CMA 0.77 vs serial's 0.73 (+0.04)
- Natural context propagation — one conversation means no information loss between "agents"
- Intent preservation identical to serial (IP: 0.80) — the single agent understands intent just as well
- No silo problem by design — the agent sees all its own previous reasoning

### Weaknesses
- JSON formatting discipline — parser JSON validity 90% vs serial's ~100%. The single agent sometimes wraps JSON in markdown fences, adds commentary, or produces slightly malformed output
- Category routing less precise — auto_verifiable dropped from 100% to 71%. The single agent doesn't route as cleanly when handling all four tasks
- Overall pass rate much lower (16% vs 29%) — driven by structural/formatting failures, not reasoning quality
- Slower execution — one long conversation vs parallel-ish agent calls
- ClarificationRelevance is the biggest failure source — 23/68 predictions fail. The single agent produces generic review questions instead of targeting the Verification Builder's specific operationalization assumptions. This is the single biggest score drag.
- ReasoningQuality on categorizer reasoning — 11 failures. The categorizer step reasoning is weaker when done as one turn in a conversation vs a dedicated agent.

### Prompt Needs
- Strongest impact: tighten the review/clarification turn instructions — "questions must target specific assumptions the Verification Builder made when operationalizing vague terms, not generic clarifications"
- JSON output discipline: "Return ONLY raw JSON, no markdown fences, no commentary"
- Category routing instructions need to be as precise as the dedicated categorizer's prompt
- Consider a JSON repair step after each turn rather than relying on the model

### Key Metrics (Run 16 — single with review v3, all 6 judges)
- Pass rate: 37% | IP: 0.79 | CMA: 0.77 | Verification-Builder-centric: 0.52
- auto_v: 71% | auto_m: 93% | human: 88%

---

## Swarm (not yet implemented)

Backlog item 2. Expected to test collaborative multi-round processing. The PipelineCoherence evaluator will be especially interesting here — swarm agents share context differently than serial or single.

---

## Cross-Architecture Observations

### The Reasoning vs Formatting Tradeoff
The single agent reasons slightly better (CMA 0.77 vs 0.75, IP 0.80 vs 0.78) but the gap is smaller than initially thought. The Verification-Builder-centric composite score is essentially identical (0.50 vs 0.50). The real difference is in structural discipline — serial has 100% auto_verifiable accuracy vs single's 71%.

### The Clarification Quality Gap — BOTH Architectures
ClarificationRelevance is the biggest failure source on BOTH architectures — 25 failures on serial, 23 on single. This is not an architecture problem. It's a Review prompt problem. The ReviewAgent produces generic questions regardless of whether it's a dedicated agent (serial) or a conversation turn (single). This is the single highest-impact prompt fix available.

### Shared Failure Profile
The failure profiles are remarkably similar across architectures:

| Evaluator | Serial Failures | Single Failures | Architecture-Specific? |
|---|---|---|---|
| ClarificationRelevance | 25 | 23 | No — Review prompt issue |
| R1_ClarificationQuality | 16 | 18 | No — same root cause |
| ReasoningQuality_review | 12 | 9 | No — Review prompt issue |
| ReasoningQuality_categorizer | 8 | 11 | Slight — single worse |
| CategoryMatch | 5 | 10 | Yes — single worse at routing |
| IntentExtraction | 3 | 7 | Yes — single worse at parsing |
| JSONValidity_parser | 3 | 6 | Yes — single worse at JSON |
| CriteriaMethodAlignment | 3 | 4 | No — similar |
| PipelineCoherence | 2 | 2 | No — identical |
| IntentPreservation | 2 | 3 | No — similar |

### Key Takeaway: Fix the Review Prompt First
ClarificationRelevance + R1_ClarificationQuality + ReasoningQuality_review account for 53 failures on serial and 50 on single. These are all Review prompt issues. Fixing the Review prompt would have the largest impact on BOTH architectures simultaneously. This is architecture-agnostic low-hanging fruit.

### Implication for Prompt Strategy (Updated)
- Priority 1: Fix the Review prompt — biggest impact, helps both architectures
- Priority 2 (single only): Tighten JSON output discipline and category routing
- Priority 3 (serial only): Improve coherence (agents building on predecessors)
- The silo problem (PipelineCoherence) is minimal on both architectures (2 failures each) — not the bottleneck we expected

### The PipelineCoherence Surprise
Both architectures have only 2 PipelineCoherence failures. The silo problem hypothesis — that serial agents re-interpret from scratch — is not supported by the data. Either the agents are already building on each other reasonably well, or the PipelineCoherence evaluator isn't sensitive enough to detect subtle coherence issues. Worth investigating the 2 failing test cases to understand what coherence failure looks like.

### What Would Make Single Beat Serial?
Fix JSON formatting (6 failures → 0) and category routing (10 failures → ~5). The reasoning quality is already better. These are prompt fixes, not architectural changes.

### What Would Make Serial Beat Single?
Fix the Review prompt (53 failures → ~20). Serial already has better structural discipline. The Review prompt is the bottleneck for both architectures.

---

## How to Update This Doc

After each comparative eval run:
1. Update the metrics under the relevant architecture section
2. Add new observations to Cross-Architecture Observations
3. If a prompt change is made, note what changed and whether it helped
4. Keep the Prompt Needs sections current — remove items that have been addressed, add new ones discovered
