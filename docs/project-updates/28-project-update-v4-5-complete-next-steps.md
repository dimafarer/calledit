# Project Update 28 — V4-5 Complete, Revised Execution Order

**Date:** March 24, 2026
**Context:** V4-5a integration tested, V4-5b implemented. Revised the remaining v4 execution order based on what we've learned.
**Audience:** Future self for project narrative; next agent for context pickup
**Git Commit:** Pending

### Referenced Kiro Specs
- `.kiro/specs/verification-agent-core/` — Spec V4-5a (COMPLETE + integration tested)
- `.kiro/specs/verification-triggers/` — Spec V4-5b (COMPLETE)

### Prerequisite Reading
- `docs/project-updates/27-project-update-v4-5-verification-agent-planning.md` — V4-5a/5b execution results

---

## What Happened This Session

### V4-5a Integration Testing
- Deployed verification executor prompt to Prompt Management (ID: `ZQQNZIP6SK`)
- Integration test 1 (Lakers prediction): 408s, Browser context overflow, agent recovered with inconclusive verdict, DDB updated correctly. Confirms Gateway + Brave Search needed for Phase 2.
- Integration test 2 ("test" prediction): 30s clean end-to-end. Inconclusive with 0.95 confidence. Full pipeline validated.
- All pipeline components confirmed working: DDB load → prompt fetch → agent invoke → structured output → DDB update → JSON return.

### V4-5b Implementation
- Promoted `verification_date` to top-level DDB attribute (prerequisite for GSI)
- Created and ran GSI setup script — `status-verification_date-index` ACTIVE on `calledit-db`
- Built scanner Lambda at `infrastructure/verification-scanner/` with dual invocation mode (HttpInvoker for dev, AgentCoreInvoker for prod)
- SAM template with EventBridge rate(15 minutes), Python 3.12 zip Lambda
- 170 tests passing across both agent projects (148 creation + 22 verification)

### Revised Execution Order (Decisions 107-110)

After reviewing what's complete and what's needed, the remaining v4 work is reordered. The original plan had Memory (V4-6) before cutover (V4-8). The revised order prioritizes getting the agents live first, then iterating with eval and memory.

**New order:**

1. **Deploy agents with `agentcore launch`** — Both creation and verification agents are integration tested and ready. Deploy them as AgentCore runtimes. Enable the verification scanner once the verification agent has an `AGENT_ID`.

2. **Frontend cutover** — Connect the React PWA (S3 + CloudFront) to the v4 AgentCore agents. This replaces the v3 Lambda backend. Downtime is acceptable — this is a demo project, not production SaaS. The frontend needs updates for v4 data shapes (strength indicator instead of categories, stream events instead of WebSocket messages).

3. **Eval framework update + baseline** — Adapt the eval framework and dashboard to work with the v4 AgentCore agents. Run a baseline eval against the golden dataset. This gives us a data-driven quality measurement before adding Memory.

4. **Memory integration + retest** — Add AgentCore Memory (STM for clarification rounds, LTM for user preferences and prediction facts). Rerun eval to measure the impact. Memory is additive — it makes the agents smarter but doesn't change the API contract or frontend integration.

**Rationale:** Memory (V4-6) was originally planned before cutover because the architecture doc described it as part of the creation agent's core flow. But the current implementation proves the HITL loop works without Memory — DDB bundles carry all the state needed for clarification rounds. Memory enrichment is an optimization, not a prerequisite. Getting the agents live and measured first gives us a baseline to compare against when Memory is added.

## Decisions Made

- **Decision 107:** Deploy agents before Memory integration. Both agents work end-to-end without AgentCore Memory. DDB bundles carry all state for clarification rounds and verification. Memory (STM + LTM) is additive — deploy first, add Memory second, measure the delta.

- **Decision 108:** Frontend cutover accepts downtime. The React PWA (S3 + CloudFront) will be pointed at v4 AgentCore agents, replacing the v3 Lambda backend. No blue/green deployment, no feature flags. Downtime during cutover is acceptable for a demo project.

- **Decision 109:** Eval baseline before Memory. Run the eval framework against the deployed v4 agents to establish a quality baseline. Then add Memory and rerun to measure improvement. This follows the isolated single-variable testing methodology (Decision 50).

- **Decision 110:** Scanner deploys with schedule disabled. The verification scanner SAM template deploys with `Enabled: false` on the EventBridge rule. Enable it after the verification agent is deployed via `agentcore launch` and the `VERIFICATION_AGENT_ID` is known.

## Revised Spec Mapping

| Step | Spec | Status |
|------|------|--------|
| 1. Deploy agents | V4-8a (AgentCore Launch) | NEW — needs spec |
| 2. Frontend cutover | V4-8b (Frontend Cutover) | NEW — needs spec |
| 3. Eval baseline | V4-7a (Eval Layer 1) | Existing — needs update for v4 |
| 4. Memory + retest | V4-6 (Memory Integration) | Existing — unchanged |

The original V4-8 (Production Cutover) is split into V4-8a (deploy agents) and V4-8b (frontend cutover) since they're now separate steps with the eval baseline in between.

## What the Next Agent Should Do

1. Spec and execute V4-8a: `agentcore launch` for both agents, enable scanner with agent ID
2. Spec and execute V4-8b: Frontend cutover (S3 + CloudFront → v4 agents)
3. Update V4-7a spec for v4 eval framework, run baseline
4. Execute V4-6 (Memory), rerun eval

### Key Files
- `calleditv4/` — Creation agent (ready for `agentcore launch`)
- `calleditv4-verification/` — Verification agent (ready for `agentcore launch`)
- `infrastructure/verification-scanner/` — Scanner Lambda (deploy with schedule disabled)
- `.kiro/steering/agentcore-architecture.md` — Architecture guardrails

### Test Counts
- 148 creation agent tests
- 22 verification agent tests
- 170 total, all passing
