# CalledIt — Architecture Diagrams

GenAI portfolio reference · Strands GraphBuilder + HITL Improvement Loop + EventBridge Verification

---

## Diagram 1: Runtime Request Flow

What happens when a user submits a prediction — from browser through the GraphBuilder pipeline, ReviewAgent, and HITL improvement loop

```mermaid
sequenceDiagram
    participant Browser as 🌐 Browser
    participant APIGW as ☁️ API Gateway<br/>WebSocket
    participant Lambda as λ strands_make_call_graph.py
    participant Graph as GraphBuilder<br/>prediction_graph.py
    participant Parser as 🔍 Parser Agent<br/>(Claude 3.5 Sonnet)
    participant Cat as 🏷️ Categorizer Agent<br/>(Claude 3.5 Sonnet)
    participant VB as 🔨 Verification Builder<br/>(Claude 3.5 Sonnet)
    participant Bedrock as 🤖 Amazon Bedrock
    participant Review as 🔎 ReviewAgent<br/>(Claude 3.5 Sonnet)

    Browser->>APIGW: WS connect + submit prediction
    APIGW->>Lambda: $default event {action, prompt, timezone}

    Lambda->>APIGW: {type: "status", status: "processing"}
    APIGW->>Browser: Processing message

    Lambda->>Graph: execute_prediction_graph(prompt, timezone, datetime)

    Note over Graph,VB: GraphBuilder automatic context propagation

    Graph->>Parser: initial prompt (prediction + datetime + timezone)
    Parser->>Bedrock: invoke with @tool parse_relative_date
    Bedrock-->>Parser: {prediction_statement, verification_date, date_reasoning}
    Parser-->>Graph: Parser output in state

    Graph->>Cat: original prompt + Parser state
    Cat->>Bedrock: pure reasoning, no tools
    Bedrock-->>Cat: {verifiable_category, category_reasoning}
    Cat-->>Graph: Categorizer output in state

    Graph->>VB: original prompt + Parser state + Categorizer state
    VB->>Bedrock: pure reasoning, no tools
    Bedrock-->>VB: {verification_method: {source, criteria, steps}}
    VB-->>Graph: Verification Builder output in state

    Graph-->>Lambda: MultiAgentResult with all node outputs

    Lambda->>Lambda: parse_graph_results() → extract JSON from each node
    Lambda->>Review: review_prediction(complete response)
    Review->>Bedrock: meta-analysis — which sections are improvable?
    Bedrock-->>Review: {reviewable_sections: [{section, improvable, questions, reasoning}]}

    Lambda->>APIGW: {type: "call_response", content: full structured response}
    APIGW->>Browser: Prediction + verifiability category + verification method

    Lambda->>APIGW: {type: "complete"}
    APIGW->>Browser: Done

    Note over Browser,Review: HITL Improvement Loop (separate improve_call Lambda)

    Browser->>APIGW: {action: "request_questions", section: "prediction_statement"}
    APIGW->>Lambda: improve_call Lambda
    Lambda->>Review: ask_improvement_questions(section, questions)
    Review-->>Lambda: friendly formatted questions
    Lambda->>APIGW: {type: "improvement_questions", data: {section, questions}}
    APIGW->>Browser: Questions displayed to user

    Browser->>APIGW: {action: "submit_improvements", section, user_input, original_response}
    APIGW->>Lambda: improve_call Lambda
    Lambda->>Review: regenerate_section(section, original_value, user_input, context)
    Review->>Bedrock: regenerate with cascade logic
    Bedrock-->>Review: updated section value
    Lambda->>APIGW: {type: "improved_response", data: improvement_result}
    APIGW->>Browser: Updated prediction displayed

    alt change_type == "significant"
        Lambda->>Review: review_call_response(updated_response)
        Review->>Bedrock: re-analyze for further improvements
        Lambda->>APIGW: {type: "review_complete", data: new_review}
        APIGW->>Browser: New improvable sections offered
    end
```

> **Key insight:** The GraphBuilder handles context propagation automatically — each agent receives the original task plus all prior agents' outputs without manual state management. The ReviewAgent sits outside the graph as a fourth meta-analysis agent. The HITL loop runs in a separate Lambda (`improve_call.py`) triggered by distinct WebSocket actions.

---

## Diagram 2: Module Dependency Graph

How the files import each other across the two Lambda functions

```mermaid
graph TD
    subgraph MakeCall["λ strands_make_call — Prediction Pipeline Lambda"]
        SH["strands_make_call_graph.py
        ─────────────────────
        • lambda_handler() entry point
        • WebSocket event routing
        • Streaming callback handler
        • Calls execute_prediction_graph()
        • Calls ReviewAgent for meta-analysis"]

        PG["prediction_graph.py
        ─────────────────────
        • GraphBuilder setup
        • create_prediction_graph()
        • execute_prediction_graph()
        • parse_graph_results()
        • extract_json_from_text()
        • Singleton: prediction_graph"]

        GS["graph_state.py
        ─────────────────────
        • PredictionGraphState (TypedDict)
        • VerificationMethod (TypedDict)
        • ReviewableSection (TypedDict)
        • State schema for all agents"]

        subgraph Agents["Pipeline Agent Modules"]
            PA["parser_agent.py
            • create_parser_agent()
            • @tool parse_relative_date
            • @tool current_time (strands_tools)
            • PARSER_SYSTEM_PROMPT"]

            CA["categorizer_agent.py
            • create_categorizer_agent()
            • No tools (pure reasoning)
            • 5 verifiability categories
            • CATEGORIZER_SYSTEM_PROMPT"]

            VBA["verification_builder_agent.py
            • create_verification_builder_agent()
            • No tools (pure reasoning)
            • Builds source/criteria/steps
            • VERIFICATION_BUILDER_SYSTEM_PROMPT"]
        end

        RA["review_agent.py
        ─────────────────────
        • ReviewAgent class
        • review_prediction()
        • generate_improvement_questions()
        • regenerate_section()
        • Cascade logic for prediction_statement"]

        UT["utils.py
        • get_current_datetime_in_timezones()
        • convert_local_to_utc()"]
    end

    subgraph ImproveCall["λ improve_call — HITL Improvement Lambda"]
        IC["improve_call.py
        ─────────────────────
        • lambda_handler()
        • action: request_questions
        • action: submit_improvements
        • Conditional re-review trigger"]
    end

    subgraph Verification["λ verify_predictions — EventBridge Lambda"]
        VP["verify_predictions.py
        • PredictionVerificationRunner
        • Scans DDB for pending predictions
        • Runs verification batch"]

        VA["verification_agent.py
        • PredictionVerificationAgent
        • Executes verification_method steps
        • Returns TRUE/FALSE/INCONCLUSIVE"]

        DDB2["ddb_scanner.py
        • query_pending_predictions()"]

        EN["email_notifier.py
        • Notifies user of result"]
    end

    subgraph AWS["AWS Services"]
        BED["🤖 Amazon Bedrock
        (Claude 3.5 Sonnet)"]
        DDB["🗄️ DynamoDB"]
        EB["⏰ EventBridge
        (scheduled trigger)"]
    end

    SH -->|"calls"| PG
    SH -->|"calls"| RA
    SH -->|"calls"| UT
    PG -->|"imports"| PA
    PG -->|"imports"| CA
    PG -->|"imports"| VBA
    PG -->|"uses schema"| GS

    IC -->|"imports"| RA

    PA & CA & VBA & RA -->|"Strands Agent SDK"| BED
    VA -->|"Strands Agent SDK"| BED

    VP -->|"imports"| VA
    VP -->|"imports"| DDB2
    VP -->|"imports"| EN
    DDB2 -->|"boto3"| DDB
    SH -->|"boto3"| DDB

    EB -->|"triggers on prediction date"| VP
```

> **Key insight:** Two separate Lambdas handle two distinct workflows — the GraphBuilder pipeline (initial prediction processing) and the HITL improvement loop. A third EventBridge-triggered Lambda runs verification on the prediction date using the machine-executable instructions the Verification Builder produced. The graph is compiled once as a module-level singleton in `prediction_graph.py` and reused on warm invocations.

---

## Diagram 3: Full System Flow — Prediction Lifecycle

From user submission through improvement loop to eventual verification on prediction date

```mermaid
flowchart TD
    SUBMIT["User submits prediction
    (natural language)"]

    SUBMIT --> GRAPH["GraphBuilder Pipeline
    ────────────────────
    strands_make_call Lambda"]

    GRAPH --> PARSER["🔍 Parser Agent
    ────────────────────
    Extracts exact prediction text
    @tool parse_relative_date
    @tool current_time
    → prediction_statement
    → verification_date
    → date_reasoning"]

    PARSER -->|"full state propagated"| CATEG["🏷️ Categorizer Agent
    ────────────────────
    Classifies verifiability
    No tools — pure reasoning
    → verifiable_category
    → category_reasoning"]

    CATEG -->|"full state propagated"| VB["🔨 Verification Builder
    ────────────────────
    Builds verification plan
    No tools — pure reasoning
    → source (list)
    → criteria (list)
    → steps (list)"]

    VB --> REVIEW["🔎 ReviewAgent (meta-analysis)
    ────────────────────
    Analyzes complete pipeline output
    Identifies improvable sections
    Generates targeted questions
    → reviewable_sections"]

    REVIEW --> BROWSER["Browser displays:
    • Structured prediction
    • Verifiability category
    • Verification method
    • Improvable sections (clickable)"]

    BROWSER --> IMPROVE{User wants
    to improve?}

    IMPROVE -->|"No"| SAVE["Save to DynamoDB
    status: pending
    verification_date stored"]

    IMPROVE -->|"Yes — clicks section"| QUESTIONS["improve_call Lambda
    ────────────────────
    ReviewAgent generates
    friendly questions for section"]

    QUESTIONS --> ANSWER["User answers questions"]

    ANSWER --> REGEN["ReviewAgent regenerates section
    ────────────────────
    prediction_statement → cascades to
    verification_date + verification_method
    Other fields → targeted update"]

    REGEN --> SIGNIFICANT{Significant
    change?}

    SIGNIFICANT -->|"No"| BROWSER
    SIGNIFICANT -->|"Yes"| REVIEW

    SAVE --> CATCHECK{verifiable_category?}

    CATCHECK -->|"human_verifiable_only"| HUMAN["User manually verifies
    on prediction date"]

    CATCHECK -->|"agent_verifiable
    api_tool_verifiable
    strands_tool_verifiable
    current_tool_verifiable"| EVENTBRIDGE["EventBridge trigger
    fires on verification_date"]

    EVENTBRIDGE --> VERAGENT["🤖 Verification Agent
    ────────────────────
    Executes verification_method steps
    against real-world data sources
    → TRUE / FALSE / INCONCLUSIVE"]

    VERAGENT --> EMAIL["Email notifier
    sends result to user"]
```

> **Notice:** The verifiability category set by the Categorizer Agent directly determines the end-of-lifecycle path — human verification vs. autonomous agent verification. This is the design decision that makes agent-verifiable predictions genuinely useful: the Verification Builder writes machine-executable instructions specifically so the verification agent can run them without human involvement. The HITL improvement loop exists precisely to give users the chance to make a prediction more specific before it gets locked in — improving the chance the verification agent can resolve it autonomously.

---

## Proposed v2 Architecture

Redesign replacing the current separate-Lambda HITL loop with a single unified graph, stateful round-trip refinement, and parallel branch delivery.

### Key design changes from v1

**1. ReviewAgent joins the graph as a parallel branch**
Rather than running outside the graph in a separate invocation, ReviewAgent becomes a fourth node in the graph, executing in parallel after the pipeline completes. The first three agents' JSON is returned to the client immediately via WebSocket as soon as they finish. ReviewAgent's meta-analysis arrives as a second push when ready. The human has a usable result from round one without waiting for review.

**2. Full graph re-trigger on clarification (replaces improve_call Lambda)**
When the user provides clarification, the entire graph re-runs with the accumulated state. The separate `improve_call` Lambda and its hardcoded cascade logic (`regenerate_section()`) are eliminated. Agents decide for themselves whether new information requires them to update their previous output.

**3. Stateful PredictionGraphState carries full round history**
The state schema gains three new fields:
- `round` — integer, increments with each re-trigger
- `user_clarifications` — list of strings, accumulates across all rounds so round 3 agents see what was clarified in rounds 1 and 2
- Previous agent outputs pre-populated in initial state for round 2+

Each agent's system prompt instructs: "You are refining a prediction. Your previous output is in the state. Review it in light of any new clarifications — confirm it if it stands, update it if the new information makes a more precise version possible. We are iterating toward greater specificity with each round."

**4. Human can submit at any time**
The first-round result is complete and submittable immediately. Clarification rounds are opportunity, not gate. The user can choose zero, one, or multiple refinement cycles before submitting.

**5. Social media blast remains deterministic at pipeline end**
Unchanged from v1 — once a prediction is verified correct, the blast is a deterministic post-pipeline step.

---

### v2 Diagram 1: Unified Graph with Parallel Branch

```mermaid
sequenceDiagram
    participant Browser as Browser
    participant APIGW as API Gateway WebSocket
    participant Lambda as strands_make_call
    participant Graph as GraphBuilder v2
    participant Parser as Parser Agent
    participant Cat as Categorizer Agent
    participant VB as Verification Builder
    participant Review as ReviewAgent
    participant Bedrock as Amazon Bedrock

    Browser->>APIGW: submit prediction (natural language)
    APIGW->>Lambda: {prompt, timezone, round, user_clarifications, prev_state}

    Lambda->>Graph: execute_graph(enriched_state)

    Note over Graph,VB: Pipeline branch — sequential with state propagation

    Graph->>Parser: state {prompt, round, clarifications, prev_parser_output}
    Parser->>Bedrock: refine or confirm previous output
    Bedrock-->>Parser: prediction_statement + verification_date
    Parser-->>Graph: updated parser output

    Graph->>Cat: state + parser output
    Cat->>Bedrock: refine or confirm category
    Bedrock-->>Cat: verifiable_category
    Cat-->>Graph: updated categorizer output

    Graph->>VB: state + parser + categorizer output
    VB->>Bedrock: refine or confirm verification plan
    Bedrock-->>VB: verification_method
    VB-->>Graph: updated VB output

    Graph->>Lambda: pipeline complete — first three agents done
    Lambda->>APIGW: {type: "prediction_ready", data: pipeline_json}
    APIGW->>Browser: Structured prediction displayed — submittable now

    Note over Graph,Review: Review branch — parallel, delivers when ready

    Graph->>Review: full pipeline state
    Review->>Bedrock: meta-analysis of complete output
    Bedrock-->>Review: reviewable_sections
    Graph->>Lambda: review complete
    Lambda->>APIGW: {type: "review_ready", data: reviewable_sections}
    APIGW->>Browser: Improvable sections offered

    alt User chooses to clarify
        Browser->>APIGW: {action: "clarify", user_input, current_state}
        APIGW->>Lambda: re-trigger with round+1 + accumulated clarifications
        Lambda->>Graph: execute_graph(enriched_state with full history)
        Note over Graph,Review: Full graph re-runs — agents refine, not restart
    end

    alt User chooses to submit
        Browser->>APIGW: {action: "submit", prediction}
        Lambda->>DDB: save prediction, status: pending
    end
```

---

### v2 Diagram 2: State Schema Evolution Across Rounds

```mermaid
flowchart LR
    subgraph Round1["Round 1 — Initial State"]
        R1["prompt: raw user input
        round: 1
        user_clarifications: []
        prev_parser_output: null
        prev_categorizer_output: null
        prev_vb_output: null"]
    end

    subgraph Round2["Round 2 — After First Clarification"]
        R2["prompt: original
        round: 2
        user_clarifications: [clarification_1]
        prev_parser_output: {round 1 result}
        prev_categorizer_output: {round 1 result}
        prev_vb_output: {round 1 result}"]
    end

    subgraph Round3["Round 3 — After Second Clarification"]
        R3["prompt: original
        round: 3
        user_clarifications: [clarification_1, clarification_2]
        prev_parser_output: {round 2 result}
        prev_categorizer_output: {round 2 result}
        prev_vb_output: {round 2 result}"]
    end

    Round1 -->|user clarifies| Round2
    Round2 -->|user clarifies again| Round3
    Round1 -->|user submits| SAVE["DynamoDB — prediction saved"]
    Round2 -->|user submits| SAVE
    Round3 -->|user submits| SAVE
```

> **Key insight:** Each round the agents receive the full history of what was decided before and what the user has added. They are not re-doing prior work — they are standing on it. A prediction that starts vague becomes progressively more precise and verifiable with each cycle, and each agent only updates its section if the new information makes a better version possible.

---

### v2 Change Summary

| | v1 | v2 |
|---|---|---|
| ReviewAgent location | Outside graph, separate invocation | Inside graph, parallel branch |
| HITL mechanism | Separate `improve_call` Lambda | Full graph re-trigger |
| Cascade logic | Hardcoded in `regenerate_section()` | Agent judgment from accumulated state |
| State across rounds | Not preserved — regenerate from scratch | Full history in PredictionGraphState |
| Client delivery | Single response after all agents complete | Two pushes: pipeline first, review when ready |
| Clarification cycles | Bounded by `improve_call` design | Unlimited — each round enriches the state |
