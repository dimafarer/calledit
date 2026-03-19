# Eval Run Log

Append-only log of every eval run. Each entry captures: what changed, key metrics, insights, and next actions. Scan this to understand the eval history without reading full project update narratives.

---

## Run 1 — March 15, 14:50
- **Config:** dataset v2.0, prompts DRAFT/DRAFT/DRAFT/DRAFT, no judge, serial
- **Pass rate:** 68% | auto_v: 100% | auto_m: 93% | human: 76%
- **What changed:** First v2 dataset run, deterministic evaluators only
- **Insight:** Baseline established. Deterministic-only pass rate looks good but doesn't catch reasoning quality issues.

## Run 2 — March 15, 18:07
- **Config:** dataset v2.0, prompts DRAFT/DRAFT/DRAFT/DRAFT, judge, serial
- **Pass rate:** 51% | auto_v: 100% | auto_m: 100% | human: 82%
- **What changed:** Added Opus 4.6 LLM judge
- **Insight:** Judge drops pass rate from 68% to 51%. Proves the judge catches real quality issues that deterministic evaluators miss. The 17% gap is the "reasoning quality tax."

## Run 3 — March 15, 19:26
- **Config:** dataset v2.0, prompts DRAFT/2/DRAFT/DRAFT, judge, serial
- **Pass rate:** 38% | auto_v: 100% | auto_m: 71% | human: 88%
- **What changed:** Categorizer v2 (expanded human_only definition)
- **Insight:** human_only improved but automatable regressed hard (100% → 71%). The expanded definition is too aggressive — it's pulling automatable predictions into human_only.

## Run 4 — March 15, 23:49
- **Config:** dataset v2.0, prompts 1/2/1/1, judge, serial
- **Pass rate:** 35% | auto_v: 100% | auto_m: 86% | human: 94%
- **What changed:** Pinned all prompts to numbered versions (no more DRAFT)
- **Insight:** DDB float fix applied. Proper version tracking now in place. Automatable recovered partially from Run 3's regression.

## Run 5 — March 16, 21:41
- **Config:** dataset v3.0, prompts 1/2/1/1, judge, serial
- **Pass rate:** 34% | auto_v: 100% | auto_m: 86% | human: 100%
- **What changed:** Dataset v3 with verification criteria ground truth. New evaluators: IntentPreservation, CriteriaMethodAlignment
- **Insight:** New evaluators added but scores not yet tracked in summary. human_only hit 100%.

## Run 6 — March 16, 23:50
- **Config:** dataset v3.0, prompts 1/1/1/1, judge, serial
- **Pass rate:** 34% | auto_v: 100% | auto_m: 86% | human: 82%
- **What changed:** Categorizer reverted to v1 (testing v1 vs v2 effect)
- **Insight:** Reverting categorizer didn't change overall pass rate (still 34%). human_only dropped from 100% to 82%. Categorizer v2 is better for human_only but worse for automatable.

## Run 7 — March 17, 14:24
- **Config:** dataset v3.1, prompts 1/2/1/1, judge, serial
- **Pass rate:** 32% | auto_v: 100% | auto_m: 71% | human: 88%
- **IP:** 0.69 | **CMA:** 0.67
- **What changed:** Dataset v3.1 (7 subjective ground truth fixes)
- **Insight:** New baseline for Verification Builder iteration. IP and CMA now tracked. Both below 0.80 target.

## Run 8 — March 17, 16:14
- **Config:** dataset v3.1, prompts 1/2/2/1, judge, serial
- **Pass rate:** 35% | auto_v: 100% | auto_m: 71% | human: 94%
- **IP:** 0.82 | **CMA:** 0.74
- **What changed:** Verification Builder v2 (operationalization + specificity matching)
- **Insight:** IP passed the 0.80 target (+0.13 from Run 7). CMA improved but still below 0.80. The Verification Builder now operationalizes vague terms into measurable conditions.
- **Next:** Iterate on Review prompt to see if it affects CMA.

## Run 9 — March 17, 19:24
- **Config:** dataset v3.1, prompts 1/2/2/2, judge, serial
- **Pass rate:** 40% | auto_v: 100% | auto_m: 71% | human: 94%
- **IP:** 0.80 | **CMA:** 0.73
- **What changed:** Review v2 (operationalization validation questions)
- **Insight:** +4.4% overall from Review prompt alone. IP held steady (Verification Builder v2 gains stable). CMA flat — expected since Review doesn't directly affect Verification Builder method quality.
- **Next:** Per-agent evaluators needed to pinpoint where method quality breaks down.

## Run 10 — March 17, 23:41
- **Config:** dataset v3.1, prompts 1/2/2/2, judge, serial (1 prediction only)
- **IP:** 0.90 | **CMA:** 0.70
- **What changed:** Spec 10 smoke test — first run with all 6 per-agent judges + Verification-Builder-centric score
- **Insight:** All 6 judges fired successfully. Verification-Builder-centric composite score computed. Ready for full runs.

## Run 11 — March 18, 00:15
- **Config:** dataset v3.1, prompts 1/2/2/2, no judge, serial (1 prediction)
- **Pass rate:** 100%
- **What changed:** Serial backend smoke test (model_id wiring validation)
- **Insight:** Validated model override threading works correctly.

## Run 12 — March 18, 00:42
- **Config:** dataset v3.1, prompts 1/2/2/2, no judge, single (1 prediction)
- **Pass rate:** 100%
- **What changed:** First single-agent backend run (multi-prompt conversation)
- **Insight:** Single backend works. Same prompts from Prompt Management delivered as conversation turns.

## Run 13 — March 18, 16:01 ⭐ First full architecture comparison
- **Config:** dataset v3.1, prompts 1/2/2/2, judge, single (full 68 predictions)
- **Pass rate:** 16% | auto_v: 71% | auto_m: 79% | human: 82%
- **IP:** 0.80 | **CMA:** 0.77 | **Verification-Builder-centric:** 0.50
- **What changed:** First full single-agent run with all judges. Compare against Run 9 (serial, same config).
- **Insight:** 
  - IP identical to serial (0.80) — both architectures preserve intent equally well
  - CMA better on single (0.77 vs 0.73) — single agent produces better verification methods
  - Overall pass rate much worse (16% vs 40%) — single agent fails on structural/formatting evaluators
  - Parser JSON validity 90% (vs ~100% serial) — single agent is sloppy with JSON output format
  - auto_verifiable dropped from 100% to 71% — category routing is less precise on single
  - The single agent reasons better but formats worse. Two separate problems, two separate fixes.
- **Next:** 
  - Serial: improve coherence (agents building on each other instead of re-interpreting)
  - Single: tighten JSON output discipline in the prompt
  - Launch dashboard to visualize the per-evaluator breakdown side by side

---

## How to Use This Log

After every eval run, append an entry with:
1. Run number and timestamp
2. Config (dataset, prompts, judge yes/no, architecture)
3. Key metrics (pass rate, per-category, IP, CMA, Verification-Builder-centric score)
4. What changed (exactly one variable per Decision 50)
5. Insight (what the numbers tell us)
6. Next (what to do based on the insight)

## Run 14 — March 18, 20:35 ⭐ Serial re-run with all 6 judges
- **Config:** dataset v3.1, prompts 1/2/2/2, judge, serial (full 68 predictions)
- **Pass rate:** 25% | auto_v: 100% | auto_m: 71% | human: 94%
- **IP:** 0.78 | **CMA:** 0.75 | **Verification-Builder-centric:** 0.50
- **What changed:** Re-run of Run 9 config with all 6 per-agent judges (Run 9 only had 2 judges)
- **Insight:**
  - Pass rate dropped from Run 9's 40% to 25% — the 4 new per-agent judges are catching issues the old evaluators missed
  - IP dropped slightly from 0.80 to 0.78 — model non-determinism, within noise range
  - CMA improved slightly from 0.73 to 0.75 — also within noise range
  - Verification-Builder-centric score: 0.50 (same as single backend Run 13)
  - auto_verifiable still 100% — serial graph nails these consistently
  - Now have true apples-to-apples comparison with Run 13 (single, same config, same judges)
- **Comparison with Run 13 (single):**
  - Pass rate: serial 25% vs single 16% — serial still wins on structural discipline
  - IP: serial 0.78 vs single 0.80 — single slightly better at intent preservation
  - CMA: serial 0.75 vs single 0.77 — single slightly better at method quality
  - Verification-Builder-centric: both 0.50 — identical composite score
  - auto_verifiable: serial 100% vs single 71% — serial much better at category routing
  - PipelineCoherence data now available for serial — check report for silo problem quantification
- **Next:** Run compare_runs.py with both full-judge reports to see per-evaluator failure breakdown on serial
