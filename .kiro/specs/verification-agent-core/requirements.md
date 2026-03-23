# Requirements Document — Spec V4-5a: Verification Agent Core

## Introduction

Build the second AgentCore runtime for CalledIt v4: the Verification Agent. This agent runs at `verification_date` to determine whether a prediction came true. It receives a `prediction_id`, loads the prediction bundle from DynamoDB, uses a Strands Agent with Browser + Code Interpreter + current_time tools to gather evidence, and produces a structured verdict (confirmed/refuted/inconclusive). The verdict and evidence are written back to DDB.

The verification agent is NOT user-facing. It runs in batch mode, triggered by EventBridge (V4-5b). The entrypoint is synchronous (`def handler`, not `async def`) and returns a JSON string — no streaming needed. This is a separate AgentCore project in `calleditv4-verification/` (Decision 105), following the one-agent-per-runtime pattern (Decision 86).

### What V4-5a Delivers
1. New AgentCore project `calleditv4-verification/` scaffolded with `agentcore create`
2. Synchronous entrypoint that receives `prediction_id`, loads bundle, runs verification, updates DDB, returns verdict
3. Strands Agent with Browser + Code Interpreter + current_time tools
4. Verification prompt from Bedrock Prompt Management
5. Structured verdict via Pydantic model (verdict, confidence, evidence, reasoning)
6. DDB update with verdict, evidence, timestamp, status change

### What V4-5a Does NOT Deliver
- EventBridge triggers (V4-5b)
- DDB GSI for status+date queries (V4-5b / backlog item 14)
- Memory integration (V4-6)
- Frontend display of verification results (V4-7)

### Key Decisions
- Decision 86: Two separate AgentCore runtimes (creation + verification)
- Decision 96: No mocks in tests
- Decision 104: Split into V4-5a (agent core) and V4-5b (triggers)
- Decision 105: Separate project directory `calleditv4-verification/`
- Decision 106: Minimal code duplication (~20 lines) over shared packages

## Glossary

- **Verification_Agent**: The Strands Agent running inside the verification AgentCore runtime. Uses Browser, Code Interpreter, and current_time tools to gather evidence and produce a verdict
- **Prediction_Bundle**: The structured JSON object in DynamoDB (PK=`PRED#{id}`, SK=`BUNDLE`) containing parsed_claim, verification_plan, verifiability_score, and all creation-time metadata
- **Verification_Plan**: The `verification_plan` field within the Prediction_Bundle, containing `sources`, `criteria`, and `steps` lists created by the Creation Agent
- **Verdict**: The structured output of the Verification_Agent: one of `confirmed`, `refuted`, or `inconclusive`
- **Evidence_Item**: A structured record of one piece of evidence gathered during verification, containing source URL/name, finding text, and which criterion it relates to
- **Verification_Result**: The complete Pydantic model output: verdict, confidence, evidence list, and reasoning
- **Bundle_Loader**: The module responsible for loading prediction bundles from DDB and writing verification results back
- **Prompt_Management**: Bedrock Prompt Management service storing the verification prompt as an immutable versioned resource

## Requirements

### Requirement 1: Project Scaffold

**User Story:** As a developer, I want a self-contained AgentCore project for the verification agent, so that it can be developed, tested, and deployed independently from the creation agent.

#### Acceptance Criteria

1. THE Verification_Agent project SHALL reside in `calleditv4-verification/` at the repository root, separate from `calleditv4/` (Decision 105)
2. THE project SHALL contain `src/main.py` (entrypoint), `src/models.py` (Pydantic models), `src/bundle_loader.py` (DDB operations), `tests/` directory, `pyproject.toml`, and `.bedrock_agentcore.yaml`
3. THE `.bedrock_agentcore.yaml` SHALL configure the project for `agentcore dev` and `agentcore launch` as a standalone AgentCore runtime
4. THE `pyproject.toml` SHALL declare dependencies on `strands-agents`, `strands-agents-tools`, `pydantic`, and `boto3`
5. THE project SHALL be runnable via `agentcore dev` for local testing and invocable via `agentcore invoke --dev` without depending on any files in `calleditv4/`

### Requirement 2: Bundle Loading

**User Story:** As the verification agent, I need to load the prediction bundle from DynamoDB by prediction_id, so that I have the verification plan, criteria, and sources needed to execute verification.

#### Acceptance Criteria

1. WHEN the entrypoint receives a payload with `prediction_id`, THE Bundle_Loader SHALL load the Prediction_Bundle from DynamoDB using key `PK=PRED#{prediction_id}`, `SK=BUNDLE`
2. IF the Prediction_Bundle does not exist for the given prediction_id, THEN THE Verification_Agent SHALL return an error result with a descriptive message and SHALL NOT invoke the Strands Agent
3. IF the Prediction_Bundle has a `status` other than `pending`, THEN THE Verification_Agent SHALL return an error result indicating the prediction has already been processed and SHALL NOT invoke the Strands Agent
4. THE Bundle_Loader SHALL use the same DDB key format (`PK=PRED#{id}`, `SK=BUNDLE`) as the Creation Agent (Decision 106: ~20 lines of duplicated code, no shared package)
5. THE Bundle_Loader SHALL use `_convert_floats_to_decimal()` for any float-to-Decimal conversion needed for DDB writes, duplicated from the Creation Agent's `bundle.py`

### Requirement 3: Verification Execution

**User Story:** As the system, I want the verification agent to follow the verification plan using Browser and Code Interpreter tools, so that it gathers real evidence to determine whether the prediction came true.

#### Acceptance Criteria

1. THE Verification_Agent SHALL create a Strands Agent with model `us.anthropic.claude-sonnet-4-20250514-v1:0` and tools: AgentCore Browser, AgentCore Code Interpreter, and current_time
2. THE Verification_Agent SHALL fetch the verification prompt from Bedrock Prompt Management (prompt name: `calledit-verification-executor`) and use it as the agent's system prompt
3. THE Verification_Agent SHALL construct a user message containing the prediction statement, verification plan (sources, criteria, steps), and verification_date from the loaded Prediction_Bundle
4. THE Verification_Agent SHALL invoke the Strands Agent synchronously with `structured_output_model` set to the Verification_Result Pydantic model, so the verdict is type-safe and validated
5. IF Bedrock Prompt Management is unavailable, THEN THE Verification_Agent SHALL fail with a clear error and SHALL NOT fall back to a hardcoded prompt (consistent with AgentCore steering doc)

### Requirement 4: Verdict Model

**User Story:** As a developer, I want a well-defined Pydantic model for the verification verdict, so that the agent's output is type-safe, validated, and consistent across all predictions.

#### Acceptance Criteria

1. THE Verification_Result model SHALL have a `verdict` field constrained to one of: `confirmed`, `refuted`, `inconclusive`
2. THE Verification_Result model SHALL have a `confidence` field of type float, constrained to the range [0.0, 1.0]
3. THE Verification_Result model SHALL have an `evidence` field of type `List[Evidence_Item]`, where each Evidence_Item has fields: `source` (str — URL or source name), `finding` (str — what was found), `relevant_to_criteria` (str — which criterion this evidence addresses)
4. THE Verification_Result model SHALL have a `reasoning` field (str) explaining the verdict decision
5. ALL Pydantic model fields SHALL include `Field(description=...)` so Strands can generate accurate tool specifications, consistent with the Creation Agent's model pattern

### Requirement 5: DynamoDB Update

**User Story:** As the system, I want the verification result written back to the prediction bundle in DynamoDB, so that the verdict is persisted and the prediction status reflects the verification outcome.

#### Acceptance Criteria

1. WHEN verification completes with a `confirmed` or `refuted` verdict, THE Bundle_Loader SHALL update the Prediction_Bundle status from `pending` to `verified`
2. WHEN verification completes with an `inconclusive` verdict, THE Bundle_Loader SHALL update the Prediction_Bundle status from `pending` to `inconclusive`
3. THE DDB update SHALL write the following fields to the Prediction_Bundle: `verdict` (str), `confidence` (float as Decimal), `evidence` (list), `reasoning` (str), `verified_at` (ISO 8601 timestamp), and `prompt_versions.verification` (str — the prompt version used)
4. THE DDB update SHALL use a `ConditionExpression` of `attribute_exists(PK) AND #s = :pending` to prevent overwriting a bundle that was already verified or deleted between load and update
5. IF the `ConditionExpression` fails, THEN THE Bundle_Loader SHALL log the conflict and return the verdict without raising an exception — the verification result is still valid even if the DDB write was a no-op

### Requirement 6: Verification Prompt in Prompt Management

**User Story:** As a developer, I want the verification prompt managed in Bedrock Prompt Management alongside the creation prompts, so that prompt versioning, iteration, and eval are consistent across both agents.

#### Acceptance Criteria

1. THE CloudFormation template (`infrastructure/prompt-management/template.yaml`) SHALL include a new `AWS::Bedrock::Prompt` resource named `calledit-verification-executor`
2. THE prompt SHALL instruct the Verification_Agent to follow the verification plan steps, check the planned sources using Browser, evaluate against the planned criteria, and use Code Interpreter for calculations when needed
3. THE prompt SHALL instruct the Verification_Agent to produce a structured verdict with evidence items that reference specific criteria from the verification plan
4. THE prompt SHALL instruct the Verification_Agent to return `inconclusive` when the event has not yet occurred, evidence is contradictory, or sources are unavailable — rather than guessing
5. A new `AWS::Bedrock::PromptVersion` resource SHALL be created for the initial version of the verification prompt
6. THE prompt template SHALL accept input variables for the prediction statement, verification plan, and verification date, so the entrypoint can substitute bundle data at invocation time

### Requirement 7: Error Handling

**User Story:** As the system, I want the verification agent to never raise unhandled exceptions, so that a single failed verification does not crash the batch processing loop (V4-5b).

#### Acceptance Criteria

1. IF the Strands Agent raises any exception during verification, THEN THE Verification_Agent SHALL catch the exception, log it, and return an `inconclusive` verdict with confidence 0.0 and the exception message in the reasoning field
2. IF the DDB load fails (network error, permissions, throttling), THEN THE Verification_Agent SHALL log the error and return a JSON error response — it SHALL NOT attempt to invoke the Strands Agent
3. THE entrypoint handler SHALL be a synchronous function (`def handler`, not `async def`) that returns a JSON string containing the verdict or error — no streaming, no yielded events
4. THE entrypoint return value SHALL be a JSON string parseable by the caller (EventBridge trigger in V4-5b), containing at minimum: `prediction_id`, `verdict`, `confidence`, and `status` (success/error)
5. WHEN returning an inconclusive verdict due to an error, THE Verification_Agent SHALL still attempt the DDB update to record the inconclusive status — a failed DDB update after an error SHALL be logged but SHALL NOT raise
