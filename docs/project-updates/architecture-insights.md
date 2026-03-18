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

### Key Metrics (Run 9 — best serial config)
- Pass rate: 40% | IP: 0.80 | CMA: 0.73
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
- Overall pass rate much lower (16% vs 40%) — driven by structural/formatting failures, not reasoning quality
- Slower execution — one long conversation vs parallel-ish agent calls

### Prompt Needs
- Stronger JSON output discipline: "Return ONLY raw JSON, no markdown fences, no commentary"
- Explicit output schema validation instructions for each conversation turn
- Consider a JSON repair step after each turn (parse, validate, fix) rather than relying on the model to get it right
- Category routing instructions need to be as precise as the dedicated categorizer's prompt

### Key Metrics (Run 13 — first full single run)
- Pass rate: 16% | IP: 0.80 | CMA: 0.77 | Verification-Builder-centric: 0.50
- auto_v: 71% | auto_m: 79% | human: 82%

---

## Swarm (not yet implemented)

Backlog item 2. Expected to test collaborative multi-round processing. The PipelineCoherence evaluator will be especially interesting here — swarm agents share context differently than serial or single.

---

## Cross-Architecture Observations

### The Reasoning vs Formatting Tradeoff
The single agent reasons better (CMA +0.04) but formats worse (JSON validity -10%, category accuracy -29%). This suggests the serial graph's advantage isn't in reasoning quality — it's in structural discipline. Each serial agent has a narrow, focused prompt that produces clean output. The single agent has a broader prompt that produces better reasoning but less disciplined formatting.

### Implication for Prompt Strategy
- Serial prompts should focus on coherence (building on predecessors) — the formatting is already good
- Single prompts should focus on output discipline — the reasoning is already good
- These are independent improvements. Neither architecture needs to copy the other's approach.

### The PipelineCoherence Question
We don't yet have PipelineCoherence scores from a full run with all 6 judges on both architectures. Run 13 had the judges but we need to check if PipelineCoherence data is in the report. This is the key metric for the silo problem hypothesis.

### What Would Make Single Beat Serial?
If the single agent's JSON formatting issues are fixed (bringing structural pass rates up to serial's level), the single agent would likely score higher overall because its reasoning quality is already better. The fix is probably a 30-minute prompt iteration, not an architectural change.

### What Would Make Serial Beat Single?
If the serial graph's coherence problem is fixed (agents building on each other), the serial graph could match or exceed the single agent's reasoning quality while keeping its structural discipline advantage. This is a harder fix — it requires changes to how the graph propagates context between nodes.

---

## How to Update This Doc

After each comparative eval run:
1. Update the metrics under the relevant architecture section
2. Add new observations to Cross-Architecture Observations
3. If a prompt change is made, note what changed and whether it helped
4. Keep the Prompt Needs sections current — remove items that have been addressed, add new ones discovered
