# CalledIt: Creation → Verification Pipeline

How an ambiguous natural language prediction becomes a definitive, verifiable JSON bundle.

---

## The Core Contract

The system has two agents with a clear handoff:

1. **Creation Agent** — Takes ambiguous human language, resolves all ambiguity, produces a structured JSON prediction bundle with concrete dates, measurable criteria, and executable verification steps.

2. **Verification Agent** — Takes the structured bundle, executes the verification plan using web search tools, and produces a definitive verdict (confirmed/refuted/inconclusive).

The prediction bundle is the contract between them. If the creation agent produces a good bundle, the verification agent has everything it needs. If the bundle is ambiguous, the verification agent can't do its job.

---

## Stage 1: Ambiguous Input

User submits a natural language prediction:

```
"The Lakers will win their game tonight"
```

This is ambiguous in multiple ways:
- "tonight" — which date? Depends on when the user said it and their timezone
- "the Lakers" — which Lakers? (LA Lakers assumed, but not stated)
- "win" — regular season? playoffs? what counts as a win?
- "their game" — which specific game?

---

## Stage 2: Creation Agent (3-Turn Pipeline)

The creation agent runs three sequential LLM turns, each producing structured output via Pydantic models.

### Turn 1: Parse (ParsedClaim)

**Input:** Raw prediction + current datetime + user timezone
**Prompt:** `prediction_parser` (from Bedrock Prompt Management, version 2)
**Tools:** `current_time`, `code_interpreter` (for date math)

**Output:**
```json
{
  "statement": "The Lakers will win their game tonight",
  "verification_date": "2026-04-26T06:00:00Z",
  "date_reasoning": "Tonight refers to evening of April 25, 2026 PT. 
    Basketball games conclude by 11 PM PT = 06:00 UTC April 26."
}
```

The parser's job: resolve "tonight" to a concrete ISO 8601 datetime. This is the critical disambiguation step — after this, there's no ambiguity about *when* to verify.

### Turn 2: Plan (VerificationPlan)

**Input:** ParsedClaim + original prediction + tool manifest
**Prompt:** `verification_planner` (version 2)

**Output:**
```json
{
  "sources": ["ESPN.com", "NBA.com", "Yahoo Sports"],
  "criteria": [
    "The Los Angeles Lakers played a game on April 25, 2026",
    "The Lakers won (final score > opponent)",
    "The game is completed (not postponed/cancelled)"
  ],
  "steps": [
    "Navigate to ESPN NBA scoreboard for April 25, 2026",
    "Find Lakers game result",
    "Extract final score",
    "Verify Lakers score > opponent score",
    "Confirm game status is Final"
  ],
  "verification_mode": "at_date"
}
```

The planner's job: define *what* to check, *where* to check it, and *how* to check it. The criteria must be measurable and binary.

### Turn 3: Review (PlanReview)

**Input:** ParsedClaim + VerificationPlan + original prediction
**Prompt:** `plan_reviewer` (version 3)

**Output:**
```json
{
  "verifiability_score": 0.75,
  "score_tier": "high",
  "verifiability_reasoning": "Sports results are public data...",
  "dimension_assessments": [
    {"dimension": "criteria_specificity", "assessment": "strong"},
    {"dimension": "source_availability", "assessment": "strong"},
    {"dimension": "temporal_clarity", "assessment": "strong"},
    {"dimension": "outcome_objectivity", "assessment": "strong"},
    {"dimension": "tool_coverage", "assessment": "moderate"}
  ],
  "reviewable_sections": [
    {
      "section": "criteria",
      "improvable": true,
      "questions": ["Which Lakers team — LA Lakers or another?"],
      "reasoning": "Assumes LA Lakers but user didn't specify"
    }
  ],
  "verification_mode": "at_date"
}
```

The reviewer's job: score how likely the verification agent is to succeed, and flag assumptions that could be clarified with the user.

### Mode Resolution

If planner says `at_date` but reviewer says `immediate`, the reviewer wins (has more context from the full plan).

---

## Stage 3: Prediction Bundle (DynamoDB)

All three turns are assembled into a single bundle and saved to DynamoDB:

```json
{
  "PK": "PRED#pred-abc123",
  "SK": "BUNDLE",
  
  "prediction_id": "pred-abc123",
  "raw_prediction": "The Lakers will win their game tonight",
  "status": "pending",
  "created_at": "2026-04-25T14:00:00Z",
  
  "parsed_claim": {
    "statement": "The Lakers will win their game tonight",
    "verification_date": "2026-04-26T06:00:00Z",
    "date_reasoning": "..."
  },
  
  "verification_plan": {
    "sources": ["ESPN.com", "NBA.com"],
    "criteria": ["Lakers played on April 25", "Lakers won"],
    "steps": ["Check ESPN scoreboard", "Extract score", "Compare"],
    "verification_mode": "at_date"
  },
  
  "verifiability_score": 0.75,
  "score_tier": "high",
  "verification_mode": "at_date",
  "verification_date": "2026-04-26T06:00:00Z",
  
  "prompt_versions": {
    "prediction_parser": "2",
    "verification_planner": "2",
    "plan_reviewer": "3"
  }
}
```

This bundle is the complete, unambiguous specification of:
- **What** to verify (criteria)
- **When** to verify (verification_date)
- **How** to verify (steps + sources)
- **What mode** to use (at_date = check after the date arrives)

---

## Stage 4: Verification Agent

Triggered at `verification_date` (by EventBridge or eval runner).

### Input

Loads the bundle from DynamoDB and builds a prompt:

```
PREDICTION: The Lakers will win their game tonight
VERIFICATION DATE: 2026-04-26T06:00:00Z
VERIFICATION MODE: at_date

VERIFICATION PLAN:
Sources: ESPN.com, NBA.com
Criteria: Lakers played on April 25, Lakers won
Steps: Check ESPN scoreboard, Extract score, Compare

Execute this verification plan now.
```

### Execution

The agent uses tools to gather evidence:
- `brave_web_search` — searches for "Lakers game result April 25 2026"
- `code_interpreter` — date math if needed
- `current_time` — checks if verification_date has arrived

### Mode-Specific Rules

- **immediate**: Verify now, no date check needed
- **at_date**: If current_time < verification_date → return inconclusive (too early). If current_time >= verification_date → execute plan
- **before_date**: Can confirm early if event happened. Can only refute after deadline passes
- **recurring**: Append snapshot, don't overwrite previous results

### Output (VerificationResult)

```json
{
  "verdict": "confirmed",
  "confidence": 0.95,
  "evidence": [
    {
      "source": "ESPN.com",
      "finding": "Lakers 112, Rockets 105 — Final",
      "relevant_to_criteria": "Lakers won (score > opponent)"
    }
  ],
  "reasoning": "ESPN confirms Lakers defeated Rockets 112-105 on April 25."
}
```

### DynamoDB Update

Bundle updated with verdict, evidence, reasoning, and status changed to "verified".

---

## The Full Flow (Diagram)

```
┌─────────────────────────────────────────────────────────┐
│  USER INPUT                                             │
│  "The Lakers will win their game tonight"               │
│  timezone: America/Los_Angeles                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  CREATION AGENT (3 turns)                               │
│                                                         │
│  Turn 1 — PARSE                                         │
│  "tonight" → 2026-04-25T23:00:00 PT                    │
│  verification_date → 2026-04-26T06:00:00Z               │
│                                                         │
│  Turn 2 — PLAN                                          │
│  sources: [ESPN, NBA.com]                               │
│  criteria: [Lakers played, Lakers won]                  │
│  steps: [Check scoreboard, Extract score, Compare]      │
│  mode: at_date                                          │
│                                                         │
│  Turn 3 — REVIEW                                        │
│  verifiability_score: 0.75 (high)                       │
│  reviewable: "Which Lakers team?"                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  DYNAMODB — Prediction Bundle                           │
│                                                         │
│  PK: PRED#pred-abc123  SK: BUNDLE                       │
│  status: pending                                        │
│  verification_date: 2026-04-26T06:00:00Z                │
│  All parsed_claim, verification_plan, review fields     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │  [EventBridge fires at verification_date]
                       ▼
┌─────────────────────────────────────────────────────────┐
│  VERIFICATION AGENT                                     │
│                                                         │
│  1. Load bundle from DDB                                │
│  2. Check: current_time >= verification_date?           │
│     - No → return inconclusive (too early)              │
│     - Yes → proceed                                     │
│  3. Execute verification steps with tools               │
│     brave_web_search("Lakers game April 25 2026")       │
│  4. Map evidence to criteria                            │
│  5. Produce verdict: confirmed / refuted / inconclusive │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  DYNAMODB — Updated Bundle                              │
│                                                         │
│  verdict: "confirmed"                                   │
│  confidence: 0.95                                       │
│  evidence: [{source: "ESPN", finding: "Lakers 112..."}] │
│  status: "verified"                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

1. **The creation agent's job is disambiguation.** It takes "tonight" and produces "2026-04-26T06:00:00Z". It takes "the Lakers" and produces measurable criteria. After the creation agent runs, there should be zero ambiguity left.

2. **The bundle is the contract.** The verification agent never sees the raw prediction text in isolation — it always has the structured plan with concrete dates, sources, criteria, and steps.

3. **Mode rules are strict.** The verification agent follows mode-specific rules mechanically. For `at_date`, if the date hasn't arrived, it returns inconclusive — no exceptions. This prevents premature verdicts.

4. **Clarification closes gaps.** When the reviewer flags assumptions (e.g., "which Lakers team?"), the system can ask the user for clarification before finalizing the bundle. Each clarification round re-runs the full 3-turn pipeline with accumulated context.

5. **Prompts are versioned.** Every bundle records which prompt versions were used. This makes eval results reproducible — you can always trace a verdict back to the exact prompts that produced the bundle.

---

## Known Limitations

- **Time-relative predictions in static datasets**: Predictions like "tonight" or "tomorrow" get re-resolved every time the creation agent processes them. If the dataset was written weeks ago, "tonight" means a different night than intended. The new base-056 through base-060 predictions use explicit dates to avoid this.

- **Verification timing**: For `at_date` mode, the verification agent must run *after* the verification_date. If the eval runner invokes it too early, it correctly returns inconclusive — but this means a second pass is needed.

- **Tool availability**: The verification agent's ability to resolve predictions depends on its tools (brave_web_search, browser, code_interpreter). If a prediction requires a tool the agent doesn't have (e.g., flight tracking API), it returns inconclusive.
